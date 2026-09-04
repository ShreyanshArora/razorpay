"""Phase 4b — the deterministic Policy Engine + Audit Log.

The AI RECOMMENDS. This engine DECIDES what the system is allowed to do.
It enforces bounded, explainable, idempotent, stoppable actions.

Guarantees:
  - Nothing auto-executes above a value/size threshold -> human review.
  - Every action is idempotent (a decision_id is derived from cluster+action;
    re-running never double-acts).
  - Stopping rules are explicit and logged.
  - Every decision carries a WHY (the checks that passed) and links to the
    case file + evidence facts.
"""
from __future__ import annotations
import hashlib, time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

# Bounds
AUTO_ACT_MAX_EXPOSURE = 200000.0     # ₹ above this -> human review, no auto action
AUTO_ACT_MAX_ACCOUNTS = 25           # clusters bigger than this -> human review
MIN_CONFIDENCE_TO_ACT = 70           # investigator confidence floor
MIN_RING_PROB_TO_ACT = 0.6


@dataclass
class Decision:
    decision_id: str
    cluster_id: str
    authorized: bool
    action: str                    # authorized action, or "human_review"
    target_accounts: list[str]
    reason_checks: list[str]       # human-readable WHY (each check that passed/failed)
    stopped_reason: str | None
    exposure_protected: float
    legit_accounts_hit: int
    verdict: str
    confidence: int
    ring_probability: float
    created_at: str

    def as_dict(self): return asdict(self)


class AuditLog:
    def __init__(self):
        self._events: list[dict] = []
        self._executed: dict[str, dict] = {}   # decision_id -> record (idempotency)

    def log(self, cluster_id: str, event: str, detail: dict | None = None):
        self._events.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "cluster_id": cluster_id, "event": event, "detail": detail or {},
        })

    def already_executed(self, decision_id: str) -> bool:
        return decision_id in self._executed

    def mark_executed(self, decision_id: str, record: dict):
        self._executed[decision_id] = record

    def events(self) -> list[dict]:
        return list(self._events)


def _decision_id(cluster_id: str, action: str, targets: list[str]) -> str:
    h = hashlib.sha256(("|".join([cluster_id, action] + sorted(targets))).encode()).hexdigest()
    return f"dec_{h[:12]}"


def authorize(case_file, chosen, ring_probability: float, audit: AuditLog) -> Decision:
    """Run the recommended intervention through policy checks."""
    cid = case_file.cluster_id
    checks: list[str] = []
    stopped = None
    authorized = True
    action = chosen.action

    # ---- stopping rules / bounds ----
    if case_file.verdict != "fraud_ring":
        authorized = False; action = "clear" if case_file.verdict in ("family","office","reseller") else "human_review"
        stopped = f"verdict is '{case_file.verdict}', not a fraud ring"
        checks.append(f"✗ verdict={case_file.verdict} → no enforcement (protect legitimate customers)")
    else:
        checks.append("✓ verdict = fraud_ring")
        if case_file.confidence < MIN_CONFIDENCE_TO_ACT:
            authorized = False; action = "human_review"
            stopped = f"confidence {case_file.confidence} < {MIN_CONFIDENCE_TO_ACT}"
            checks.append(f"✗ confidence {case_file.confidence} below floor {MIN_CONFIDENCE_TO_ACT}")
        else:
            checks.append(f"✓ confidence {case_file.confidence} ≥ {MIN_CONFIDENCE_TO_ACT}")

        if ring_probability < MIN_RING_PROB_TO_ACT:
            authorized = False; action = "human_review"
            stopped = f"ring_probability {ring_probability:.2f} < {MIN_RING_PROB_TO_ACT}"
            checks.append(f"✗ ML ring-probability {ring_probability:.2f} below floor")
        else:
            checks.append(f"✓ ML ring-probability {ring_probability:.2f} ≥ {MIN_RING_PROB_TO_ACT}")

        if chosen.total_exposure > AUTO_ACT_MAX_EXPOSURE:
            authorized = False; action = "human_review"
            stopped = f"exposure ₹{chosen.total_exposure:,.0f} exceeds auto-action cap"
            checks.append(f"✗ exposure ₹{chosen.total_exposure:,.0f} > cap ₹{AUTO_ACT_MAX_EXPOSURE:,.0f} → human review")
        else:
            checks.append(f"✓ exposure ₹{chosen.total_exposure:,.0f} within auto-action cap")

        if len(chosen.target_accounts) > AUTO_ACT_MAX_ACCOUNTS:
            authorized = False; action = "human_review"
            stopped = f"{len(chosen.target_accounts)} accounts exceeds auto-action cap"
            checks.append(f"✗ {len(chosen.target_accounts)} target accounts > cap {AUTO_ACT_MAX_ACCOUNTS} → human review")
        else:
            checks.append(f"✓ {len(chosen.target_accounts)} target accounts within cap")

        if authorized:
            checks.append(f"✓ minimum defensible action selected: {action} "
                          f"(protects {chosen.risk_reduced_pct:.0%} of exposure, "
                          f"{chosen.legit_accounts_hit} legit accounts impacted)")

    did = _decision_id(cid, action, chosen.target_accounts)

    # ---- idempotency ----
    if audit.already_executed(did):
        checks.append(f"✓ idempotency: decision {did} already executed — no duplicate action")
        stopped = stopped or "duplicate — already executed"

    dec = Decision(
        decision_id=did, cluster_id=cid, authorized=authorized, action=action,
        target_accounts=chosen.target_accounts, reason_checks=checks,
        stopped_reason=stopped, exposure_protected=chosen.exposure_protected,
        legit_accounts_hit=chosen.legit_accounts_hit, verdict=case_file.verdict,
        confidence=case_file.confidence, ring_probability=round(ring_probability, 4),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    audit.log(cid, "decision_made", {"decision_id": did, "action": action,
                                     "authorized": authorized, "stopped": stopped})
    return dec


def execute(decision: Decision, audit: AuditLog) -> dict:
    """Simulated bounded execution with idempotency + graceful failure handling."""
    if not decision.authorized:
        audit.log(decision.cluster_id, "execution_skipped",
                  {"decision_id": decision.decision_id, "reason": "not authorized / human review"})
        return {"executed": False, "reason": decision.stopped_reason or "not authorized"}
    if audit.already_executed(decision.decision_id):
        audit.log(decision.cluster_id, "execution_skipped_idempotent",
                  {"decision_id": decision.decision_id})
        return {"executed": False, "reason": "idempotent: already executed"}
    record = {"decision_id": decision.decision_id, "action": decision.action,
              "targets": decision.target_accounts, "at": decision.created_at}
    audit.mark_executed(decision.decision_id, record)
    audit.log(decision.cluster_id, "executed", record)
    return {"executed": True, "record": record}
