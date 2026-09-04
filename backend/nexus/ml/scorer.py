"""Phase 2b — the ML ring-likelihood scorer.

Gradient-boosted trees over cluster features. Outputs a calibrated-ish
ring probability in [0,1]. This is the layer that catches EVASIVE rings
(which structural rules miss) and clears LEGIT lookalikes (which structural
rules wrongly flag). Deterministic ML — no LLM here.
"""
from __future__ import annotations
import pickle
from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier

from nexus.ml.features import FEATURE_NAMES, features_to_vector


@dataclass
class ScoredCluster:
    cluster_id: str
    ring_probability: float
    top_features: list[tuple[str, float]]   # (name, value) contributing most


class RingScorer:
    def __init__(self):
        self.model = GradientBoostingClassifier(
            n_estimators=200, max_depth=3, learning_rate=0.08,
            subsample=0.9, random_state=0,
        )
        self.feature_importance_: dict[str, float] = {}

    def fit(self, feats: list[dict], labels: list[int]):
        X = np.vstack([features_to_vector(f) for f in feats])
        y = np.array(labels)
        self.model.fit(X, y)
        self.feature_importance_ = dict(
            sorted(zip(FEATURE_NAMES, self.model.feature_importances_),
                   key=lambda kv: kv[1], reverse=True)
        )
        return self

    def score(self, feat: dict) -> float:
        X = features_to_vector(feat).reshape(1, -1)
        return float(self.model.predict_proba(X)[0, 1])

    def explain(self, cluster_id: str, feat: dict) -> ScoredCluster:
        prob = self.score(feat)
        # rank this cluster's features by global importance, keep the meaningful ones
        ranked = [(name, feat[name]) for name in self.feature_importance_
                  if self.feature_importance_[name] > 0.01][:6]
        return ScoredCluster(cluster_id, prob, ranked)

    def save(self, path: str):
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(path: str) -> "RingScorer":
        with open(path, "rb") as f:
            return pickle.load(f)
