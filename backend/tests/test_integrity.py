"""
Tests for: core/integrity.py — SHA-256 hashing and chain-of-custody verification.
"""
import pytest
import hashlib
from core.integrity import compute_file_hash, compute_content_hash


class TestFileHash:
    def test_basic_bytes(self):
        data = b"Hello Forensic World"
        assert compute_file_hash(data) == hashlib.sha256(data).hexdigest()

    def test_empty_bytes(self):
        data = b""
        assert compute_file_hash(data) == hashlib.sha256(data).hexdigest()

    def test_large_payload(self):
        data = b"X" * 1_000_000
        assert compute_file_hash(data) == hashlib.sha256(data).hexdigest()

    def test_determinism(self):
        data = b"Same input always produces same hash"
        h1 = compute_file_hash(data)
        h2 = compute_file_hash(data)
        assert h1 == h2

    def test_collision_resistance(self):
        h1 = compute_file_hash(b"input_a")
        h2 = compute_file_hash(b"input_b")
        assert h1 != h2


class TestContentHash:
    def test_basic_string(self):
        text = "Hello Forensic World"
        assert compute_content_hash(text) == hashlib.sha256(text.encode("utf-8")).hexdigest()

    def test_unicode(self):
        text = "Victim: अरुण कुमार"
        assert compute_content_hash(text) == hashlib.sha256(text.encode("utf-8")).hexdigest()

    def test_empty_string(self):
        assert compute_content_hash("") == hashlib.sha256(b"").hexdigest()
