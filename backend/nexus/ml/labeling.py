"""Assign ground-truth labels to DETECTED clusters, for training and eval.

A detected cluster is labelled RING (1) if a majority of its accounts belong to
the same planted fraud ring; otherwise LEGIT (0). We also record the dominant
ground-truth id and how 'pure' the cluster is, for honest per-type reporting.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass

from nexus.schema import World
from nexus.graph.entity_graph import Cluster


@dataclass
class ClusterLabel:
    cluster_id: str
    is_ring: int                 # 1 fraud ring, 0 legit
    dominant_truth: str | None   # e.g. ring_eva_007 or legit_off_003
    dominant_kind: str           # "ring_obvious" | "ring_evasive" | "legit" | "mixed"
    purity: float
    n_accounts: int
    n_fraud_accounts: int        # ground-truth fraud accounts inside (for FP-cost)
    n_legit_accounts: int


def label_cluster(cluster: Cluster, world: World, ring_threshold: float = 0.5) -> ClusterLabel:
    acc_ring = {a.account_id: a.ring_id for a in world.accounts}
    acc_pop = {a.account_id: a.population.value for a in world.accounts}

    ring_ids = [acc_ring.get(a) for a in cluster.account_ids]
    ring_counter = Counter(r for r in ring_ids if r)
    dominant_truth, dom_n = (ring_counter.most_common(1)[0] if ring_counter else (None, 0))
    purity = dom_n / cluster.size if cluster.size else 0.0

    n_fraud = sum(1 for a in cluster.account_ids
                  if acc_pop.get(a) in ("ring_obvious", "ring_evasive"))
    n_legit = cluster.size - n_fraud

    # cluster is a ring if the dominant truth is a fraud ring AND it's the majority
    is_ring = 0
    dominant_kind = "legit"
    if dominant_truth and dominant_truth.startswith("ring_") and purity >= ring_threshold:
        is_ring = 1
        dominant_kind = "ring_obvious" if dominant_truth.startswith("ring_obv") else "ring_evasive"
    elif dominant_truth and dominant_truth.startswith("legit_"):
        dominant_kind = "legit"
    elif n_fraud > 0 and n_legit > 0:
        dominant_kind = "mixed"

    return ClusterLabel(
        cluster_id=cluster.cluster_id, is_ring=is_ring,
        dominant_truth=dominant_truth, dominant_kind=dominant_kind,
        purity=purity, n_accounts=cluster.size,
        n_fraud_accounts=n_fraud, n_legit_accounts=n_legit,
    )
