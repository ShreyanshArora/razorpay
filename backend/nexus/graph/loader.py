"""Load a persisted world JSON back into typed objects (public view only for detection)."""
from __future__ import annotations
import json, os
from datetime import datetime
from dateutil import parser as dtparser
from nexus.schema import Account, Transaction, World, Population, LookalikeKind

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def load_world(name: str) -> World:
    path = os.path.join(DATA_DIR, f"{name}.json")
    with open(path) as f:
        raw = json.load(f)
    accounts, txns = [], []
    for a in raw["accounts"]:
        accounts.append(Account(
            account_id=a["account_id"],
            created_at=dtparser.isoparse(a["created_at"]),
            population=Population(a["population"]),
            ring_id=a.get("ring_id"),
            lookalike_kind=LookalikeKind(a["lookalike_kind"]) if a.get("lookalike_kind") else None,
        ))
    for t in raw["transactions"]:
        txns.append(Transaction(
            txn_id=t["txn_id"], account_id=t["account_id"], amount=t["amount"],
            created_at=dtparser.isoparse(t["created_at"]),
            device_id=t["device_id"], ip_id=t["ip_id"],
            card_fingerprint=t["card_fingerprint"],
            shipping_address_id=t["shipping_address_id"],
            status=t["status"], disputed=t["disputed"],
            population=Population(t["population"]), ring_id=t.get("ring_id"),
        ))
    return World(accounts=accounts, transactions=txns,
                 seed=raw["meta"]["seed"], split=raw["meta"]["split"])
