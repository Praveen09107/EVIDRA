"""
Tests for: agents/parsers/format_normalizer.py — CDR detection, PII masking, phone normalization.
"""
import pytest
from agents.parsers.format_normalizer import (
    detect_cdr_operator, normalize_msisdn, mask_pii,
    normalize_datetime, CDR_OPERATOR_SIGNATURES
)


class TestCDROperatorDetection:
    def test_airtel_detection(self):
        cols = ["PhoneNumber", "Date", "Time", "CallType", "Duration"]
        op, score = detect_cdr_operator(cols)
        assert op == "AIRTEL"
        assert score > 0.4

    def test_jio_detection(self):
        cols = ["MSISDN", "CALL_DATE", "CALL_TIME", "CALL_TYPE", "DURATION_SEC"]
        op, score = detect_cdr_operator(cols)
        assert op == "JIO"

    def test_bsnl_detection(self):
        cols = ["Subscriber No", "Call Date", "Call Time", "Outgoing/Incoming"]
        op, score = detect_cdr_operator(cols)
        assert op == "BSNL"

    def test_vi_detection(self):
        cols = ["Mobile Number", "Transaction Date", "Transaction Time", "Call Type"]
        op, score = detect_cdr_operator(cols)
        assert op == "VI"

    def test_unknown_columns(self):
        cols = ["FooBar", "BazQux"]
        op, score = detect_cdr_operator(cols)
        assert op == "GENERIC"

    def test_whitespace_handling(self):
        cols = ["  PhoneNumber  ", " Date ", " Time ", " CallType ", " Duration "]
        op, score = detect_cdr_operator(cols)
        assert op == "AIRTEL"


class TestPhoneNormalization:
    def test_10_digit(self):
        assert normalize_msisdn("9876543210") == "919876543210"

    def test_with_dash(self):
        assert normalize_msisdn("98765-43210") == "919876543210"

    def test_with_leading_zero(self):
        assert normalize_msisdn("09876543210") == "919876543210"

    def test_with_country_code(self):
        assert normalize_msisdn("+919876543210") == "919876543210"

    def test_with_091_prefix(self):
        assert normalize_msisdn("0919876543210") == "919876543210"

    def test_already_12_digits(self):
        assert normalize_msisdn("919876543210") == "919876543210"

    def test_short_number(self):
        result = normalize_msisdn("12345")
        assert result == "12345"


class TestPIIMasking:
    def test_phone_masked(self):
        text = "Call 9876543210 for info"
        masked, count = mask_pii(text)
        assert "9876543210" not in masked
        assert count >= 1

    def test_email_masked(self):
        text = "Send to john@example.com"
        masked, count = mask_pii(text)
        assert "john@example.com" not in masked
        assert "[EMAIL_MASKED]" in masked

    def test_aadhaar_masked(self):
        text = "Aadhaar: 1234 5678 9012"
        masked, count = mask_pii(text)
        assert "1234 5678 9012" not in masked

    def test_pan_masked(self):
        text = "PAN: ABCDE1234F"
        masked, count = mask_pii(text)
        assert "ABCDE1234F" not in masked

    def test_no_pii(self):
        text = "This is a clean sentence"
        masked, count = mask_pii(text)
        assert masked == text
        assert count == 0

    def test_multiple_pii(self):
        text = "Phone 9876543210 email test@test.com PAN ABCDE1234F"
        masked, count = mask_pii(text)
        assert count >= 3


class TestDatetimeNormalization:
    def test_iso_format(self):
        result = normalize_datetime("2026-05-09", "14:30:00")
        assert result is not None
        assert "2026" in result

    def test_indian_format(self):
        result = normalize_datetime("09/05/2026", "14:30:00")
        assert result is not None

    def test_date_only(self):
        result = normalize_datetime("2026-05-09")
        assert result is not None

    def test_invalid_date(self):
        result = normalize_datetime("not-a-date")
        assert result == "not-a-date"
