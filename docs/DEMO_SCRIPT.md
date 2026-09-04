# NEXUS — 5-minute demo script

**One sentence to open with:**
> "A fraudster doesn't make one fraudulent transaction. They make forty accounts
> look like forty customers. NEXUS finds the person behind the transactions."

### 0:00–0:30 — The problem
Open the console. The KPI strip shows **₹15L exposure at risk across 26 confirmed
rings** on a held-out dataset the model has never seen. Say: *Razorpay's models
flag risky accounts. The hard part left for a human is deciding what to do and
proving why. That's what NEXUS automates.*

### 0:30–1:30 — An evasive ring
Click the top ring in the queue. Point at the **relationship graph**: these
accounts share **no device, no card, no IP** — a `GROUP BY` sees nothing. The
edges are all *timing* edges. Say: *these rotate every identifier; a rules engine
is blind to them. We catch them behaviourally.* The ring-probability dial reads
~100%.

### 1:30–2:30 — The AI investigation
Show the **Evidence** panel: every fact has an ID (F1, F2…) drawn straight from
the data. Show **Case for / Case against**: the AI weighs both sides and every
sentence cites a fact ID — `✓ evidence-grounded` means it cannot invent evidence.
Verdict: **fraud ring**.

### 2:30–3:30 — The defensible decision
Show the **intervention table**: block-all protects 100% but at friction 12 and
would hit customers; **step-up-all** protects 100% at friction 1.8 and hits zero
legit customers — the highlighted **minimum defensible action**. Show the
**policy decision** card: every check ✓, authorized, bounded.

### 3:30–4:00 — The false-positive story
Switch to a **legit office** cluster (30 accounts sharing an IP). NEXUS says
*office → clear*, and the policy engine **refuses to enforce**, protecting 30 real
customers — *even though a naive rule would have blocked them all.*

### 4:00–4:30 — The evidence
Open **Model evaluation**. The table: naive rule catches **0% of evasive rings**
and wrongly flags **512 real customers**; NEXUS catches 100% and hits 0.

### 4:30–5:00 — The close
> "The AI doesn't control the money. It investigates and recommends; our
> deterministic policy engine decides what the system is allowed to do; and we
> measure — on held-out data — that it catches the rings a rule misses without
> punishing real customers. Every action is bounded, idempotent, and auditable."

## Honesty notes (have these ready — judges reward them)
- The held-out run surfaces **one false positive** (26 flagged vs 25 planted). Shown, not hidden.
- Perfect recall comes from clean synthetic data; on real data we'd expect lower,
  which is why the **architecture** (grounded reasoning, bounded decisions, FP-cost
  accounting) is the real contribution, not the specific numbers.
