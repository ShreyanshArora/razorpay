"""Smoke tests: the phase 0-2 pipeline runs and hits sane quality bars."""
from nexus.graph.loader import load_world
from nexus.pipeline import run_detection, build_training_set
from nexus.ml.scorer import RingScorer
from nexus.ml.features import extract_features
from nexus.ml.labeling import label_cluster
from nexus.eval.harness import evaluate


def test_worlds_load():
    for name in ("world_dev", "world_test"):
        w = load_world(name)
        assert len(w.accounts) > 500
        assert len(w.transactions) > 1000


def test_graph_recovers_all_rings():
    w = load_world("world_dev")
    clusters, widx, G = run_detection(w)
    # every planted ring should surface with >=60% of members in one cluster
    from collections import Counter, defaultdict
    acc_ring = {a.account_id: a.ring_id for a in w.accounts}
    truth = defaultdict(set)
    for a in w.accounts:
        if a.ring_id and a.ring_id.startswith("ring_"):
            truth[a.ring_id].add(a.account_id)
    best = defaultdict(int)
    for c in clusters:
        cnt = Counter(acc_ring.get(a) for a in c.account_ids if acc_ring.get(a))
        for r, n in cnt.items():
            best[r] = max(best[r], n)
    recovered = sum(1 for r in truth if best[r] / len(truth[r]) >= 0.6)
    assert recovered == len(truth), f"only recovered {recovered}/{len(truth)} rings"


def test_nexus_beats_baseline_on_heldout():
    dev = load_world("world_dev")
    _, feats, labels, _ = build_training_set(dev)
    scorer = RingScorer().fit(feats, labels)

    test = load_world("world_test")
    clusters, widx, _ = run_detection(test)
    tfeats = [extract_features(c, widx) for c in clusters]
    tlabels = [label_cluster(c, test) for c in clusters]
    scores = [scorer.score(f) for f in tfeats]
    m = evaluate("nexus", scores, tlabels, 0.5)
    assert m.precision >= 0.9
    assert m.recall >= 0.85
    assert m.recall_evasive >= 0.7   # the hard case
