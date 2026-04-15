# Stakeholder Communication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Draft and deliver a stakeholder email announcing the ADP Job Functions rollout, and add a Rollout Status page to the existing GitHub Pages site.

**Architecture:** Two independent deliverables — a plain-text email draft saved for the sender to copy/send, and a new `status.html` page that follows the existing site structure (shared `styles.css`, same nav, Inter font). New CSS classes are appended to `styles.css` before the existing responsive block. No JavaScript required.

**Tech Stack:** HTML, CSS (existing Inter + CSS custom properties), plain text for email draft

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Create | `email-draft.txt` | Plain-text stakeholder email ready to copy/send |
| Modify | `website/index.html` | Add "Status" nav link |
| Modify | `website/explorer.html` | Add "Status" nav link |
| Modify | `website/styles.css` | Append status page component styles before responsive block |
| Create | `website/status.html` | Rollout Status page |

---

## Task 1: Draft the stakeholder email

**Files:**
- Create: `email-draft.txt`

- [ ] **Step 1: Write the email draft**

Create `email-draft.txt` in the repo root with the following content (fill in your name and the live GitHub Pages URL before sending):

```
Subject: Job Grouping Framework Update: Job Functions Loaded in ADP

Hi all,

Quick update on the job grouping and permissioning framework — a structured
system that maps every job title to a consistent grouping and set of data
access rules. You can see the full framework here: [FRAMEWORK URL]

What we did: We've completed the first implementation step — loading the job
groupings into ADP as Job Functions. This field is the foundation for
consistent definitions across reports, dashboards, and eventually automated
data access.

Where we are: The Job Function field has been configured in ADP, but we're not
yet seeing it appear on employee profiles. We've completed what we expected to
do on our end and are now investigating what additional step is needed.

Ask for HR/Talent: Could someone with ADP admin access help look into this?
The question is whether getting the field to populate on profiles requires an
additional configuration step, a sync to be triggered, or a support ticket
with ADP. Happy to connect with whoever is the right person.

What comes next: Once employee profiles are reflecting their Job Function,
we'll be able to start connecting the groupings to downstream tools and
reports. I'll send a follow-up note when that step is live.

Let me know if you have questions.

[YOUR NAME]
```

- [ ] **Step 2: Commit**

```bash
git add email-draft.txt
git commit -m "docs: add stakeholder email draft for ADP Job Functions update"
```

---

## Task 2: Add Status nav link to existing pages

**Files:**
- Modify: `website/index.html`
- Modify: `website/explorer.html`

Both pages share the same nav block. The current nav links are Overview and Job Explorer. Add a third link for Status.

- [ ] **Step 1: Update index.html nav**

Find this block in `website/index.html` (inside `<div class="nav-links">`):

```html
      <a href="index.html" class="nav-link active">Overview</a>
      <a href="explorer.html" class="nav-link">Job Explorer</a>
```

Replace with:

```html
      <a href="index.html" class="nav-link active">Overview</a>
      <a href="explorer.html" class="nav-link">Job Explorer</a>
      <a href="status.html" class="nav-link">Status</a>
```

- [ ] **Step 2: Update explorer.html nav**

Find this block in `website/explorer.html` (inside `<div class="nav-links">`):

```html
      <a href="index.html" class="nav-link">Overview</a>
      <a href="explorer.html" class="nav-link active">Job Explorer</a>
```

Replace with:

```html
      <a href="index.html" class="nav-link">Overview</a>
      <a href="explorer.html" class="nav-link active">Job Explorer</a>
      <a href="status.html" class="nav-link">Status</a>
```

- [ ] **Step 3: Commit**

```bash
git add website/index.html website/explorer.html
git commit -m "feat: add Status nav link to existing pages"
```

---

## Task 3: Add status page CSS to styles.css

**Files:**
- Modify: `website/styles.css` (insert before line 1164, the `/* ── Responsive` block)

- [ ] **Step 1: Append new CSS block before the responsive section**

In `website/styles.css`, find the line:

```css
/* ── Responsive ───────────────────────────────────────────────────────────── */
```

Insert the following block immediately before it:

```css
/* ── Status page ─────────────────────────────────────────────────────────── */
.status-summary-bar {
  background: var(--white);
  border-bottom: 1px solid var(--border);
  padding: 20px 0;
}
.status-summary-inner {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}
.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  font-size: 14px;
  padding: 6px 14px;
  border-radius: 20px;
}
.status-indicator--blocked { background: #fef3c7; color: #b45309; }
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}
.status-summary-desc { font-size: 14px; color: var(--text-2); }

.phase-list {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  background: var(--white);
  box-shadow: var(--shadow);
}
.phase-item {
  padding: 20px 24px;
  border-bottom: 1px solid var(--border);
}
.phase-item:last-child { border-bottom: none; }
.phase-item--blocked { background: #fffbeb; }
.phase-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.phase-name { font-size: 15px; font-weight: 600; color: var(--text); }
.phase-badge {
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .03em;
  padding: 4px 12px;
  border-radius: 20px;
  white-space: nowrap;
  flex-shrink: 0;
}
.phase-badge--complete  { background: #dcfce7; color: #15803d; }
.phase-badge--blocked   { background: #fef3c7; color: #b45309; }
.phase-badge--pending   { background: #f1f5f9; color: #64748b; }
.phase-badge--ongoing   { background: #dbeafe; color: #1d4ed8; }
.phase-note {
  margin-top: 10px;
  font-size: 13px;
  color: var(--text-2);
  line-height: 1.6;
}
.phase-note strong { color: var(--text); }

```

- [ ] **Step 2: Commit**

```bash
git add website/styles.css
git commit -m "feat: add status page CSS components"
```

---

## Task 4: Build status.html

**Files:**
- Create: `website/status.html`

- [ ] **Step 1: Create the file**

Create `website/status.html` with the following content:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Rollout Status · Job Grouping Framework</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="styles.css" />
</head>
<body>

<!-- ── Navigation ─────────────────────────────────────────────────────────── -->
<nav class="nav">
  <div class="nav-inner">
    <span class="nav-brand">Job Grouping Framework</span>
    <div class="nav-links">
      <a href="index.html" class="nav-link">Overview</a>
      <a href="explorer.html" class="nav-link">Job Explorer</a>
      <a href="status.html" class="nav-link active">Status</a>
    </div>
  </div>
</nav>

<!-- ── Page header ────────────────────────────────────────────────────────── -->
<div class="explorer-header">
  <div class="container">
    <h1>Rollout Status</h1>
    <p>Live tracking of the job grouping framework implementation progress.</p>
  </div>
</div>

<!-- ── Summary bar ────────────────────────────────────────────────────────── -->
<div class="status-summary-bar">
  <div class="container">
    <div class="status-summary-inner">
      <div class="status-indicator status-indicator--blocked">
        <span class="status-dot"></span>
        In Progress
      </div>
      <p class="status-summary-desc">Investigating ADP profile sync &mdash; 2 of 6 phases complete</p>
    </div>
  </div>
</div>

<!-- ── Phase tracker ──────────────────────────────────────────────────────── -->
<section class="section">
  <div class="container">
    <div class="phase-list">

      <div class="phase-item">
        <div class="phase-header">
          <span class="phase-name">Framework designed and published</span>
          <span class="phase-badge phase-badge--complete">✓ Complete</span>
        </div>
      </div>

      <div class="phase-item">
        <div class="phase-header">
          <span class="phase-name">Job Functions loaded in ADP</span>
          <span class="phase-badge phase-badge--complete">✓ Complete</span>
        </div>
      </div>

      <div class="phase-item phase-item--blocked">
        <div class="phase-header">
          <span class="phase-name">Job Functions flowing to employee profiles</span>
          <span class="phase-badge phase-badge--blocked">⚠ Open Question</span>
        </div>
        <div class="phase-note">
          <strong>Investigating:</strong> Job Functions have been loaded in ADP but are not yet
          appearing on employee profiles. It is unclear whether this requires an additional ADP
          configuration step, a sync to be triggered, or a support ticket. We are working with
          HR/Talent to determine next steps.
        </div>
      </div>

      <div class="phase-item">
        <div class="phase-header">
          <span class="phase-name">Data pipelines consuming Job Function field</span>
          <span class="phase-badge phase-badge--pending">Pending</span>
        </div>
      </div>

      <div class="phase-item">
        <div class="phase-header">
          <span class="phase-name">Updating groupings across tools and dashboards</span>
          <span class="phase-badge phase-badge--pending">Pending</span>
        </div>
      </div>

      <div class="phase-item">
        <div class="phase-header">
          <span class="phase-name">Permissions framework live</span>
          <span class="phase-badge phase-badge--pending">Pending</span>
        </div>
      </div>

      <div class="phase-item">
        <div class="phase-header">
          <span class="phase-name">Updates / changes to job group mappings</span>
          <span class="phase-badge phase-badge--ongoing">Ongoing</span>
        </div>
        <div class="phase-note">
          The mapping CSV is the single source of truth. Updates are reviewed and applied on a
          rolling basis as new job titles are created or existing mappings need correction.
        </div>
      </div>

    </div>
  </div>
</section>

</body>
</html>
```

- [ ] **Step 2: Open `website/status.html` in a browser and verify**

Check:
- Nav shows Overview, Job Explorer, Status (Status is highlighted as active)
- Summary bar shows amber "In Progress" pill + description text
- Phase list renders as a card with 7 rows
- First two rows show green "✓ Complete" badges
- Third row has amber background, "⚠ Open Question" badge, and note text below
- Rows 4–6 show grey "Pending" badges
- Last row shows blue "Ongoing" badge with note text below

- [ ] **Step 3: Commit**

```bash
git add website/status.html
git commit -m "feat: add Rollout Status page"
```

---

## Task 5: Push and verify GitHub Pages

- [ ] **Step 1: Push to origin**

```bash
git push origin main
```

- [ ] **Step 2: Confirm GitHub Pages deployment**

Visit the live site (typically at `https://<org>.github.io/<repo>/`) and confirm:
- Status page loads at `/status.html`
- Nav Status link is present on Overview and Job Explorer pages
- All badge colors and note text render correctly

- [ ] **Step 3: Copy the live status page URL**

You'll want to include a link to `status.html` in the stakeholder email (replace `[FRAMEWORK URL]` in `email-draft.txt` with the Overview page URL, and optionally add a separate link to the Status page).
