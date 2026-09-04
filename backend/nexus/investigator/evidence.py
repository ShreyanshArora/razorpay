"""Phase 3a — deterministic Evidence Builder.

Turns a scored cluster into a structured EvidenceBundle: a list of atomic,
fact-ID'd findings extracted straight from the data. The LLM investigator may
ONLY reference these fact IDs — it cannot introduce new claims. That is what
makes the case file un-bullshittable: every sentence is anchored to a fact that
a human can click and verify.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, field

from nexus.graph.entity_graph import Cluster
from nexus.ml.features import extract_features, WorldIndex, STRUCTURING_THRESHOLD


@dataclass
class Fact:
    fact_id: str
    kind: str            # "shared_identifier" | "timing" | "amount" | "dispute" | "velocity" | "structure"
    statement: str       # human-readable, literally true
    weight: str          # "strong" | "moderate" | "weak"
    direction: str       # "incriminating" | "exculpatory" | "neutral"
    evidence: dict = field(default_factory=dict)  # the raw data backing it (clickable)

    def as_dict(self):
        return asdict(self)


@dataclass
class EvidenceBundle:
    cluster_id: str
    n_accounts: int
    ring_probability: float
    facts: list[Fact]
    feature_snapshot: dict

    def as_dict(self):
        d = asdict(self)
        d["facts"] = [f.as_dict() for f in self.facts]
        return d

    def fact_ids(self) -> set[str]:
        return {f.fact_id for f in self.facts}


class EvidenceBuilder:
    def __init__(self, world_index: WorldIndex):
        self.widx = world_index

    def build(self, cluster: Cluster, ring_probability: float) -> EvidenceBundle:
        feat = extract_features(cluster, self.widx)
        facts: list[Fact] = []
        fid = 0

        def add(kind, statement, weight, direction, evidence):
            nonlocal fid
            fid += 1
            facts.append(Fact(f"F{fid}", kind, statement, weight, direction, evidence))

        n = cluster.size

        # ---- shared identifiers (incriminating if present; note absence too) ----
        for kind, label in [("device", "device"), ("card", "card fingerprint"),
                            ("address", "shipping address"), ("ip", "IP")]:
            shared = cluster.shared.get(kind, {})
            multi = {v: accs for v, accs in shared.items() if len(accs) >= 2}
            if multi:
                biggest_v = max(multi, key=lambda v: len(multi[v]))
                cnt = len(multi[biggest_v])
                # IP-sharing alone is weak (offices); device/card/address stronger
                weight = "weak" if kind == "ip" else "strong"
                add("shared_identifier",
                    f"{cnt} of {n} accounts share the same {label} ({biggest_v}).",
                    weight, "incriminating",
                    {"kind": kind, "value": biggest_v, "accounts": multi[biggest_v]})

        # absence of hard identifiers is EXCULPATORY-looking but, combined with tight
        # timing, is the signature of an EVASIVE ring — we state it neutrally.
        if feat["shared_device_ratio"] < 0.05 and feat["shared_card_ratio"] < 0.05:
            add("shared_identifier",
                f"Accounts share no device or card fingerprint (identifier rotation).",
                "moderate", "neutral",
                {"shared_device_ratio": round(feat["shared_device_ratio"], 3),
                 "shared_card_ratio": round(feat["shared_card_ratio"], 3)})

        # ---- timing ----
        if feat["creation_span_min"] <= 30:
            add("timing",
                f"All {n} accounts were created within {feat['creation_span_min']:.0f} minutes.",
                "strong", "incriminating",
                {"creation_span_min": round(feat["creation_span_min"], 1)})
        elif feat["creation_span_min"] >= 60 * 24:
            add("timing",
                f"Accounts were created over {feat['creation_span_min']/1440:.1f} days (organic spread).",
                "moderate", "exculpatory",
                {"creation_span_min": round(feat["creation_span_min"], 1)})

        if feat["txn_span_min"] <= 20:
            add("timing",
                f"Transactions occurred inside a {feat['txn_span_min']:.0f}-minute burst.",
                "strong", "incriminating",
                {"txn_span_min": round(feat["txn_span_min"], 1)})

        # ---- amount structuring ----
        if feat["near_threshold_ratio"] >= 0.4:
            add("structure",
                f"{feat['near_threshold_ratio']*100:.0f}% of transactions fall just under the "
                f"₹{STRUCTURING_THRESHOLD:.0f} threshold (structuring).",
                "strong", "incriminating",
                {"near_threshold_ratio": round(feat["near_threshold_ratio"], 3),
                 "threshold": STRUCTURING_THRESHOLD})
        if feat["amount_cv"] < 0.1 and n >= 3:
            add("amount",
                f"Transaction amounts are unusually uniform (variation {feat['amount_cv']:.2f}).",
                "moderate", "incriminating",
                {"amount_cv": round(feat["amount_cv"], 3)})
        elif feat["amount_cv"] > 0.6:
            add("amount",
                f"Transaction amounts vary naturally (variation {feat['amount_cv']:.2f}).",
                "weak", "exculpatory",
                {"amount_cv": round(feat["amount_cv"], 3)})

        # ---- disputes ----
        if feat["dispute_ratio"] >= 0.3:
            add("dispute",
                f"{feat['dispute_ratio']*100:.0f}% of transactions were later disputed/charged back.",
                "strong", "incriminating",
                {"dispute_ratio": round(feat["dispute_ratio"], 3)})
        elif feat["dispute_ratio"] <= 0.02:
            add("dispute",
                f"Dispute rate is negligible ({feat['dispute_ratio']*100:.1f}%).",
                "moderate", "exculpatory",
                {"dispute_ratio": round(feat["dispute_ratio"], 3)})

        return EvidenceBundle(
            cluster_id=cluster.cluster_id, n_accounts=n,
            ring_probability=round(ring_probability, 4),
            facts=facts, feature_snapshot={k: round(v, 3) for k, v in feat.items()},
        )
