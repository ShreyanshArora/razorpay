"""Phase 5a — the NEXUS service layer.

Runs the full pipeline once, caches the results, and offers clean accessors the
API routes wrap. Keeps all heavy work out of the request path so the UI is snappy.
"""
from __future__ import annotations
import json, os
from functools import lru_cache

from nexus.graph.loader import load_world
from nexus.pipeline import run_detection, build_training_set
from nexus.ml.scorer import RingScorer
from nexus.ml.features import extract_features, WorldIndex
from nexus.decision.engine import DecisionEngine
from nexus.decision.policy import AuditLog

DATA = os.path.join(os.path.dirname(__file__), "..", "..", "data")


class NexusService:
    def __init__(self, world_name: str = "world_test"):
        self.world = load_world(world_name)
        self.clusters, self.widx, self.graph = run_detection(self.world)
        # Train the scorer in-process from the dev world. This avoids depending on a
        # pickled model that can break across scikit-learn / Python versions.
        _dev = load_world("world_dev")
        _clusters, _feats, _labels, _ = build_training_set(_dev)
        self.scorer = RingScorer().fit(_feats, _labels)
        self.audit = AuditLog()
        self.engine = DecisionEngine(self.scorer, self.widx, self.audit)
        self._cluster_by_id = {c.cluster_id: c for c in self.clusters}
        self._decisions: dict = {}
        self._process_all()

    def _process_all(self):
        for c in self.clusters:
            cd = self.engine.process(c, auto_execute=False)
            self._decisions[c.cluster_id] = cd

    # ---- accessors ----
    def overview(self) -> dict:
        rings = [cd for cd in self._decisions.values() if cd.case_file.verdict == "fraud_ring"]
        total_exposure = sum(cd.recommended.total_exposure for cd in rings)
        protected = sum(cd.recommended.exposure_protected for cd in rings
                        if cd.decision.authorized)
        auto = sum(1 for cd in rings if cd.decision.authorized)
        review = sum(1 for cd in rings if not cd.decision.authorized)
        return {
            "world": self.world.split, "seed": self.world.seed,
            "accounts": len(self.world.accounts),
            "transactions": len(self.world.transactions),
            "clusters_detected": len(self.clusters),
            "rings_confirmed": len(rings),
            "exposure_at_risk": round(total_exposure, 2),
            "exposure_protected": round(protected, 2),
            "auto_actioned": auto, "human_review": review,
            "audit_events": len(self.audit.events()),
        }

    def list_cases(self) -> list[dict]:
        rows = []
        for cd in self._decisions.values():
            cf = cd.case_file
            rows.append({
                "cluster_id": cd.cluster_id,
                "verdict": cf.verdict,
                "confidence": cf.confidence,
                "ring_probability": cd.ring_probability,
                "n_accounts": cd.evidence.n_accounts,
                "exposure": cd.recommended.total_exposure,
                "recommended_action": cd.recommended.action,
                "authorized": cd.decision.authorized,
                "decision_action": cd.decision.action,
                "provider": cf.provider,
                "narrative": cf.narrative,
            })
        # rings first, then by exposure
        rows.sort(key=lambda r: (r["verdict"] != "fraud_ring", -r["exposure"]))
        return rows

    def case(self, cluster_id: str) -> dict | None:
        cd = self._decisions.get(cluster_id)
        return cd.as_dict() if cd else None

    def graph_data(self, cluster_id: str) -> dict | None:
        """Nodes + edges for the force-directed cluster graph."""
        cluster = self._cluster_by_id.get(cluster_id)
        if not cluster:
            return None
        sub = self.graph.subgraph(cluster.account_ids)
        nodes = [{"id": a, "exposure": round(sum(
                    t.amount for t in self.widx.txns_by_account.get(a, [])
                    if t.status == "captured"), 2)}
                 for a in cluster.account_ids]
        edges = []
        for u, v, d in sub.edges(data=True):
            edges.append({"source": u, "target": v,
                          "kinds": sorted(d["kinds"]),
                          "weight": d.get("weight", 1)})
        return {"cluster_id": cluster_id, "nodes": nodes, "edges": edges}

    def audit_events(self, cluster_id: str | None = None) -> list[dict]:
        evs = self.audit.events()
        if cluster_id:
            evs = [e for e in evs if e["cluster_id"] == cluster_id]
        return evs

    def eval_results(self) -> dict:
        with open(os.path.join(DATA, "eval_results.json")) as f:
            return json.load(f)

    def execute_case(self, cluster_id: str) -> dict:
        from nexus.decision.policy import execute
        cd = self._decisions.get(cluster_id)
        if not cd:
            return {"error": "not found"}
        return execute(cd.decision, self.audit)


@lru_cache(maxsize=1)
def get_service() -> NexusService:
    return NexusService()
