"""
job_groupings_classifier.py

Assigns job grouping levels to job titles using a pre-built mapping CSV
(job_groupings_mapping.csv).  The mapping is generated once from the allowed
jobs SOT (allowed_jobs_sot.csv) and the grouping rules; admins can then edit
it directly to handle edge cases or add new titles.

When a (job_title, department) pair is not found in the mapping, an alert is
sent to a Slack webhook so an admin can review and update the mapping.

Workflow:
    1. Run once to build/refresh the mapping CSV:
           python job_groupings_classifier.py build-mapping

    2. Review and edit job_groupings_mapping.csv as needed.

    3. Classify a job at runtime:
           python job_groupings_classifier.py classify "Teacher" "Math"

    4. Classify every entry in the SOT:
           python job_groupings_classifier.py classify-sot

    5. Export a full permissions CSV (one row per job, boolean column per rule):
           python job_groupings_classifier.py export-permissions

    6. Regenerate the website data file from the permissions CSV:
           python job_groupings_classifier.py export-data-js

Environment variables:
    SLACK_WEBHOOK_URL   Incoming webhook for unmatched-job alerts (optional).

Requirements: Python 3.10+, no third-party packages.
"""

import csv
import json
import os
import re
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ── Paths ─────────────────────────────────────────────────────────────────────

_HERE = Path(__file__).parent
SOT_PATH = _HERE / 'allowed_jobs_sot.csv'
MAPPING_PATH = _HERE / 'job_groupings_mapping.csv'
PERMISSIONS_DESIGNATIONS_PATH = _HERE / 'permission_designations.csv'
PERMISSIONS_OUTPUT_PATH = _HERE / 'job_groupings_with_permissions.csv'
MAPPING_COLUMNS = ['Jobs', 'Departments', 'Grouping', 'Level', 'Confidence', 'Notes']

# ── Permissions per grouping ──────────────────────────────────────────────────
# Derived from the "Add-in Permissions Beyond Default" column in
# general_grouping_rules.csv.  Rule names match the "Rule Name" column in
# permission_designations.csv exactly.

GROUPING_PERMISSIONS: dict[str, set[str]] = {
    'Chief Level (1)': {
        'All Locations', 'All Staff/Students', 'Salary', 'PM Data', 'Survey Access',
    },
    'EDs, HOSs, MDOs (2)': {
        'All Locations in Region', 'All Staff/Students', 'Salary', 'PM Data', 'Survey Access',
    },
    'KTAF or Regional Managing Director (3)': {
        'All Locations', 'All Staff/Students', 'Salary', 'PM Data', 'Survey Access',
    },
    'School Leader (4)': {
        "User's School Only", 'All Staff/Students', 'Salary', 'PM Data', 'Survey Access',
    },
    'DSOs (4)': {
        "User's School Only", 'All Staff/Students', 'Salary', 'PM Data', 'Survey Access',
    },
    'KTAF or Regional Director (4)': {
        'All Locations', "User's Department Only", 'All Staff/Students',
        'Salary', 'PM Data', 'Survey Access',
    },
    'Assistant School Leaders (5)': {
        "User's School Only", 'Teachers & Students Only', 'Salary', 'PM Data', 'Survey Access',
    },
    # Levels 5b–7 receive no additional permissions beyond the system default
}


# ── Result type ───────────────────────────────────────────────────────────────

@dataclass
class GroupingResult:
    grouping_name: str
    level: Optional[int]         # 1–7, or None if unmatched
    confidence: str              # 'high', 'medium', 'low', 'unmatched'
    notes: str = field(default='')

    def __str__(self) -> str:
        lvl = str(self.level) if self.level is not None else '?'
        suffix = f'  [{self.notes}]' if self.notes else ''
        return f"{self.grouping_name} (level {lvl}, {self.confidence}){suffix}"


# ── Department taxonomy (used only during mapping generation) ─────────────────

CENTRAL_DEPARTMENTS: set[str] = {
    'accounting', 'administration and events', 'advocacy', 'compliance',
    'data', 'development', 'executive', 'facilities', 'finance', 'growth',
    'human resources', 'innovation', 'interns', 'leadership development',
    'marketing, comms, and enrollment', 'purchasing', 'race, equity, inclusion',
    'real estate', 'real estate and facilities', 'special projects',
    'talent acquisition', 'teacher development', 'teaching and learning',
    'technology',
    # School-support dept whose non-instructional staff follow KTAF rules
    'school support', 'student experience',
}

SCHOOL_DEPARTMENTS: set[str] = {
    'computer science', 'elementary', 'english', 'es specials', 'high',
    'history', 'math', 'middle', 'ms enrichment', 'music',
    'physical education', 'school leadership', 'science', 'social work',
    'special education', 'student support', 'visual and performing arts',
    'world languages', 'writing',
}

ADDITIONAL_WORK_DEPT = 'additional work assignment'

# ── Special designation departments ───────────────────────────────────────────
# Maps lowercase department names to the special designation rule name that
# applies to all staff in that department by default.  These align with the
# "Special" rule-type rows in permission_designations.csv.  Admins may grant
# or revoke these per-individual; these defaults reflect the typical expectation.
SPECIAL_DESIGNATION_DEPARTMENTS: dict[str, str] = {
    'data':            'Data Team',
    'human resources': 'HR Team',
    'accounting':      'Finance, Accounting, and Compliance Team',
    'finance':         'Finance, Accounting, and Compliance Team',
    'compliance':      'Finance, Accounting, and Compliance Team',
    'executive':       'CEO',
}

# Frontline school operations titles (Level 6 ADSOs/Ops-SOMs/AOMs/Receptionists)
FRONTLINE_OPS_TITLES: set[str] = {
    'operations coordinator',
    'school operations manager',
    'operations associate',
    'receptionist',
    'office manager',
    'associate director of school operations',   # ADSO
}

# Keyword patterns for school-based non-instructional staff (Level 6)
SCHOOL_NON_INSTRUCTIONAL_PATTERNS: list[str] = [
    r'\bparaprofessional\b', r'\baide\b', r'\bcustodian\b', r'\bporter\b',
    r'\bsecurity\b', r'\bcrossing guard\b', r'\bnurse\b', r'\bsocial worker\b',
    r'\bspeech language pathologist\b', r'\boccupational therapist\b',
    r'\blearning specialist\b', r'\blearning disabilities teacher\b',
    r'\bschool psychologist\b', r'\bbehavior (analyst|specialist)\b',
    r'\bcounselor\b', r'\bstudent support\b', r'\bacademic interventionist\b',
    r'\bsubstitute teacher\b', r'\bteacher aide\b', r'\bmental health counselor\b',
    r'\binstructional aide\b', r'\bcanvasser\b',
]


# ── Rule engine (mapping generation only) ────────────────────────────────────

def _classify_by_rules(job_title: str, department: str) -> GroupingResult:
    """
    Derive a grouping from title + department using the general grouping rules.
    This is called once during mapping generation, not at classification time.
    """
    t = job_title.strip().lower()
    d = department.strip().lower()

    def hit(name: str, level: int, notes: str = '') -> GroupingResult:
        return GroupingResult(name, level, 'high', notes)

    def maybe(name: str, level: int, notes: str) -> GroupingResult:
        return GroupingResult(name, level, 'medium', notes)

    # ── Level 7: Interns + temporary extra-duty assignments ──────────────────
    if re.match(r'^intern\b', t):
        return hit('Intern (7)', 7)

    if d == ADDITIONAL_WORK_DEPT:
        return GroupingResult(
            'Intern (7)', 7, 'medium',
            'Temporary/additional assignment; treated as Level 7'
        )

    # ── Level 1: Chiefs and Co-Presidents ────────────────────────────────────
    if re.match(r'^chief\b', t) or t == 'co-president':
        return hit('Chief Level (1)', 1)

    # ── Level 2: Executive Directors, Heads of Schools, MDOs ─────────────────
    if re.search(r'\bexecutive director\b', t):
        return hit('EDs, HOSs, MDOs (2)', 2)

    if re.match(r'^(deputy )?head of schools?( in residence)?$', t):
        return hit('EDs, HOSs, MDOs (2)', 2)

    if re.match(r'^managing director of (school )?operations$', t):
        return hit('EDs, HOSs, MDOs (2)', 2)

    if re.match(r'^managing director of growth$', t):
        return hit('EDs, HOSs, MDOs (2)', 2)

    # ── Level 3: KTAF/Regional Managing Directors and Deputy Chiefs ───────────
    if re.match(r'^managing director\b', t):
        if d in CENTRAL_DEPARTMENTS:
            return hit('KTAF or Regional Managing Director (3)', 3)
        return maybe(
            'KTAF or Regional Managing Director (3)', 3,
            f'Managing Director in "{department}" — verify region vs school scope'
        )

    if re.match(r'^deputy\b', t):
        if d == 'executive':
            return hit('EDs, HOSs, MDOs (2)', 2)
        return maybe(
            'KTAF or Regional Managing Director (3)', 3,
            f'Deputy in "{department}" — may be Level 2 or 3; review seniority'
        )

    # ── Level 4a: School Leaders ──────────────────────────────────────────────
    if re.match(r'^school leader( in residence)?$', t):
        return hit('School Leader (4)', 4)

    # ── Level 4b: DSOs ────────────────────────────────────────────────────────
    # Matches both "Director School Operations" and "Fellow School Operations Director"
    if re.match(r'^(fellow )?director (of )?(campus|school) operations?$', t):
        return hit('DSOs (4)', 4)
    if re.match(r'^fellow (campus|school) operations? director$', t):
        return hit('DSOs (4)', 4)

    # ── Level 4c: KTAF/Regional Directors + Achievement Directors ─────────────
    if re.match(r'^achievement director$', t):
        return hit('KTAF or Regional Director (4)', 4)

    if re.match(r'^director\b', t):
        if d in CENTRAL_DEPARTMENTS:
            return hit('KTAF or Regional Director (4)', 4)
        if d == 'kipp forward':
            return maybe(
                'KTAF or Regional Director (4)', 4,
                'KIPP Forward Director — verify school-embedded vs central'
            )
        return maybe(
            'KTAF or Regional Director (4)', 4,
            f'Director in "{department}" — confirm Level 4 vs Level 6'
        )

    # ── Level 5a: Assistant School Leaders ───────────────────────────────────
    if re.match(r'^assistant school leader\b', t):
        return hit('Assistant School Leaders (5)', 5)

    # ── NOTE: Level 6 title-specific patterns must be checked BEFORE the
    #    department-based Level 5 catch-all so that, e.g., a Teacher or Dean
    #    in a central-adjacent dept (School Support) is correctly Level 6.

    # ── Level 6a: Lead Teachers ───────────────────────────────────────────────
    if re.match(r'^teacher( esl)?$', t) or re.match(r'^ese teacher$', t):
        return hit('Teacher (6)', 6)

    # ── Level 6b: Teachers in Residence ──────────────────────────────────────
    if re.match(r'^(teacher|instructor) in residence\b', t):
        return hit('Teacher in Residence (6)', 6)

    # ── Level 6c: Deans ───────────────────────────────────────────────────────
    if re.match(r'^(assistant )?dean\b', t):
        return hit('Deans (6)', 6)

    # ── Level 6d: Frontline school operations staff ───────────────────────────
    if t in FRONTLINE_OPS_TITLES:
        return hit('ADSOs, Ops-SOMs, AOMs, & Receptionists (6)', 6)

    # ── Level 6e: School-based non-instructional staff (keyword patterns) ─────
    # "couselor" covers a known typo in the SOT ("Team and Family Couselor")
    for pattern in SCHOOL_NON_INSTRUCTIONAL_PATTERNS + [r'\bcouselor\b']:
        if re.search(pattern, t):
            return hit('School-based Non-Instructional Staff (6)', 6)

    # ── Level 5b: KTAF/Regional individual contributors ───────────────────────
    # Associate Directors in central depts manage ICs (not managers) → Level 5
    if re.match(r'^associate director\b', t) and d in CENTRAL_DEPARTMENTS:
        return maybe(
            'KTAF or Regional Staff (5)', 5,
            'Associate Director assumed Level 5; upgrade to Level 4 if they manage managers'
        )

    if d in CENTRAL_DEPARTMENTS:
        return maybe(
            'KTAF or Regional Staff (5)', 5,
            f'Central/KTAF dept "{department}" — individual contributor assumed'
        )

    # ── KIPP Forward non-director roles ──────────────────────────────────────
    # Directors and teacher-pattern roles are already handled above.
    # Managers/Coordinators/Associates in KIPP Forward follow KTAF Level 5 rules.
    if d == 'kipp forward':
        if re.match(r'^(manager|coordinator|associate|specialist|analyst)\b', t):
            return maybe(
                'KTAF or Regional Staff (5)', 5,
                'KIPP Forward management/coordinator role — individual contributor assumed'
            )
        if re.match(r'^fellow\b', t):
            return hit('Intern (7)', 7)
        return maybe(
            'KTAF or Regional Staff (5)', 5,
            f'KIPP Forward role — no specific rule matched; review grouping'
        )

    # ── Department fallbacks ──────────────────────────────────────────────────
    if d in SCHOOL_DEPARTMENTS:
        return maybe(
            'School-based Non-Instructional Staff (6)', 6,
            f'School dept "{department}" — no specific rule matched; treated as non-instructional'
        )

    if d == 'operations':
        if re.search(r'\b(custodian|porter|security|nurse|receptionist|crossing guard|facilities|campus)\b', t):
            return hit('School-based Non-Instructional Staff (6)', 6)
        return maybe(
            'School-based Non-Instructional Staff (6)', 6,
            'Operations dept — could be school or central ops; verify'
        )

    # ── Fallthrough ───────────────────────────────────────────────────────────
    return GroupingResult(
        'Unknown', None, 'low',
        f'No rule matched for "{job_title}" in "{department}"'
    )


# ── Mapping CSV: build and load ────────────────────────────────────────────────

def _load_sot(sot_path: Path) -> list[tuple[str, str]]:
    """Load the SOT CSV and return a deduplicated list of (job_title, department)."""
    seen: set[tuple[str, str]] = set()
    entries: list[tuple[str, str]] = []
    with open(sot_path, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            key = (row['Jobs'].strip(), row['Departments'].strip())
            if key[0] and key[1] and key not in seen:
                seen.add(key)
                entries.append(key)
    return entries


def build_mapping(
    sot_path: Path = SOT_PATH,
    mapping_path: Path = MAPPING_PATH,
    overwrite: bool = False,
) -> None:
    """
    Generate job_groupings_mapping.csv from the SOT + grouping rules.

    Existing rows in the mapping are preserved unless overwrite=True, so admins
    can manually correct entries without them being overwritten on the next run.
    New SOT entries (not already in the mapping) are appended.

    Args:
        sot_path:     Path to allowed_jobs_sot.csv
        mapping_path: Path to write/update job_groupings_mapping.csv
        overwrite:    If True, regenerate the entire mapping from rules.
    """
    sot_entries = _load_sot(sot_path)

    # Load existing mapping (so admin edits are preserved)
    existing: dict[tuple[str, str], dict] = {}
    if mapping_path.exists() and not overwrite:
        with open(mapping_path, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                key = (row['Jobs'].strip(), row['Departments'].strip())
                existing[key] = row

    rows_written = 0
    rows_skipped = 0

    with open(mapping_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=MAPPING_COLUMNS)
        writer.writeheader()

        for title, dept in sot_entries:
            key = (title, dept)
            if key in existing and not overwrite:
                # Preserve admin-edited row
                writer.writerow(existing[key])
                rows_skipped += 1
            else:
                result = _classify_by_rules(title, dept)
                writer.writerow({
                    'Jobs': title,
                    'Departments': dept,
                    'Grouping': result.grouping_name,
                    'Level': result.level if result.level is not None else '',
                    'Confidence': result.confidence,
                    'Notes': result.notes,
                })
                rows_written += 1

    total = rows_written + rows_skipped
    print(
        f"Mapping saved to {mapping_path}\n"
        f"  {total} entries total  ({rows_written} (re)generated, {rows_skipped} preserved)"
    )


def load_mapping(mapping_path: Path = MAPPING_PATH) -> dict[tuple[str, str], GroupingResult]:
    """
    Load the mapping CSV into a dict keyed by (job_title_lower, department_lower).
    """
    if not mapping_path.exists():
        raise FileNotFoundError(
            f"Mapping file not found: {mapping_path}\n"
            "Run  python job_groupings_classifier.py build-mapping  to generate it."
        )

    mapping: dict[tuple[str, str], GroupingResult] = {}
    with open(mapping_path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            title = row['Jobs'].strip()
            dept = row['Departments'].strip()
            level_raw = row.get('Level', '').strip()
            level = int(level_raw) if level_raw.isdigit() else None
            key = (title.lower(), dept.lower())
            mapping[key] = GroupingResult(
                grouping_name=row.get('Grouping', 'Unknown').strip(),
                level=level,
                confidence=row.get('Confidence', 'high').strip(),
                notes=row.get('Notes', '').strip(),
            )
    return mapping


# ── Permissions export ────────────────────────────────────────────────────────

def _normalise_apostrophes(text: str) -> str:
    """Replace curly/smart apostrophes with straight ASCII apostrophes."""
    return text.replace('\u2019', "'").replace('\u2018', "'")


def _load_permission_rule_names(
    designations_path: Path = PERMISSIONS_DESIGNATIONS_PATH,
) -> list[str]:
    """
    Return the ordered list of rule names from permission_designations.csv.
    Apostrophes are normalised to straight ASCII so they match GROUPING_PERMISSIONS.
    These become the column headers in the permissions output CSV.
    """
    names: list[str] = []
    with open(designations_path, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            name = _normalise_apostrophes(row['Rule Name'].strip())
            if name:
                names.append(name)
    return names


def export_permissions_csv(
    mapping_path: Path = MAPPING_PATH,
    designations_path: Path = PERMISSIONS_DESIGNATIONS_PATH,
    output_path: Path = PERMISSIONS_OUTPUT_PATH,
) -> None:
    """
    Write a CSV that combines each job's grouping with a TRUE/FALSE column for
    every permission rule defined in permission_designations.csv.

    Columns: Jobs, Departments, Grouping, Level, <one column per rule name>

    Permissions are assigned based on GROUPING_PERMISSIONS; any grouping not
    listed there (Levels 5b–7, Unmatched) gets FALSE for all rule columns.

    Args:
        mapping_path:      Path to job_groupings_mapping.csv (source of truth).
        designations_path: Path to permission_designations.csv (defines columns).
        output_path:       Destination CSV path.
    """
    rule_names = _load_permission_rule_names(designations_path)
    output_columns = ['Jobs', 'Departments', 'Grouping', 'Level'] + rule_names

    rows_written = 0
    with open(mapping_path, newline='', encoding='utf-8') as src, \
         open(output_path, 'w', newline='', encoding='utf-8') as dst:

        reader = csv.DictReader(src)
        writer = csv.DictWriter(dst, fieldnames=output_columns)
        writer.writeheader()

        for row in reader:
            grouping = row['Grouping'].strip()
            dept_lower = row['Departments'].strip().lower()
            granted = GROUPING_PERMISSIONS.get(grouping, set())
            special_designation = SPECIAL_DESIGNATION_DEPARTMENTS.get(dept_lower)

            out_row: dict = {
                'Jobs': row['Jobs'],
                'Departments': row['Departments'],
                'Grouping': grouping,
                'Level': row['Level'],
            }
            for rule in rule_names:
                if rule in granted:
                    out_row[rule] = 'TRUE'
                elif special_designation is not None and rule == special_designation:
                    out_row[rule] = 'TRUE'
                else:
                    out_row[rule] = 'FALSE'

            writer.writerow(out_row)
            rows_written += 1

    print(f"Permissions CSV saved to {output_path}  ({rows_written} rows, {len(rule_names)} rule columns)")


# ── Website data JS export ────────────────────────────────────────────────────

DATA_JS_PATH = _HERE / 'website' / 'data.js'


def export_data_js(
    permissions_path: Path = PERMISSIONS_OUTPUT_PATH,
    output_path: Path = DATA_JS_PATH,
) -> None:
    """
    Generate website/data.js from job_groupings_with_permissions.csv.

    Produces:
        const JOB_DATA = [...];     // one object per job-department pair
        const PERMISSION_COLS = [...];  // ordered list of permission column names

    Re-run this after export_permissions_csv() to refresh the explorer site.
    """
    rows: list[dict] = []
    perm_cols: list[str] = []

    with open(permissions_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        base_cols = {'Jobs', 'Departments', 'Grouping', 'Level'}
        # Capture permission column order from the first file scan
        perm_cols = [c for c in (reader.fieldnames or []) if c not in base_cols]

        for row in reader:
            level_raw = row.get('Level', '').strip()
            level_val = int(level_raw) if level_raw.isdigit() else None
            perms = {col: row[col].strip().upper() == 'TRUE' for col in perm_cols}
            rows.append({
                'title': row['Jobs'].strip(),
                'dept': row['Departments'].strip(),
                'grouping': row['Grouping'].strip(),
                'level': level_val,
                'permissions': perms,
            })

    perm_cols_json = json.dumps(perm_cols, indent=2)
    rows_json = json.dumps(rows, indent=2)

    output_path.write_text(
        f'// Auto-generated from {permissions_path.name}\n'
        f'// Re-run: python job_groupings_classifier.py export-permissions'
        f', then export-data-js\n\n'
        f'const JOB_DATA = {rows_json};\n\n'
        f'const PERMISSION_COLS = {perm_cols_json};\n',
        encoding='utf-8',
    )
    print(
        f"Data JS saved to {output_path}\n"
        f"  {len(rows)} job entries, {len(perm_cols)} permission columns"
    )


# ── Slack alert ───────────────────────────────────────────────────────────────

def send_slack_alert(
    job_title: str,
    department: str,
    webhook_url: Optional[str] = None,
) -> bool:
    """
    Post an alert to Slack when a job title is not found in the mapping.

    The webhook URL is read from the SLACK_WEBHOOK_URL environment variable if
    not passed explicitly.  Returns True if the message was sent successfully.
    """
    url = webhook_url or os.environ.get('SLACK_WEBHOOK_URL')
    if not url:
        # No webhook configured — log to stderr and continue
        import sys
        print(
            f'[ALERT] Unmatched job: "{job_title}" in "{department}" — '
            'not in job_groupings_mapping.csv. '
            'Set SLACK_WEBHOOK_URL to send Slack alerts.',
            file=sys.stderr,
        )
        return False

    payload = {
        'text': (
            f':warning: *Unmatched job title detected*\n'
            f'>*Title:* {job_title}\n'
            f'>*Department:* {department}\n'
            f'This combination is not in `job_groupings_mapping.csv`. '
            f'Please review and add a mapping entry.'
        )
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url, data=data, headers={'Content-Type': 'application/json'}, method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=5):
            return True
    except urllib.error.URLError as exc:
        import sys
        print(f'[ALERT] Slack notification failed: {exc}', file=sys.stderr)
        return False


# ── Classifier ────────────────────────────────────────────────────────────────

class JobGroupingClassifier:
    """
    Classifies (job_title, department) pairs using a pre-built mapping CSV.

    Lookup is a strict dictionary match — no guessing.  Unmatched titles trigger
    a Slack alert so an admin can update the mapping.

    Usage:
        classifier = JobGroupingClassifier()
        result = classifier.classify('Teacher', 'Math')
        print(result)
    """

    def __init__(
        self,
        mapping_path: Path = MAPPING_PATH,
        slack_webhook_url: Optional[str] = None,
    ) -> None:
        self._mapping = load_mapping(mapping_path)
        self._slack_webhook = slack_webhook_url or os.environ.get('SLACK_WEBHOOK_URL')

    def classify(self, job_title: str, department: str) -> GroupingResult:
        """
        Look up a (job_title, department) pair in the mapping.

        If found, returns the stored GroupingResult.
        If not found, sends a Slack alert and returns an 'unmatched' result.
        """
        key = (job_title.strip().lower(), department.strip().lower())

        if key in self._mapping:
            return self._mapping[key]

        # Not in mapping — alert and return unmatched
        send_slack_alert(job_title, department, self._slack_webhook)
        return GroupingResult(
            grouping_name='Unmatched',
            level=None,
            confidence='unmatched',
            notes=(
                f'"{job_title}" in "{department}" is not in the mapping. '
                'An alert has been sent — please update job_groupings_mapping.csv.'
            ),
        )

    def classify_batch(
        self,
        inputs: list[tuple[str, str]],
    ) -> list[dict]:
        """
        Classify a list of (job_title, department) pairs.

        Returns a list of dicts with keys:
            job_title, department, grouping, level, confidence, notes
        """
        results = []
        for job_title, department in inputs:
            r = self.classify(job_title, department)
            results.append({
                'job_title': job_title,
                'department': department,
                'grouping': r.grouping_name,
                'level': r.level,
                'confidence': r.confidence,
                'notes': r.notes,
            })
        return results

    def classify_sot(self, sot_path: Path = SOT_PATH) -> list[dict]:
        """Classify every entry in the allowed jobs SOT."""
        entries = _load_sot(sot_path)
        return self.classify_batch(entries)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _print_results(rows: list[dict]) -> None:
    header = f"{'Job Title':<45} {'Department':<35} {'Grouping':<45} {'Lvl':>3}  {'Conf':<10}  Notes"
    print(header)
    print('-' * len(header))
    for r in rows:
        lvl = str(r['level']) if r['level'] is not None else '?'
        print(
            f"{r['job_title']:<45} "
            f"{r['department']:<35} "
            f"{r['grouping']:<45} "
            f"{lvl:>3}  "
            f"{r['confidence']:<10}  "
            f"{r['notes']}"
        )


if __name__ == '__main__':
    import sys

    args = sys.argv[1:]

    if not args or args[0] == 'build-mapping':
        overwrite = '--overwrite' in args
        build_mapping(overwrite=overwrite)

    elif args[0] == 'classify':
        if len(args) < 3:
            print('Usage: python job_groupings_classifier.py classify "Job Title" "Department"')
            sys.exit(1)
        classifier = JobGroupingClassifier()
        result = classifier.classify(args[1], args[2])
        print(result)

    elif args[0] == 'classify-sot':
        classifier = JobGroupingClassifier()
        rows = classifier.classify_sot()
        _print_results(rows)

    elif args[0] == 'export-permissions':
        export_permissions_csv()

    elif args[0] == 'export-data-js':
        export_data_js()

    else:
        print(__doc__)
        sys.exit(1)
