# AIVENTRA — Input Interface Text Diagrams
### Complete UI Reference: Evidence Upload, Case Creation & Input Pages
**Based on Input Specification v1.0 — All 6 Evidence Categories**

---

## OVERVIEW — Page Map for Input Flows

```
/cases/new
  ├── Step 1: Case Details
  └── Step 2: Evidence Upload
        ├── Cat A: Autopsy & Medical Documents
        ├── Cat B: CDR / Call Detail Records
        ├── Cat C: Location & GPS Data
        ├── Cat D: Financial Records
        ├── Cat E: Device & App Data
        └── Cat F: Scene & Environmental

/cases/:id/evidence
  └── Evidence Manager (add more files post-creation)

/cases/:id/evidence/:fileId/review
  └── Extracted Fields Review (per-category, post-parse)
        ├── Autopsy Extraction Review
        ├── CDR Preview & Mapping
        ├── Location Preview
        ├── Financial Preview
        ├── Device Data Preview
        └── Scene Report Review
```

---

---

## PAGE: `/cases/new` — STEP 1: Case Details

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ⬡ AIVENTRA                                             👤 Arjun Sharma ▾   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ← Back to Dashboard                                                        │
│                                                                             │
│  ●━━━━━━━━━━━━━━━○                                                          │
│  Step 1: Case Details    Step 2: Upload Evidence                            │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  New Case                                                            │  │
│  │  ────────────────────────────────────────────────────────────────── │  │
│  │                                                                      │  │
│  │  Case Number *              [Auto-suggested — editable]              │  │
│  │  ┌──────────────────────────────────────────────────────────────┐   │  │
│  │  │  CASE-2026-005                                               │   │  │
│  │  └──────────────────────────────────────────────────────────────┘   │  │
│  │  ✓ Case number available                                             │  │
│  │                                                                      │  │
│  │  Case Title *                                                        │  │
│  │  ┌──────────────────────────────────────────────────────────────┐   │  │
│  │  │  e.g. Kumar Homicide Investigation                           │   │  │
│  │  └──────────────────────────────────────────────────────────────┘   │  │
│  │                                                                      │  │
│  │  Brief Description (optional)                                        │  │
│  │  ┌──────────────────────────────────────────────────────────────┐   │  │
│  │  │                                                              │   │  │
│  │  │                                                              │   │  │
│  │  └──────────────────────────────────────────────────────────────┘   │  │
│  │  Max 500 characters                                                  │  │
│  │                                                                      │  │
│  │  Priority          Assigned To                                       │  │
│  │  ┌───────────────┐  ┌──────────────────────────────────────────┐    │  │
│  │  │  🔴 HIGH    ▾ │  │  Arjun Sharma (you)                    ▾ │    │  │
│  │  └───────────────┘  └──────────────────────────────────────────┘    │  │
│  │  [LOW | MEDIUM | HIGH | CRITICAL]                                    │  │
│  │                                                                      │  │
│  │  ───────────────────────────────────────────────────────────────    │  │
│  │  Subject / Victim Information (optional — used in report header)    │  │
│  │                                                                      │  │
│  │  Subject Name *          Subject Age       Subject Gender            │  │
│  │  ┌───────────────────┐   ┌─────────────┐   ┌─────────────────────┐  │  │
│  │  │  [MASKED IN UI]   │   │  34         │   │  MALE             ▾ │  │  │
│  │  └───────────────────┘   └─────────────┘   └─────────────────────┘  │  │
│  │  ⚠ PII — masked in all agent outputs. Stored encrypted.             │  │
│  │                                                                      │  │
│  │  Incident Date (approx.)     Incident Location                      │  │
│  │  ┌──────────────────────┐    ┌──────────────────────────────────┐   │  │
│  │  │  07 / 05 / 2026  📅  │    │  New Delhi                       │   │  │
│  │  └──────────────────────┘    └──────────────────────────────────┘   │  │
│  │                                                                      │  │
│  │                                          [ Continue to Upload → ]   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## PAGE: `/cases/new` — STEP 2: Evidence Upload Hub

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ⬡ AIVENTRA                                             👤 Arjun Sharma ▾   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ━━━━━━━━━━━━━━━●                                                           │
│  Step 1: Case Details    Step 2: Upload Evidence                            │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Upload Evidence Files                                               │  │
│  │  Select a category and upload the corresponding files.               │  │
│  │  You can add more evidence later from the case page.                 │  │
│  │  ────────────────────────────────────────────────────────────────── │  │
│  │                                                                      │  │
│  │  ┌─────────────────────────────────────────────────────────────┐    │  │
│  │  │  [A] Autopsy     [B] CDR      [C] Location                  │    │  │
│  │  │  [D] Financial   [E] Device   [F] Scene                     │    │  │
│  │  └─────────────────────────────────────────────────────────────┘    │  │
│  │                    ↑ Active tab shown below                          │  │
│  │                                                                      │  │
│  │  ┌─── TAB PANEL (changes per selected tab) ───────────────────────┐ │  │
│  │  │  [See each tab panel detailed below]                           │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                      │  │
│  │  ─────────────────────────────────────────────────────────────────  │  │
│  │  Evidence Summary                                                    │  │
│  │                                                                      │  │
│  │  ● Cat A — Autopsy Report      1 file    ✓ Uploaded                 │  │
│  │  ○ Cat B — CDR Records         0 files   (optional)                 │  │
│  │  ○ Cat C — Location Data       0 files   (optional)                 │  │
│  │  ○ Cat D — Financial Records   0 files   (optional)                 │  │
│  │  ○ Cat E — Device Data         0 files   (optional)                 │  │
│  │  ○ Cat F — Scene Documents     0 files   (optional)                 │  │
│  │                                                                      │  │
│  │  ⚠ Minimum requirement: At least 1 Category A (Autopsy) file        │  │
│  │    OR 2+ other categories for meaningful analysis.                   │  │
│  │                                                                      │  │
│  │  Expected Analysis Quality:   ██████░░░░  ADEQUATE                  │  │
│  │  (quality bar updates live as files are added)                       │  │
│  │                                                                      │  │
│  │                [ ← Back ]          [ Create Case & Begin Analysis ]  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## UPLOAD TAB — Category A: Autopsy & Medical Documents

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  [A] Autopsy  [B] CDR  [C] Location  [D] Financial  [E] Device  [F] Scene   │
│   ─────                                                                      │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  📋 Category A — Autopsy & Medical Documents                        │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  The official post-mortem examination report from the forensic       │   │
│  │  pathologist. This is the most critical evidence category.           │   │
│  │                                                                      │   │
│  │  Accepted Formats                                                    │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  ✓ PDF (text-based or scanned)   ✓ DOCX                       │ │   │
│  │  │  ✓ JPG / PNG (scan photos)       ✓ TIFF                       │ │   │
│  │  │  ✓ TXT                                                         │ │   │
│  │  │  Max file size: 500 MB per file                                │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │                                                                │ │   │
│  │  │          ☁  Drag and drop file here                           │ │   │
│  │  │                     or                                         │ │   │
│  │  │              [ Browse Files ]                                  │ │   │
│  │  │                                                                │ │   │
│  │  │    ℹ  Note: Scanned PDFs will be auto-processed via OCR.     │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  ──────── OR manually specify report type ────────                  │   │
│  │                                                                      │   │
│  │  Report Sub-type (optional — helps normalizer)                      │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │  Auto-detect                                               ▾  │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  │  Options: Auto-detect | AIIMS/NIMHANS Format | State Hospital        │   │
│  │           Format | Fill-in Template | Free-form Narrative            │   │
│  │                                                                      │   │
│  │  ──────── Uploaded Files ────────────────────────────────────────── │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  📄 PME_Kumar_2026.pdf                    2.1 MB   ✓ Queued   │ │   │
│  │  │  Type: PDF (scanned) · OCR will be applied                    │ │   │
│  │  │  SHA-256: a3f8c2...d41e   [🗑 Remove]                         │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  Fields that will be extracted from this document:                  │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  ✦ Cause & Manner of Death     ✦ Postmortem Signs (TOD)       │ │   │
│  │  │  ✦ Injuries & Defensive Wounds ✦ Toxicology Findings          │ │   │
│  │  │  ✦ Body Temperature / Weight   ✦ Scene Parameters (if noted)  │ │   │
│  │  │  ✦ Pathologist & Report Ref    ✦ Internal / Organ Findings    │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │  Feeds: Autopsy Agent → TOD Agent → Hypothesis Manager              │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## UPLOAD TAB — Category B: CDR / Call Detail Records

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  [A] Autopsy  [B] CDR  [C] Location  [D] Financial  [E] Device  [F] Scene   │
│              ─────                                                           │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  📞 Category B — CDR / Call Detail Records                          │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  Raw call/SMS logs from telecom operators. Contains every call,      │   │
│  │  SMS, data session with timestamps and cell tower IDs.               │   │
│  │                                                                      │   │
│  │  Accepted Formats                                                    │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  ✓ CSV (most common — Airtel/Jio/BSNL/Vi)                     │ │   │
│  │  │  ✓ XLSX / XLS                                                  │ │   │
│  │  │  ✓ PDF (court-formatted — OCR + table extraction)              │ │   │
│  │  │  ✓ TXT (pipe or tab delimited)                                 │ │   │
│  │  │  ✓ JSON (API export)   ✓ XML                                   │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │          ☁  Drag and drop CDR file here                        │ │   │
│  │  │                     or  [ Browse Files ]                        │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  Telecom Operator (helps column mapping)                            │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │  Auto-detect                                               ▾  │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  │  Options: Auto-detect | Airtel | Jio | BSNL | Vi | Other            │   │
│  │                                                                      │   │
│  │  Subject Phone Number (MSISDN)                                      │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │  +91 9876543210                                               │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  │  ⚠ PII — will be masked as 98XXXXXX10 in all agent outputs           │   │
│  │                                                                      │   │
│  │  CDR Date Range (used for timeline scoping)                         │   │
│  │  From  ┌──────────────────┐   To  ┌──────────────────┐             │   │
│  │        │  01 / 05 / 2026  │       │  09 / 05 / 2026  │             │   │
│  │        └──────────────────┘       └──────────────────┘             │   │
│  │                                                                      │   │
│  │  ──────── Uploaded Files ────────────────────────────────────────── │   │
│  │                                                                      │   │
│  │  (no files yet)                                                      │   │
│  │                                                                      │   │
│  │  Fields that will be extracted:                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  ✦ Call/SMS timestamps          ✦ Event type (MOC/MTC/SMS)    │ │   │
│  │  │  ✦ Duration (seconds)           ✦ Cell tower ID + coordinates │ │   │
│  │  │  ✦ Counterparty (masked)        ✦ IMEI (masked)               │ │   │
│  │  │  ✦ Silence windows (>4h gaps)   ✦ Data sessions               │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  15 Pattern Rules will be applied (late-night calls, call bursts,   │   │
│  │  rapid sequences, IMEI changes, location jumps, etc.)               │   │
│  │                                                                      │   │
│  │  Feeds: Digital Timeline Agent → Anomaly Detector → Hypothesis Mgr  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## UPLOAD TAB — Category C: Location & GPS Data

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  [A] Autopsy  [B] CDR  [C] Location  [D] Financial  [E] Device  [F] Scene   │
│                        ──────────                                            │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  📍 Category C — Location & GPS Data                                │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  Geographic coordinate records over time: phone GPS logs, Google     │   │
│  │  Timeline, vehicle GPS, geofence logs, or CDR tower mapping.         │   │
│  │                                                                      │   │
│  │  Accepted Formats                                                    │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  ✓ Google Takeout JSON (Timeline export)                       │ │   │
│  │  │  ✓ GPX (GPS Exchange Format — fitness apps, car GPS)           │ │   │
│  │  │  ✓ KML (Google Earth, mapping apps)                            │ │   │
│  │  │  ✓ CSV (lat/lon/timestamp — IoT, custom trackers)              │ │   │
│  │  │  ✓ GeoJSON   ✓ XLSX (fleet GPS systems)                        │ │   │
│  │  │  ✓ Cell Tower CSV (operator tower logs)                        │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │          ☁  Drag and drop location file here                   │ │   │
│  │  │                     or  [ Browse Files ]                        │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  Location Source Type (helps normalizer)                            │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │  Auto-detect                                               ▾  │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  │  Options: Auto-detect | Google Timeline | GPX Device | Car GPS       │   │
│  │           | Cell Tower Log | IoT Tracker | Other                     │   │
│  │                                                                      │   │
│  │  Belongs To                                                          │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │  Victim                                                    ▾  │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  │  Options: Victim | Suspect | Witness | Unknown                        │   │
│  │                                                                      │   │
│  │  Crime Scene Reference Coordinates (for proximity analysis)         │   │
│  │  Latitude  ┌──────────────────┐  Longitude ┌──────────────────┐     │   │
│  │            │  28.7041         │            │  77.1025         │     │   │
│  │            └──────────────────┘            └──────────────────┘     │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │  [ 🗺 Pick on Map ]                                           │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  │  Proximity threshold: 200m (default — used for SCENE_PRESENCE flag) │   │
│  │                                                                      │   │
│  │  Fields that will be extracted:                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  ✦ Lat/Lon coordinates       ✦ Timestamps (UTC normalized)    │ │   │
│  │  │  ✦ Speed (km/h)              ✦ Activity type (STILL/VEHICLE)  │ │   │
│  │  │  ✦ Accuracy (meters)         ✦ Altitude                       │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  Analyses: Scene presence · Movement trajectory · Location jumps     │   │
│  │  Impossible movement flags · Last known location · Alibi check       │   │
│  │  Feeds: Digital Timeline → Anomaly Detector → Hypothesis Manager     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## UPLOAD TAB — Category D: Financial Records

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  [A] Autopsy  [B] CDR  [C] Location  [D] Financial  [E] Device  [F] Scene   │
│                                      ───────────                             │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  💰 Category D — Financial Records                                  │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  Bank statements, UPI transactions, NEFT/RTGS logs, credit card      │   │
│  │  records. Shows financial behaviour before death.                    │   │
│  │                                                                      │   │
│  │  Accepted Formats                                                    │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  ✓ CSV / XLSX (bank statements — SBI, HDFC, ICICI, Axis, PNB) │ │   │
│  │  │  ✓ PDF bank statements (OCR required)                          │ │   │
│  │  │  ✓ UPI transaction JSON (PhonePe/GPay — court order)           │ │   │
│  │  │  ✓ JSON (FinTech API: Razorpay, Cashfree)                      │ │   │
│  │  │  ✓ NEFT/RTGS CSV                                                │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │          ☁  Drag and drop financial file here                  │ │   │
│  │  │                     or  [ Browse Files ]                        │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  Source Institution                                                  │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │  Auto-detect                                               ▾  │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  │  Options: Auto-detect | SBI | HDFC | ICICI | Axis | PNB | PhonePe   │   │
│  │           | GPay | Paytm | Razorpay | Other                          │   │
│  │                                                                      │   │
│  │  Belongs To                                                          │   │
│  │  ┌────────────────────┐   Account Type                              │   │
│  │  │  Victim          ▾ │   ┌───────────────────────────────────┐     │   │
│  │  └────────────────────┘   │  Savings Account                ▾ │     │   │
│  │                            └───────────────────────────────────┘     │   │
│  │                                                                      │   │
│  │  Large Transaction Threshold (for anomaly detection)                │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │  ₹ 50,000  (default)                                         │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  │  Transactions above this amount near TOD will be flagged.            │   │
│  │                                                                      │   │
│  │  Fields that will be extracted:                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  ✦ Transaction timestamp (UTC)  ✦ Transaction type            │ │   │
│  │  │  ✦ Amount (INR)                 ✦ Balance after               │ │   │
│  │  │  ✦ Counterparty (masked)        ✦ Channel (UPI/NEFT/ATM)      │ │   │
│  │  │  ✦ Reference number             ✦ Location hint (ATM area)    │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  6 Pattern Rules: large withdrawal · unusual transfer ·              │   │
│  │  activity near TOD · ATM location · financial silence ·              │   │
│  │  incoming credit after death                                         │   │
│  │  Feeds: Digital Timeline → Anomaly Detector → Hypothesis Manager     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## UPLOAD TAB — Category E: Device & App Data

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  [A] Autopsy  [B] CDR  [C] Location  [D] Financial  [E] Device  [F] Scene   │
│                                                      ────────                │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  📱 Category E — Device & App Data                                  │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  Mobile app extracts: WhatsApp, Telegram, email, social media,       │   │
│  │  Cellebrite UFED reports, SQLite dumps, browser history.             │   │
│  │                                                                      │   │
│  │  Accepted Formats                                                    │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  ✓ WhatsApp chat export (.txt)                                 │ │   │
│  │  │  ✓ Telegram JSON export                                        │ │   │
│  │  │  ✓ iMessage/SMS backup XML                                     │ │   │
│  │  │  ✓ Cellebrite UFED report (PDF)                                │ │   │
│  │  │  ✓ Android backup XML   ✓ Email MBOX/EML                       │ │   │
│  │  │  ✓ Social media JSON (Facebook/Instagram — court order)        │ │   │
│  │  │  ✓ SQLite database dumps (direct forensics)                    │ │   │
│  │  │  ✓ App-specific CSV (dating apps, ride-hailing)                │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │          ☁  Drag and drop device data file here                │ │   │
│  │  │                     or  [ Browse Files ]                        │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  Data Source / App                                                   │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │  Auto-detect                                               ▾  │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  │  Options: Auto-detect | WhatsApp | Telegram | Cellebrite UFED        │   │
│  │           | iMessage | Email | Instagram | Android Backup | SQLite   │   │
│  │                                                                      │   │
│  │  Device Platform                    Belongs To                       │   │
│  │  ┌──────────────────────────────┐   ┌─────────────────────────────┐ │   │
│  │  │  Auto-detect               ▾ │   │  Victim                   ▾ │ │   │
│  │  └──────────────────────────────┘   └─────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  ⚠ Sensitivity Notice                                               │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  ⚠ Device data contains sensitive personal content.           │ │   │
│  │  │    All message text will be:                                   │ │   │
│  │  │    • PII-stripped (names → [CONTACT_1], [CONTACT_2])           │ │   │
│  │  │    • Stored only in masked form in analysis outputs            │ │   │
│  │  │    • Original text locked in encrypted storage                 │ │   │
│  │  │    • Sentiment-classified (POSITIVE/NEUTRAL/NEGATIVE/          │ │   │
│  │  │      DISTRESSED/THREATENING) — not full text used in analysis  │ │   │
│  │  │    • Search queries redacted — accessible to Lead              │ │   │
│  │  │      Investigator+ only                                        │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  Fields that will be extracted:                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  ✦ Message timestamp           ✦ Event type (sent/received)   │ │   │
│  │  │  ✦ App name                    ✦ Content sentiment             │ │   │
│  │  │  ✦ Counterparty (masked)       ✦ Deleted message flag         │ │   │
│  │  │  ✦ Media type                  ✦ Platform (Android/iOS)       │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  Hypothesis Signals: DISTRESSED content → suicide · THREATENING →   │   │
│  │  homicide · farewell message → suicide · deleted msgs → homicide     │   │
│  │  Feeds: Digital Timeline → Anomaly Detector → Hypothesis Manager     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## UPLOAD TAB — Category F: Scene & Environmental Documents

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  [A] Autopsy  [B] CDR  [C] Location  [D] Financial  [E] Device  [F] Scene   │
│                                                               ───────        │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  🔍 Category F — Scene & Environmental Documents                    │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  Scene examination reports, temperature logs, first responder        │   │
│  │  reports, photo EXIF metadata, witness statement metadata.           │   │
│  │                                                                      │   │
│  │  Accepted Formats                                                    │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  ✓ PDF (scene examination / FSL report / first responder)      │ │   │
│  │  │  ✓ DOCX (witness statement — content masked, metadata only)    │ │   │
│  │  │  ✓ CSV (temperature logger / IoT sensor data)                  │ │   │
│  │  │  ✓ JPG / PNG (EXIF timestamp + GPS extracted, image NOT used)  │ │   │
│  │  │  ✓ TXT (scene notes)                                           │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │          ☁  Drag and drop scene document here                  │ │   │
│  │  │                     or  [ Browse Files ]                        │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  Document Sub-type                                                   │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │  Auto-detect                                               ▾  │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  │  Options: Auto-detect | First Responder Report | FSL Scene Report    │   │
│  │           | Temperature Logger CSV | Witness Statement               │   │
│  │           | Crime Scene Photos (EXIF) | Scene Sketch                 │   │
│  │                                                                      │   │
│  │  ── Optional Manual Overrides (if scene details known upfront) ───  │   │
│  │                                                                      │   │
│  │  Scene Type               Discovery Time                            │   │
│  │  ┌──────────────────────┐  ┌────────────────────────────────────┐  │   │
│  │  │  INDOOR            ▾ │  │  07/05/2026  14:00              📅 │  │   │
│  │  └──────────────────────┘  └────────────────────────────────────┘  │   │
│  │  [INDOOR | OUTDOOR | VEHICLE | PUBLIC]                              │   │
│  │                                                                      │   │
│  │  Ambient Temperature at Scene    Humidity (%)                       │   │
│  │  ┌──────────────────────────┐    ┌─────────────────────────────┐   │   │
│  │  │  18.0  °C                │    │  55  %                      │   │   │
│  │  └──────────────────────────┘    └─────────────────────────────┘   │   │
│  │                                                                      │   │
│  │  Was heating/cooling ON at scene?    Windows open?                  │   │
│  │  ○ Yes   ● No   ○ Unknown            ○ Yes   ● No   ○ Unknown       │   │
│  │                                                                      │   │
│  │  ⚠ These values directly affect TOD estimation accuracy.            │   │
│  │    If a temperature logger CSV is available, upload it above —      │   │
│  │    it provides the most accurate ambient temperature series.        │   │
│  │                                                                      │   │
│  │  Fields that will be extracted:                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  ✦ Ambient temp series (for Henssge extended model)           │ │   │
│  │  │  ✦ Discovery time · First responder arrival time              │ │   │
│  │  │  ✦ Signs of struggle · Door lock state · Blood spatter        │ │   │
│  │  │  ✦ Items near body · Body position (corroboration)            │ │   │
│  │  │  ✦ Scene sealed time · Photo EXIF timestamps + GPS            │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │  Feeds: TOD Agent (ambient temp) · Autopsy Agent (corroboration)    │   │
│  │         Hypothesis Manager (signs of struggle, locked room, etc.)   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## POST-PARSE REVIEW: `/cases/:id/evidence/:fileId/review`
### Sub-page A — Autopsy Extraction Review

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ⬡ AIVENTRA  /  CASE-2026-001  /  Evidence Review                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ← Back to Case                                                             │
│                                                                             │
│  📄 PME_Kumar_2026.pdf  ·  Category A — Autopsy Report  ·  2.1 MB          │
│  OCR confidence: 91%  ·  Schema detected: State Hospital Format             │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Extracted Fields — Review & Confirm                                 │  │
│  │  ─────────────────────────────────────────────────────────────────  │  │
│  │  Agents have extracted these fields. Review and correct if needed.   │  │
│  │                                                                      │  │
│  │  ▼ SECTION 1: Identification & Metadata                   [verify]  │  │
│  │  ┌────────────────────────────────────────────────────────────────┐ │  │
│  │  │  Pathologist Name    [Dr. R. Sharma]              ✓ Extracted  │ │  │
│  │  │  Autopsy Date        [2026-05-07]                 ✓ Extracted  │ │  │
│  │  │  Report Reference    [PME/2026/04721]             ✓ Extracted  │ │  │
│  │  │  Examining Agency    [State Forensic Lab, Delhi]  ✓ Extracted  │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                      │  │
│  │  ▼ SECTION 2: Cause & Manner of Death             ⚠ Review Needed  │  │
│  │  ┌────────────────────────────────────────────────────────────────┐ │  │
│  │  │  Cause 1a   [Haemorrhagic shock            ]  ✓ Extracted      │ │  │
│  │  │  Cause 1b   [Stab wound to thorax          ]  ✓ Extracted      │ │  │
│  │  │  Cause 1c   [— (none)                      ]                   │ │  │
│  │  │  Cause 2    [Hypertension                  ]  ✓ Extracted      │ │  │
│  │  │                                                                 │ │  │
│  │  │  Manner of Death                                                │ │  │
│  │  │  ┌──────────────────────────────────────────────────────────┐  │ │  │
│  │  │  │  HOMICIDE                                              ▾  │  │ │  │
│  │  │  └──────────────────────────────────────────────────────────┘  │ │  │
│  │  │  [HOMICIDE | SUICIDE | ACCIDENTAL | NATURAL | UNDETERMINED]    │ │  │
│  │  │  Extraction confidence: 0.91  ⚠ Confirm this value            │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                      │  │
│  │  ▼ SECTION 3: Postmortem Signs (TOD Inputs)              ✓ All OK  │  │
│  │  ┌────────────────────────────────────────────────────────────────┐ │  │
│  │  │  Rigor Mortis Stage    [FULL              ▾]  ✓ Extracted      │ │  │
│  │  │  Livor Mortis Stage    [EARLY             ▾]  ✓ Extracted      │ │  │
│  │  │  Livor Distribution    [posterior, fixed    ]  ✓ Extracted     │ │  │
│  │  │  Decomposition Stage   [NONE              ▾]  ✓ Extracted      │ │  │
│  │  │  Algor Mortis Notes    [Body cold to touch  ]  ✓ Extracted     │ │  │
│  │  │                                                                 │ │  │
│  │  │  Rectal Temp (°C)   [30.0]  Measured At  [2026-05-07 14:00]   │ │  │
│  │  │  Body Weight (kg)   [70.0]                                     │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                      │  │
│  │  ▼ SECTION 4: External Examination                        ✓ All OK │  │
│  │  ┌────────────────────────────────────────────────────────────────┐ │  │
│  │  │  Injuries Present    [✓ Yes]                                   │ │  │
│  │  │  Injury List         [stab wound L thorax, contusion R temple] │ │  │
│  │  │  Defensive Wounds    [✓ Yes]  Detail: [Linear cuts on R palm ] │ │  │
│  │  │  Clothing State      [Torn, bloodstained                      ]│ │  │
│  │  │  Position Found      [Supine on bedroom floor                 ]│ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                      │  │
│  │  ▼ SECTION 5: Internal Examination                        ✓ All OK │  │
│  │  ▼ SECTION 6: Toxicology                                 ✓ All OK  │  │
│  │  ▼ SECTION 7: Scene / Environmental                      ✓ All OK  │  │
│  │                                                                      │  │
│  │  ─────────────────────────────────────────────────────────────────  │  │
│  │  Extraction Quality: 94%  ·  39 / 41 fields extracted               │  │
│  │  Missing: cause_1c (expected none), tox_report_reference            │  │
│  │                                                                      │  │
│  │          [ ← Back ]    [ Save Corrections & Run Analysis → ]        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## POST-PARSE REVIEW — Category B: CDR Column Mapping

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ⬡ AIVENTRA  /  CASE-2026-001  /  Evidence Review — CDR                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  📊 CDR_Victim_Airtel.csv  ·  Category B — CDR  ·  1.2 MB                  │
│  Operator detected: AIRTEL  ·  12,847 rows  ·  May 1–9, 2026               │
│  Normalization confidence: 97%                                              │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Column Mapping — Review                                             │  │
│  │  ─────────────────────────────────────────────────────────────────  │  │
│  │  Canonical Field         ←   Detected Source Column    Confidence   │  │
│  │  ─────────────────────────────────────────────────────────────────  │  │
│  │  event_timestamp         ←   Date + Time               ✓  99%       │  │
│  │  event_type              ←   CallType                  ✓  98%       │  │
│  │  duration_seconds        ←   Duration                  ✓  99%       │  │
│  │  counterparty_msisdn     ←   CalledNumber              ✓  98%       │  │
│  │  cell_tower_id           ←   TowerID                   ✓  99%       │  │
│  │  tower_latitude          ←   TowerLatitude             ✓  99%       │  │
│  │  tower_longitude         ←   TowerLongitude            ✓  99%       │  │
│  │  imei                    ←   IMEI                      ✓  99%       │  │
│  │  data_volume_kb          ←   (not in this file)        ─  N/A       │  │
│  │                                                                      │  │
│  │  ─────────────────────────────────────────────────────────────────  │  │
│  │  Data Preview (first 5 rows — masked)                                │  │
│  │  ┌────────────────────────────────────────────────────────────────┐ │  │
│  │  │  Timestamp            Type   Dur  Party        Tower           │ │  │
│  │  │  2026-05-07 02:15:33  MOC    127  98XXXXXX67   DEL-NW-0045    │ │  │
│  │  │  2026-05-07 02:18:44  SMS_MO 0    98XXXXXX67   DEL-NW-0045    │ │  │
│  │  │  2026-05-07 08:33:12  MISSED 0    (MISSED)     DEL-SE-0187    │ │  │
│  │  │  2026-05-07 10:14:22  MTC    43   98XXXXXX91   DEL-SE-0187    │ │  │
│  │  │  2026-05-07 12:07:55  MOC    312  98XXXXXX04   DEL-SE-0187    │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                      │  │
│  │  Quick Stats                                                         │  │
│  │  • Total events: 12,847                                              │  │
│  │  • Unique contacts (masked): 87                                      │  │
│  │  • Date range: May 1–9, 2026                                         │  │
│  │  • Silence windows >4h detected: 3 (will be flagged as anomalies)   │  │
│  │  • Tower location coverage: 94% of events have coordinates          │  │
│  │                                                                      │  │
│  │          [ ← Back ]    [ Confirm Mapping & Proceed → ]              │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## EVIDENCE QUALITY GATE — Shown Before Analysis Starts

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ⬡ AIVENTRA  /  CASE-2026-001  /  Pre-Analysis Gate                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Evidence Quality Check                                                     │
│  All files pass 3 quality gates before analysis begins.                     │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Gate 1: Integrity (SHA-256 · MIME · Malware · Size)                │  │
│  │  ┌────────────────────────────────────────────────────────────────┐ │  │
│  │  │  PME_Kumar_2026.pdf      ✓ PASS  (SHA-256 verified, clean)    │ │  │
│  │  │  CDR_Victim_Airtel.csv   ✓ PASS  (SHA-256 verified, clean)    │ │  │
│  │  │  Scene_Report.pdf        ✓ PASS  (SHA-256 verified, clean)    │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                      │  │
│  │  Gate 2: Parsability (readable · encoding · timestamps · schema)    │  │
│  │  ┌────────────────────────────────────────────────────────────────┐ │  │
│  │  │  PME_Kumar_2026.pdf      ✓ PASS  (scanned PDF → OCR 91%)      │ │  │
│  │  │  CDR_Victim_Airtel.csv   ✓ PASS  (12,847 rows, schema 97%)    │ │  │
│  │  │  Scene_Report.pdf        ✓ PASS  (text-based, schema 89%)     │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                      │  │
│  │  Gate 3: Usefulness (per-agent minimum requirements)                │  │
│  │  ┌────────────────────────────────────────────────────────────────┐ │  │
│  │  │  TOD Agent        ✓ PASS   rectal_temp + rigor + livor found  │ │  │
│  │  │  Timeline Agent   ✓ PASS   12,847 events with timestamps      │ │  │
│  │  │  Hypothesis Mgr   ✓ PASS   8 Bayesian signals available       │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                      │  │
│  │  ─────────────────────────────────────────────────────────────────  │  │
│  │  Evidence Coverage:  A ✓  B ✓  C ─  D ─  E ─  F ✓                  │  │
│  │  Expected Quality:   ████████░░  GOOD                               │  │
│  │  Mode:  TOD = PHYSICS_ONLY  ·  Hypothesis = MEDIUM-HIGH             │  │
│  │                                                                      │  │
│  │  ⚠ No location data (Category C). Scene presence analysis           │  │
│  │    will not be available. Upload CDR tower data for partial          │  │
│  │    location coverage.                                                │  │
│  │                                                                      │  │
│  │  ℹ Adding Category C, D, E files will improve analysis quality.     │  │
│  │  [ + Add More Evidence ]           [ Begin Analysis → ]             │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## EVIDENCE MANAGER — `/cases/:id/evidence` (Post-Creation)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ⬡ AIVENTRA  /  CASE-2026-001  /  Evidence                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Kumar Homicide Investigation — Evidence Files       [ + Add Evidence ]     │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Filter: [All ▾]  [All Status ▾]              Sort: [Uploaded ▾]    │  │
│  ├──────────────────────────────────────────────────────────────────────┤  │
│  │                                                                      │  │
│  │  📄  PME_Kumar_2026.pdf                                             │  │
│  │      Category A · Autopsy Report · 2.1 MB                          │  │
│  │      Uploaded May 9, 02:14 IST · by Arjun Sharma                   │  │
│  │      ✓ PROCESSED · OCR 91% · 39/41 fields extracted                │  │
│  │      SHA-256: a3f8c2...d41e                    [ View Extraction ]  │  │
│  │  ────────────────────────────────────────────────────────────────── │  │
│  │                                                                      │  │
│  │  📊  CDR_Victim_Airtel.csv                                          │  │
│  │      Category B · CDR Records · 1.2 MB                             │  │
│  │      Uploaded May 9, 02:17 IST · by Arjun Sharma                   │  │
│  │      ✓ PROCESSED · 12,847 events · Airtel format                   │  │
│  │      SHA-256: f7d3a1...b82c                    [ View Preview ]    │  │
│  │  ────────────────────────────────────────────────────────────────── │  │
│  │                                                                      │  │
│  │  📄  Scene_Report.pdf                                               │  │
│  │      Category F · Scene Report · 0.8 MB                            │  │
│  │      Uploaded May 9, 02:19 IST · by Arjun Sharma                   │  │
│  │      ✓ PROCESSED · ambient_temp extracted · discovery time found   │  │
│  │      SHA-256: 2c9e7f...a14d                    [ View Extraction ]  │  │
│  │  ────────────────────────────────────────────────────────────────── │  │
│  │                                                                      │  │
│  │  Evidence Coverage                                                   │  │
│  │  A ✓ Autopsy    B ✓ CDR    C ─ Location    D ─ Financial            │  │
│  │  E ─ Device     F ✓ Scene                                           │  │
│  │                                                                      │  │
│  │  [ + Upload Location Data ]  [ + Upload Financial Records ]         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

*All diagrams reflect the AIVENTRA Evidence & Input Specification v1.0*
*6 Categories · 11 Accepted Formats · 3 Quality Gates · Full PII Masking*
