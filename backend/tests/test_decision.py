"""Phase 4 tests: minimum-defensible-action, policy gating, idempotency."""
from collections import Counter
from nexus.graph.loader import load_world
from nexus.pipeline import run_detection
from nexus.ml.scorer import RingScorer
from nexus.ml.features import WorldIndex
from nexus.decision.engine import DecisionEngine
from nexus.decision.policy import AuditLog, execute
import os

DATA = os.path.join(os.path.dirname(__file__), "..", "data")


def _truth(c, acc_ring):
    r = Counter(acc_ring.get(a) for a in c.account_ids if acc_ring.get(a)).most_common(1)
    return r[0][0] if r else "none"


def _engine():
    world = load_world("world_test")
    clusters, widx, _ = run_detection(world)
    scorer = RingScorer.load(os.path.join(DATA, "ring_scorer.pkl"))
    acc_ring = {a.account_id: a.ring_id for a in world.accounts}
    audit = AuditLog()
    return DecisionEngine(scorer, widx, audit), clusters, acc_ring, audit


def test_ring_authorized_with_min_action():
    engine, clusters, acc_ring, _ = _engine()
    ring = next(c for c in clusters if _truth(c, acc_ring).startswith("ring_") and c.size >= 5)
    cd = engine.process(ring)
    assert cd.case_file.verdict == "fraud_ring"
    assert cd.decision.authorized is True
    # prefers step-up over block (lower friction) when it meets the target
    assert cd.recommended.action.startswith("step_up")
    assert cd.recommended.legit_accounts_hit == 0


def test_legit_cluster_not_enforced():
    engine, clusters, acc_ring, _ = _engine()
    legit = next(c for c in clusters if _truth(c, acc_ring).startswith("legit_off") and c.size >= 12)
    cd = engine.process(legit)
    assert cd.decision.authorized is False
    assert cd.decision.action in ("clear", "human_review")


def test_idempotency():
    engine, clusters, acc_ring, audit = _engine()
    ring = next(c for c in clusters if _truth(c, acc_ring).startswith("ring_") and c.size >= 5)
    cd = engine.process(ring, auto_execute=True)
    # second execution of the same decision must be a no-op
    res = execute(cd.decision, audit)
    assert res["executed"] is False
    assert "idempotent" in res["reason"]


def test_all_citations_grounded():
    engine, clusters, acc_ring, _ = _engine()
    ring = next(c for c in clusters if _truth(c, acc_ring).startswith("ring_") and c.size >= 5)
    cd = engine.process(ring)
    valid = cd.evidence.fact_ids()
    for r in cd.case_file.reasons_for + cd.case_file.reasons_against:
        for fid in r.fact_ids:
            assert fid in valid, f"hallucinated citation {fid}"
