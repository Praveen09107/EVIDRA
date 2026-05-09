# AIVENTRA — System Specification v1.0
### AI-Powered Forensic Triage & Postmortem Intelligence System
**HackHere Community · AIVENTRA Track · Implementation Reference**

---

> **Document status:** Implementation-ready  
> **Audience:** All development team members  
> **Scope:** End-to-end — intake → processing → dashboard → output  

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Project Structure](#2-project-structure)
3. [Runtime Input Specification](#3-runtime-input-specification)
4. [Suspect Interrogation Audio Pipeline](#4-suspect-interrogation-audio-pipeline)
5. [AI Agent Specifications](#5-ai-agent-specifications)
6. [Evidence Correlation & Fusion Engine](#6-evidence-correlation--fusion-engine)
7. [Dashboard Specification](#7-dashboard-specification)
8. [API Contract](#8-api-contract)
9. [Technology Stack](#9-technology-stack)
10. [Legal & Ethical Compliance](#10-legal--ethical-compliance)
11. [Novelty Features](#11-novelty-features)
12. [Build Sequence](#12-build-sequence)
13. [Environment Setup](#13-environment-setup)

---

## 1. System Overview

### 1.1 Problem

Forensic investigations are bottlenecked by manual evidence processing. Autopsy reports take days to analyse. CCTV footage requires hours of manual review. Suspect statements are cross-referenced by hand against evidence — slowly, inconsistently, and with high risk of oversight.

### 1.2 What AIVENTRA Does

AIVENTRA ingests five evidence types, processes each through a dedicated AI agent, correlates outputs through a fusion engine, and delivers structured investigative intelligence through a unified dashboard — in minutes, not days.

### 1.3 End-to-End Flow

```
INVESTIGATOR INTAKE
        │
        ├── Autopsy PDF ──────────────► Autopsy Agent (II-Medical-32B)
        │                                       │
        ├── Postmortem readings ────────► TOD Agent (Henssge + sklearn)
        │                                       │
        ├── Suspect audio recordings ──► Whisper STT → Interrogation Agent (Qwen3-32B)
        │                                       │
        ├── CCTV event log + frames ───► Image Agent (Qwen2.5-VL-72B)
        │                                       │
        └── CDR / GPS metadata ────────► Timeline & Anomaly Agent (Qwen3-8B)
                                                │
                                    ┌───────────▼───────────┐
                                    │   CORRELATION ENGINE   │
                                    │  Hypothesis Manager    │
                                    │  Claim Extractor       │
                                    │  Evidence-Claim Mapper │
                                    │  Argument Graph        │
                                    │  Collision Agent       │
                                    └───────────┬───────────┘
                                                │
                                    ┌───────────▼───────────┐
                                    │   INVESTIGATION        │
                                    │   DASHBOARD            │
                                    │   React Frontend       │
                                    └───────────────────────┘
```

### 1.4 Core Case Data Model

Every agent reads from and writes to a shared `Case` object. Define this first — everything depends on it.

```python
# schemas/case.py

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class PostmortemReadings(BaseModel):
    body_temp_celsius: float
    ambient_temp_celsius: float
    body_weight_kg: float
    clothing_factor: str          # naked | light | heavy | blanket
    rigor_mortis_stage: str       # none | partial | full | resolving
    livor_mortis_stage: str       # absent | present_unfixed | present_fixed
    body_position: str            # prone | supine | lateral | seated
    discovery_datetime: datetime

class EvidenceItem(BaseModel):
    evidence_id: str
    evidence_type: str            # autopsy | cctv | cdr | gps | image | audio
    source_file: str
    upload_timestamp: datetime
    legal_authorization_ref: str
    processed: bool = False
    agent_output: Optional[dict] = None

class SuspectSession(BaseModel):
    suspect_id: str
    full_name: str
    age: int
    gender: str
    address: str
    relation_to_case: str
    caution_administered: bool
    legal_rep_present: bool
    session_datetime: datetime
    recording_files: List[str] = []
    transcript_output: Optional[dict] = None
    verification_output: Optional[dict] = None

class TODWindow(BaseModel):
    earliest: datetime
    latest: datetime
    confidence: str               # HIGH | MEDIUM | LOW
    method: str                   # henssge | hybrid | livor_only
    margin_hours: float

class Case(BaseModel):
    case_id: str
    incident_date: datetime
    discovery_datetime: datetime
    scene_location: str
    scene_gps: tuple[float, float]
    case_classification: str
    assigned_investigator: str
    case_priority: str            # HIGH | MEDIUM | LOW
    custody_window_hours: Optional[int] = None

    # Evidence
    evidence_items: List[EvidenceItem] = []
    postmortem_readings: Optional[PostmortemReadings] = None
    suspect_sessions: List[SuspectSession] = []

    # Agent outputs
    autopsy_findings: Optional[dict] = None
    tod_window: Optional[TODWindow] = None
    unified_timeline: Optional[List[dict]] = None
    anomaly_flags: Optional[List[dict]] = None
    argument_graph: Optional[dict] = None
    risk_score: Optional[float] = None
    risk_explanation: Optional[dict] = None

    # Investigator
    hypotheses: List[dict] = []
    investigator_annotations: List[dict] = []
    audit_log: List[dict] = []
```

---

## 2. Project Structure

```
aiventra/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── schemas/
│   │   ├── case.py                # Core case data model (above)
│   │   ├── evidence.py            # Evidence item schemas
│   │   └── agent_outputs.py       # All agent output schemas
│   ├── agents/
│   │   ├── llm_client.py          # Featherless API wrapper
│   │   ├── autopsy_agent.py
│   │   ├── tod_agent.py
│   │   ├── stt_agent.py           # Whisper transcription
│   │   ├── interrogation_agent.py
│   │   ├── image_agent.py
│   │   ├── timeline_agent.py
│   │   ├── hypothesis_manager.py
│   │   ├── claim_extractor.py
│   │   ├── evidence_claim_mapper.py
│   │   ├── collision_agent.py
│   │   ├── argument_graph.py
│   │   ├── nbe_agent.py
│   │   ├── bias_monitor.py
│   │   └── risk_scorer.py
│   ├── pipeline/
│   │   ├── ingest.py              # Evidence upload handlers
│   │   ├── fusion.py              # Correlation & fusion engine
│   │   └── orchestrator.py        # Pipeline sequencing
│   ├── routers/
│   │   ├── cases.py
│   │   ├── evidence.py
│   │   ├── suspects.py
│   │   └── dashboard.py
│   └── db/
│       ├── postgres.py
│       ├── neo4j_client.py
│       └── redis_client.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── CaseOverview.jsx
│   │   │   ├── SuspectPanel.jsx
│   │   │   ├── EvidenceTimeline.jsx
│   │   │   ├── ArgumentGraph.jsx
│   │   │   ├── InvestigatorActions.jsx
│   │   │   └── AuditTrail.jsx
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── NewCase.jsx
│   │   │   └── SuspectIntake.jsx
│   │   └── api/
│   │       └── client.js
│   └── package.json
├── mock_data/
│   ├── sample_autopsy.txt
│   ├── sample_cctv_log.csv
│   ├── sample_cdr.csv
│   └── sample_suspect_audio_transcript.json
├── .env
├── docker-compose.yml
└── requirements.txt
```

---

## 3. Runtime Input Specification

These are inputs the investigator provides per case — not training data.

### 3.1 Case Intake Form

```json
{
  "case_id": "CASE_2024_0041",
  "incident_date": "2024-03-15T00:00:00Z",
  "discovery_datetime": "2024-03-15T22:45:00Z",
  "scene_location": "12, Velachery Main Road, Chennai - 600042",
  "scene_gps": [13.0827, 80.2707],
  "case_classification": "suspicious_death",
  "assigned_investigator": "OFF_7821",
  "case_priority": "HIGH",
  "custody_window_hours": 24
}
```

### 3.2 Postmortem Scene Readings

```json
{
  "body_temp_celsius": 31.2,
  "ambient_temp_celsius": 27.4,
  "body_weight_kg": 68,
  "clothing_factor": "light",
  "rigor_mortis_stage": "full",
  "livor_mortis_stage": "present_fixed",
  "body_position": "supine",
  "discovery_datetime": "2024-03-15T22:45:00Z"
}
```

> **Note:** `ambient_temp_celsius` is auto-fetched from Open-Meteo API using `scene_gps` + `discovery_datetime` if not manually provided.

```python
# backend/agents/tod_agent.py — ambient temp auto-fetch

import requests

def fetch_ambient_temp(lat: float, lng: float, dt: str) -> float:
    date = dt[:10]
    hour = int(dt[11:13])
    url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat}&longitude={lng}"
        f"&start_date={date}&end_date={date}"
        f"&hourly=temperature_2m"
    )
    resp = requests.get(url).json()
    return resp["hourly"]["temperature_2m"][hour]
```

### 3.3 CCTV Event Log — CSV Format

```csv
camera_id,camera_name,location_name,latitude,longitude,timestamp,event_type,object_type,object_count,direction,confidence_score,clip_reference,notes
CAM_001,North Gate Cam,North Gate Entrance,13.0827,80.2707,2024-03-15 21:45:12,person_detected,person,1,entering,0.91,CLIP_0291,Male subject dark jacket
CAM_003,Parking Lot Cam,Parking Lot C,13.0819,80.2715,2024-03-15 21:52:34,vehicle_detected,car,1,entering,0.94,CLIP_0104,Dark sedan no plate visible
CAM_007,Back Alley Cam,Service Lane B,13.0812,80.2699,2024-03-15 22:05:17,motion_detected,person,2,unknown,0.79,CLIP_0388,Two figures briefly visible
CAM_003,Parking Lot Cam,Parking Lot C,13.0819,80.2715,2024-03-15 22:18:41,vehicle_detected,car,1,exiting,0.94,CLIP_0105,Same sedan exiting
CAM_001,North Gate Cam,North Gate Entrance,13.0827,80.2707,2024-03-15 22:22:09,person_detected,person,1,exiting,0.88,CLIP_0296,Male subject same jacket exiting
```

### 3.4 CDR Data — CSV Format

```csv
record_id,caller_number,callee_number,call_type,timestamp_start,duration_seconds,caller_tower_id,caller_tower_lat,caller_tower_lng,callee_tower_id,callee_tower_lat,callee_tower_lng
CDR_001,+91-98400-XXXXX,+91-77080-XXXXX,VOICE,2024-03-15 21:30:44,187,TWR_CHN_042,13.0821,80.2701,TWR_CHN_018,13.0654,80.2491
CDR_002,+91-98400-XXXXX,+91-94440-XXXXX,SMS,2024-03-15 21:58:12,0,TWR_CHN_042,13.0821,80.2701,,,
CDR_003,+91-98400-XXXXX,+91-77080-XXXXX,VOICE,2024-03-15 22:31:05,43,TWR_CHN_044,13.0798,80.2689,TWR_CHN_042,13.0821,80.2701
```

### 3.5 Suspect Session — Pre-Interrogation Form

```json
{
  "suspect_id": "SUS_001",
  "full_name": "Name as per ID",
  "age": 34,
  "gender": "Male",
  "address": "45, Anna Nagar, Chennai - 600040",
  "relation_to_case": "suspect",
  "known_locations": ["Anna Nagar", "Velachery", "T. Nagar"],
  "alibi_claimed_prior": "Claims to have been at restaurant on MG Road until 11pm",
  "legal_rep_present": true,
  "caution_administered": true,
  "session_datetime": "2024-03-16T10:00:00Z",
  "interviewing_officer_id": "OFF_7821"
}
```

---

## 4. Suspect Interrogation Audio Pipeline

This is the most novel pipeline in AIVENTRA. It covers the complete flow from recording to cross-verified dashboard output.

### 4.1 Flow Diagram

```
Officer creates Suspect Session record
          │
          ▼
Caution administered? ──NO──► System warning logged, blocks upload
          │
         YES
          │
          ▼
Voice recorder started
Suspect states: name → address → statement
          │
          ▼
Audio file uploaded (MP3/WAV/M4A)
Linked to suspect_id
          │
          ▼
┌─────────────────────────────────┐
│   WHISPER LARGE V3              │
│   Speech-to-Text + Diarisation  │
│   Word-level timestamps         │
│   WhisperX speaker separation   │
└─────────────┬───────────────────┘
              │
              ▼
    Structured transcript JSON
              │
              ▼
┌─────────────────────────────────┐
│   INTERROGATION AGENT           │
│   Qwen/Qwen3-32B                │
│   Featherless AI                │
│   Thinking mode ON              │
└─────────────┬───────────────────┘
              │
    ┌─────────▼─────────┐
    │  Cross-verify      │
    │  against:          │
    │  • Pre-interrogation│
    │    form data        │
    │  • CCTV logs        │
    │  • CDR data         │
    │  • Autopsy timeline │
    │  • GPS records      │
    └─────────┬─────────┘
              │
              ▼
    Verification report JSON
              │
              ▼
    Suspect Verification Panel
    on Dashboard
```

### 4.2 Whisper Transcription Implementation

```python
# backend/agents/stt_agent.py

import whisper
import whisperx
import json
from datetime import datetime

def transcribe_audio(
    audio_path: str,
    suspect_id: str,
    recording_id: str,
    device: str = "cpu"
) -> dict:
    """
    Transcribe suspect audio using Whisper Large v3 with WhisperX diarisation.
    Returns structured transcript with word-level timestamps and speaker labels.
    """

    # Step 1: Load model
    model = whisper.load_model("large-v3", device=device)

    # Step 2: Transcribe with word timestamps
    result = model.transcribe(
        audio_path,
        word_timestamps=True,
        language=None,           # auto-detect — handles Tamil/English code-switching
        verbose=False
    )

    # Step 3: Speaker diarisation via WhisperX
    diarize_model = whisperx.DiarizationPipeline(use_auth_token=None, device=device)
    diarize_segments = diarize_model(audio_path, min_speakers=2, max_speakers=4)
    result = whisperx.assign_word_speakers(diarize_segments, result)

    # Step 4: Structure output
    segments = []
    for i, seg in enumerate(result["segments"]):
        segments.append({
            "segment_id": i + 1,
            "speaker": seg.get("speaker", "UNKNOWN"),
            "start_time": round(seg["start"], 2),
            "end_time": round(seg["end"], 2),
            "text": seg["text"].strip(),
            "confidence": round(
                sum(w.get("probability", 0.9) for w in seg.get("words", [])) /
                max(len(seg.get("words", [])), 1), 3
            ),
            "words": [
                {
                    "word": w["word"],
                    "start": round(w["start"], 3),
                    "end": round(w["end"], 3),
                    "confidence": round(w.get("probability", 0.9), 3)
                }
                for w in seg.get("words", [])
            ]
        })

    transcript = {
        "recording_id": recording_id,
        "suspect_id": suspect_id,
        "transcription_timestamp": datetime.utcnow().isoformat(),
        "language_detected": result.get("language", "unknown"),
        "duration_seconds": round(result["segments"][-1]["end"] if result["segments"] else 0, 1),
        "model_used": "whisper-large-v3",
        "segments": segments,
        "full_text": " ".join(seg["text"] for seg in result["segments"])
    }

    return transcript


def extract_suspect_segments_only(transcript: dict) -> str:
    """
    Filter transcript to suspect speech only for analysis.
    WhisperX labels speakers as SPEAKER_00, SPEAKER_01 etc.
    Officer is typically the first speaker; suspect is second.
    Manual override available via suspect_speaker_label param.
    """
    suspect_text = []
    for seg in transcript["segments"]:
        # Heuristic: non-SPEAKER_00 segments are suspect
        # Override this if officer is not first speaker
        if seg["speaker"] != "SPEAKER_00":
            suspect_text.append({
                "time": seg["start_time"],
                "text": seg["text"]
            })
    return suspect_text
```

### 4.3 Interrogation Agent — Full Implementation

```python
# backend/agents/interrogation_agent.py

from agents.llm_client import call_llm
import json

INTERROGATION_SYSTEM_PROMPT = """
You are a forensic statement analysis assistant in a criminal investigation.
You will receive a suspect's spoken statement (transcribed from audio) and
a summary of existing case evidence.

Your tasks:
1. Extract all verifiable claims from the suspect's statement
2. Cross-verify each claim against the provided evidence
3. Flag contradictions, corroborations, and unverifiable statements
4. Detect internal inconsistencies within the statement
5. Surface new leads not previously in the evidence base

Output ONLY valid JSON following this exact schema. No preamble. No explanation outside the JSON.

{
  "suspect_id": "",
  "identity_verification": {
    "name_stated": "",
    "name_matches_record": true,
    "address_stated": "",
    "address_matches_record": true,
    "identity_confidence": "HIGH | MEDIUM | LOW",
    "discrepancy_detail": ""
  },
  "claims": [
    {
      "claim_id": "CL001",
      "statement_verbatim": "",
      "timestamp_in_recording_seconds": 0,
      "claim_type": "location | alibi | knowledge | timeline | identity | relationship | other",
      "time_referenced": "",
      "location_referenced": "",
      "persons_referenced": [],
      "verification_status": "CORROBORATED | CONTRADICTED | UNVERIFIABLE | NEW_LEAD",
      "evidence_used": [],
      "contradiction_detail": "",
      "corroboration_detail": "",
      "recommended_action": "",
      "confidence": "HIGH | MEDIUM | LOW"
    }
  ],
  "internal_inconsistencies": [
    {
      "flag_id": "IC001",
      "claim_a_id": "",
      "claim_b_id": "",
      "claim_a_text": "",
      "claim_b_text": "",
      "description": "",
      "severity": "MINOR | MODERATE | SIGNIFICANT"
    }
  ],
  "identity_anchor_check": {
    "name_stated_in_opening": "",
    "address_stated_in_opening": "",
    "opening_statement_present": true
  },
  "new_leads": [
    {
      "lead_id": "NL001",
      "description": "",
      "suggested_action": "",
      "priority": "HIGH | MEDIUM | LOW"
    }
  ],
  "overall_consistency_score": 0,
  "key_contradictions_summary": "",
  "legal_flags": []
}

STRICT RULES:
- Never conclude guilt — flag contradictions only, not culpability
- Anonymise all third-party names as Person_A, Person_B etc
- Distinguish between what suspect directly claims vs what they imply
- UNVERIFIABLE is not the same as CONTRADICTED — use it when no evidence exists
- Flag in legal_flags if: caution not administered, leading questions detected,
  duress indicators in speech, legal rep not present
- overall_consistency_score: 0 = all claims contradicted, 100 = all claims corroborated
"""

def run_interrogation_agent(
    suspect_id: str,
    suspect_segments: list,
    pre_interrogation_data: dict,
    evidence_summary: dict
) -> dict:
    """
    Cross-verify suspect statement against all available evidence.

    Args:
        suspect_id: Suspect session ID
        suspect_segments: List of {time, text} dicts from STT (suspect speech only)
        pre_interrogation_data: Officer-entered form data (name, address, known_locations etc)
        evidence_summary: Structured summary of all processed evidence for this case
    """

    # Format suspect statement for prompt
    statement_text = "\n".join([
        f"[{round(seg['time'])}s] {seg['text']}"
        for seg in suspect_segments
    ])

    # Format evidence summary
    evidence_text = json.dumps(evidence_summary, indent=2)

    # Format pre-interrogation data
    prior_data_text = json.dumps(pre_interrogation_data, indent=2)

    user_prompt = f"""
SUSPECT ID: {suspect_id}

PRE-INTERROGATION RECORD (officer-entered, ground truth for identity verification):
{prior_data_text}

EXISTING CASE EVIDENCE SUMMARY:
{evidence_text}

SUSPECT STATEMENT (transcribed from audio, timestamps in seconds):
{statement_text}

Cross-verify all claims. Output the JSON analysis.
/think
"""

    raw_output = call_llm(
        system_prompt=INTERROGATION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        model="Qwen/Qwen3-32B",
        temperature=0.6
    )

    # Parse JSON — strip any markdown fences if present
    clean = raw_output.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    return json.loads(clean.strip())
```

### 4.4 Evidence Summary Builder

The interrogation agent needs a summary of all processed evidence. This is built by the fusion engine before calling the agent:

```python
# backend/pipeline/fusion.py

def build_evidence_summary(case: dict) -> dict:
    """
    Build a concise evidence summary for use in agent cross-verification prompts.
    Keeps token count manageable — full raw data stays in DB.
    """
    summary = {
        "case_id": case["case_id"],
        "tod_window": case.get("tod_window"),

        "cctv_events": [
            {
                "camera": e["camera_name"],
                "location": e["location_name"],
                "gps": [e["latitude"], e["longitude"]],
                "timestamp": e["timestamp"],
                "event": e["event_type"],
                "description": e["notes"]
            }
            for e in case.get("cctv_events", [])
        ],

        "cdr_flags": [
            {
                "number": r["caller_number"],
                "timestamp": r["timestamp_start"],
                "tower_location": [r["caller_tower_lat"], r["caller_tower_lng"]],
                "call_type": r["call_type"],
                "duration": r["duration_seconds"]
            }
            for r in case.get("cdr_records", [])
            if r.get("flagged_near_scene")  # only scene-proximate records
        ],

        "autopsy_key_findings": {
            "cause_of_death": case.get("autopsy_findings", {}).get("cause_of_death"),
            "time_indicators": case.get("autopsy_findings", {}).get("time_indicators"),
            "injury_summary": case.get("autopsy_findings", {}).get("injury_patterns")
        },

        "known_locations_in_case": list(set(
            [e["location_name"] for e in case.get("cctv_events", [])]
        ))
    }
    return summary
```

### 4.5 Cross-Verification Example

| Suspect Statement | Evidence Source | Verification Result |
|---|---|---|
| *"I saw the body at 9am. I was at the north gate."* | CCTV CAM_001: No person detected 08:45–09:15 | **CONTRADICTED — HIGH** · CDR also places phone 3.2km away at 08:58 |
| *"I did not know the victim personally."* | CDR: 4 calls between suspect and victim in 72hrs before TOD | **CONTRADICTED — MEDIUM** · Recommend call log review |
| *"I was at a restaurant on MG Road until 11pm."* | No CCTV or CDR for that location in evidence base | **UNVERIFIABLE** · Recommend: request restaurant CCTV + payment records |
| *"I left the area before 10pm."* | CCTV CAM_001: Subject exiting at 22:22 (10:22pm) | **CONTRADICTED — HIGH** · Exited 22 minutes after claimed departure |

### 4.6 Dashboard Output — Suspect Verification Panel

Each suspect gets a card showing:

```
┌─────────────────────────────────────────────────────────────┐
│  SUS_001 · Male, 34 · Suspect                               │
│  Consistency Score: 23/100  ████░░░░░░░░░░  [HIGH RISK]     │
├─────────────────────────────────────────────────────────────┤
│  CLAIM BREAKDOWN                                             │
│  ✗ CL001 · Location at 9am          CONTRADICTED  HIGH      │
│    → CCTV: no detection. CDR: 3.2km away at 08:58          │
│  ✗ CL002 · No prior knowledge       CONTRADICTED  MEDIUM    │
│    → CDR: 4 calls with victim in 72hrs before TOD           │
│  ~ CL003 · At restaurant until 11pm UNVERIFIABLE            │
│    → Action: Request restaurant CCTV + payment records      │
│  ✗ CL004 · Left before 10pm         CONTRADICTED  HIGH      │
│    → CCTV CAM_001: Exiting at 22:22                        │
├─────────────────────────────────────────────────────────────┤
│  INTERNAL INCONSISTENCIES                                    │
│  IC001 · SIGNIFICANT                                         │
│    Claims no knowledge of victim [CL002] vs               │
│    References victim by first name unprompted [17:34s]      │
├─────────────────────────────────────────────────────────────┤
│  NEW LEADS                                                   │
│  NL001 · HIGH PRIORITY                                       │
│    Suspect mentioned "the other person who was there"       │
│    → Unidentified third party. Investigate.                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. AI Agent Specifications

### 5.1 Shared LLM Client

```python
# backend/agents/llm_client.py

import requests
import os
import json

FEATHERLESS_API_KEY = os.getenv("FEATHERLESS_API_KEY")
BASE_URL = "https://api.featherless.ai/v1/chat/completions"

def call_llm(
    system_prompt: str,
    user_prompt: str,
    model: str = "Qwen/Qwen3-32B",
    temperature: float = 0.6,
    max_tokens: int = 2000
) -> str:
    """
    Single entry point for all Featherless AI LLM calls.
    OpenAI-compatible — swap model string to change agent.
    """
    response = requests.post(
        BASE_URL,
        headers={
            "Authorization": f"Bearer {FEATHERLESS_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        },
        timeout=120
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def safe_json_parse(raw: str) -> dict:
    """Strip markdown fences and parse JSON safely."""
    clean = raw.strip()
    if clean.startswith("```"):
        parts = clean.split("```")
        clean = parts[1] if len(parts) > 1 else clean
        if clean.startswith("json"):
            clean = clean[4:]
    return json.loads(clean.strip())
```

### 5.2 Autopsy Agent

**Model:** `Intelligent-Internet/II-Medical-32B-Preview`  
**Why:** Medical fine-tuned on Qwen3-32B base. 32K context. BioBERT-class medical terminology understanding. Reliable structured JSON on clinical text.

```python
# backend/agents/autopsy_agent.py

import fitz  # PyMuPDF — pip install pymupdf
from agents.llm_client import call_llm, safe_json_parse

AUTOPSY_SYSTEM_PROMPT = """
You are a forensic pathology analysis assistant.
Extract structured information from autopsy reports.
Return ONLY valid JSON with exactly these fields:

{
  "cause_of_death": "",
  "manner_of_death": "homicide | suicide | accidental | natural | undetermined",
  "injury_patterns": [
    {
      "injury_id": "INJ_001",
      "type": "blunt_force | sharp_force | gunshot | strangulation | other",
      "location": "",
      "description": "",
      "perimortem": true
    }
  ],
  "body_regions_affected": [],
  "toxicology": {
    "substances_detected": [],
    "alcohol_level": null,
    "drug_screen": ""
  },
  "postmortem_indicators": {
    "body_temp_noted": null,
    "rigor_stage_noted": "",
    "livor_stage_noted": "",
    "decomposition_stage": "none | early | moderate | advanced"
  },
  "time_indicators": "",
  "medical_observations": [],
  "pathologist_conclusions": "",
  "analyst_confidence": "HIGH | MEDIUM | LOW"
}

Return ONLY JSON. No preamble. No explanation outside the JSON.
"""

def extract_pdf_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    return "\n".join(page.get_text() for page in doc)

def run_autopsy_agent(pdf_path: str) -> dict:
    report_text = extract_pdf_text(pdf_path)
    raw = call_llm(
        system_prompt=AUTOPSY_SYSTEM_PROMPT,
        user_prompt=f"Autopsy report:\n\n{report_text}\n\n/no_think",
        model="Intelligent-Internet/II-Medical-32B-Preview",
        temperature=0.1,
        max_tokens=1500
    )
    return safe_json_parse(raw)
```

### 5.3 TOD Agent

**Model:** Henssge formula (physics) + `sklearn.GradientBoostingRegressor` (correction)  
**Why:** Legally defensible deterministic core. ML corrects for non-ideal scene conditions.

```python
# backend/agents/tod_agent.py

import math
from datetime import datetime, timedelta
from schemas.case import PostmortemReadings, TODWindow

# Clothing correction factors (Henssge standard values)
CLOTHING_FACTORS = {
    "naked":    1.0,
    "light":    0.9,
    "heavy":    0.7,
    "blanket":  0.5
}

def henssge_tod(readings: PostmortemReadings) -> TODWindow:
    """
    Henssge nomogram implementation.
    Estimates time since death using body temperature decay.

    Reference: Henssge C. (1988) Death time estimation in case work.
    Forensic Science International, 37(3), 217-236.
    """
    T_body   = readings.body_temp_celsius
    T_ambient = readings.ambient_temp_celsius
    T_death  = 37.2  # assumed normal body temp at time of death
    weight   = readings.body_weight_kg
    cf       = CLOTHING_FACTORS.get(readings.clothing_factor, 0.9)

    # Henssge corrected body weight
    corrected_weight = weight * cf

    # Double exponential decay — Henssge formula
    # Returns estimated hours since death
    B = math.exp(0.0284 * corrected_weight) - 12.9

    if B <= 0 or T_body <= T_ambient:
        # Fall back to livor/rigor estimation if temp data invalid
        return estimate_from_postmortem_stage(readings)

    numerator = math.log(
        (T_body - T_ambient) / (T_death - T_ambient)
    )
    denominator = math.log(B / (B + 1))

    if denominator == 0:
        return estimate_from_postmortem_stage(readings)

    hours_since_death = numerator / denominator

    # Henssge standard margin of error: ±2.8 hours (95% confidence)
    margin = 2.8
    discovery_time = readings.discovery_datetime

    return TODWindow(
        earliest=discovery_time - timedelta(hours=abs(hours_since_death) + margin),
        latest=discovery_time - timedelta(hours=max(0, abs(hours_since_death) - margin)),
        confidence="HIGH" if T_body > T_ambient + 2 else "MEDIUM",
        method="henssge",
        margin_hours=margin
    )


def estimate_from_postmortem_stage(readings: PostmortemReadings) -> TODWindow:
    """
    Fallback: estimate TOD from rigor and livor stage when temperature data is unreliable.
    Based on standard forensic pathology staging timelines.
    """
    stage_map = {
        ("none",    "absent"):          (0,  3),
        ("partial", "present_unfixed"): (2,  8),
        ("full",    "present_unfixed"): (6, 12),
        ("full",    "present_fixed"):   (8, 24),
        ("resolving","present_fixed"):  (18, 48),
    }
    key = (readings.rigor_mortis_stage, readings.livor_mortis_stage)
    low, high = stage_map.get(key, (4, 16))

    discovery_time = readings.discovery_datetime
    return TODWindow(
        earliest=discovery_time - timedelta(hours=high),
        latest=discovery_time - timedelta(hours=low),
        confidence="MEDIUM",
        method="livor_only",
        margin_hours=(high - low) / 2
    )
```

### 5.4 Timeline & Anomaly Agent

**Models:**  
- Isolation Forest (sklearn) — anomaly detection on event sequences  
- `Qwen/Qwen3-8B` via Featherless — timeline narration

```python
# backend/agents/timeline_agent.py

import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import LabelEncoder
import numpy as np
from agents.llm_client import call_llm, safe_json_parse

def detect_anomalies(cctv_df: pd.DataFrame, cdr_df: pd.DataFrame) -> list:
    """
    Run Isolation Forest on combined CCTV + CDR event data.
    Flags statistically anomalous events — gaps, silences, unusual patterns.
    """
    # Feature engineering
    events = []

    for _, row in cctv_df.iterrows():
        events.append({
            "timestamp_unix": pd.Timestamp(row["timestamp"]).timestamp(),
            "source_type": 0,  # CCTV = 0
            "lat": float(row["latitude"]),
            "lng": float(row["longitude"]),
            "confidence": float(row["confidence_score"])
        })

    for _, row in cdr_df.iterrows():
        events.append({
            "timestamp_unix": pd.Timestamp(row["timestamp_start"]).timestamp(),
            "source_type": 1,  # CDR = 1
            "lat": float(row["caller_tower_lat"]) if row["caller_tower_lat"] else 0,
            "lng": float(row["caller_tower_lng"]) if row["caller_tower_lng"] else 0,
            "confidence": 1.0
        })

    if not events:
        return []

    df = pd.DataFrame(events).sort_values("timestamp_unix")

    # Add inter-event gap as feature
    df["time_gap_seconds"] = df["timestamp_unix"].diff().fillna(0)

    features = df[["timestamp_unix", "source_type", "lat", "lng",
                   "confidence", "time_gap_seconds"]].values

    # Isolation Forest — contamination=0.1 means ~10% of events flagged
    clf = IsolationForest(contamination=0.1, random_state=42)
    df["anomaly_score"] = clf.fit_predict(features)
    df["raw_score"] = clf.score_samples(features)

    anomalies = df[df["anomaly_score"] == -1].to_dict("records")
    return anomalies


TIMELINE_NARRATION_PROMPT = """
You are a forensic intelligence analyst.
Given a chronological list of evidence events and flagged anomalies,
write a concise investigative timeline summary (3-5 sentences).

Rules:
- State facts only — no speculation
- Use precise timestamps
- Call out all anomaly flags explicitly
- Note gaps, silences, and suspicious patterns
- End with the most significant finding

Return a JSON object:
{
  "narrative": "",
  "key_anomalies": [],
  "most_significant_finding": "",
  "recommended_investigation_steps": []
}
"""

def narrate_timeline(events: list, anomalies: list) -> dict:
    event_text = "\n".join([
        f"{e['timestamp']} [{e['source']}]: {e['description']}"
        for e in events
    ])
    anomaly_text = "\n".join([
        f"ANOMALY FLAGGED: {a.get('description', str(a))}"
        for a in anomalies
    ])

    raw = call_llm(
        system_prompt=TIMELINE_NARRATION_PROMPT,
        user_prompt=f"Events:\n{event_text}\n\nAnomalies:\n{anomaly_text}\n\n/no_think",
        model="Qwen/Qwen3-8B",
        temperature=0.1,
        max_tokens=800
    )
    return safe_json_parse(raw)
```

### 5.5 Hypothesis Manager

**Model:** `Qwen/Qwen3-4B`  
**Why:** Top IFEval class at 4B. Constrained JSON rewriting. Fastest inference in pipeline.

```python
# backend/agents/hypothesis_manager.py

from agents.llm_client import call_llm, safe_json_parse

HYPOTHESIS_SYSTEM_PROMPT = """
You are a forensic investigation assistant.
Convert the investigator's informal hypothesis into a structured JSON object.

Return ONLY valid JSON with exactly these fields:
{
  "hypothesis_id": "H001",
  "normalized_statement": "",
  "key_entities": [],
  "temporal_claims": [],
  "spatial_claims": [],
  "inferential_claims": [],
  "confidence_basis": "investigator_assertion | evidence_based | speculation"
}

No preamble. No explanation outside the JSON.
"""

def normalise_hypothesis(text: str, hypothesis_id: str, ambiguous: bool = False) -> dict:
    think_flag = "/think" if ambiguous else "/no_think"
    raw = call_llm(
        system_prompt=HYPOTHESIS_SYSTEM_PROMPT,
        user_prompt=f"Hypothesis: {text}\n{think_flag}",
        model="Qwen/Qwen3-4B",
        temperature=0.1,
        max_tokens=500
    )
    result = safe_json_parse(raw)
    result["hypothesis_id"] = hypothesis_id
    return result
```

### 5.6 Claim Extractor

**Model:** `Qwen/Qwen3-14B`  
**Why:** Logical decomposition needs depth. Qwen3-14B matches Qwen2.5-32B on reasoning tasks. Thinking mode mandatory — implicit claim recognition requires reasoning trace.

```python
# backend/agents/claim_extractor.py

from agents.llm_client import call_llm, safe_json_parse

CLAIM_EXTRACTOR_PROMPT = """
You are a forensic logic analyst.
Decompose the hypothesis into discrete, individually testable claims.
Each claim must assert exactly ONE thing.

Return ONLY a valid JSON array:
[
  {
    "claim_id": "C001",
    "statement": "",
    "type": "spatial | temporal | factual | inferential",
    "implicit": false,
    "testable_against": "cctv | cdr | autopsy | gps | witness | any"
  }
]

Rules:
- Split temporally distinct events into separate claims
- Extract implicit inferences as claims marked implicit: true
- Never merge two assertions into one claim
- Never invent claims not in the hypothesis
"""

def extract_claims(normalized_hypothesis: dict) -> list:
    raw = call_llm(
        system_prompt=CLAIM_EXTRACTOR_PROMPT,
        user_prompt=f"Hypothesis: {normalized_hypothesis['normalized_statement']}\n/think",
        model="Qwen/Qwen3-14B",
        temperature=0.6,
        max_tokens=1000
    )
    return safe_json_parse(raw)
```

### 5.7 Evidence-Claim Mapper

**Model:** `Qwen/Qwen3-32B`  
**Why:** Hardest NLI task in pipeline. Multi-hop implicit inference across spatial + temporal dimensions. Wrong classification has direct forensic consequence. Thinking trace = explainability output shown to investigator.

```python
# backend/agents/evidence_claim_mapper.py

from agents.llm_client import call_llm, safe_json_parse

MAPPER_SYSTEM_PROMPT = """
You are a forensic evidence analyst.
Classify the logical relationship between one piece of evidence and one claim.

Think through:
1. What does the claim assert (spatial / temporal / factual)?
2. What does the evidence directly show?
3. What can be inferred from the evidence?
4. Do timing, location, and identity align?
5. Is the relationship direct or via inference chain?

Output ONLY valid JSON:
{
  "claim_id": "",
  "evidence_id": "",
  "relationship": "SUPPORTS | CONTRADICTS | IRRELEVANT",
  "confidence": "HIGH | MEDIUM | LOW",
  "reasoning": "",
  "inference_chain": []
}

CRITICAL RULES:
- Never label ambiguous evidence as SUPPORTS at HIGH confidence
- When uncertain between SUPPORTS and IRRELEVANT, choose IRRELEVANT
- Partial spatial or temporal overlap = MEDIUM confidence SUPPORTS at best
- Identity not confirmed = downgrade confidence one level
"""

def map_evidence_to_claim(claim: dict, evidence: dict) -> dict:
    raw = call_llm(
        system_prompt=MAPPER_SYSTEM_PROMPT,
        user_prompt=f"""
Claim: {claim['statement']}
Claim type: {claim['type']}

Evidence type: {evidence.get('evidence_type')}
Evidence description: {evidence.get('description')}
Evidence timestamp: {evidence.get('timestamp')}
Evidence location: {evidence.get('location', 'unknown')}
Evidence source: {evidence.get('source_file')}

/think
""",
        model="Qwen/Qwen3-32B",
        temperature=0.6,
        max_tokens=800
    )
    result = safe_json_parse(raw)
    result["claim_id"] = claim["claim_id"]
    result["evidence_id"] = evidence.get("evidence_id")
    return result
```

### 5.8 Image Agent

**Model:** `Qwen/Qwen2.5-VL-72B-Instruct` via Featherless  
**Why:** Vision-language model. Accepts image + text input. Outputs structured bbox + JSON. Handles crime scene, autopsy, and CCTV frame types.

```python
# backend/agents/image_agent.py

import base64
import requests
import os
from agents.llm_client import safe_json_parse

FEATHERLESS_API_KEY = os.getenv("FEATHERLESS_API_KEY")

SCENE_IMAGE_PROMPT = """
You are a forensic scene analysis assistant.
Analyze this crime scene photograph and extract structured observations.
Return ONLY valid JSON. No preamble.

{
  "scene_type": "indoor | outdoor | vehicle | other",
  "body_present": true,
  "body_observations": {
    "position": "prone | supine | lateral | seated | other",
    "location_in_scene": "",
    "visible_injuries": [],
    "clothing_description": "",
    "postmortem_indicators": {
      "livor_mortis_visible": false,
      "livor_location": "",
      "rigor_indicators": ""
    }
  },
  "evidence_markers": [],
  "scene_disturbance": {
    "signs_of_struggle": false,
    "struggle_observations": [],
    "blood_spatter_present": false,
    "spatter_description": ""
  },
  "items_of_interest": [],
  "image_quality": "GOOD | MODERATE | POOR",
  "analyst_confidence": "HIGH | MEDIUM | LOW"
}

RULES: Never state cause of death. Never identify persons by appearance.
Clinical observation only. Flag unclear items as uncertain.
"""

def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def analyse_image(image_path: str, image_type: str = "scene") -> dict:
    """
    Send image to Qwen2.5-VL-72B for forensic analysis.
    image_type: scene | autopsy | cctv_frame
    """
    b64 = encode_image(image_path)
    ext = image_path.split(".")[-1].lower()
    media_type = "image/jpeg" if ext in ["jpg", "jpeg"] else "image/png"

    response = requests.post(
        "https://api.featherless.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {FEATHERLESS_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "Qwen/Qwen2.5-VL-72B-Instruct",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{b64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": SCENE_IMAGE_PROMPT + "\n/no_think"
                        }
                    ]
                }
            ],
            "temperature": 0.1,
            "max_tokens": 1200
        },
        timeout=180
    )
    raw = response.json()["choices"][0]["message"]["content"]
    return safe_json_parse(raw)
```

### 5.9 Agent Summary Table

| Agent | Model | Size | Mode | Task Level |
|---|---|---|---|---|
| Autopsy Agent | II-Medical-32B-Preview | 32B | Non-thinking | L2 |
| TOD Agent | Henssge + sklearn | Local | Deterministic | L1 |
| STT Agent | Whisper Large v3 | Local | Open-source | — |
| Interrogation Agent | Qwen/Qwen3-32B | 32B | Thinking ON | L3 |
| Image Agent | Qwen2.5-VL-72B | 72B VLM | Non-thinking | L2 |
| Timeline & Anomaly | IsoForest + Qwen3-8B | Local + 8B | Toggle | L1 |
| Hypothesis Manager | Qwen/Qwen3-4B | 4B | Toggle | L1 |
| Claim Extractor | Qwen/Qwen3-14B | 14B | Thinking ON | L3 |
| Evidence-Claim Mapper | Qwen/Qwen3-32B | 32B | Thinking ON | L3 |
| Collision Agent | Python math | Local | Deterministic | — |
| Argument Graph | NetworkX | Local | Deterministic | — |
| NBE Agent | DeepSeek-R1-Distill-8B | 8B | Thinking ON | L3 |
| Bias Monitor | Rules + Qwen3-4B | Local + 4B | Toggle | L1 |
| Reasoning Replay | Qwen/Qwen3-32B | 32B | Thinking ON | L3 |

---

## 6. Evidence Correlation & Fusion Engine

### 6.1 CDR Scene Proximity Check

```python
# backend/pipeline/fusion.py

from math import radians, sin, cos, sqrt, atan2

def haversine_km(lat1, lng1, lat2, lng2) -> float:
    """Distance between two GPS points in kilometers."""
    R = 6371
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))


def flag_numbers_near_scene(
    cdr_records: list,
    scene_gps: tuple,
    tod_window: dict,
    radius_km: float = 1.0
) -> list:
    """
    Find phone numbers whose tower pings place them within
    radius_km of the scene during the TOD window.
    """
    from datetime import datetime

    tod_start = datetime.fromisoformat(tod_window["earliest"])
    tod_end   = datetime.fromisoformat(tod_window["latest"])
    scene_lat, scene_lng = scene_gps

    flagged = []
    for record in cdr_records:
        if not record.get("caller_tower_lat"):
            continue

        dist = haversine_km(
            scene_lat, scene_lng,
            float(record["caller_tower_lat"]),
            float(record["caller_tower_lng"])
        )

        ts = datetime.fromisoformat(record["timestamp_start"])

        if dist <= radius_km and tod_start <= ts <= tod_end:
            flagged.append({
                "number": record["caller_number"],
                "timestamp": record["timestamp_start"],
                "distance_from_scene_km": round(dist, 3),
                "tower_id": record["caller_tower_id"],
                "call_type": record["call_type"]
            })

    return flagged


def build_unified_timeline(cctv_events: list, cdr_records: list,
                            gps_points: list, autopsy_events: list) -> list:
    """
    Merge all evidence sources into a single chronological timeline.
    Each event tagged with source type and confidence.
    """
    timeline = []

    for e in cctv_events:
        timeline.append({
            "timestamp": e["timestamp"],
            "source": "CCTV",
            "source_id": e["camera_id"],
            "location": e["location_name"],
            "gps": [e["latitude"], e["longitude"]],
            "description": f"{e['event_type']}: {e.get('notes','')}",
            "confidence": e["confidence_score"],
            "clip_ref": e.get("clip_reference")
        })

    for r in cdr_records:
        timeline.append({
            "timestamp": r["timestamp_start"],
            "source": "CDR",
            "source_id": r["caller_number"],
            "location": r.get("caller_tower_id"),
            "gps": [r.get("caller_tower_lat"), r.get("caller_tower_lng")],
            "description": f"{r['call_type']} ({r['duration_seconds']}s)",
            "confidence": 1.0,
            "clip_ref": None
        })

    for g in gps_points:
        timeline.append({
            "timestamp": g["timestamp"],
            "source": "GPS",
            "source_id": g.get("device_id"),
            "location": None,
            "gps": [g["latitude"], g["longitude"]],
            "description": "GPS trace point",
            "confidence": 0.95,
            "clip_ref": None
        })

    timeline.sort(key=lambda x: x["timestamp"])
    return timeline
```

### 6.2 Collision Agent

```python
# backend/agents/collision_agent.py

from datetime import datetime, timedelta

def collides_with_tod(
    event_timestamp: str,
    tod_window: dict,
    buffer_minutes: int = 5
) -> bool:
    """
    Check if an event falls within the TOD window (with buffer).
    Pure arithmetic — no ML needed.
    """
    ts = datetime.fromisoformat(event_timestamp)
    tod_start = datetime.fromisoformat(tod_window["earliest"])
    tod_end   = datetime.fromisoformat(tod_window["latest"])
    buffer    = timedelta(minutes=buffer_minutes)

    return (tod_start - buffer) <= ts <= (tod_end + buffer)


def find_collisions(unified_timeline: list, tod_window: dict) -> list:
    """Return all timeline events that fall within the TOD window."""
    return [
        event for event in unified_timeline
        if collides_with_tod(event["timestamp"], tod_window)
    ]
```

---

## 7. Dashboard Specification

### 7.1 Panel Architecture

```
Dashboard (React)
│
├── Panel 1: Case Overview
│   ├── Case metadata, priority badge, custody countdown
│   ├── TOD window bar chart (Recharts)
│   ├── Risk score gauge (D3.js)
│   └── Top 3 anomaly cards
│
├── Panel 2: Suspect Verification
│   ├── One card per suspect (SuspectCard.jsx)
│   ├── Consistency score bar
│   ├── Claim breakdown table (CORROBORATED/CONTRADICTED/UNVERIFIABLE)
│   ├── Internal inconsistency list
│   └── New leads action items
│
├── Panel 3: Evidence Timeline
│   ├── Horizontal timeline (Recharts Timeline)
│   ├── Colour-coded by source (CCTV/CDR/GPS/Autopsy/Statement)
│   ├── TOD window shaded region
│   ├── Anomaly flags as warning icons
│   └── Click event → source file + legal auth + confidence
│
├── Panel 4: Argument Graph
│   ├── D3.js force-directed graph
│   ├── Nodes: Claims (□), Evidence (○), Suspects (◇)
│   ├── Edges: SUPPORTS (green), CONTRADICTS (red), IRRELEVANT (grey)
│   └── Click node → full reasoning trace from Evidence-Claim Mapper
│
├── Panel 5: Investigator Actions
│   ├── Submit hypothesis form
│   ├── Disagree with AI output
│   ├── Upload new evidence
│   ├── Generate handoff brief
│   └── Generate court narrative
│
└── Panel 6: Audit Trail
    ├── Immutable action log
    ├── Filter by actor / action type / date
    └── Export as PDF
```

### 7.2 Key React Components

```jsx
// frontend/src/components/SuspectPanel.jsx

import { useState } from "react";

const statusColors = {
  CORROBORATED:  "bg-green-100 text-green-800 border-green-300",
  CONTRADICTED:  "bg-red-100 text-red-800 border-red-300",
  UNVERIFIABLE:  "bg-amber-100 text-amber-800 border-amber-300",
  NEW_LEAD:      "bg-blue-100 text-blue-800 border-blue-300"
};

const statusIcons = {
  CORROBORATED: "✓",
  CONTRADICTED: "✗",
  UNVERIFIABLE: "~",
  NEW_LEAD: "→"
};

export function SuspectCard({ suspect }) {
  const [expanded, setExpanded] = useState(false);
  const score = suspect.verification_output?.overall_consistency_score ?? 0;

  const scoreColor =
    score >= 70 ? "bg-green-500" :
    score >= 40 ? "bg-amber-500" : "bg-red-500";

  return (
    <div className="border rounded-xl p-4 mb-4 shadow-sm">
      {/* Header */}
      <div className="flex justify-between items-center mb-3">
        <div>
          <span className="font-bold text-gray-800">{suspect.suspect_id}</span>
          <span className="text-gray-500 ml-2 text-sm">
            {suspect.gender}, {suspect.age} · {suspect.relation_to_case}
          </span>
        </div>
        <div className="text-right">
          <div className="text-xs text-gray-500 mb-1">Consistency Score</div>
          <div className="flex items-center gap-2">
            <div className="w-24 h-2 bg-gray-200 rounded-full">
              <div
                className={`h-2 rounded-full ${scoreColor}`}
                style={{ width: `${score}%` }}
              />
            </div>
            <span className="font-bold text-sm">{score}/100</span>
          </div>
        </div>
      </div>

      {/* Claims */}
      <table className="w-full text-sm mb-3">
        <thead>
          <tr className="text-left text-gray-500 border-b">
            <th className="pb-1">Claim</th>
            <th className="pb-1">Status</th>
            <th className="pb-1">Confidence</th>
          </tr>
        </thead>
        <tbody>
          {suspect.verification_output?.claims?.map(claim => (
            <tr key={claim.claim_id} className="border-b border-gray-50">
              <td className="py-2 pr-4 text-gray-700 max-w-xs">
                {claim.statement_verbatim?.substring(0, 80)}...
              </td>
              <td className="py-2 pr-4">
                <span className={`text-xs px-2 py-0.5 rounded-full border font-medium
                  ${statusColors[claim.verification_status]}`}>
                  {statusIcons[claim.verification_status]} {claim.verification_status}
                </span>
              </td>
              <td className="py-2 text-gray-500 text-xs">{claim.confidence}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Contradiction detail */}
      {expanded && suspect.verification_output?.claims?.filter(
        c => c.verification_status === "CONTRADICTED"
      ).map(c => (
        <div key={c.claim_id} className="bg-red-50 border border-red-200 rounded p-2 mb-2 text-xs">
          <span className="font-medium text-red-700">Contradiction: </span>
          <span className="text-red-600">{c.contradiction_detail}</span>
        </div>
      ))}

      <button
        onClick={() => setExpanded(!expanded)}
        className="text-xs text-blue-600 underline mt-1"
      >
        {expanded ? "Show less" : "Show contradiction details"}
      </button>
    </div>
  );
}
```

---

## 8. API Contract

### 8.1 Core Endpoints

```
POST   /api/cases                          Create new case
GET    /api/cases/{case_id}                Get full case object
POST   /api/cases/{case_id}/autopsy        Upload autopsy PDF → trigger agent
POST   /api/cases/{case_id}/postmortem     Submit postmortem readings → TOD estimation
POST   /api/cases/{case_id}/cctv           Upload CCTV CSV → parse + anomaly detection
POST   /api/cases/{case_id}/cdr            Upload CDR CSV → scene proximity analysis
POST   /api/cases/{case_id}/images         Upload scene/autopsy images → image agent
POST   /api/cases/{case_id}/suspects       Create suspect session
POST   /api/cases/{case_id}/suspects/{id}/audio    Upload audio → STT → interrogation agent
GET    /api/cases/{case_id}/suspects/{id}/verification  Get cross-verification report
POST   /api/cases/{case_id}/hypotheses     Submit investigator hypothesis
GET    /api/cases/{case_id}/timeline       Get unified correlated timeline
GET    /api/cases/{case_id}/argument-graph Get argument graph JSON
GET    /api/cases/{case_id}/dashboard      Get full dashboard data object
POST   /api/cases/{case_id}/disagree       Investigator disagrees with output → re-run
GET    /api/cases/{case_id}/handoff-brief  Generate handoff brief
GET    /api/cases/{case_id}/court-narrative Generate plain-English narrative
GET    /api/cases/{case_id}/audit          Get full audit log
```

### 8.2 FastAPI Router — Suspect Audio

```python
# backend/routers/suspects.py

from fastapi import APIRouter, UploadFile, File, HTTPException
from agents.stt_agent import transcribe_audio, extract_suspect_segments_only
from agents.interrogation_agent import run_interrogation_agent
from pipeline.fusion import build_evidence_summary
from db.postgres import get_case, update_case
import shutil, uuid, os

router = APIRouter(prefix="/api/cases/{case_id}/suspects", tags=["suspects"])

@router.post("/{suspect_id}/audio")
async def upload_suspect_audio(
    case_id: str,
    suspect_id: str,
    file: UploadFile = File(...)
):
    case = await get_case(case_id)

    # Find suspect session
    suspect = next(
        (s for s in case["suspect_sessions"] if s["suspect_id"] == suspect_id),
        None
    )
    if not suspect:
        raise HTTPException(404, "Suspect session not found")

    # Legal gate — caution must have been administered
    if not suspect["caution_administered"]:
        await log_audit(case_id, "CAUTION_NOT_ADMINISTERED_UPLOAD_BLOCKED",
                        suspect_id=suspect_id)
        raise HTTPException(
            403,
            "Upload blocked: caution_administered is False for this suspect session. "
            "Administer caution and update the session record before uploading audio."
        )

    # Save audio file
    recording_id = f"REC_{suspect_id}_{uuid.uuid4().hex[:6].upper()}"
    save_path = f"/tmp/{recording_id}.{file.filename.split('.')[-1]}"
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Step 1: Transcribe
    transcript = transcribe_audio(save_path, suspect_id, recording_id)

    # Step 2: Extract suspect speech only
    suspect_segments = extract_suspect_segments_only(transcript)

    # Step 3: Build evidence summary
    evidence_summary = build_evidence_summary(case)

    # Step 4: Cross-verify
    verification = run_interrogation_agent(
        suspect_id=suspect_id,
        suspect_segments=suspect_segments,
        pre_interrogation_data={
            "full_name": suspect["full_name"],
            "address": suspect["address"],
            "known_locations": suspect.get("known_locations", []),
            "alibi_claimed_prior": suspect.get("alibi_claimed_prior", "")
        },
        evidence_summary=evidence_summary
    )

    # Step 5: Persist
    await update_case(case_id, {
        f"suspect_sessions.{suspect_id}.transcript_output": transcript,
        f"suspect_sessions.{suspect_id}.verification_output": verification
    })

    await log_audit(case_id, "SUSPECT_AUDIO_PROCESSED",
                    suspect_id=suspect_id, recording_id=recording_id)

    os.remove(save_path)

    return {
        "recording_id": recording_id,
        "transcript_segments": len(transcript["segments"]),
        "claims_extracted": len(verification.get("claims", [])),
        "contradictions_found": sum(
            1 for c in verification.get("claims", [])
            if c["verification_status"] == "CONTRADICTED"
        ),
        "consistency_score": verification.get("overall_consistency_score"),
        "message": "Audio processed and cross-verified successfully"
    }


@router.get("/{suspect_id}/verification")
async def get_verification(case_id: str, suspect_id: str):
    case = await get_case(case_id)
    suspect = next(
        (s for s in case["suspect_sessions"] if s["suspect_id"] == suspect_id),
        None
    )
    if not suspect:
        raise HTTPException(404, "Suspect not found")
    return suspect.get("verification_output", {"message": "Not yet processed"})
```

---

## 9. Technology Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Frontend | React | 18.x | Dashboard UI |
| Styling | Tailwind CSS | 3.x | Component styling |
| Charts | Recharts | 2.x | Timeline, gauge, scores |
| Graph viz | D3.js | 7.x | Argument graph |
| Backend | Python FastAPI | 0.111+ | REST API + WebSocket |
| Task queue | Celery + Redis | 5.x | Async agent jobs |
| STT | OpenAI Whisper | large-v3 | Audio transcription |
| Diarisation | WhisperX | latest | Speaker separation |
| LLM API | Featherless AI | — | All LLM agent calls |
| Vision model | Qwen2.5-VL-72B | — | Image analysis |
| Anomaly detection | scikit-learn | 1.4+ | Isolation Forest |
| TOD physics | Custom (numpy) | — | Henssge formula |
| Graph DB | Neo4j | 5.x | Evidence-entity graph |
| Primary DB | PostgreSQL + PostGIS | 16.x | Case data |
| Document store | MongoDB | 7.x | Raw reports, media |
| Cache | Redis | 7.x | Session, queue |
| Auth | Keycloak | 24.x | RBAC, JWT, audit |
| Explainability | SHAP | 0.45+ | Risk score explanation |
| PDF parsing | PyMuPDF (fitz) | 1.24+ | Autopsy report extraction |
| Env data | Open-Meteo API | — | Ambient temperature |
| Deployment | Docker + Kubernetes | — | Containerised deployment |

---

## 10. Legal & Ethical Compliance

### 10.1 Evidence Authorization Gates

Every upload requires a legal authorization reference. System logs and enforces this.

| Evidence Type | Legal Requirement (India) | Enforcement |
|---|---|---|
| CCTV — public | Written requisition from gazetted police officer | Mandatory ref field |
| CCTV — private | Owner consent OR court order | Mandatory ref field |
| CDR / call records | SP-rank order + Home Secretary approval (Telegraph Act) | Mandatory ref field + officer rank validation |
| Device GPS extraction | Physical seizure warrant or carrier court order | Mandatory ref field |
| Suspect audio | Caution administered + voluntary statement | Boolean gate — upload blocked if false |

### 10.2 System Ethical Boundaries

- All AI outputs labelled as **preliminary investigative assistance** — not legal conclusions
- Risk scores are prioritisation tools — not guilt indicators
- Model version + prompt version logged with every agent run — reproducibility for court
- No output usable as sole basis for arrest, charge, or prosecution
- Explainable AI outputs accompany every classification — SHAP values + reasoning traces

### 10.3 Audit Log Entry Schema

```python
{
  "log_id": "LOG_20240316_001",
  "timestamp": "2024-03-16T10:34:22Z",
  "case_id": "CASE_2024_0041",
  "actor": "OFF_7821",
  "action": "SUSPECT_AUDIO_PROCESSED",
  "target_id": "SUS_001",
  "model_used": "Qwen/Qwen3-32B",
  "model_version": "Qwen3-32B-2025-04",
  "prompt_version": "interrogation_agent_v1.2",
  "legal_auth_ref": "AUTH_CHN_2024_0089",
  "output_hash": "sha256:abc123...",
  "ip_address": "192.168.1.44"
}
```

---

## 11. Novelty Features

### 11.1 Investigator Disagreement Mode

When an investigator clicks "I disagree" on any AI output:

```python
@router.post("/{case_id}/disagree")
async def disagree_with_output(case_id: str, body: dict):
    """
    Re-run affected agent with investigator's context appended.
    Logs the disagreement and updated output to audit trail.
    """
    output_id = body["output_id"]      # e.g. claim classification ID
    disagreement_text = body["reason"] # investigator's explanation
    agent_type = body["agent_type"]    # e.g. "evidence_claim_mapper"

    # Append investigator context to original prompt and re-run
    augmented_result = re_run_agent_with_context(
        agent_type, output_id, disagreement_text
    )

    await log_audit(case_id, "INVESTIGATOR_DISAGREEMENT",
                    output_id=output_id, context=disagreement_text)
    return augmented_result
```

### 11.2 Investigative Momentum Score

```python
def calculate_momentum_score(argument_graph: dict) -> dict:
    claims = argument_graph.get("claims", [])
    if not claims:
        return {"score": 0, "unsupported": [], "contradicted": []}

    supported    = [c for c in claims if c.get("support_count", 0) > 0]
    contradicted = [c for c in claims if c.get("contradiction_count", 0) > 0]
    unsupported  = [c for c in claims if c.get("support_count", 0) == 0]

    score = round((len(supported) / len(claims)) * 100)

    return {
        "score": score,
        "total_claims": len(claims),
        "supported_count": len(supported),
        "contradicted_count": len(contradicted),
        "unsupported_count": len(unsupported),
        "unsupported_claims": [c["statement"] for c in unsupported],
        "message": f"{score}% of claims have supporting evidence. "
                   f"{len(unsupported)} claim(s) require evidence mapping."
    }
```

---

## 12. Build Sequence

### Day 1 Morning — Foundation
```
1. Set up project structure (Section 2)
2. Define Case schema in schemas/case.py
3. Spin up PostgreSQL + Redis via docker-compose
4. Implement llm_client.py — test Featherless connection
5. Implement FastAPI main.py with /api/cases CRUD
```

### Day 1 Afternoon — Evidence Ingestion
```
6. Implement autopsy PDF upload endpoint → autopsy_agent.py
7. Implement postmortem form endpoint → tod_agent.py (Henssge)
8. Implement CCTV CSV upload → parse into DB
9. Implement CDR CSV upload → scene proximity check
```

### Day 1 Evening — Suspect Audio Pipeline (PRIORITY)
```
10. Implement stt_agent.py (Whisper transcription)
11. Implement interrogation_agent.py
12. Wire up /suspects/{id}/audio endpoint
13. Test with mock audio → verify cross-check output
```

### Day 2 Morning — Intelligence Layer
```
14. Implement timeline_agent.py (Isolation Forest + narration)
15. Implement hypothesis_manager.py → claim_extractor.py
16. Implement evidence_claim_mapper.py
17. Implement argument_graph.py (NetworkX)
18. Implement collision_agent.py
```

### Day 2 Afternoon — Dashboard
```
19. React app setup (Vite + Tailwind)
20. Implement SuspectPanel — highest demo impact
21. Implement EvidenceTimeline
22. Implement CaseOverview with risk score + TOD bar
23. Connect to FastAPI via axios
```

### Day 2 Evening — Demo Prep
```
24. Load mock data (autopsy + CCTV + CDR + suspect audio)
25. Pre-run full pipeline on mock case
26. Cache dashboard output
27. Rehearse 3-minute demo script
```

---

## 13. Environment Setup

### 13.1 `.env` File

```env
# Featherless AI
FEATHERLESS_API_KEY=your_key_here

# Database
POSTGRES_URL=postgresql://aiventra:password@localhost:5432/aiventra
MONGO_URL=mongodb://localhost:27017/aiventra
REDIS_URL=redis://localhost:6379

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# External APIs
OPEN_METEO_BASE=https://archive-api.open-meteo.com/v1/archive

# Auth
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=aiventra
KEYCLOAK_CLIENT_ID=aiventra-api
```

### 13.2 `requirements.txt`

```
fastapi==0.111.0
uvicorn==0.29.0
pydantic==2.7.0
python-multipart==0.0.9
requests==2.31.0
pymupdf==1.24.3
openai-whisper==20231117
whisperx==3.1.5
scikit-learn==1.4.2
pandas==2.2.2
numpy==1.26.4
networkx==3.3
asyncpg==0.29.0
motor==3.4.0
redis==5.0.4
python-dotenv==1.0.1
shap==0.45.1
celery==5.4.0
```

### 13.3 `docker-compose.yml`

```yaml
version: "3.9"
services:
  postgres:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_DB: aiventra
      POSTGRES_USER: aiventra
      POSTGRES_PASSWORD: password
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]

  mongo:
    image: mongo:7
    ports: ["27017:27017"]
    volumes: ["mongodata:/data/db"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  neo4j:
    image: neo4j:5
    environment:
      NEO4J_AUTH: neo4j/password
    ports: ["7474:7474", "7687:7687"]
    volumes: ["neo4jdata:/data"]

  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [postgres, mongo, redis, neo4j]
    volumes: ["./backend:/app"]
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [backend]

volumes:
  pgdata:
  mongodata:
  neo4jdata:
```

---

*AIVENTRA System Specification v1.0 — HackHere Community — Confidential*  
*All AI outputs are investigative assistance tools. No output constitutes a legal conclusion.*
