import pytest
import hashlib
from core.integrity import compute_file_hash, compute_content_hash

def test_compute_file_hash():
    # Test SHA-256 for bytes
    test_bytes = b"Hello Forensic World"
    expected_hash = hashlib.sha256(test_bytes).hexdigest()
    assert compute_file_hash(test_bytes) == expected_hash

def test_compute_content_hash():
    # Test SHA-256 for strings
    test_string = "Hello Forensic World"
    expected_hash = hashlib.sha256(test_string.encode("utf-8")).hexdigest()
    assert compute_content_hash(test_string) == expected_hash
