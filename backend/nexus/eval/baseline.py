"""Naive baseline to beat: a structural rule-of-thumb, the kind a first-pass
fraud rule would use.

  'Flag a cluster as a fraud ring if enough of its accounts share a hard
   identifier (device / card / address) OR the same IP.'

This catches OBVIOUS rings well. It is BLIND to evasive rings (no shared
identifiers) and it WRONGLY flags legit offices/families (which share IP/device).
That failure mode is exactly the false-positive cost NEXUS reduces.
"""
from __future__ import annotations
from nexus.ml.features import extract_features
from nexus.graph.entity_graph import Cluster
from nexus.ml.features import WorldIndex


def baseline_is_ring(cluster: Cluster, world_index: WorldIndex,
                     share_threshold: float = 0.5) -> float:
    """Returns a pseudo-probability in {0,1}-ish: 1.0 if the structural rule fires."""
    feat = extract_features(cluster, world_index)
    hard_share = max(feat["shared_device_ratio"], feat["shared_card_ratio"],
                     feat["shared_address_ratio"], feat["shared_ip_ratio"])
    return 1.0 if hard_share >= share_threshold else 0.0
