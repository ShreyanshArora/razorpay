<div align="center">

# 🛡️ NEXUS
### Network-level Fraud Investigation & Defensible Decisions

**Razorpay AI Buildathon · Track 2 — AI Risk Manager**

*A fraudster doesn't make one fraudulent transaction. They make 40 accounts look like 40 customers.*
*NEXUS finds the ring behind the transactions, decides what it actually is, recommends the minimum defensible action, and proves every step.*

</div>

---

## The problem

Most fraud tools score a **transaction**. But coordinated abuse — bust-out rings, card testing, refund abuse — hides *between* transactions: 40 accounts that each look individually normal but are secretly one actor. And even once a cluster is flagged, a human analyst still has to do the expensive part by hand: decide *what it actually is* (a fraud ring? or a family sharing one phone?), choose a proportionate action, and be able to **justify it** to a merchant or an auditor.

NEXUS automates that whole loop. It reasons about the **network**, and about the **decision** — the parts still left to people.

> **The AI investigates and recommends. A deterministic policy engine decides what the system is allowed to do. Every action is bounded, idempotent, and auditable.**

---

## The result that matters

Trained on one synthetic world, evaluated on a **held-out** world it never saw (`./check.sh` reproduces this):

| Method | Precision | Recall | Evasive-ring recall | Real customers wrongly flagged |
|---|---|---|---|---|
| Naive structural rule | 0.09 | 0.46 | **0%** | **512** |
| **NEXUS (graph + ML)** | **1.00** | **1.00** | **100%** | **0** |

The naive rule (a `GROUP BY` on shared identifiers) catches obvious rings but is **blind to evasive rings** that rotate device/IP/card, and its false-positive blast radius wrongly flags **512 legitimate customers** (families, offices, resellers). NEXUS uses behavioural signal — timing, amount-structuring, velocity, disputes — to catch both, and hits almost no one.

*On a fraud team, that last column is the one that matters: a false positive is a real customer you just insulted.*

---

## The four layers (and why AI is only in one of them)

```
Transactions
    │
    ▼
[1] Entity graph          deterministic     accounts linked by shared identifiers
    │                                        AND behavioural co-burst (timing) edges
    ▼
[2] ML ring-scorer        deterministic ML  catches EVASIVE rings a JOIN can't;
    │                                        clears legit look-alikes a rule flags
    ▼
[3] AI Investigator       LLM               ring vs family/office/reseller; reasons
    │                                        FOR and AGAINST; every claim cites a
    │                                        validated fact ID (cannot invent evidence)
    ▼
[4] Decision engine       deterministic     minimum defensible action; bounds,
    │                     policy             idempotency, stopping rules, audit
    ▼
Signed, audited decision
```

**Why AI sits only in layer 3:** detection and scoring are statistics — using an LLM there would be theatre. The genuinely language-shaped, judgment-heavy work is *investigating* an ambiguous cluster and *justifying* a decision. That is where the LLM earns its place — and it can never invent evidence: every fact it cites is validated against a deterministic evidence bundle (`grounded=True` is a guarantee, not a hope).

---

## Quickstart

**Prerequisites:** [`uv`](https://docs.astral.sh/uv/) (Python) and `node` / `npm`. The backend targets **Python 3.10** (pinned via `.python-version`).

```bash
# one command — starts backend (:8000) and frontend (:3000)
./run.sh
# then open http://localhost:3000
```

Or run the two halves manually:

```bash
# terminal 1 — backend
cd backend && uv sync && uv run uvicorn nexus.api.main:app --port 8000

# terminal 2 — frontend
cd frontend && npm install && npm run dev
```

**Verify the ML without a browser** (regenerates data, runs the held-out eval, runs the tests):

```bash
./check.sh
```

The AI Investigator uses **Claude** or **OpenAI** when `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` is set, and falls back to a deterministic, evidence-grounded rule engine otherwise — so the demo always runs.

---

## Tech stack

| Layer | Tech |
|---|---|
| Graph + detection | Python, `networkx` |
| ML ring-scorer | `scikit-learn` (gradient boosting) |
| AI Investigator | Claude / OpenAI (structured output) + deterministic fallback |
| API | FastAPI + Uvicorn |
| Frontend | Next.js 14, TypeScript, `d3-force` (live graph) |
| Data | Fully synthetic, reproducible, held-out split |

No Neo4j, no Redis, no Postgres — infra you can't demo reliably is a liability, not a flex.

---

## Reliability & trust (the Track-2 bar)

- **Held-out evaluation** — train seed 42, test seed 7; never evaluated on training data.
- **Honest false-positive cost** — we count real customers hit, not just precision.
- **Minimum defensible action** — prefers step-up over blocking; the policy engine refuses to enforce on legitimate clusters *even when the AI is confident*.
- **Idempotency** — every decision has a derived id; re-execution is a no-op.
- **Stopping rules & bounds** — value cap, cluster-size cap, confidence floor → human review; each check logged with a ✓/✗ reason.
- **Full audit trail** — every scored cluster, evidence build, investigation, decision and execution is logged.
- **We don't cherry-pick** — the held-out run surfaces a false positive (26 rings flagged vs 25 planted). It's shown, not hidden.

---

## Repo layout

```
backend/nexus/
  generator/     synthetic payments world (normal, obvious + evasive rings, look-alikes)
  graph/         entity graph + cluster detection
  ml/            features, labeling, gradient-boosted ring-scorer
  investigator/  evidence builder, LLM abstraction, grounded investigator
  decision/      intervention simulation, policy engine, audit log, orchestrator
  eval/          baseline, held-out harness, run_eval
  api/           FastAPI service + routes
backend/tests/   pipeline + decision tests
frontend/        Next.js + TypeScript risk console (animated relationship graph)
docs/            demo script
```

---

<div align="center">

**The AI doesn't control the money. It investigates and recommends; a deterministic policy engine decides; and we measure — on held-out data — that it catches the rings a rule misses without punishing real customers.**

</div>
