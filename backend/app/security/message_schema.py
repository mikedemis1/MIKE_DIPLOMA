# backend/app/security/message_schema.py

import json
import secrets
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from app.security.crypto_engine import CryptoEngine, get_crypto_engine


class NodeRole(str, Enum):
    """
    Ρόλος κόμβου (zero-trust policy).
    - controller: π.χ. ο κεντρικός controller UI / orchestrator.
    - zone_display: ο client που εμφανίζει διαφημίσεις σε μια ζώνη.
    - system: κεντρικά services, monitoring, κ.λπ.
    Μπορείς να προσθέσεις κι άλλα (e.g. 'analytics', 'admin').
    """
    CONTROLLER = "controller"
    ZONE_DISPLAY = "zone_display"
    SYSTEM = "system"


class MessageHeader(BaseModel):
    """
    Header του signed μηνύματος.

    Περιέχει:
    - node_id: ποιος κόμβος έστειλε το μήνυμα.
    - zone_id: σε ποια ζώνη ανήκει (αν χρειάζεται).
    - role: τι ρόλο έχει αυτός ο κόμβος (για policy rules).
    - msg_type: τι είδους μήνυμα είναι (π.χ. 'PLACEMENT_UPDATE').
    - timestamp: χρόνος δημιουργίας (UTC) για anti-replay window.
    - nonce: τυχαίο token για anti-replay (ανά μήνυμα).
    - alg: όνομα αλγορίθμου HMAC (συμβατό με CryptoEngine.algorithm_name).
    - version: schema version του πρωτοκόλλου.
    """
    node_id: str = Field(..., description="Logical node id, e.g. 'controller-1'")
    zone_id: Optional[str] = Field(
        None, description="Zone id, e.g. 'glassfloor-1' (optional)"
    )
    role: NodeRole
    msg_type: str
    timestamp: datetime
    nonce: str
    alg: Optional[str] = Field(
        None,
        description="Algorithm name used for HMAC (e.g. 'HMAC_SHA256').",
    )
    version: str = Field(
        "1.0",
        description="Message schema version for future migrations.",
    )


class SignedMessage(BaseModel):
    """
    Πλήρες signed μήνυμα.

    - header: Metadata για το ποιος / τι / πότε.
    - payload: Το πραγματικό business περιεχόμενο (π.χ. ποια ads σε ποιες οθόνες).
    - hmac: Η υπογραφή (HMAC hex) πάνω σε (header + payload).
    """
    header: MessageHeader
    payload: Dict[str, Any]
    hmac: str

    def _to_canonical_bytes(self) -> bytes:
        """
        Γυρνάει (header + payload) σε σταθερό JSON string (sorted keys),
        ΧΩΡΙΣ το hmac, ώστε:
        - ο υπολογισμός HMAC να είναι deterministic,
        - να έχουμε το ίδιο input σε υπογραφή/επαλήθευση.

        Αυτό είναι σημαντικό για να μην αλλάζει το digest
        απλά και μόνο επειδή άλλαξε η σειρά των keys.
        """
        data = {
            "header": self.header.dict(),
            "payload": self.payload,
        }
        json_str = json.dumps(
            data,
            sort_keys=True,          # σταθερή σειρά κλειδιών
            separators=(",", ":"),   # χωρίς περιττά spaces
            ensure_ascii=False,
        )
        return json_str.encode("utf-8")

    def compute_hmac(
        self,
        secret_key: str,
        crypto: Optional[CryptoEngine] = None,
    ) -> str:
        """
        Υπολογίζει το HMAC και το γράφει στο self.hmac.
        """
        if crypto is None:
            crypto = get_crypto_engine()

        message_bytes = self._to_canonical_bytes()
        signature = crypto.sign(message_bytes, secret_key)
        self.hmac = signature
        return self.hmac

    def verify_hmac(
        self,
        secret_key: str,
        crypto: Optional[CryptoEngine] = None,
    ) -> bool:
        """
        Επαληθεύει το HMAC του μηνύματος.

        Σημείωση:
        - Δεν ελέγχει μόνο του timestamps ή nonces.
          Αυτό θα το κάνουμε στο WebSocket layer (anti-replay window).
        """
        if crypto is None:
            crypto = get_crypto_engine()

        if not self.hmac:
            return False

        message_bytes = self._to_canonical_bytes()
        return crypto.verify(message_bytes, self.hmac, secret_key)

    @classmethod
    def create(
        cls,
        *,
        node_id: str,
        role: NodeRole,
        msg_type: str,
        payload: Dict[str, Any],
        secret_key: str,
        zone_id: Optional[str] = None,
        crypto: Optional[CryptoEngine] = None,
    ) -> "SignedMessage":
        """
        Convenience factory:
        - Φτιάχνει header (timestamp, nonce, alg).
        - Δημιουργεί SignedMessage.
        - Υπολογίζει και βάζει το HMAC.

        Αυτό θα καλείται συνήθως εκεί που στέλνεις μηνύματα προς τα WebSockets.
        """
        if crypto is None:
            crypto = get_crypto_engine()

        header = MessageHeader(
            node_id=node_id,
            zone_id=zone_id,
            role=role,
            msg_type=msg_type,
            timestamp=datetime.now(timezone.utc),
            nonce=secrets.token_hex(16),  # 128-bit nonce σε hex
            alg=crypto.algorithm_name,
        )

        msg = cls(header=header, payload=payload, hmac="")
        msg.compute_hmac(secret_key=secret_key, crypto=crypto)
        return msg
