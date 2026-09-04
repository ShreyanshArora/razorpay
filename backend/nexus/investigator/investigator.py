"""Phase 3b — the AI Investigator.

Takes an EvidenceBundle and produces a CaseFile:
  - verdict: fraud_ring | family | office | reseller | inconclusive
  - confidence 0-100
  - reasons_for / reasons_against  (each cites fact_ids from the bundle)
  - narrative  (human-readable, grounded)
  - recommended_posture (advisory only — the Decision Engine in Phase 4 decides)

CRITICAL SAFETY PROPERTY: every fact_id the model cites is validated against the
bundle. Any hallucinated citation is dropped and flagged. The LLM reasons; it
cannot invent evidence.
"""
from __future__ import annotations
import json, re
from dataclasses import dataclass, asdict, field

from nexus.investigator.evidence import EvidenceBundle
from nexus.investigator.llm import call_llm, get_provider, LLMUnavailable

VERDICTS = ["fraud_ring", "family", "office", "reseller", "inconclusive"]

SYSTEM_PROMPT = """You are a senior payments fraud analyst at a large PSP.
You investigate CLUSTERS of accounts that a graph+ML system flagged as possibly
coordinated. Your job is NOT to rubber-stamp the score. You must decide what the
cluster actually is and justify it from the provided evidence facts ONLY.

Possible verdicts:
- fraud_ring : coordinated abuse (bust-out, structuring, card testing, refund abuse)
- family     : a household sharing a device/address; legitimate
- office     : coworkers on one corporate IP; legitimate, unrelated people
- reseller   : one legitimate high-volume seller; shared card/address is expected
- inconclusive : evidence is genuinely ambiguous

Rules:
- Cite ONLY the fact IDs given (e.g. F1, F3). NEVER invent facts or IDs.
- Weigh evidence FOR and AGAINST. A shared IP alone suggests an office, not a ring.
  Identifier rotation + tight timing + structuring + disputes suggests an evasive ring.
- Output STRICT JSON only, no prose outside JSON, matching:
{"verdict": "...", "confidence": 0-100,
 "reasons_for": [{"fact_ids": ["F1"], "point": "..."}],
 "reasons_against": [{"fact_ids": ["F2"], "point": "..."}],
 "narrative": "2-4 sentence investigator summary",
 "recommended_posture": "escalate|step_up|monitor|clear"}"""


@dataclass
class Reason:
    fact_ids: list[str]
    point: str
    def as_dict(self): return asdict(self)


@dataclass
class CaseFile:
    cluster_id: str
    verdict: str
    confidence: int
    reasons_for: list[Reason]
    reasons_against: list[Reason]
    narrative: str
    recommended_posture: str
    provider: str
    grounded: bool                       # True if all cited facts existed
    dropped_citations: list[str] = field(default_factory=list)

    def as_dict(self):
        d = asdict(self)
        d["reasons_for"] = [r.as_dict() for r in self.reasons_for]
        d["reasons_against"] = [r.as_dict() for r in self.reasons_against]
        return d


def _render_facts(bundle: EvidenceBundle) -> str:
    lines = [f"Cluster {bundle.cluster_id}: {bundle.n_accounts} accounts, "
             f"ML ring-probability {bundle.ring_probability:.2f}", "", "EVIDENCE FACTS:"]
    for f in bundle.facts:
        lines.append(f"  {f.fact_id} [{f.kind}/{f.weight}/{f.direction}]: {f.statement}")
    return "\n".join(lines)


def investigate(bundle: EvidenceBundle) -> CaseFile:
    provider = get_provider()
    try:
        raw = call_llm(SYSTEM_PROMPT, _render_facts(bundle), provider)
        cf = _parse_and_ground(raw, bundle, provider)
        if cf is not None:
            return cf
    except (LLMUnavailable, Exception):
        pass
    # deterministic fallback
    return _rule_based(bundle)


def _parse_and_ground(raw: str, bundle: EvidenceBundle, provider: str) -> CaseFile | None:
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    valid = bundle.fact_ids()
    dropped: list[str] = []

    def clean(reasons):
        out = []
        for r in reasons or []:
            ids = [i for i in r.get("fact_ids", []) if i in valid]
            bad = [i for i in r.get("fact_ids", []) if i not in valid]
            dropped.extend(bad)
            if ids:  # keep only reasons anchored to real facts
                out.append(Reason(ids, r.get("point", "")))
        return out

    verdict = data.get("verdict", "inconclusive")
    if verdict not in VERDICTS:
        verdict = "inconclusive"
    return CaseFile(
        cluster_id=bundle.cluster_id, verdict=verdict,
        confidence=int(max(0, min(100, data.get("confidence", 50)))),
        reasons_for=clean(data.get("reasons_for")),
        reasons_against=clean(data.get("reasons_against")),
        narrative=str(data.get("narrative", ""))[:600],
        recommended_posture=data.get("recommended_posture", "monitor"),
        provider=provider, grounded=(len(dropped) == 0), dropped_citations=dropped,
    )


def _rule_based(bundle: EvidenceBundle) -> CaseFile:
    """Deterministic, fully-grounded investigator. Same schema as the LLM path.
    Encodes the analyst heuristics so the demo runs without any API key."""
    f = bundle.feature_snapshot
    facts = {fact.fact_id: fact for fact in bundle.facts}
    for_r, against_r = [], []

    def fids(kind=None, direction=None):
        return [ff.fact_id for ff in bundle.facts
                if (kind is None or ff.kind == kind)
                and (direction is None or ff.direction == direction)]

    # The most ROBUST legitimacy signal is behaviour, not which identifier is shared:
    # legit clusters have near-zero disputes; fraud rings dispute heavily.
    low_disputes = f["dispute_ratio"] <= 0.08
    high_disputes = f["dispute_ratio"] >= 0.25
    shares_hard_id = (f["shared_device_ratio"] >= 0.4 or f["shared_card_ratio"] >= 0.4
                      or f["shared_address_ratio"] >= 0.4)
    identifier_rotation = (f["shared_device_ratio"] < 0.1 and f["shared_card_ratio"] < 0.1)

    reseller = (f["txns_per_account"] >= 4.0 and low_disputes and bundle.n_accounts <= 4)
    family = (shares_hard_id and low_disputes and bundle.n_accounts <= 14 and not reseller)
    office = (shares_hard_id and low_disputes and bundle.n_accounts >= 12
              and f["creation_span_min"] > 60 * 24 * 5)
    evasive = (identifier_rotation and (high_disputes or f["near_threshold_ratio"] > 0.4
                                        or f["txn_span_min"] < 25))
    obvious = (shares_hard_id and high_disputes and f["creation_span_min"] <= 60)

    incriminating = fids(direction="incriminating")
    exculpatory = fids(direction="exculpatory")

    if evasive or obvious:
        verdict = "fraud_ring"
        conf = int(min(97, 60 + bundle.ring_probability * 35))
        for_r.append(Reason(incriminating[:4] or fids(),
                            "Coordinated signals: " +
                            ("identifier rotation with tight timing/structuring."
                             if evasive else "shared identifiers, burst creation, disputes.")))
        if exculpatory:
            against_r.append(Reason(exculpatory, "Some signals are ambiguous."))
    elif office:
        verdict, conf = "office", 74
        for_r.append(Reason(fids("shared_identifier"), "Shared corporate infrastructure across coworkers."))
        against_r.append(Reason(exculpatory or fids("dispute"),
                                "Spread-out account creation and negligible disputes."))
    elif reseller:
        verdict, conf = "reseller", 72
        for_r.append(Reason(fids("shared_identifier") or fids(), "High per-account order volume."))
        against_r.append(Reason(exculpatory or fids("dispute"), "Negligible disputes — legitimate seller."))
    elif family:
        verdict, conf = "family", 76
        for_r.append(Reason(fids("shared_identifier"), "Shared home device/address."))
        against_r.append(Reason(exculpatory or fids("dispute"),
                                "Low disputes and organic activity — a household."))
    else:
        verdict, conf = "inconclusive", 50
        if incriminating:
            for_r.append(Reason(incriminating[:3], "Some coordinated signals present."))
        if exculpatory:
            against_r.append(Reason(exculpatory, "Countervailing legitimate signals."))

    posture = {"fraud_ring": "escalate" if bundle.ring_probability > 0.8 else "step_up",
               "family": "clear", "office": "clear", "reseller": "clear",
               "inconclusive": "monitor"}[verdict]
    narr = {
        "fraud_ring": f"Cluster of {bundle.n_accounts} accounts shows coordinated abuse signals; "
                      f"ML ring-probability {bundle.ring_probability:.0%}. Treat as a ring.",
        "family": "Small cluster sharing a home device/address with organic timing — a household.",
        "office": "Accounts share only a corporate IP with no other coordination — coworkers.",
        "reseller": "High-volume single seller with negligible disputes — legitimate.",
        "inconclusive": "Mixed signals; needs human review before any action.",
    }[verdict]
    return CaseFile(
        cluster_id=bundle.cluster_id, verdict=verdict, confidence=conf,
        reasons_for=for_r, reasons_against=against_r, narrative=narr,
        recommended_posture=posture, provider="fallback",
        grounded=True, dropped_citations=[],
    )
