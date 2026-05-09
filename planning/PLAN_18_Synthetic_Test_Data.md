# PLAN 18 — Synthetic Test Data (Demo Case)
**Owner:** Dev A | **Hour:** 21:00–22:00 | **Priority:** CRITICAL

---

## 1. Objective
Generate `CASE-2026-001 "Kumar"` — a complete synthetic forensic case for the demo. This ensures the pipeline has realistic data to parse, extract, and fuse.

---

## 2. Generator Script

**File: `tests/fixtures/generate_case.py`**

```python
"""
Generate synthetic test case data for AIVENTRA demo.
Creates: autopsy report text, CDR CSV, financial CSV.
"""
import csv, os, random
from datetime import datetime, timedelta

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "case_2026_001")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_autopsy_report():
    report = """
MEDICO-LEGAL AUTOPSY REPORT
Case Number: ML-2026-00147
Date of Autopsy: 10-May-2026, 10:30 AM
Examining Pathologist: Dr. R. Venkatesh

IDENTIFYING INFORMATION:
Name: Arun Kumar (Deceased)
Age: 34 years
Sex: Male
Weight: 72 kg
Last Known Alive: 08-May-2026, approximately 11:00 PM
Body Found: 09-May-2026, 06:30 AM

EXTERNAL & INTERNAL EXAMINATION:
Body temperature: 28.4°C (measured rectally at scene, 07:15 AM)
Ambient temperature: 24.2°C (recorded at scene)
Rigor mortis: FULL
Livor mortis: FIXED

INJURIES:
1. Blunt force trauma to the right temporal region. Severity: SEVERE.
2. Linear abrasions on both forearms (defensive). Severity: MODERATE.

CAUSE OF DEATH: Craniocerebral injury due to blunt force trauma to head.
MANNER OF DEATH: HOMICIDE
"""
    filepath = os.path.join(OUTPUT_DIR, "autopsy_report_kumar.txt")
    with open(filepath, "w") as f:
        f.write(report)
    print(f"Generated: {filepath}")

def generate_cdr_csv():
    filepath = os.path.join(OUTPUT_DIR, "cdr_kumar_airtel.csv")
    base_date = datetime(2026, 5, 7, 0, 0, 0)
    
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Date & Time", "Call Type", "Duration(Sec)", "Other Party", "Cell ID", "IMEI"])
        
        # Add normal events
        for i in range(10):
            ts = base_date + timedelta(hours=8+i)
            writer.writerow([ts.strftime("%Y-%m-%d %H:%M:%S"), "Outgoing Voice", 120, "9876543210", "BLR-T001", "IMEI123"])
            
        # Add anomalous event right before death
        ts_anom = datetime(2026, 5, 8, 23, 15, 0)
        writer.writerow([ts_anom.strftime("%Y-%m-%d %H:%M:%S"), "Incoming SMS", 0, "UNKNOWN", "BLR-T045", "IMEI123"])
        
    print(f"Generated: {filepath}")

def generate_financial_csv():
    filepath = os.path.join(OUTPUT_DIR, "financial_kumar_hdfc.csv")
    
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Date","Narration","Withdrawal","Deposit","Balance"])
        
        # Normal
        writer.writerow(["2026-05-01", "SALARY", 0, 85000, 85000])
        writer.writerow(["2026-05-05", "GROCERIES", 2000, 0, 83000])
        
        # Anomaly
        writer.writerow(["2026-05-07", "ATM WITHDRAWAL BLR-WHITEFIELD", 50000, 0, 33000])
        
    print(f"Generated: {filepath}")

if __name__ == "__main__":
    generate_autopsy_report()
    generate_cdr_csv()
    generate_financial_csv()
```

## Acceptance Criteria
- [ ] Script runs and generates 3 files in `tests/fixtures/case_2026_001/`
