<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# will it contain all pages frontend it feels like theres something missing and thus check everything once more and make sure that the design is compatible with the backend and the architecture

There are **25 total pages** — you had 8 so far, with **17 missing**. Here is the complete, corrected master inventory with a fresh prompt for every page, backend-compatible and consistent.

***

## ✅ COMPLETE MASTER PAGE INVENTORY

**25 pages total across 6 groups. Previously designed: 8. Newly added: 17.**

***

## 🔴 MISSING PAGES — NEW PROMPTS


***

### PAGE 1B — `/login/mfa` — MFA TOTP Step

```
DESIGN BRIEF: AIVENTRA MFA Verification Screen

[Apply AIVENTRA Design System]

This is STEP 2 of login. User has passed password check.
Same two-column layout as /login.

LEFT COLUMN: Same as login page (logo, tagline, feature bullets)

RIGHT COLUMN CARD:
- Back link top-left: "← Back to login" in #6366F1, 13px
- Shield icon (indigo, 32px) centered above heading
- Heading: "Two-Factor Authentication" 20px weight 600 white
- Subtext: "Enter the 6-digit code from your authenticator app." 
  #9CA3AF 13px

6-DIGIT OTP INPUT:
6 individual square input boxes in a row (48px × 56px each, 8px gap):
  [ _ ] [ _ ] [ _ ] [ _ ] [ _ ] [ _ ]
- Each box: #0F1623 bg, 1px #374151 border, 20px font white bold centered
- Active box: #6366F1 border with glow
- On fill: auto-focus moves to next box
- Paste support: pasting 6 digits auto-fills all

TIMER ROW (below OTP inputs):
  "Code expires in " + countdown "00:28" in amber
  Progress bar below: thin 4px height, amber fill shrinking
  
RESEND ROW:
  "Didn't receive a code?" #4B5563 · "Resend" #6366F1 (disabled until 
  timer expires, then clickable)

VERIFY BUTTON:
Full width, "Verify & Sign In →", indigo filled, 44px, 
grey/disabled state if OTP incomplete

ERROR STATE (wrong code):
Red border on all 6 boxes + shake animation
"⚠ Invalid code. 2 attempts remaining." in red below inputs

SECURITY NOTE at bottom:
Lock icon + "TOTP via Google Authenticator · MFA required for all roles"
#4B5563 12px centered
```


***

### PAGE 1C — `/forgot-password`

```
DESIGN BRIEF: AIVENTRA Forgot Password Screen

[Apply AIVENTRA Design System]

Same two-column layout as login.

RIGHT COLUMN CARD:
- "← Back to login" link top
- Key icon (indigo, 28px)
- Heading: "Reset your password" 20px 600 white
- Subtext: "Enter your official email. We'll send a reset link if 
  the account exists." #9CA3AF

Email input: full width, envelope icon left
"Send Reset Link" button: indigo filled full width

SUCCESS STATE (after submit, regardless of whether email exists):
Replace form with:
  ✓ green checkmark circle (48px)
  "If this email is registered, a reset link has been sent."
  "Check your official inbox." in #9CA3AF
  "← Return to login" indigo link

Note: No confirmation of whether email exists (security best practice)
```


***

### PAGE 5C — `/cases/:id/evidence/:fileId/review` — Cat C: Location Preview

```
DESIGN BRIEF: AIVENTRA Evidence Review — Location Data Preview

[Apply AIVENTRA Design System]

FILE BANNER:
Map-pin icon (green) + filename + "Category C · Location Data"
Badges: "Source: Google Timeline" | "4,821 points" | "May 1–9, 2026"

TWO-COLUMN LAYOUT (55% / 45%):

LEFT COLUMN:

CARD 1 — SOURCE DETECTION:
  "Source Detected: GOOGLE TIMELINE" green badge
  Fields verified row:
    timestamp ✓ · latitude ✓ · longitude ✓ · accuracy ✓
    speed ✓ · activity_type ✓ · altitude ✓

CARD 2 — SAMPLE DATA TABLE (5 rows):
  Columns: Timestamp | Lat | Lon | Activity | Speed | Accuracy
  Values: monospace, masked (coordinates shown as-is — GPS is not PII)
  5 rows of real-format sample data shown

CARD 3 — SCENE PROXIMITY SETTINGS:
  "Crime Scene Reference" section
  Lat input + Lon input (prefilled if set earlier)
  "[ 🗺 Pick on Map ]" ghost button (opens modal)
  Proximity threshold slider: 50m → 500m, default 200m
  Preview: "Events within 200m of scene: [calculating...]"

RIGHT COLUMN:

CARD 1 — MOVEMENT SUMMARY:
  Stats in 2×2 grid:
    "4,821" total fixes | "INDOOR/OUTDOOR" dominant activity
    "0" impossible movements | "2" location jumps flagged
  
  Activity type distribution bars:
    STILL       ████████████  68%
    IN_VEHICLE  ████          18%
    WALKING     ██            10%
    UNKNOWN     █             4%

CARD 2 — TIMELINE COVERAGE:
  "Location data covers:" label
  Horizontal time bar showing coverage vs gaps:
    May 1 ████████░░████████░████████ May 9
    Gaps shown as white spaces — hover shows "No data: May 3 14:00–19:00"
  
  "Last GPS fix before silence:" 
  "2026-05-07 02:19:44 · 28.7041, 77.1025" in monospace green

CARD 3 — TOD INTERSECTION PREVIEW:
  Indigo tinted box:
  "TOD Window: 23:30 May 6 → 07:00 May 7"
  "GPS fixes in TOD window: 47 points"
  "Device at scene during TOD: ✓ YES (38 of 47 fixes within 200m)"
  → "SCENE_PRESENCE flag will be raised"

FOOTER:
"← Back" | "Confirm & Proceed →" indigo button
```


***

### PAGE 5D — Cat D: Financial Preview

```
DESIGN BRIEF: AIVENTRA Evidence Review — Financial Records Preview

[Apply AIVENTRA Design System]

FILE BANNER:
Credit-card icon (amber) + filename + "Category D · Financial Records · 0.9 MB"
Badges: "HDFC Bank — Auto-detected 96%" | "234 transactions" | "Apr 7–May 7, 2026"

TWO-COLUMN LAYOUT (55% / 45%):

LEFT COLUMN:

CARD 1 — COLUMN MAPPING TABLE:
Same style as CDR mapping page.
Canonical Field → Source Column → Sample → Confidence

  timestamp         | Date            | 07/05/26     | ✓ 98%
  transaction_type  | (inferred)      | DEBIT        | ✓ 95%
  amount_inr        | Withdrawal Amt. | 10,000.00    | ✓ 99%
  balance_after     | Closing Balance | 77,500.00    | ✓ 99%
  narration_cleaned | Narration       | ATM WDL...   | ✓ 94%
  channel           | (inferred)      | ATM          | ✓ 91%
  location_hint     | Narration       | PITAMPURA DEL| ✓ 78% ⚠
  counterparty_masked | Narration     | [CONTACT_1]  | ✓ 89%

CARD 2 — DATA PREVIEW (5 rows, masked):
  Date       | Type           | Amount      | Channel | Balance After
  07/05/26   | ATM_WITHDRAWAL | ₹10,000     | ATM     | ₹77,500
  07/05/26   | UPI_RECEIVE    | +₹50,000    | UPI     | ₹87,500
  06/05/26   | NEFT_OUT       | ₹2,50,000   | NEFT    | ₹37,500
  05/05/26   | DEBIT          | ₹1,200      | CARD    | ₹2,87,500
  04/05/26   | CREDIT         | +₹15,000    | UPI     | ₹2,88,700

Amber note: "Counterparty names replaced with [CONTACT_1] etc."

RIGHT COLUMN:

CARD 1 — FINANCIAL STATS:
  4 stat boxes:
    "234" total transactions
    "₹2,60,000" largest single transaction
    "3" large transactions (>₹50K threshold)
    "1" ⚠ anomalous timing (3AM transaction)

CARD 2 — TRANSACTION TYPE BREAKDOWN:
  Horizontal bars:
    DEBIT/CARD    ███████  45%
    UPI_SEND      █████    30%
    ATM_WITHDRAWAL ███     15%
    NEFT_OUT      █        6%
    CREDIT        █        4%

CARD 3 — 6 PATTERN RULES PREVIEW:
  Each rule with status:
  ✓ Large withdrawal before death    WILL CHECK  (threshold ₹50K)
  ✓ Financial activity near TOD      WILL CHECK  (±2h window)
  ✓ ATM location corroboration       WILL CHECK  
  ✓ Unusual transfer out             WILL CHECK  (2σ threshold)
  ✓ Ceased financial activity        WILL CHECK
  ⚠ Incoming credit after death      WILL CHECK  (1 suspicious tx found)

Large Transaction Threshold override input: "₹ [50,000]" — editable

FOOTER: "← Back" | "Confirm & Proceed →"
```


***

### PAGE 5E — Cat E: Device Data Preview

```
DESIGN BRIEF: AIVENTRA Evidence Review — Device & App Data Preview

[Apply AIVENTRA Design System]

FILE BANNER:
Smartphone icon (violet) + "WhatsApp_Export_Ravi.txt" + "Category E · Device Data"
Badges: "WhatsApp — Auto-detected 99%" | "847 messages" | "App: WhatsApp"
Warning badge: "⚠ Sensitive content — PII masking active"

TWO-COLUMN LAYOUT:

LEFT COLUMN:

CARD 1 — SOURCE DETECTION:
  "App: WhatsApp Export (.txt)" — large pill green
  Platform: ANDROID (inferred from export format)
  Belongs to: [Victim ▾] dropdown
  Conversation with: [CONTACT_1] (masked)

CARD 2 — CONTENT MASKING NOTICE:
  Full-width amber box (amber left border 3px, #F59E0B10 bg):
  "⚠ Content Masking Applied
   All message text has been PII-stripped before display.
   Real names → [CONTACT_1], [CONTACT_2]
   Original text: LOCKED in encrypted storage.
   Agents will only receive: masked text + sentiment label."

CARD 3 — SAMPLE EVENTS TABLE (5 rows, masked):
  Timestamp          | Type           | Content (masked, 80 chars)  | Sentiment
  2026-05-07 02:17   | MESSAGE_SENT   | "yeah can we talk tomorrow" | NEGATIVE
  2026-05-07 02:19   | MESSAGE_SENT   | "not really. later"         | DISTRESSED ⚠
  2026-05-07 02:20   | MESSAGE_RECEIVED| "Sure. you ok?"            | NEUTRAL
  2026-05-07 09:45   | MESSAGE_RECEIVED| "[C1]: Hello?"             | NEUTRAL
  2026-05-07 11:23   | MESSAGE_RECEIVED| "[C1]: Please call me back"| NEUTRAL

Row "DISTRESSED" has red-tinted row background
Tooltip on DISTRESSED: "Classified by sentiment model as showing signs of 
hopelessness or farewell. This signal will be sent to Hypothesis Manager."

CARD 4 — DELETED MESSAGE CHECK:
  (only shown if source is Cellebrite/SQLite)
  Grey info: "WhatsApp .txt export — deleted message detection not available.
  Upload Cellebrite UFED or SQLite dump for deleted message analysis."

RIGHT COLUMN:

CARD 1 — SENTIMENT DISTRIBUTION:
  Donut-style breakdown (or horizontal bars):
    NEUTRAL    ████████████  61%
    NEGATIVE   ████          20%
    DISTRESSED ███           14%  ← amber highlight
    POSITIVE   █             4%
    THREATENING ─             1%  ← red highlight if present

CARD 2 — COMMUNICATION TIMELINE:
  Same mini-timeline strip as CDR review
  Events plotted as dots by type
  Last message highlighted: "02:20 — Last outgoing message"
  Silence window visible: "02:20 → 14:00 — NO ACTIVITY (11h 40m)"
  
CARD 3 — HYPOTHESIS SIGNALS PREVIEW:
  Indigo tinted box:
  Signals generated from this file:
    ● DISTRESSED content detected (14% of messages)    → LR_SUICIDE +
    ● Communication cessation at 02:20                 → TOD corroboration
    ● Last outgoing message: 02:20                     → Alive-time anchor
    ✗ No THREATENING content detected
    ✗ No farewell message detected
    ✗ No deleted messages (source limitation)

SEARCH QUERY ACCESS NOTICE (small box at bottom of right col):
  "🔒 Search query events (if any) are redacted.
  Accessible to Lead Investigator+ only with audit log."

FOOTER: "← Back" | "Confirm & Proceed →"
```


***

### PAGE 5F — Cat F: Scene Report Extraction Review

```
DESIGN BRIEF: AIVENTRA Evidence Review — Scene Report Extraction

[Apply AIVENTRA Design System]

FILE BANNER:
Search icon (blue) + "Scene_Report_FirstResponder.pdf" + "Category F · Scene Report"
Badges: "First Responder Report — detected" | "Text-based PDF" | "14 fields extracted"

TWO-COLUMN LAYOUT:

LEFT COLUMN — EXTRACTED FIELDS ACCORDION:

SECTION 1: Scene Parameters (TOD-Critical) — ⚠ amber badge
  (TOD IMPACT BOX at top: "🌡 These fields directly control TOD Agent accuracy")
  
  Grid of extracted fields:
    Scene Type         [INDOOR          ▾]  ✓ Extracted
    Discovery Time     [2026-05-07 14:00 ]  ✓ Extracted
    Ambient Temp (°C)  [18.0             ]  ✓ Extracted  ← CRITICAL
    Humidity (%)       [55               ]  ✓ Extracted
    Windows Open?      ○ Yes  ● No  ○ Unknown  ✓ Extracted
    Heating/Cooling ON?○ Yes  ● No  ○ Unknown  ✓ Extracted
    Body Surface       [BED              ▾]  ✓ Extracted

  TEMPERATURE LOGGER NOTE:
    Blue info box: "No temperature logger CSV uploaded.
    Using single ambient temp value (18.0°C).
    Upload a CSV logger for the extended Henssge model 
    with variable ambient temperature (more accurate)."
    [ + Upload Temperature Logger ] — ghost button

SECTION 2: Hypothesis Signals — ✓ green badge
    Signs of Struggle  [✓ Yes]            ⚠ HOMICIDE signal
    Door Lock State    [Locked from inside]  → affects hypothesis
    Blood Spatter      [✓ Yes]
    Footprints Present [✗ No]
    Items Near Body    [Mobile phone, empty glass]
    Body Position      [Supine on bedroom floor]
    First Responder Arrival [2026-05-07 14:22]
    Scene Sealed At    [2026-05-07 15:00]

SECTION 3: Photo EXIF Metadata (if photos uploaded):
    5 photos detected:
    Photo 1: 2026-05-07 14:23 · 28.7041, 77.1025 · Device: iPhone 15
    Photo 2: 2026-05-07 14:25 · 28.7041, 77.1025 · Device: iPhone 15
    [+ 3 more...]
    "ℹ Image content is NOT processed — only EXIF metadata used."

RIGHT COLUMN:

CARD 1 — TOD AGENT IMPACT:
  Summary of what TOD agent receives from this file:
    ambient_temp_celsius:     18.0  ← feeds Henssge
    clothing_insulation:      MEDIUM
    body_covered:             NONE
    immersion:                NONE
    scene_type:               INDOOR
    found_dead_time:          2026-05-07 14:00  ← prior upper bound
  
  TOD Mode impact: "Ambient temp available → PHYSICS_ONLY mode enabled"
  Quality badge: "GOOD" amber

CARD 2 — HYPOTHESIS SIGNALS FROM SCENE:
  Table: Signal → Value → Direction
    signs_of_struggle    TRUE     → LR_HOMICIDE +
    door_lock_state      Locked   → Locked-room flag ⚠
    blood_spatter        TRUE     → LR_HOMICIDE +
    footprints_present   FALSE    → inconclusive

CARD 3 — CHAIN OF CUSTODY ANCHOR:
  "Scene sealed at 15:00 — all evidence collected before seal"
  "First responder arrived at 14:22 — 22 min after discovery"
  Small chain icon with "Custody event will be logged on confirm"

FOOTER: "← Back" | "Confirm & Proceed →"
```


***

### PAGE 9 — `/cases/:id` — Full Timeline Tab

```
DESIGN BRIEF: AIVENTRA Case — Full Digital Timeline Tab

[Apply AIVENTRA Design System]

This is the most data-dense page in the system.

TOPBAR + Case Header (as per Overview page)
TABS: [Overview] [Timeline ←active] [TOD] [Anomalies] [Hypothesis] [Evidence] [Report] [Replay]

FILTER BAR (full-width row below tabs):
  Date Range: [May 6 ←→ May 9]  Event Type: [All Types ▾]  
  Category: [All Evidence ▾]  Show Anomalies Only: [toggle off]
  [Reset Filters]

MAIN LAYOUT (left 70%, right 30%):

LEFT SIDE — MASTER TIMELINE:

TIMELINE SCALE CONTROL:
  "[ Day view ] [ Hour view ] [ 6h window ]" toggle pills
  Zoom: [−] [═══════════════] [+]

VERTICAL TIMELINE STRIP (scrollable, hour-by-hour):
  
  Date header: "MAY 6, 2026 — TUESDAY"
  
  Each hour row: 
    Time label (left, monospace) + horizontal event lane (right)
    Events shown as colored pills/dots on the lane
  
  EVENT PILL COLORS (by category):
    📞 Blue   — CDR call events
    💬 Violet — CDR SMS events  
    📍 Green  — Location events
    💰 Amber  — Financial events
    📱 Purple — Device/app events
    🔴 Red    — Anomaly flagged events (pulsing ring)
  
  SPECIAL MARKERS:
    ──── dashed green line: "Last seen alive 01:00"
    ★ red star + vertical line: "TOD Estimate 03:30"
    ──── dashed amber line: "Body found 14:00"
    ░░░░ indigo shaded band over 23:30–07:00: "TOD 95% Window"
  
  SAMPLE ROWS:
    02:15 │ ●[MOC 127s → 98XXX67 DEL-NW-0045]
    02:17 │ ●[SMS sent → 98XXX67] ●[WhatsApp sent NEGATIVE]
    02:19 │ ●[SMS sent] ●[WhatsApp sent DISTRESSED]⚠
    02:20 │ ●[WhatsApp sent] ← Last message
    [SILENCE BAND: 02:20 → 14:00 — 11h 40min gap, red background tint]
    14:00 │ ◆ Body discovered
    14:22 │ ◆ First responder arrival

RIGHT SIDE — EVENT INSPECTOR (sticky):
  When user clicks an event, this panel shows:
  
  "Event Detail" header
  
  Event type badge + timestamp
  Raw canonical values table:
    event_type:        MOC
    timestamp:         2026-05-07 02:15:33 UTC
    duration_seconds:  127
    counterparty:      98XXXXXX67 (masked)
    cell_tower:        DEL-NW-0045
    coordinates:       28.7041, 77.1025
    anomaly_score:     0.82 ⚠ HIGH
  
  "Anomaly Flags on this event:" section:
    [LATE_NIGHT_CALL] [LAST_CONTACT_BEFORE_SILENCE]
  
  "Hypothesis Impact:" section:
    → Contributes to HOMICIDE signal: last_contact_before_death
  
  "Agent that produced this:" 
    Digital Timeline Agent · Rule 5 · CDR Source

  Mini-map below (if location event):
    Small map showing tower/GPS location dot
    Scene location marker for reference
```


***

### PAGE 10 — TOD Analysis Tab

```
DESIGN BRIEF: AIVENTRA Case — TOD Analysis Tab

[Apply AIVENTRA Design System]

TABS: [...] [TOD Analysis ←active] [...]

THREE-COLUMN TOP ROW:

COL 1 — RESULT CARD:
  "TIME OF DEATH ESTIMATE" 10px uppercase #4B5563
  "03:30 AM" — 36px weight 800 white
  "May 7, 2026" — 16px #9CA3AF
  Mode: "PHYSICS_ONLY" grey pill
  
  Interval band:
    ├────────────●────────────┤
   11:30 PM    03:30      07:00 AM
   (May 6)    (MODE)     (May 7)
   "95% Credible Interval — 7.5 hour window"

COL 2 — CONSISTENCY CHECKS:
  "Postmortem Sign Consistency" 11px uppercase
  4 rows with status icons:
    Rigor Mortis      ✓ CONSISTENT   (FULL → 8–36h ✓ matches)
    Livor Mortis      ✓ CONSISTENT   (EARLY → 2–12h ✓ matches)
    Decomposition     ✓ CONSISTENT   (NONE → <48h ✓ matches)
    Algor Mortis      ✓ CONSISTENT   (body cold → >6h ✓ matches)
  
  Overall: "All 4 signs consistent with estimated TOD window" green

COL 3 — COMPONENT WEIGHTS:
  "What Drove This Estimate" 11px uppercase
  Horizontal bars showing contribution weight:
    Henssge Core         ████████████  52%  (indigo)
    Heuristic Signs      █████         22%  (violet)
    Prior (Timeline)     ████          18%  (blue)
    ML Surrogate         ██            8%   (green)

SECTION 2: HENSSGE INPUTS (full width card):
  Title: "Physics Core — Henssge Inputs & Parameters"
  
  8-field grid:
    Rectal Temp (°C):       30.0     ← from Cat A autopsy
    Ambient Temp (°C):      18.0     ← from Cat F scene
    Body Weight (kg):       70.0     ← from Cat A
    Clothing Insulation:    MEDIUM   ← from Cat A/F
    Scene Type:             INDOOR   ← from Cat F
    Body Surface:           BED      ← from Cat F
    Body Covered:           NONE     ← from Cat A/F
    Measurement Time:       14:00    ← from Cat A

  Computed by Henssge:
    "PMI mean: 10.5 h · 95% range: [7.3 h, 13.7 h]"
    "TOD Henssge estimate: 03:30 AM [00:17–06:43]"
  
  Each field shows which evidence file it came from:
    [📄 PME_Kumar.pdf] [🔍 Scene_Report.pdf]

SECTION 3: MONTE CARLO DISTRIBUTION (full width):
  Title: "Posterior Distribution — Monte Carlo (10,000 samples)"
  
  Histogram chart:
    X-axis: Time (10 PM May 6 → 10 AM May 7)
    Y-axis: Density
    Bars: indigo gradient
    Shaded region: 95% CI in lighter indigo
    Vertical line: mode (03:30) in white
    Vertical dashed lines: 2.5% and 97.5% quantiles
  
  "Uncertainty sources: measurement noise ±0.5°C · 
   Henssge correction factor variance · ambient temp uncertainty"

SECTION 4: WARNINGS (if any):
  Amber warning cards for each warning:
    "TOD window is 7.5h wide — consider uploading Cat C 
     location data to narrow window with alive-time corroboration"
```


***

### PAGE 11 — Anomalies Tab

```
DESIGN BRIEF: AIVENTRA Case — Anomalies Tab

[Apply AIVENTRA Design System]

TABS: [...] [Anomalies ←active] [...]

SUMMARY ROW (3 stat cards):
  "12 Total Anomalies"  |  "3 CRITICAL (score >0.9)"  |  "2 In TOD Window"
  Card colors: grey | red | amber

FILTER ROW:
  [All Sources ▾] [All Severity ▾] [TOD Window Only: toggle] [Sort: Score ▾]

TWO-COLUMN LAYOUT (65% / 35%):

LEFT — ANOMALY LIST:
Each anomaly as a card (sorted by score desc):

ANOMALY CARD DESIGN:
  Left border 4px in severity color
  CRITICAL: red | HIGH: orange | MEDIUM: amber | LOW: blue

  CARD EXAMPLE 1 (CRITICAL):
    Score badge: "0.94 CRITICAL" red pill  +  "In TOD Window" amber pill
    Title: "Last outgoing communication before 11h silence"
    Detail: "Last CDR event: MOC call at 02:17 to 98XXXXXX67 (127s)
             Followed by silence until 14:00 discovery. 
             Duration: 11h 43min gap."
    Evidence source: [📞 CDR — Cat B] [📱 WhatsApp — Cat E]
    Rule: "Rule 5: Last communication before silence"
    
    Anomaly Methods row:
      Isolation Forest: ●●●●○ (4/5)  Autoencoder: 0.94 reconstruction error

  CARD EXAMPLE 2 (HIGH):
    "Distressed message content at 02:19" 
    Source: [📱 WhatsApp — Cat E]
    "Content sentiment: DISTRESSED — 'not really. later'"
    
  [+ more cards...]

RIGHT — HOTSPOT CORRELATOR PANEL (sticky):
  Title: "Hotspot Windows"
  Subtext: "Time windows where multiple anomalies cluster 
            AND overlap with TOD 95% band"
  
  HOTSPOT 1 (primary):
    Red glowing card:
    "🔥 PRIMARY HOTSPOT"
    Window: 02:15 — 02:20 (May 7)
    In TOD band: ✓ YES
    Anomalies in window: 4
      • Last outgoing call (0.94)
      • Last WhatsApp sent (0.91)
      • Distressed message (0.89)
      • Communication cessation (0.85)
    "HIGH investigative significance"
  
  HOTSPOT 2:
    Amber card:
    "SECONDARY HOTSPOT"
    Window: 23:47 May 6 (ATM withdrawal)
    In TOD band: Partially (within 95% window)
    Anomalies: 2
  
  Below: "Hotspot windows have been sent to Hypothesis Manager 
          as spatial-temporal signals."
```


***

### PAGE 12 — Hypothesis Tab

```
DESIGN BRIEF: AIVENTRA Case — Hypothesis Tab

[Apply AIVENTRA Design System]

TABS: [...] [Hypothesis ←active] [...]

TOP ROW — 4 HYPOTHESIS CARDS (equal width):

CARD DESIGN:
  Background: #111827, border colored by rank
  #1 rank card: indigo glow border

  HOMICIDE CARD (leading):
    "🏴 HOMICIDE" — 18px weight 800 red
    "79%" — 32px weight 800 white
    Small bar: ████████████░░ 79%
    "Rank #1 · 8 signals contributed"
    [View Signals ▾] (expands inline)
  
  ACCIDENT CARD:
    "ACCIDENT" amber, "12%", rank #2
  
  SUICIDE CARD:
    "SUICIDE" blue, "6%", rank #3
  
  NATURAL CARD:
    "NATURAL CAUSES" green, "3%", rank #4

SECTION 2 — BAYESIAN SIGNALS TABLE (full width):
  Title: "All Signals & Likelihood Ratio Contributions"
  
  Table columns:
    Signal | Source | Value | LR Applied | Direction | Confidence
  
  Rows (sorted by abs contribution):
    manner_of_death      Cat A  HOMICIDE   LR×15.0   ↑ HOMICIDE  0.91
    defensive_wounds     Cat A  TRUE       LR×3.2    ↑ HOMICIDE  0.87
    signs_of_struggle    Cat F  TRUE       LR×2.8    ↑ HOMICIDE  0.93
    last_contact_30min   Cat B  TRUE       LR×2.1    ↑ HOMICIDE  0.82
    comm_cessation_tod   Cat B  MATCHES    LR×1.4    neutral     0.75
    distressed_content   Cat E  0.14 score LR×0.8    ↑ SUICIDE   0.71
    drug_trace           Cat A  Alprazolam LR×0.6    ↑ SUICIDE   0.68
    no_financial_cease   Cat D  —          LR×0.5    ↑ ACCIDENT  0.55
  
  Color coding: HOMICIDE rows red tint, SUICIDE rows blue tint

SECTION 3 — TRAJECTORY CHART (full width):
  Title: "Hypothesis Evolution — As Evidence Was Processed"
  
  Line chart (time/processing order on X, probability on Y):
    4 lines in hypothesis colors
    X-axis steps: "After Cat A" | "After Cat B" | "After Cat F" 
                  | "After Hotspot" | "Final"
    Lines show probability shifting as evidence accumulates
    HOMICIDE line: starts 0.25 (uniform), climbs to 0.79
    Tooltip on hover: shows which evidence caused each jump

SECTION 4 — INVESTIGATOR NOTES:
  "Notes & Override" section (leadinvestigator+ only)
  Textarea: "Add investigator judgment..."
  "Override posterior?" toggle with reason field
  Audit note: "Any override is logged and included in report"
```


***

### PAGE 13 — Report Tab

```
DESIGN BRIEF: AIVENTRA Case — Report Tab

[Apply AIVENTRA Design System]

TABS: [...] [Report ←active] [...]

TWO-COLUMN LAYOUT (70% / 30%):

LEFT — REPORT PREVIEW:
  Full report rendered as styled document inside a white card
  (white bg #FFFFFF, black text — looks like a real document)
  
  REPORT DOCUMENT STYLE:
    Header: "AIVENTRA FORENSIC INTELLIGENCE REPORT"
    Case ID, Date, Prepared by, Classification
    CONFIDENTIAL watermark (diagonal, faint)
  
  Sections (collapsible in preview):
    1. Executive Summary (LLM-generated narrative)
    2. Case Overview & Evidence Inventory
    3. Autopsy Findings Summary (from Cat A)
    4. Time of Death Analysis (TOD window, method, confidence)
    5. Digital Timeline Analysis (key events, anomalies)
    6. Financial Analysis (if Cat D present)
    7. Device Data Analysis (if Cat E present)
    8. Hypothesis Assessment (all 4 with probabilities)
    9. Key Signals & Evidence Table
    10. Reasoning Replay Summary
    11. Investigator Notes
    12. Appendix: Evidence File Hashes & Custody Log
  
  PII in report: shows masked version by default
  "🔒 Showing masked version — your role: Investigator"
  Toggle (leadinvestigator+ only): "Show unmasked ▾" with reason prompt

RIGHT — EXPORT PANEL (sticky):
  Title: "Export Report"
  
  FORMAT OPTIONS:
    ● PDF (printable, court-format)    [recommended]
    ○ DOCX (editable)
    ○ JSON (machine-readable structured)
  
  PII SETTING (role-gated):
    ● Masked version (all roles)
    ○ Unmasked (leadinvestigator+ only — requires reason)
  
  SECTIONS TO INCLUDE (checkboxes, all checked by default):
    ✓ Executive Summary
    ✓ TOD Analysis
    ✓ Digital Timeline
    ✓ Hypothesis Assessment
    ✓ Evidence Hash Table
    ✓ Reasoning Replay
    ✗ Raw Evidence Data (excluded by default)
  
  "[ Download Report ↓ ]" — large indigo filled button
  
  Divider
  
  REPORT METADATA:
    Generated: May 9, 2026 02:14 IST
    By: Arjun Sharma (Investigator)
    Model: GPT-4o · TOD: Henssge v2.1
    Report Hash: a3f8c2...d41e
    "This hash can be used to verify report integrity"
```


***

### PAGE 14 — Reasoning Replay Tab

```
DESIGN BRIEF: AIVENTRA Case — Reasoning Replay Tab

[Apply AIVENTRA Design System]

TABS: [...] [Reasoning Replay ←active] [...]

INTRO BAR:
  "Complete AI Reasoning Chain — Every decision is traceable and cryptographically linked."
  "11 agents · 47 reasoning steps · Chain integrity: ✓ Verified"

FILTER ROW:
  [All Agents ▾] [All Step Types ▾] [Show Only Key Decisions: toggle]

VERTICAL REASONING CHAIN (scrollable):

Each agent has a section:

AGENT SECTION HEADER:
  Colored left border (per agent color) + agent icon + name
  "Agent 1 — Evidence Parser" + run timestamp + duration badge

STEP CARDS within agent (nested, indented):
  Each step card (small, compact):
  
  Step type badge: TRIGGER / PARSE / DECISION / OUTPUT / ERROR
  
  Example Agent 4 (Autopsy Agent) steps:
    
    ┌─[TRIGGER]──────────────────────────────────────────────┐
    │ Input: canonical_autopsy_json (39 fields)              │
    │ Triggered by: Format Normalizer → output ready         │
    └────────────────────────────────────────────────────────┘
    ↓
    ┌─[DECISION]─────────────────────────────────────────────┐
    │ COD vs Injury consistency check                        │
    │ "Cause 1b = stab wound; injury_list confirms stab      │
    │  wound L thorax. ✓ Consistent."                       │
    │ Confidence: 0.94                                       │
    └────────────────────────────────────────────────────────┘
    ↓
    ┌─[DECISION]─────────────────────────────────────────────┐
    │ Manner of death classification                         │
    │ "Physical injuries + defensive wounds + mechanism      │
    │  = HOMICIDE. Confidence: 0.91"                        │
    └────────────────────────────────────────────────────────┘
    ↓
    ┌─[OUTPUT]───────────────────────────────────────────────┐
    │ AutopsyResult emitted → TOD Agent + Hypothesis Manager │
    │ manner_of_death: HOMICIDE (0.91)                       │
    │ 6 signals forwarded to Hypothesis Manager              │
    └────────────────────────────────────────────────────────┘

CHAIN HASH LINK (between each agent section):
  Small row: 🔗 "Chain link: prev_hash: a3f8c2... → self_hash: b7d9e1..."
  "Cryptographic integrity: ✓ Verified"
  
  (if tampered: red row "⚠ CHAIN BROKEN at step 14 — hash mismatch")

BOTTOM SUMMARY:
  "End of reasoning chain. All 47 steps verified.
   Reasoning chain hash: [full hash in monospace]
   This hash is included in the exported report."
```


***

### PAGE 15 — Admin: User Management

```
DESIGN BRIEF: AIVENTRA Admin — User Management

[Apply AIVENTRA Design System]
Role gate: admin only. Show "403 — Not Authorized" for other roles.

TOPBAR + Breadcrumb: "← Dashboard / Admin / Users"
Admin badge in topbar: "⚙ Admin Mode" in red pill

PAGE HEADER ROW:
  "User Management" + "Invite User +" button

STATS ROW (3 cards):
  "8 Total Users" | "2 Lead Investigators" | "4 Investigators"

FILTER BAR:
  Search by name/email | Role filter dropdown | Status filter

USER TABLE:
Headers: Avatar + Name | Email | Role | Status | Last Login | Cases | Actions

Row example:
  🟢 Arjun Sharma    arjun@cbi.gov  Investigator     Active   May 9 02:14   3 cases  [Edit] [Deactivate]
  🟢 Priya Menon     priya@cbi.gov  Lead Investigator Active   May 9 01:40   5 cases  [Edit] [Deactivate]
  🔴 Vikram Das      vikram@...     Viewer            Inactive  May 1         1 case   [Edit] [Activate]

ROLE BADGES (colored pills):
  admin: red | leadinvestigator: orange | investigator: blue | viewer: grey

INVITE USER MODAL (shown when "+ Invite User" clicked):
  Name input | Email input | Role dropdown | 
  "Send Invite" button (sends magic-link + TOTP setup)

EDIT USER MODAL:
  Role change dropdown + case assignment multiselect + Save
```


***

### PAGE 16 — Admin: Audit Log Viewer

```
DESIGN BRIEF: AIVENTRA Admin — Audit Log Viewer

[Apply AIVENTRA Design System]
Admin only.

TOPBAR + Breadcrumb: "← Admin / Audit Log"

HEADER ROW:
  "Audit Log" title
  Chain integrity status: "✓ Chain Integrity Verified (last check: 2 min ago)" green
  "[ Verify Chain Now ]" ghost button | "[ Export Log ]" indigo button

STATS ROW:
  "12,847 Total Events" | "0 Tamper Alerts" | "3 Anomaly Flags" (amber)

FILTER BAR:
  Date range picker | User filter | Action type filter | Result filter (SUCCESS/DENIED/ALERT)
  "Show Anomalies Only" toggle

AUDIT TABLE (full width):
Headers: Timestamp | User | Role | Action | Resource | Result | IP | Chain

Row examples (most recent first):
  02:14:33  Arjun Sharma  Investigator  EVIDENCE_UPLOAD   PME_Kumar.pdf   SUCCESS  10.0.0.4  ✓
  02:14:35  SYSTEM        -             AGENT_RUN_START   AutopsyAgent    SUCCESS  internal  ✓
  02:14:44  SYSTEM        -             AGENT_RUN_COMPLETE AutopsyAgent   SUCCESS  internal  ✓
  02:15:12  Arjun Sharma  Investigator  EVIDENCE_ACCESS   CDR_Victim.csv  SUCCESS  10.0.0.4  ✓

Action color coding:
  EVIDENCE_* → blue | AGENT_* → indigo | LOGIN* → green | DENIED → red | ALERT → red pulse

Chain column: ✓ (green verified) or ⚠ BROKEN (red)

ANOMALY FLAGS SECTION (pinned at top if anomalies exist):
  Amber card: "3 access anomaly flags in last 24h"
  List of flagged events with detail
```


***

### PAGE 17 — Chain of Custody Viewer

```
DESIGN BRIEF: AIVENTRA Chain of Custody — Per File

[Apply AIVENTRA Design System]
leadinvestigator+ only.

BREADCRUMB: "← Evidence / PME_Kumar.pdf / Chain of Custody"

FILE HEADER:
  PDF icon + filename + size + upload date
  SHA-256 hash: "[full hash in monospace, copyable]"
  "✓ Current hash matches registered hash — file unmodified"
  
  Hash Comparison widget:
    Registered hash: [a3f8c2...d41e] (at upload)
    Current hash:    [a3f8c2...d41e] (verified now)
    Status: ✓ MATCH — indigo badge

CUSTODY TIMELINE (vertical, chronological):
  Each custody event as a timeline node:
  
  ● 2026-05-09 02:14:00 — UPLOADED
    By: Arjun Sharma (Investigator) · IP: 10.0.0.4
    Hash at access: a3f8c2...d41e ✓
    Chain link: prev 000000... → self a3f8c2...
    
  ● 2026-05-09 02:14:35 — AGENT_RUN (Evidence Parser)
    By: SYSTEM (agent pipeline)
    Hash verified: ✓ match
    
  ● 2026-05-09 02:14:40 — AGENT_RUN (OCR Agent)
    By: SYSTEM
    
  ● 2026-05-09 02:14:44 — AGENT_RUN (Autopsy Agent)
    By: SYSTEM
    
  ● 2026-05-09 02:30:12 — READ
    By: Arjun Sharma (viewed extraction review)

BOTTOM:
  "Export Custody Log" button (for court submission)
  "Full chain verified — 6 events — no tampering detected"
```


***

### PAGE 18 — Settings / Profile

```
DESIGN BRIEF: AIVENTRA Settings — Profile & Security

[Apply AIVENTRA Design System]

BREADCRUMB: "← Dashboard / Settings"

TWO-COLUMN LAYOUT (60% / 40%):

LEFT — PROFILE FORM:
  Avatar circle (initials, indigo bg) + "Change Photo" (not for sensitive deployment)
  
  Name field (read-only for non-admin)
  Email field (read-only)
  Role badge (display only)
  Agency/Department input
  
  "Change Password" section:
    Current password input
    New password input + strength meter
    Confirm new password
    [Update Password] button

RIGHT — MFA SETTINGS:
  Title: "Two-Factor Authentication"
  Status: "● ENABLED" green badge (MFA required, cannot be disabled)
  
  "Authenticator App" section:
    QR code display (for re-setup)
    Secret key (masked, show button for lead+)
    "Re-setup Authenticator" button → shows new QR + secret
  
  "Recovery Codes" section:
    "8 recovery codes remaining"
    [View Codes] (requires password confirmation)
    [Generate New Codes] (invalidates old ones)
  
  SECURITY NOTE:
    Amber box: "MFA cannot be disabled. Contact admin if you lose 
    access to your authenticator."

BOTTOM:
  Last login: May 9, 2026 02:14 IST from 10.0.0.4
  "[ View my activity log ]" link
```


***

## 📋 Complete Page Checklist

| \# | Page | Route | Status |
| :-- | :-- | :-- | :-- |
| 1 | Login | `/login` | ✅ Done |
| 2 | MFA Step | `/login/mfa` | 🆕 New |
| 3 | Forgot Password | `/forgot-password` | 🆕 New |
| 4 | Dashboard | `/dashboard` | ✅ Done |
| 5 | New Case Step 1 | `/cases/new` | ✅ Done |
| 6 | New Case Step 2 | `/cases/new` | ✅ Done |
| 7 | Quality Gate | `/cases/:id/quality-gate` | ✅ Done |
| 8 | Case Overview Tab | `/cases/:id` | ✅ Done |
| 9 | Timeline Tab | `/cases/:id/timeline` | 🆕 New |
| 10 | TOD Analysis Tab | `/cases/:id/tod` | 🆕 New |
| 11 | Anomalies Tab | `/cases/:id/anomalies` | 🆕 New |
| 12 | Hypothesis Tab | `/cases/:id/hypothesis` | 🆕 New |
| 13 | Evidence Manager | `/cases/:id/evidence` | ✅ Done |
| 14 | Report Tab | `/cases/:id/report` | 🆕 New |
| 15 | Reasoning Replay Tab | `/cases/:id/reasoning` | 🆕 New |
| 16 | Review: Cat A Autopsy | `/evidence/:id/review` | ✅ Done |
| 17 | Review: Cat B CDR | `/evidence/:id/review` | ✅ Done |
| 18 | Review: Cat C Location | `/evidence/:id/review` | 🆕 New |
| 19 | Review: Cat D Financial | `/evidence/:id/review` | 🆕 New |
| 20 | Review: Cat E Device | `/evidence/:id/review` | 🆕 New |
| 21 | Review: Cat F Scene | `/evidence/:id/review` | 🆕 New |
| 22 | Admin: Users | `/admin/users` | 🆕 New |
| 23 | Admin: Audit Log | `/admin/audit` | 🆕 New |
| 24 | Chain of Custody | `/admin/custody/:id` | 🆕 New |
| 25 | Settings/Profile | `/settings/profile` | 🆕 New |

**8 previously designed ✅ · 17 newly added 🆕 · 25 total pages**
<span style="display:none">[^1][^2]</span>

<div align="center">⁂</div>

[^1]: paste.txt

[^2]: AIVENTRA_Security_Specification.md

