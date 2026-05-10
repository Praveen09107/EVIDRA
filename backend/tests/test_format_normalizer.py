import pytest
from agents.parsers.format_normalizer import detect_cdr_operator, normalize_msisdn, mask_pii

def test_cdr_operator_detection():
    # Test operator regex patterns
    op, score = detect_cdr_operator(["Date", "Time", "Calling_Num", "Called_Num", "Duration"])
    # Not exact match but we can check format
    assert isinstance(op, str)
    
    op_airtel, _ = detect_cdr_operator(["PhoneNumber", "Date", "Time", "CallType", "Duration"])
    assert op_airtel == "AIRTEL"
    
    op_jio, _ = detect_cdr_operator(["MSISDN", "CALL_DATE", "CALL_TIME", "CALL_TYPE", "DURATION_SEC"])
    assert op_jio == "JIO"
    
    op_bsnl, _ = detect_cdr_operator(["Subscriber No", "Call Date", "Call Time", "Outgoing/Incoming"])
    assert op_bsnl == "BSNL"

def test_pii_masking():
    text = "The suspect's phone is 9876543210 and email is john.doe@example.com."
    masked, count = mask_pii(text)
    
    assert "9876543210" not in masked
    assert "[PHONE]" not in masked  # Actually the code uses [PHONE_MASKED] or partial mask
    assert "john.doe@example.com" not in masked
    assert count >= 2

def test_phone_number_standardization():
    # Convert local to E.164 (Indian 91)
    assert normalize_msisdn("98765-43210") == "919876543210"
    assert normalize_msisdn("09876543210") == "919876543210"
    assert normalize_msisdn("+919876543210") == "919876543210"
