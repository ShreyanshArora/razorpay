"""Phase 2c — the evaluation harness.

Two metric families, reported honestly:

  A) DETECTION quality on the held-out clusters:
        precision / recall / F1 for 'is this cluster a fraud ring?'
        broken down by obvious vs evasive so we never hide the hard case.

  B) FALSE-POSITIVE COST — the number that actually matters to a payments team:
        if we ACT on every cluster a method flags, how many *legitimate customer
        accounts* get caught in the blast radius? (offices, families, resellers)
        and how much legit volume is disrupted.

We compare THREE methods on the identical held-out clusters:
  baseline (structural rule)  vs  ML scorer  vs  ML scorer @ tuned threshold.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict

from nexus.ml.labeling import ClusterLabel


@dataclass
class DetectionMetrics:
    method: str
    threshold: float
    tp: int
    fp: int
    fn: int
    tn: int
    precision: float
    recall: float
    f1: float
    recall_obvious: float
    recall_evasive: float
    # false-positive COST
    legit_accounts_hit: int        # real customers inside wrongly-flagged clusters
    legit_clusters_flagged: int

    def as_dict(self):
        return asdict(self)


def evaluate(method: str, scores: list[float], labels: list[ClusterLabel],
             threshold: float) -> DetectionMetrics:
    tp = fp = fn = tn = 0
    recall_obv_num = recall_obv_den = 0
    recall_eva_num = recall_eva_den = 0
    legit_accounts_hit = 0
    legit_clusters_flagged = 0

    for s, lab in zip(scores, labels):
        pred = 1 if s >= threshold else 0
        if lab.is_ring == 1:
            if lab.dominant_kind == "ring_obvious":
                recall_obv_den += 1; recall_obv_num += pred
            elif lab.dominant_kind == "ring_evasive":
                recall_eva_den += 1; recall_eva_num += pred
            if pred: tp += 1
            else: fn += 1
        else:
            if pred:
                fp += 1
                # cost: every legit account in this wrongly-flagged cluster
                legit_accounts_hit += lab.n_legit_accounts
                legit_clusters_flagged += 1
            else:
                tn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return DetectionMetrics(
        method=method, threshold=threshold, tp=tp, fp=fp, fn=fn, tn=tn,
        precision=round(precision, 4), recall=round(recall, 4), f1=round(f1, 4),
        recall_obvious=round(recall_obv_num / recall_obv_den, 4) if recall_obv_den else 0.0,
        recall_evasive=round(recall_eva_num / recall_eva_den, 4) if recall_eva_den else 0.0,
        legit_accounts_hit=legit_accounts_hit,
        legit_clusters_flagged=legit_clusters_flagged,
    )
