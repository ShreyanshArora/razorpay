"""Phase 4c — the NEXUS decision orchestrator.

Ties every layer together for a single cluster and returns one signed CaseDecision:
  cluster -> evidence -> AI investigation -> per-account risk ->
  intervention simulation -> minimum defensible action -> policy authorization -> audit.
"""
from __future__ import annotations
from dataclasses import dataclass

from nexus.graph.entity_graph import Cluster
from nexus.ml.features import extract_features, WorldIndex
from nexus.ml.scorer import RingScorer
from nexus.investigator.evidence import EvidenceBuilder, EvidenceBundle
from nexus.investigator.investigator import investigate, CaseFile
from nexus.decision.interventions import (
    AccountRisk, enumerate_interventions, minimum_defensible, Intervention,
)
from nexus.decision.policy import authorize, execute, Decision, AuditLog


@dataclass
class CaseDecision:
    cluster_id: str
    ring_probability: float
    case_file: CaseFile
    evidence: EvidenceBundle
    interventions: list[Intervention]
    recommended: Intervention
    decision: Decision

    def as_dict(self):
        return {
            "cluster_id": self.cluster_id,
            "ring_probability": self.ring_probability,
            "case_file": self.case_file.as_dict(),
            "evidence": self.evidence.as_dict(),
            "interventions": [i.as_dict() for i in self.interventions],
            "recommended": self.recommended.as_dict(),
            "decision": self.decision.as_dict(),
        }


def _account_risks(cluster: Cluster, widx: WorldIndex, ring_prob: float,
                   verdict: str) -> list[AccountRisk]:
    out = []
    for aid in cluster.account_ids:
        txns = widx.txns_by_account.get(aid, [])
        exposure = sum(t.amount for t in txns if t.status == "captured")
        disputed = any(t.disputed for t in txns)
        # per-account risk: cluster ring-prob nudged by this account's own disputes
        risk = min(1.0, ring_prob + (0.1 if disputed else 0.0))
        # our best guess this specific account is legit (only relevant for legit verdicts)
        is_legit = verdict in ("family", "office", "reseller")
        out.append(AccountRisk(aid, round(exposure, 2), round(risk, 3), is_legit))
    return out


class DecisionEngine:
    def __init__(self, scorer: RingScorer, widx: WorldIndex, audit: AuditLog | None = None):
        self.scorer = scorer
        self.widx = widx
        self.eb = EvidenceBuilder(widx)
        self.audit = audit or AuditLog()

    def process(self, cluster: Cluster, auto_execute: bool = False) -> CaseDecision:
        feat = extract_features(cluster, self.widx)
        ring_prob = self.scorer.score(feat)
        self.audit.log(cluster.cluster_id, "cluster_scored", {"ring_probability": round(ring_prob, 4)})

        bundle = self.eb.build(cluster, ring_prob)
        self.audit.log(cluster.cluster_id, "evidence_built", {"n_facts": len(bundle.facts)})

        case = investigate(bundle)
        self.audit.log(cluster.cluster_id, "investigated",
                       {"verdict": case.verdict, "confidence": case.confidence,
                        "provider": case.provider, "grounded": case.grounded})

        risks = _account_risks(cluster, self.widx, ring_prob, case.verdict)
        interventions = enumerate_interventions(risks)
        recommended = minimum_defensible(interventions)
        self.audit.log(cluster.cluster_id, "intervention_selected",
                       {"action": recommended.action,
                        "risk_reduced_pct": recommended.risk_reduced_pct})

        decision = authorize(case, recommended, ring_prob, self.audit)
        if auto_execute:
            execute(decision, self.audit)

        return CaseDecision(cluster.cluster_id, round(ring_prob, 4), case, bundle,
                            interventions, recommended, decision)
