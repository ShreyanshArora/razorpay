"""Phase 4a — intervention simulation.

Given a cluster + its per-account risk, enumerate candidate interventions and
score each on TWO axes the objective function cares about:
  - risk_reduced_pct   : how much of the cluster's exposed ₹ we protect
  - friction_cost      : legitimate-customer friction we impose (step-up < block)
  - legit_accounts_hit : real customers blocked (the false-positive blast radius)

Interventions considered:
  clear             : do nothing (for legit clusters)
  monitor           : watch, no customer impact
  step_up_topk      : step-up verification on the k riskiest accounts
  step_up_all       : step-up the whole cluster
  block_topk        : hard-block the k riskiest accounts
  block_all         : hard-block the whole cluster

'Minimum defensible action' = the cheapest intervention (lowest friction +
legit-hit) that still clears a target risk-reduction bar.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict


# friction weights: blocking is far more damaging to a real customer than a step-up
FRICTION_STEP_UP = 0.15
FRICTION_BLOCK = 1.0
TARGET_RISK_REDUCTION = 0.80   # want to neutralise >=80% of exposed value


@dataclass
class AccountRisk:
    account_id: str
    exposure: float        # ₹ at risk on this account (sum of captured txns)
    risk: float            # 0-1 per-account ring-likelihood (inherited from cluster + local signals)
    is_legit_guess: bool   # our best guess this specific account is a real customer


@dataclass
class Intervention:
    action: str
    target_accounts: list[str]
    exposure_protected: float
    total_exposure: float
    risk_reduced_pct: float
    friction_cost: float
    legit_accounts_hit: int      # accounts we'd act on that we think are legit
    meets_target: bool

    def as_dict(self):
        return asdict(self)


def _score(action, targets, risks: dict[str, AccountRisk], total_exp):
    protected = sum(risks[a].exposure for a in targets)
    is_block = action.startswith("block")
    friction_per = FRICTION_BLOCK if is_block else FRICTION_STEP_UP
    friction = friction_per * len(targets)
    legit_hit = sum(1 for a in targets if risks[a].is_legit_guess)
    rr = protected / total_exp if total_exp else 0.0
    return Intervention(
        action=action, target_accounts=sorted(targets),
        exposure_protected=round(protected, 2), total_exposure=round(total_exp, 2),
        risk_reduced_pct=round(rr, 4), friction_cost=round(friction, 3),
        legit_accounts_hit=legit_hit, meets_target=rr >= TARGET_RISK_REDUCTION,
    )


def enumerate_interventions(account_risks: list[AccountRisk]) -> list[Intervention]:
    risks = {a.account_id: a for a in account_risks}
    total_exp = sum(a.exposure for a in account_risks)
    by_risk = sorted(account_risks, key=lambda a: a.risk, reverse=True)
    ids = [a.account_id for a in by_risk]
    n = len(ids)
    k = max(1, round(n * 0.6))   # "top-k riskiest" = ~60% most suspicious

    out = [
        _score("monitor", [], risks, total_exp),
        _score("step_up_topk", ids[:k], risks, total_exp),
        _score("step_up_all", ids, risks, total_exp),
        _score("block_topk", ids[:k], risks, total_exp),
        _score("block_all", ids, risks, total_exp),
    ]
    return out


def minimum_defensible(interventions: list[Intervention]) -> Intervention:
    """Cheapest intervention (lowest friction, then fewest legit hits) that hits target.
    If none hits target, fall back to the highest risk-reduction option."""
    meeting = [iv for iv in interventions if iv.meets_target and iv.action != "monitor"]
    if meeting:
        return min(meeting, key=lambda iv: (iv.friction_cost, iv.legit_accounts_hit))
    # nothing meets the bar -> take max risk reduction, tie-break on low friction
    return max(interventions, key=lambda iv: (iv.risk_reduced_pct, -iv.friction_cost))
