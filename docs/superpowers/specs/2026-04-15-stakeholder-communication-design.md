# Stakeholder Communication Design
**Date:** 2026-04-15
**Topic:** Job Groupings → ADP Job Functions rollout update

---

## Context

The job grouping and permissioning framework for KIPP NJ/Miami has been designed and published at the GitHub Pages site. The next implementation step — loading the job groupings into ADP as Job Functions — has been completed. However, Job Functions are not yet appearing on employee profiles in ADP. The cause is not yet known; it may require an ADP configuration step, a sync trigger, or a support ticket, and HR/Talent will need to help investigate.

---

## Audiences

- **HR/Talent leadership** — own ADP configuration and job records; need a specific ask
- **Senior org leaders** — need confidence that rollout is progressing; do not need technical detail

Both audiences receive the same communication (single email).

---

## Email Design

### Subject
`Job Grouping Framework Update: Job Functions Loaded in ADP`

### Structure

1. **One-sentence context** — brief reminder of what the framework is and why it matters (for senior leaders who may need a refresher); link to the framework site
2. **What was done** — Job Functions have been configured and loaded in ADP as the first concrete implementation step
3. **Current gap** — the field is loaded but not yet appearing on employee profiles; framed as an open question rather than a failure (we've done what we expected to do on our end and are now investigating)
4. **Specific ask to HR/Talent** — need help determining whether this requires an ADP configuration step, a sync trigger, or a support ticket, and who owns that next step
5. **What comes next** — once the gap is resolved, employee profiles will reflect their Job Function; a follow-up note will go out when that's live

### Tone
Informative and forward-moving — not alarming. The gap is real but not a blocker to communicating progress.

---

## Status Page Design

### Location
New file: `website/status.html`

### Nav
Add "Status" link to the existing nav bar alongside "Overview" and "Job Explorer".

### Page Structure

#### 1. Page header
Title: "Rollout Status"

#### 2. At-a-glance summary bar
A single indicator showing overall rollout state, e.g. "In Progress — Investigating ADP profile sync".

#### 3. Phase tracker

Each phase has a name, a status badge, and (where relevant) a plain-English note.

| Phase | Status | Notes |
|---|---|---|
| Framework designed and published | Complete | |
| Job Functions loaded in ADP | Complete | |
| Job Functions flowing to employee profiles | Blocked | Open question — field is loaded but not yet appearing on profiles. Investigating whether an ADP configuration step, sync trigger, or support ticket is needed. |
| Data pipelines consuming Job Function field | Pending | |
| Updating groupings across tools/dashboards | Pending | |
| Permissions framework live | Pending | |
| Updates/changes to Job Group Mappings | Ongoing | Mapping CSV is the single source of truth; updates are reviewed and applied on a rolling basis. |

**Status badge palette:**
- Complete — green
- Blocked — red/amber with a roadblock/open-question icon
- Pending — grey
- Ongoing — blue

#### 4. Notes field
The "Blocked" item includes a short paragraph explaining what's happening and what's needed to move forward. Other phases may have brief notes added as the rollout progresses.

---

## Out of Scope

- Changes to the framework itself (levels, mappings, permissions)
- ADP technical investigation (separate work item for HR/Talent)
- Automated status updates — page is updated manually as phases complete
