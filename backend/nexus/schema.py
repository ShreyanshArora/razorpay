"""Core domain schema for NEXUS.

Everything downstream (graph, ML, investigator, decision) speaks these types.
Kept deliberately flat and serializable so the FastAPI layer can return them directly.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional


# ---- Ground-truth population labels (used only for eval, never fed to the model) ----
class Population(str, Enum):
    NORMAL = "normal"              # independent legitimate customer
    RING_OBVIOUS = "ring_obvious"  # fraud ring sharing hard identifiers (device/card/addr)
    RING_EVASIVE = "ring_evasive"  # fraud ring rotating identifiers; betrayed by behaviour
    LOOKALIKE = "lookalike"        # legit cluster that LOOKS coordinated (family/office/reseller)


class LookalikeKind(str, Enum):
    FAMILY = "family"       # shared home device/address, few accounts
    OFFICE = "office"       # shared corporate IP, many unrelated people
    RESELLER = "reseller"   # one person, many orders, shared card/address, but legitimate


@dataclass
class Account:
    account_id: str
    created_at: datetime
    population: Population          # GROUND TRUTH — for eval only
    ring_id: Optional[str] = None  # GROUND TRUTH cluster id (ring_* or legit_*)
    lookalike_kind: Optional[LookalikeKind] = None

    def public(self) -> dict:
        """Fields a detector is allowed to see (no ground-truth labels)."""
        return {"account_id": self.account_id, "created_at": self.created_at.isoformat()}


@dataclass
class Transaction:
    txn_id: str
    account_id: str
    amount: float
    created_at: datetime
    # Observable identifiers the risk system legitimately has access to:
    device_id: str
    ip_id: str
    card_fingerprint: str
    shipping_address_id: str
    status: str                  # "captured" | "failed"
    disputed: bool = False       # chargeback/dispute later raised
    population: Population = Population.NORMAL   # GROUND TRUTH (eval only)
    ring_id: Optional[str] = None                # GROUND TRUTH (eval only)

    def public(self) -> dict:
        return {
            "txn_id": self.txn_id,
            "account_id": self.account_id,
            "amount": self.amount,
            "created_at": self.created_at.isoformat(),
            "device_id": self.device_id,
            "ip_id": self.ip_id,
            "card_fingerprint": self.card_fingerprint,
            "shipping_address_id": self.shipping_address_id,
            "status": self.status,
            "disputed": self.disputed,
        }


@dataclass
class World:
    """A generated synthetic payments world + its ground truth."""
    accounts: list[Account] = field(default_factory=list)
    transactions: list[Transaction] = field(default_factory=list)
    seed: int = 0
    split: str = "dev"  # "dev" | "test"

    def summary(self) -> dict:
        from collections import Counter
        acc_pop = Counter(a.population.value for a in self.accounts)
        rings = {a.ring_id for a in self.accounts if a.ring_id and a.ring_id.startswith("ring_")}
        legit = {a.ring_id for a in self.accounts if a.ring_id and a.ring_id.startswith("legit_")}
        return {
            "seed": self.seed,
            "split": self.split,
            "accounts": len(self.accounts),
            "transactions": len(self.transactions),
            "account_populations": dict(acc_pop),
            "fraud_rings": len(rings),
            "legit_clusters": len(legit),
            "disputed_txns": sum(1 for t in self.transactions if t.disputed),
        }
