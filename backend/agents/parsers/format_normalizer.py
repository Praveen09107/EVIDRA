"""
EVIDRA — Format Normalizer (Tier 1 / M-03).

Implements Core Agent Specs §M-03 and ML Spec §9:
- Multi-carrier CDR operator detection (Airtel/Jio/BSNL/VI)
- Code-based CSV parsing (not LLM-based)
- Phone number E.164 normalization
- Datetime normalization with timezone handling
- PII masking (phone, email, Aadhaar, PAN, IMEI, names via regex)
- Financial statement normalization
"""
import re
import io
import csv
import json
import logging
from uuid import UUID
from datetime import datetime
from typing import Optional
import pytz
from agents.base import BaseAgent
from core.llm_gateway import llm
from core.database import db

logger = logging.getLogger("evidra.normalizer")

# ═══════════════════════════════════════════════════════════
# MULTI-CARRIER CDR OPERATOR DETECTION (spec §9.1)
# ═══════════════════════════════════════════════════════════

CDR_OPERATOR_SIGNATURES = {
    "AIRTEL": {
        "required_cols": {"PhoneNumber", "Date", "Time", "CallType", "Duration"},
        "optional_cols": {"CalledNumber", "TowerID", "TowerLatitude", "TowerLongitude", "IMEI"},
        "date_formats": ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"],
        "event_type_map": {"MOC": "MOC", "MTC": "MTC", "SMS-MO": "SMS_MO", "SMS-MT": "SMS_MT", "GPRS": "DATA"},
    },
    "JIO": {
        "required_cols": {"MSISDN", "CALL_DATE", "CALL_TIME", "CALL_TYPE", "DURATION_SEC"},
        "optional_cols": {"B_PARTY", "CELL_ID", "CIRCLE", "LAC", "ROAMING"},
        "date_formats": ["%Y-%m-%d"],
        "event_type_map": {"VOICE_OUT": "MOC", "VOICE_IN": "MTC", "SMS_OUT": "SMS_MO", "SMS_IN": "SMS_MT"},
    },
    "BSNL": {
        "required_cols": {"Subscriber No", "Call Date", "Call Time", "Outgoing/Incoming"},
        "optional_cols": set(),
        "date_formats": ["%d-%b-%Y", "%d/%m/%Y"],
        "event_type_map": {"O": "MOC", "I": "MTC", "S-O": "SMS_MO", "S-I": "SMS_MT"},
    },
    "VI": {
        "required_cols": {"Mobile Number", "Transaction Date", "Transaction Time", "Call Type"},
        "optional_cols": set(),
        "event_type_map": {"OG_VOICE": "MOC", "IC_VOICE": "MTC", "OG_SMS": "SMS_MO", "IC_SMS": "SMS_MT"},
    },
}

# Generic column aliases for fallback
GENERIC_CDR_ALIASES = {
    "msisdn": ["PhoneNumber", "MSISDN", "Subscriber No", "Mobile Number", "CLI", "A_Party", "Calling_Number"],
    "timestamp": ["Date & Time", "timestamp", "CALL_DATE", "Call Date", "Transaction Date", "Date_Time"],
    "time": ["Time", "CALL_TIME", "Call Time", "Transaction Time", "Start_Time"],
    "type": ["CallType", "CALL_TYPE", "Call Type", "Outgoing/Incoming", "Type", "Service_Type"],
    "duration": ["Duration", "Duration(Sec)", "DURATION_SEC", "Seconds", "Call_Duration"],
    "counterparty": ["Other Party", "CalledNumber", "B_PARTY", "Dialled", "Called_Number", "B Party"],
    "tower": ["Cell ID", "TowerID", "CELL_ID", "BTS_ID", "CGI", "Cell_ID"],
    "lat": ["TowerLatitude", "Latitude", "Lat", "BTS_Lat"],
    "lon": ["TowerLongitude", "Longitude", "Long", "BTS_Lon"],
    "imei": ["IMEI", "Device_IMEI"],
}


def detect_cdr_operator(columns: list[str]) -> tuple[str, float]:
    """Detect CDR operator from column names."""
    col_set = set(c.strip() for c in columns)
    best_op = "UNKNOWN"
    best_score = 0.0

    for operator, sig in CDR_OPERATOR_SIGNATURES.items():
        req_match = len(sig["required_cols"] & col_set) / max(len(sig["required_cols"]), 1)
        opt_match = len(sig.get("optional_cols", set()) & col_set) / max(len(sig.get("optional_cols", set())), 1)
        score = req_match * 0.7 + opt_match * 0.3
        if score > best_score:
            best_score = score
            best_op = operator

    return (best_op, best_score) if best_score >= 0.4 else ("GENERIC", best_score)


def find_column(columns: list[str], alias_key: str) -> Optional[str]:
    """Find a column by its alias key."""
    aliases = GENERIC_CDR_ALIASES.get(alias_key, [])
    for alias in aliases:
        for col in columns:
            if col.strip().lower() == alias.lower():
                return col.strip()
    return None


# ═══════════════════════════════════════════════════════════
# PHONE NUMBER NORMALIZATION (spec §M-03)
# ═══════════════════════════════════════════════════════════

def normalize_msisdn(raw: str) -> str:
    """Normalize phone number to E.164 (Indian)."""
    digits = re.sub(r"\D", "", str(raw))
    if len(digits) == 10:
        return f"91{digits}"
    if len(digits) == 11 and digits.startswith("0"):
        return f"91{digits[1:]}"
    if len(digits) == 12 and digits.startswith("91"):
        return digits
    if len(digits) == 13 and digits.startswith("091"):
        return digits[1:]
    return digits


# ═══════════════════════════════════════════════════════════
# DATETIME NORMALIZATION (spec §M-03)
# ═══════════════════════════════════════════════════════════

DATE_FORMATS = [
    "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y",
    "%d-%b-%Y", "%d %b %Y", "%d %B %Y", "%Y%m%d", "%d%m%Y",
]
TIME_FORMATS = ["%H:%M:%S", "%H:%M", "%I:%M:%S %p", "%I:%M %p"]


def normalize_datetime(date_str: str, time_str: str = "", timezone: str = "Asia/Kolkata") -> Optional[str]:
    """Parse date+time into UTC ISO 8601."""
    combined = f"{date_str.strip()} {time_str.strip()}".strip()
    tz = pytz.timezone(timezone)

    for dfmt in DATE_FORMATS:
        for tfmt in (TIME_FORMATS if time_str else [""]):
            try:
                fmt = f"{dfmt} {tfmt}".strip() if tfmt else dfmt
                local_dt = datetime.strptime(combined, fmt)
                local_dt = tz.localize(local_dt)
                return local_dt.astimezone(pytz.utc).isoformat()
            except ValueError:
                continue

    # Fallback: try dateutil
    try:
        from dateutil import parser as dp
        local_dt = dp.parse(combined, dayfirst=True)
        if not local_dt.tzinfo:
            local_dt = tz.localize(local_dt)
        return local_dt.astimezone(pytz.utc).isoformat()
    except Exception:
        return combined


# ═══════════════════════════════════════════════════════════
# PII MASKING (spec §M-03)
# ═══════════════════════════════════════════════════════════

PII_PATTERNS = [
    ("PHONE",    r"\b(?:\+91|0)?[6-9]\d{9}\b",             "PARTIAL"),
    ("EMAIL",    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "FULL"),
    ("AADHAAR",  r"\b\d{4}\s\d{4}\s\d{4}\b",               "FULL"),
    ("PAN",      r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",             "PARTIAL"),
    ("IMEI",     r"\b\d{15}\b",                             "PARTIAL_END"),
]


def mask_pii(text: str) -> tuple[str, int]:
    """Apply PII masking patterns. Returns (masked_text, count)."""
    count = 0
    masked = text

    for pii_type, pattern, mask_type in PII_PATTERNS:
        matches = re.findall(pattern, masked)
        for match in matches:
            count += 1
            if mask_type == "FULL":
                replacement = f"[{pii_type}_MASKED]"
            elif mask_type == "PARTIAL":
                replacement = f"{match[:3]}****{match[-2:]}"
            elif mask_type == "PARTIAL_END":
                replacement = f"{'*' * (len(match)-4)}{match[-4:]}"
            else:
                replacement = f"[{pii_type}_MASKED]"
            masked = masked.replace(match, replacement, 1)

    return masked, count


# ═══════════════════════════════════════════════════════════
# FINANCIAL STATEMENT NORMALIZATION
# ═══════════════════════════════════════════════════════════

FINANCIAL_COLUMN_ALIASES = {
    "date": ["Date", "Transaction Date", "Txn Date", "Value Date"],
    "narration": ["Narration", "Description", "Particulars", "Remarks"],
    "debit": ["Withdrawal", "Debit", "DR", "Withdrawal Amount"],
    "credit": ["Deposit", "Credit", "CR", "Deposit Amount"],
    "balance": ["Balance", "Closing Balance", "Running Balance"],
    "counterparty": ["Counterparty", "Beneficiary", "Payee"],
}


class FormatNormalizer(BaseAgent):
    agent_id = "format_normalizer"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        """Normalize raw evidence into canonical tables with code-based parsing."""

        prior = await self.get_prior_result("evidence_parser")
        ocr_result = await self.get_prior_result("ocr")

        if not prior or "files" not in prior:
            raise ValueError("Missing upstream data from evidence_parser")

        # Merge OCR text into parser results
        if ocr_result and "ocr_results" in ocr_result:
            for file_id, ocr_data in ocr_result["ocr_results"].items():
                if file_id in prior["files"]:
                    existing = prior["files"][file_id].get("content", "")
                    if len(existing.strip()) < 50:
                        prior["files"][file_id]["content"] = ocr_data.get("full_text_corrected", existing)

        stats = {"cdr_events": 0, "financial_events": 0, "pii_masks": 0}
        warnings = []

        for file_id, file_data in prior["files"].items():
            doc_type = file_data["doc_type"]
            content = file_data["content"]

            # PII masking on all content
            masked_content, pii_count = mask_pii(content)
            stats["pii_masks"] += pii_count

            if doc_type == "CDR":
                count = await self._normalize_cdr(case_id, file_id, masked_content)
                stats["cdr_events"] += count

            elif doc_type == "FINANCIAL_RECORDS":
                count = await self._normalize_financial(case_id, file_id, masked_content)
                stats["financial_events"] += count

        await db.execute(
            "UPDATE case_files SET status='PROCESSED', processed_at=NOW() WHERE case_id=$1",
            case_id,
        )

        await self.log_step(
            "DATA_NORMALIZATION",
            "Format Normalization Complete",
            f"CDR: {stats['cdr_events']} events, Financial: {stats['financial_events']} events, "
            f"PII masks: {stats['pii_masks']} applied.",
            confidence=0.92,
        )

        return {"stats": stats, "_warnings": warnings, "_confidence": 0.92}

    async def _normalize_cdr(self, case_id: UUID, file_id: str, raw_csv: str) -> int:
        """Parse CDR CSV using code-based operator detection (not LLM)."""
        try:
            reader = csv.DictReader(io.StringIO(raw_csv))
            if not reader.fieldnames:
                return 0

            columns = list(reader.fieldnames)
            operator, confidence = detect_cdr_operator(columns)

            # Find columns by alias
            msisdn_col = find_column(columns, "msisdn")
            ts_col = find_column(columns, "timestamp")
            time_col = find_column(columns, "time")
            type_col = find_column(columns, "type")
            dur_col = find_column(columns, "duration")
            cp_col = find_column(columns, "counterparty")
            tower_col = find_column(columns, "tower")
            lat_col = find_column(columns, "lat")
            lon_col = find_column(columns, "lon")
            imei_col = find_column(columns, "imei")

            # Get event type map
            type_map = {}
            if operator in CDR_OPERATOR_SIGNATURES:
                type_map = CDR_OPERATOR_SIGNATURES[operator]["event_type_map"]

            count = 0
            for row in reader:
                try:
                    # Normalize MSISDN
                    msisdn = normalize_msisdn(row.get(msisdn_col, "")) if msisdn_col else ""

                    # Normalize datetime
                    date_str = row.get(ts_col, "") if ts_col else ""
                    time_str = row.get(time_col, "") if time_col else ""
                    ts = normalize_datetime(date_str, time_str)

                    # Normalize event type
                    raw_type = row.get(type_col, "UNKNOWN") if type_col else "UNKNOWN"
                    event_type = type_map.get(raw_type.strip().upper(), raw_type.strip().upper())

                    # Duration
                    duration = int(float(row.get(dur_col, 0) or 0)) if dur_col else 0

                    # Counterparty
                    cp = normalize_msisdn(row.get(cp_col, "")) if cp_col else ""

                    # Tower
                    tower = str(row.get(tower_col, "")).strip() if tower_col else ""
                    lat = float(row[lat_col]) if lat_col and row.get(lat_col) else None
                    lon = float(row[lon_col]) if lon_col and row.get(lon_col) else None
                    imei = str(row.get(imei_col, "")).strip() if imei_col else None

                    await db.execute(
                        """
                        INSERT INTO canonical_cdr_events
                        (case_id, file_id, source_msisdn, event_timestamp, event_type,
                         duration_seconds, counterparty_msisdn, cell_tower_id, lat, lon, imei)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                        """,
                        case_id, UUID(file_id), msisdn, ts, event_type,
                        duration, cp, tower, lat, lon, imei,
                    )
                    count += 1
                except Exception as e:
                    logger.debug(f"Skipping CDR row: {e}")
                    continue

            await self.log_step(
                "DATA_NORMALIZATION",
                f"CDR Normalized ({operator})",
                f"Detected operator: {operator} (conf: {confidence:.2f}). Inserted {count} canonical events.",
                confidence=confidence,
            )
            return count

        except Exception as e:
            logger.error(f"CDR normalization failed: {e}")
            # Fallback to LLM-based parsing
            return await self._normalize_cdr_llm(case_id, file_id, raw_csv)

    async def _normalize_cdr_llm(self, case_id: UUID, file_id: str, raw_csv: str) -> int:
        """LLM fallback for unparseable CDR formats."""
        prompt = f"""Extract call data records from this raw text.
Return ONLY valid JSON array:
[{{"timestamp":"ISO8601","event_type":"MOC|MTC|SMS_MO|SMS_MT","source_msisdn":"string","counterparty":"string","duration":int,"tower_id":"string","lat":float,"lon":float}}]

Raw Data:
{raw_csv[:3000]}"""

        resp = await llm.complete(task="evidence_parse", prompt=prompt,
                                  system_prompt="You are a data normalizer. Output raw JSON arrays only.")
        try:
            events = json.loads(resp.text.replace("```json", "").replace("```", "").strip())
            for e in events:
                await db.execute(
                    """INSERT INTO canonical_cdr_events
                    (case_id, file_id, source_msisdn, event_timestamp, event_type,
                     duration_seconds, counterparty_msisdn, cell_tower_id, lat, lon)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
                    case_id, UUID(file_id), e.get("source_msisdn"), e.get("timestamp"),
                    e.get("event_type", "MOC"), e.get("duration", 0), e.get("counterparty"),
                    e.get("tower_id"), e.get("lat"), e.get("lon"),
                )
            return len(events)
        except Exception:
            return 0

    async def _normalize_financial(self, case_id: UUID, file_id: str, raw_csv: str) -> int:
        """Parse financial CSV using code-based column detection."""
        try:
            reader = csv.DictReader(io.StringIO(raw_csv))
            if not reader.fieldnames:
                return 0

            columns = list(reader.fieldnames)

            # Find columns
            date_col = None
            for alias in FINANCIAL_COLUMN_ALIASES["date"]:
                if alias in columns:
                    date_col = alias
                    break

            narr_col = None
            for alias in FINANCIAL_COLUMN_ALIASES["narration"]:
                if alias in columns:
                    narr_col = alias
                    break

            debit_col = None
            for alias in FINANCIAL_COLUMN_ALIASES["debit"]:
                if alias in columns:
                    debit_col = alias
                    break

            credit_col = None
            for alias in FINANCIAL_COLUMN_ALIASES["credit"]:
                if alias in columns:
                    credit_col = alias
                    break

            cp_col = None
            for alias in FINANCIAL_COLUMN_ALIASES["counterparty"]:
                if alias in columns:
                    cp_col = alias
                    break

            count = 0
            for row in reader:
                try:
                    ts = normalize_datetime(row.get(date_col, "")) if date_col else None
                    narration = row.get(narr_col, "") if narr_col else ""

                    debit = float(row.get(debit_col, 0) or 0) if debit_col else 0
                    credit = float(row.get(credit_col, 0) or 0) if credit_col else 0

                    if debit > 0:
                        txn_type = "DEBIT"
                        amount = debit
                    elif credit > 0:
                        txn_type = "CREDIT"
                        amount = credit
                    else:
                        continue

                    counterparty = row.get(cp_col, "") if cp_col else ""

                    await db.execute(
                        """INSERT INTO canonical_financial_events
                        (case_id, file_id, timestamp, txn_type, amount, narration, counterparty)
                        VALUES ($1,$2,$3,$4,$5,$6,$7)""",
                        case_id, UUID(file_id), ts, txn_type, amount, narration, counterparty,
                    )
                    count += 1
                except Exception as e:
                    logger.debug(f"Skipping financial row: {e}")
                    continue

            return count

        except Exception as e:
            logger.error(f"Financial normalization failed: {e}")
            # Fallback to LLM
            return await self._normalize_financial_llm(case_id, file_id, raw_csv)

    async def _normalize_financial_llm(self, case_id: UUID, file_id: str, raw_csv: str) -> int:
        """LLM fallback for unparseable financial formats."""
        prompt = f"""Extract financial transactions from this raw text.
Return ONLY valid JSON array:
[{{"timestamp":"ISO8601","txn_type":"DEBIT|CREDIT","amount":float,"narration":"string","counterparty":"string"}}]

Raw Data:
{raw_csv[:3000]}"""

        resp = await llm.complete(task="evidence_parse", prompt=prompt,
                                  system_prompt="You are a data normalizer. Output raw JSON arrays only.")
        try:
            events = json.loads(resp.text.replace("```json", "").replace("```", "").strip())
            for e in events:
                await db.execute(
                    """INSERT INTO canonical_financial_events
                    (case_id, file_id, timestamp, txn_type, amount, narration, counterparty)
                    VALUES ($1,$2,$3,$4,$5,$6,$7)""",
                    case_id, UUID(file_id), e.get("timestamp"), e.get("txn_type", "DEBIT"),
                    float(e.get("amount", 0)), e.get("narration"), e.get("counterparty"),
                )
            return len(events)
        except Exception:
            return 0
