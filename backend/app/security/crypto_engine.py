# backend/app/security/crypto_engine.py

import os
import hmac
import hashlib
from enum import Enum
from typing import Optional, Union


class CryptoMode(str, Enum):
    """
    Υποστηριζόμενα modes υπογραφής.
    - HMAC_SHA256: κλασικό HMAC πάνω από SHA-256 (SHA-2 οικογένεια).
    - HMAC_SHA3_256: HMAC πάνω από SHA3-256 (SHA-3 οικογένεια).
    """
    HMAC_SHA256 = "HMAC_SHA256"
    HMAC_SHA3_256 = "HMAC_SHA3_256"


def _resolve_mode_from_env() -> CryptoMode:
    """
    Διαβάζει το CRYPTO_MODE από το περιβάλλον και επιστρέφει CryptoMode.
    Αν η τιμή είναι άκυρη ή δεν δοθεί, πέφτει στο HMAC_SHA256.
    """
    raw = os.getenv("CRYPTO_MODE", CryptoMode.HMAC_SHA256.value)
    try:
        return CryptoMode(raw)
    except ValueError:
        # Σε σοβαρό σύστημα θα το κάναμε log ως misconfiguration.
        return CryptoMode.HMAC_SHA256


class CryptoEngine:
    """
    CryptoEngine = ενιαίο interface για υπογραφή & επαλήθευση.

    - Χρησιμοποιείται για HMAC σήμερα.
    - Μπορεί να επεκταθεί αύριο με post-quantum signature engine ή KEM
      χωρίς να αλλάξουν τα σημεία που το καλούν (crypto-agility).
    """

    def __init__(self, mode: Union[CryptoMode, str, None] = None) -> None:
        if mode is None:
            mode = _resolve_mode_from_env()

        if isinstance(mode, str):
            try:
                mode = CryptoMode(mode)
            except ValueError as exc:
                raise ValueError(f"Unsupported CRYPTO_MODE: {mode}") from exc

        self.mode: CryptoMode = mode

    @property
    def algorithm_name(self) -> str:
        """
        Ονομα αλγορίθμου που θα γράφουμε στα headers (π.χ. "HMAC_SHA256").
        """
        return self.mode.value

    def _get_digestmod(self):
        """
        Επιστρέφει τη σωστή συνάρτηση hash από το hashlib
        ανάλογα με το επιλεγμένο mode.
        """
        if self.mode == CryptoMode.HMAC_SHA256:
            return hashlib.sha256
        elif self.mode == CryptoMode.HMAC_SHA3_256:
            return hashlib.sha3_256
        else:
            # Θεωρητικά δεν φτάνουμε ποτέ εδώ αν έχουν καλυφθεί όλα τα modes.
            raise ValueError(f"Unsupported crypto mode: {self.mode}")

    @staticmethod
    def _normalize_secret(secret_key: Union[str, bytes]) -> bytes:
        """
        Δέχεται secret ως str ή bytes και το γυρνάει σε bytes.
        """
        if isinstance(secret_key, bytes):
            return secret_key
        return secret_key.encode("utf-8")

    def sign(self, message: bytes, secret_key: Union[str, bytes]) -> str:
        """
        Υπογράφει το message με HMAC και επιστρέφει το digest σε hex string.

        - message: τα bytes που θέλουμε να προστατεύσουμε (header+payload).
        - secret_key: το shared secret του node (per-node key).
        """
        key_bytes = self._normalize_secret(secret_key)
        digestmod = self._get_digestmod()
        mac = hmac.new(key_bytes, message, digestmod=digestmod)
        return mac.hexdigest()

    def verify(self, message: bytes, signature_hex: str, secret_key: Union[str, bytes]) -> bool:
        """
        Επαληθεύει την υπογραφή.

        - Υπολογίζει HMAC πάνω στο message με το secret.
        - Χρησιμοποιεί constant-time σύγκριση (hmac.compare_digest)
          για προστασία από timing attacks.
        """
        expected = self.sign(message, secret_key)
        # constant-time compare
        return hmac.compare_digest(expected, signature_hex)


# Optional singleton για να μην φτιάχνουμε εκατό instances
_engine_singleton: Optional[CryptoEngine] = None


def get_crypto_engine() -> CryptoEngine:
    """
    Επιστρέφει ένα shared CryptoEngine instance.
    Το χρησιμοποιούμε παντού, ώστε να έχουμε ενιαίο CRYPTO_MODE.
    """
    global _engine_singleton
    if _engine_singleton is None:
        _engine_singleton = CryptoEngine()
    return _engine_singleton
