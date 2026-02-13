"""AES-CBC encryption/decryption for Philips air purifier CoAP protocol."""

import hashlib

from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad


class DigestMismatchError(Exception):
    pass


class EncryptionContext:
    SECRET_KEY = "JiangPan"  # noqa: S105  # nosec B105 - required by device protocol

    def __init__(self) -> None:
        self._client_key: str | None = None

    def set_client_key(self, client_key: str) -> None:
        self._client_key = client_key

    def _increment_client_key(self) -> None:
        if self._client_key is None:
            raise RuntimeError("Client key not initialised; call set_client_key() first")
        client_key_int = (int(self._client_key, 16) + 1) & 0xFFFFFFFF
        client_key_next = client_key_int.to_bytes(4, byteorder="big").hex().upper()
        self._client_key = client_key_next

    def _create_cipher(self, key: str) -> AES:
        key_and_iv = hashlib.md5((self.SECRET_KEY + key).encode()).hexdigest().upper()  # noqa: S324  # nosec B324 - required by device protocol
        half_keylen = len(key_and_iv) // 2
        secret_key = key_and_iv[:half_keylen]
        iv = key_and_iv[half_keylen:]
        return AES.new(
            key=secret_key.encode(),
            mode=AES.MODE_CBC,
            iv=iv.encode(),
        )

    def encrypt(self, payload: str) -> str:
        self._increment_client_key()
        key = self._client_key
        plaintext_padded = pad(payload.encode(), 16, style="pkcs7")
        cipher = self._create_cipher(key)
        ciphertext = cipher.encrypt(plaintext_padded).hex().upper()
        digest = hashlib.sha256((key + ciphertext).encode()).hexdigest().upper()
        return key + ciphertext + digest

    def decrypt(self, payload_encrypted: str) -> str:
        key = payload_encrypted[:8]
        ciphertext = payload_encrypted[8:-64]
        digest = payload_encrypted[-64:]
        digest_calculated = hashlib.sha256((key + ciphertext).encode()).hexdigest().upper()
        if digest != digest_calculated:
            raise DigestMismatchError
        cipher = self._create_cipher(key)
        plaintext_padded = cipher.decrypt(bytes.fromhex(ciphertext))
        plaintext_unpadded = unpad(plaintext_padded, 16, style="pkcs7")
        return plaintext_unpadded.decode()
