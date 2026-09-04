"""Phase 1 — the NEXUS entity graph and cluster detection.

Nodes  = accounts.
Edges  = evidence that two accounts are related. Two kinds:
  HARD identifier edges  : shared device / ip / card / shipping address.
  BEHAVIOURAL edges      : two accounts created within a tight window AND
                           transacting within a tight window (co-burst).
                           This is what surfaces EVASIVE rings that share no
                           hard identifier — a JOIN cannot produce these edges.

Cluster detection:
  1. connected components on the union graph;
  2. any component that is large + loosely connected (e.g. an office sharing one
     IP) is refined with greedy-modularity community detection so we don't merge
     genuinely unrelated accounts into one giant blob.

Everything here is DETERMINISTIC. No ML, no LLM. This is the substrate.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from itertools import combinations

import networkx as nx

from nexus.schema import World, Transaction

# Behavioural-edge thresholds (minutes)
CREATE_WINDOW_MIN = 25.0     # accounts created within this window are time-linked
BURST_WINDOW_MIN = 15.0      # transactions within this window are co-burst
# A component is "loose" (candidate for community splitting) if bigger than this
# and its density is below this.
LOOSE_MIN_SIZE = 15
LOOSE_MAX_DENSITY = 0.15

HARD_FIELDS = ("device_id", "ip_id", "card_fingerprint", "shipping_address_id")
EDGE_KIND = {
    "device_id": "device", "ip_id": "ip",
    "card_fingerprint": "card", "shipping_address_id": "address",
    "time": "time",
}


@dataclass
class Cluster:
    cluster_id: str
    account_ids: list[str]
    # shared-identifier evidence: field -> {shared_value: [account_ids]}
    shared: dict = field(default_factory=dict)
    edge_kinds: dict = field(default_factory=dict)   # kind -> count
    n_time_edges: int = 0

    @property
    def size(self) -> int:
        return len(self.account_ids)


class EntityGraphBuilder:
    def __init__(self, world: World):
        self.world = world
        self.txns_by_account: dict[str, list[Transaction]] = defaultdict(list)
        for t in world.transactions:
            self.txns_by_account[t.account_id].append(t)
        self.account_created = {a.account_id: a.created_at for a in world.accounts}
        self.G = nx.Graph()

    # --------------------------------------------------------------- build
    def build(self) -> nx.Graph:
        G = self.G
        for a in self.world.accounts:
            G.add_node(a.account_id)

        self._add_hard_edges(G)
        self._add_time_edges(G)
        return G

    def _add_hard_edges(self, G: nx.Graph):
        for field_name in HARD_FIELDS:
            groups: dict[str, set[str]] = defaultdict(set)
            for t in self.world.transactions:
                groups[getattr(t, field_name)].add(t.account_id)
            for value, accs in groups.items():
                if len(accs) < 2:
                    continue
                for a, b in combinations(sorted(accs), 2):
                    self._bump_edge(G, a, b, EDGE_KIND[field_name], value)

    def _add_time_edges(self, G: nx.Graph):
        """Behavioural co-burst edges. To stay O(n log n) we sort accounts by
        creation time and only compare accounts inside a sliding creation window,
        then confirm with a transaction-burst overlap check."""
        accs = sorted(self.world.accounts, key=lambda a: a.created_at)
        # precompute each account's earliest & latest txn time
        span = {}
        for aid, ts in self.txns_by_account.items():
            times = [t.created_at for t in ts]
            span[aid] = (min(times), max(times))

        for i, a in enumerate(accs):
            a_created = a.created_at
            for j in range(i + 1, len(accs)):
                b = accs[j]
                gap = (b.created_at - a_created).total_seconds() / 60.0
                if gap > CREATE_WINDOW_MIN:
                    break  # sorted — no later account can be closer
                # confirm a transaction co-burst
                sa, sb = span.get(a.account_id), span.get(b.account_id)
                if not sa or not sb:
                    continue
                # overlap / proximity of their transaction bursts
                latest_start = max(sa[0], sb[0])
                earliest_end = min(sa[1], sb[1])
                proximity = (latest_start - earliest_end).total_seconds() / 60.0
                if proximity <= BURST_WINDOW_MIN:
                    self._bump_edge(G, a.account_id, b.account_id, "time", None)

    @staticmethod
    def _bump_edge(G, a, b, kind, value):
        if G.has_edge(a, b):
            d = G[a][b]
            d["weight"] = d.get("weight", 0) + 1
            d["kinds"].add(kind)
            if value is not None:
                d["values"].setdefault(kind, set()).add(value)
        else:
            G.add_edge(a, b, weight=1, kinds={kind},
                       values=({kind: {value}} if value is not None else {}))


class ClusterDetector:
    def __init__(self, G: nx.Graph, world: World):
        self.G = G
        self.world = world
        self.txns_by_account: dict[str, list[Transaction]] = defaultdict(list)
        for t in world.transactions:
            self.txns_by_account[t.account_id].append(t)

    def detect(self) -> list[Cluster]:
        clusters: list[Cluster] = []
        idx = 0
        for comp in nx.connected_components(self.G):
            if len(comp) < 2:
                continue
            sub = self.G.subgraph(comp)
            parts = self._maybe_split(sub)
            for part in parts:
                if len(part) < 2:
                    continue
                idx += 1
                clusters.append(self._materialise(f"cl_{idx:04d}", part))
        # largest first — most exposed clusters surface at the top of the queue
        clusters.sort(key=lambda c: c.size, reverse=True)
        return clusters

    def _maybe_split(self, sub: nx.Graph) -> list[set]:
        n = sub.number_of_nodes()
        density = nx.density(sub) if n > 1 else 0
        if n >= LOOSE_MIN_SIZE and density < LOOSE_MAX_DENSITY:
            try:
                comms = nx.community.greedy_modularity_communities(sub, weight="weight")
                return [set(c) for c in comms]
            except Exception:
                return [set(sub.nodes())]
        return [set(sub.nodes())]

    def _materialise(self, cid: str, nodes: set) -> Cluster:
        node_list = sorted(nodes)
        shared: dict = defaultdict(lambda: defaultdict(list))
        edge_kinds: dict = defaultdict(int)
        n_time = 0
        sub = self.G.subgraph(nodes)
        for a, b, d in sub.edges(data=True):
            for k in d["kinds"]:
                edge_kinds[k] += 1
                if k == "time":
                    n_time += 1
        # reconstruct which identifiers are actually shared inside the cluster
        for field_name, kind in [("device_id", "device"), ("ip_id", "ip"),
                                  ("card_fingerprint", "card"),
                                  ("shipping_address_id", "address")]:
            val_to_accs = defaultdict(set)
            for aid in node_list:
                for t in self.txns_by_account[aid]:
                    val_to_accs[getattr(t, field_name)].add(aid)
            for val, accs in val_to_accs.items():
                if len(accs) >= 2:
                    shared[kind][val] = sorted(accs)
        return Cluster(
            cluster_id=cid, account_ids=node_list,
            shared={k: dict(v) for k, v in shared.items()},
            edge_kinds=dict(edge_kinds), n_time_edges=n_time,
        )
