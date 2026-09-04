"""Phase 2a — cluster feature extraction.

The feature set is designed so the model can separate the three hard cases:
  - OBVIOUS rings   : high shared-identifier density + tight timing + disputes
  - EVASIVE rings   : LOW shared identifiers, but tight timing + amount
                      structuring + high velocity + disputes
  - LEGIT lookalikes: may share an identifier (office IP / family device) but have
                      SPREAD-OUT timing, natural amount spread, low disputes

So structural features alone cannot win — behavioural features are what make the
model robust to evasive rings and resistant to false positives on offices/families.
"""
from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from datetime import datetime

import numpy as np

from nexus.schema import World, Transaction
from nexus.graph.entity_graph import Cluster

STRUCTURING_THRESHOLD = 5000.0

FEATURE_NAMES = [
    "size",
    "shared_device_ratio",
    "shared_ip_ratio",
    "shared_card_ratio",
    "shared_address_ratio",
    "distinct_device_ratio",     # HIGH for evasive rings (rotation), low for family
    "distinct_card_ratio",
    "creation_span_min",         # LOW = accounts created in a burst
    "creation_burst_density",    # accounts-per-minute of creation
    "txn_span_min",              # LOW = transactions in a burst
    "amount_cv",                 # coeff of variation — LOW = structured/uniform
    "near_threshold_ratio",      # frac of txns just under structuring threshold
    "mean_amount",
    "dispute_ratio",
    "fail_ratio",
    "txns_per_account",
    "time_edge_ratio",           # frac of cluster edges that are behavioural
]


def _minutes_span(times: list[datetime]) -> float:
    if len(times) < 2:
        return 0.0
    return (max(times) - min(times)).total_seconds() / 60.0


def extract_features(cluster: Cluster, world_index: "WorldIndex") -> dict:
    accs = cluster.account_ids
    n = len(accs)
    txns: list[Transaction] = []
    for aid in accs:
        txns.extend(world_index.txns_by_account.get(aid, []))
    n_txn = max(1, len(txns))

    created = [world_index.account_created[a] for a in accs]
    txn_times = [t.created_at for t in txns]

    def shared_ratio(kind_field):
        vals = Counter(getattr(t, kind_field) for t in txns)
        shared = sum(c for c in vals.values() if c > 1)
        return shared / n_txn

    def distinct_ratio(kind_field):
        return len(set(getattr(t, kind_field) for t in txns)) / n_txn

    amounts = [t.amount for t in txns]
    mean_amt = statistics.mean(amounts) if amounts else 0.0
    amount_cv = (statistics.pstdev(amounts) / mean_amt) if mean_amt > 0 and len(amounts) > 1 else 0.0
    near_thr = sum(1 for a in amounts
                   if STRUCTURING_THRESHOLD - 400 <= a < STRUCTURING_THRESHOLD) / n_txn

    creation_span = _minutes_span(created)
    txn_span = _minutes_span(txn_times)
    burst_density = n / (creation_span + 1.0)   # accounts per minute (+1 avoids /0)

    total_edges = sum(cluster.edge_kinds.values()) or 1
    time_edge_ratio = cluster.edge_kinds.get("time", 0) / total_edges

    return {
        "size": float(n),
        "shared_device_ratio": shared_ratio("device_id"),
        "shared_ip_ratio": shared_ratio("ip_id"),
        "shared_card_ratio": shared_ratio("card_fingerprint"),
        "shared_address_ratio": shared_ratio("shipping_address_id"),
        "distinct_device_ratio": distinct_ratio("device_id"),
        "distinct_card_ratio": distinct_ratio("card_fingerprint"),
        "creation_span_min": creation_span,
        "creation_burst_density": burst_density,
        "txn_span_min": txn_span,
        "amount_cv": amount_cv,
        "near_threshold_ratio": near_thr,
        "mean_amount": mean_amt,
        "dispute_ratio": sum(1 for t in txns if t.disputed) / n_txn,
        "fail_ratio": sum(1 for t in txns if t.status == "failed") / n_txn,
        "txns_per_account": len(txns) / n,
        "time_edge_ratio": time_edge_ratio,
    }


def features_to_vector(feat: dict) -> np.ndarray:
    return np.array([feat[k] for k in FEATURE_NAMES], dtype=float)


class WorldIndex:
    """Cheap lookups shared across feature extraction."""
    def __init__(self, world: World):
        self.txns_by_account = defaultdict(list)
        for t in world.transactions:
            self.txns_by_account[t.account_id].append(t)
        self.account_created = {a.account_id: a.created_at for a in world.accounts}
