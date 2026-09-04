"""Train on dev world, evaluate on held-out test world, save artifacts.

Outputs:
  backend/data/ring_scorer.pkl     — trained model
  backend/data/eval_results.json   — the headline numbers (baseline vs NEXUS)
"""
from __future__ import annotations
import json, os
from dataclasses import asdict

from nexus.graph.loader import load_world
from nexus.pipeline import build_training_set, run_detection
from nexus.ml.features import extract_features
from nexus.ml.scorer import RingScorer
from nexus.eval.baseline import baseline_is_ring
from nexus.eval.harness import evaluate

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def tune_threshold(scores, labels):
    """Pick the threshold maximising F1 on the dev set."""
    best_t, best_f1 = 0.5, -1.0
    for i in range(5, 96, 5):
        t = i / 100.0
        m = evaluate("nexus_dev", scores, labels, t)
        if m.f1 > best_f1:
            best_f1, best_t = m.f1, t
    return best_t


def main():
    # ---- train on DEV ----
    dev = load_world("world_dev")
    dev_clusters, dev_feats, dev_labels, dev_clabels = build_training_set(dev)
    scorer = RingScorer().fit(dev_feats, dev_labels)
    scorer.save(os.path.join(DATA_DIR, "ring_scorer.pkl"))

    dev_scores = [scorer.score(f) for f in dev_feats]
    tuned_t = tune_threshold(dev_scores, dev_clabels)

    # ---- evaluate on HELD-OUT TEST ----
    test = load_world("world_test")
    test_clusters, test_widx, _ = run_detection(test)
    test_feats = [extract_features(c, test_widx) for c in test_clusters]
    from nexus.ml.labeling import label_cluster
    test_clabels = [label_cluster(c, test) for c in test_clusters]

    nexus_scores = [scorer.score(f) for f in test_feats]
    base_scores = [baseline_is_ring(c, test_widx) for c in test_clusters]

    results = {
        "dev_summary": dev.summary(),
        "test_summary": test.summary(),
        "test_clusters_detected": len(test_clusters),
        "tuned_threshold": tuned_t,
        "feature_importance": {k: round(v, 4) for k, v in list(scorer.feature_importance_.items())[:10]},
        "methods": {
            "baseline_structural": evaluate("baseline_structural", base_scores, test_clabels, 0.5).as_dict(),
            "nexus_ml_default": evaluate("nexus_ml_default", nexus_scores, test_clabels, 0.5).as_dict(),
            "nexus_ml_tuned": evaluate("nexus_ml_tuned", nexus_scores, test_clabels, tuned_t).as_dict(),
        },
    }
    with open(os.path.join(DATA_DIR, "eval_results.json"), "w") as f:
        json.dump(results, f, indent=2)

    # ---- pretty print ----
    print("=" * 68)
    print("NEXUS — HELD-OUT EVALUATION (train=seed42, test=seed7)")
    print("=" * 68)
    print(f"Detected clusters on test world: {len(test_clusters)}")
    print(f"Tuned threshold (max-F1 on dev): {tuned_t}")
    print(f"\nTop features: " + ", ".join(f"{k}({v:.2f})" for k, v in list(scorer.feature_importance_.items())[:5]))
    hdr = f"\n{'method':22s} {'prec':>6} {'recall':>7} {'F1':>6} {'R.obv':>6} {'R.eva':>6} {'FP':>4} {'legit_hit':>10}"
    print(hdr); print("-" * len(hdr))
    for name, m in results["methods"].items():
        print(f"{name:22s} {m['precision']:>6.2f} {m['recall']:>7.2f} {m['f1']:>6.2f} "
              f"{m['recall_obvious']:>6.2f} {m['recall_evasive']:>6.2f} {m['fp']:>4} {m['legit_accounts_hit']:>10}")
    print("\nlegit_hit = real customer accounts caught in wrongly-flagged clusters (false-positive blast radius)")


if __name__ == "__main__":
    main()
