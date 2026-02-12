"""Tests for the encryption module."""

import pytest

from philips_airctrl.coap.encryption import DigestMismatchException, EncryptionContext


class TestEncryptionContext:
    def test_init(self):
        ctx = EncryptionContext()
        assert ctx._client_key is None

    def test_set_client_key(self):
        ctx = EncryptionContext()
        ctx.set_client_key("12345678")
        assert ctx._client_key == "12345678"

    def test_increment_client_key(self):
        ctx = EncryptionContext()
        ctx.set_client_key("00000001")
        ctx._increment_client_key()
        assert ctx._client_key == "00000002"

    def test_increment_client_key_overflow(self):
        ctx = EncryptionContext()
        ctx.set_client_key("FFFFFFFF")
        ctx._increment_client_key()
        assert ctx._client_key == "00000000"

    def test_encrypt_decrypt_roundtrip(self):
        ctx = EncryptionContext()
        ctx.set_client_key("12345678")

        original_payload = '{"test": "data", "number": 42}'
        encrypted = ctx.encrypt(original_payload)

        assert encrypted != original_payload
        assert len(encrypted) > len(original_payload)

        decrypted = ctx.decrypt(encrypted)
        assert decrypted == original_payload

    def test_encrypt_increments_key(self):
        ctx = EncryptionContext()
        ctx.set_client_key("00000001")

        ctx.encrypt("test data")
        assert ctx._client_key == "00000002"

    def test_decrypt_invalid_digest(self):
        ctx = EncryptionContext()
        ctx.set_client_key("12345678")

        encrypted = ctx.encrypt("test data")
        corrupted = encrypted[:-64] + "0" * 64

        with pytest.raises(DigestMismatchException):
            ctx.decrypt(corrupted)

    def test_decrypt_malformed_payload(self):
        ctx = EncryptionContext()

        with pytest.raises(Exception):
            ctx.decrypt("short")

        with pytest.raises(Exception):
            ctx.decrypt("ZZZZZZZZ" + "A" * 64 + "B" * 64)

    def test_multiple_encryptions_different_results(self):
        ctx = EncryptionContext()
        ctx.set_client_key("12345678")

        payload = "same data"
        encrypted1 = ctx.encrypt(payload)
        encrypted2 = ctx.encrypt(payload)

        assert encrypted1 != encrypted2
        assert ctx.decrypt(encrypted1) == payload
        assert ctx.decrypt(encrypted2) == payload

    def test_secret_key_constant(self):
        assert EncryptionContext.SECRET_KEY == "JiangPan"

    def test_encryption_format(self):
        ctx = EncryptionContext()
        ctx.set_client_key("ABCDEF12")

        encrypted = ctx.encrypt("test")

        assert encrypted.startswith("ABCDEF13")
        assert all(c in "0123456789ABCDEF" for c in encrypted)
        assert len(encrypted) >= 8 + 64
        assert (len(encrypted) - 8 - 64) % 2 == 0

    def test_create_cipher(self):
        ctx = EncryptionContext()
        cipher = ctx._create_cipher("12345678")
        assert cipher is not None
