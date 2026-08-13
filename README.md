# 🏎️ Apex Strategy — F1 Race Strategy Engine

**Live:** v4 — NumPy-vectorized Monte Carlo engine, DP optimizer, MCTS rolling replanner, FastAPI + React dashboard.
**In development:** v5 — Hybrid Strategic Search Engine ([full design doc](docs/V5_DESIGN.md), [Phase 1 results](docs/PHASE1_CALIBRATION_RESULTS.md)).

An advanced Formula 1 race strategy simulator: a high-fidelity, stochastic Monte Carlo engine
in Python/FastAPI, a Dynamic Programming and MCTS strategy optimizer layer, and an interactive
React telemetry dashboard. Everything described in this README as "live" is running code you
can start locally in under a minute (see [Quick Start](#-quick-start)); everything under
[v5 Roadmap](#-v5-roadmap-hybrid-strategic-search-engine) is a proposed direction with an
honest status marker next to it.

---

## 🗺️ Where this project is right now

This project just passed a deliberate turning point: a full review of v4 surfaced and fixed a
real correctness bug in the MCTS solver's core reward computation (not a cosmetic issue — it
affected live decisions), plus a batch of dead/broken frontend↔backend wiring. That review also
produced the first rigorous, reproducible empirical comparison between the DP optimizer and the
MCTS rolling replanner — and the honest result (MCTS currently trails DP on average in ordinary
conditions, even after a 3× search-budget increase) is what set the direction for v5.

- **v4 state at this turning point:** [`docs/archive/PROJECT_STATUS_v4.md`](docs/archive/PROJECT_STATUS_v4.md)
- **Frozen v4 README:** [`docs/archive/README_v4.md`](docs/archive/README_v4.md)
- **v5 design doc:** [`docs/V5_DESIGN.md`](docs/V5_DESIGN.md)
- **v5 Phase 1 results (calibration harness, done):** [`docs/PHASE1_CALIBRATION_RESULTS.md`](docs/PHASE1_CALIBRATION_RESULTS.md)

## 🚀 What's live today (v4)

1. **🌳 MCTS Strategy Optimizer** — Monte Carlo Tree Search capable of dynamically replanning mid-race, evaluating branching stochastic trees under uncertainty (Safety Cars & Weather).
2. **🏎️ Driver Characteristics Layer** — 21 F1 driver profiles built from a teammate-delta methodology: pace offsets, consistency (σ), and data-confidence flags.
3. **☔ Rolling Re-Optimization** — mid-race replanning that detects stochastic events (rain, Safety Car) and re-invokes the MCTS solver instead of executing a fixed pre-race plan.
4. **⚠️ Realism Layer** — fuel burn, track evolution, stochastic traffic loss.
5. **Everything from v3** — stochastic weather, DP strategy optimizer, 5 configurable circuits, two-car undercut engine, FastF1 telemetry validation.

## 🧭 v5 Roadmap: Hybrid Strategic Search Engine

**Status: Phase 1 of 7 complete.** Full detail in [`docs/V5_DESIGN.md`](docs/V5_DESIGN.md).

v5 is not "run MCTS with more iterations." The v4 empirical finding was that a 3× larger search
budget didn't close MCTS's gap to DP — which means the bottleneck isn't search volume, it's
*what the search trusts while it's cheap to think*. v5's core principle:

> **Search cheaply. Evaluate intelligently.**

MCTS should explore broadly using an inexpensive heuristic, and selectively invoke the existing
high-fidelity Monte Carlo engine only on the branches where extra accuracy actually changes the
decision — instead of treating every node the same way.

| Phase | Deliverable | Status |
|---|---|---|
| 1. Instrumentation | Calibration harness quantifying heuristic-vs-simulator disagreement | ✅ **Done** — [results](docs/PHASE1_CALIBRATION_RESULTS.md) |
| 2. Heuristic Upgrade | Real per-compound tire evaluation replacing the flat traversal heuristic | ⏳ Not started |
| 3. Hybrid Rollout Engine | Selective high-fidelity Monte Carlo evaluation inside the tree | ⏳ Not started |
| 4. Adaptive Budgeting | Progressive rollout budgets by node importance | ⏳ Not started |
| 5. Risk Integration | Risk Aversion wired into MCTS reward (DP already does this as of v4) | ⏳ Not started |
| 6. Benchmark Suite | Reproducible DP vs. v4 MCTS vs. v5 Hybrid MCTS report across scenario groups | ⏳ Not started |
| 7. Frontend | Search-mode controls, confidence/risk display, strategy explanations | ⏳ Not started |

**Phase 1 finding, in one line:** the traversal heuristic MCTS uses while descending the tree
(`base_lap_time + tire_age * 0.10`) assigns **identical cost to pitting for soft vs. hard** in
the same state — compound identity never enters the formula. Across 60 sampled states its
action ranking was close to *inverted* relative to the real simulator 40% of the time and close
to correct 52% of the time (mean rank correlation **0.101**, only **41.7%** top-1 agreement —
barely better than picking at random). Phase 2 is scoped directly off this: give the heuristic
real per-compound degradation awareness before building any selective-rollout machinery on top
of it.

---

## 📐 Mathematical Framework & Assumptions (v4, live)

### 1. Two-Phase Tire Degradation Model
$$\text{Degradation}(\text{compound}, \text{age}) = (\text{wear rate} \times \text{age}) + \begin{cases} 0 & \text{if } \text{age} \le \text{cliff threshold} \\ \text{cliff penalty} \times (\text{age} - \text{cliff threshold})^2 & \text{if } \text{age} > \text{cliff threshold} \end{cases}$$

- **Soft Compound (`soft`)**: Wear rate `0.14s/lap`, Cliff threshold Lap `15`, Cliff penalty `0.03`.
- **Medium Compound (`medium`)**: Wear rate `0.08s/lap`, Cliff threshold Lap `24`, Cliff penalty `0.02`.
- **Hard Compound (`hard`)**: Wear rate `0.04s/lap`, Cliff threshold Lap `38`, Cliff penalty `0.01`.

### 2. MCTS & Stochastic Replanning
- **UCB1 Algorithm**: min-max normalized exploitation term against a tuned exploration parameter ($C = 0.1$).
- **Dynamic Replanning Evidence**: `backend/evaluate_mcts.py` runs the *actual* production code paths head-to-head — `optimizer.optimize_strategy()`'s DP schedule executed as a fixed, non-reactive plan, against `mcts_optimizer.MCTSSolver` re-queried as a rolling replanner (on Safety Car appearance, weather regime change, and a periodic cadence), both against identical per-race Safety Car/weather/noise realizations and using the same tire-degradation and weather-penalty physics as the main engine. Over 100 paired races at `sc_probability=0.08` (elevated to stress-test replanning value) with a reduced search budget for tractability (100 rollouts/decision vs. the `/optimize-mcts` endpoint's production default of 1,000):
  - **MCTS Win Rate**: 7% — **DP Win Rate**: 93%
  - **Mean time saved by MCTS**: **-124s per race** (currently slower on average at this search budget)
  - **Best single-race outcome for MCTS**: **+2,731s**, in the one race with a genuine sustained storm — the rolling replanner reacted by pitting to intermediates when the rain hit, while the rigid DP schedule stayed on slicks (a 2.5x lap-time penalty in full wet) for the entire wet stretch.
  - **Worst single-race outcome for MCTS**: **-1,065s**, from an unnecessary extra pit stop in ordinary dry conditions.
  - This is the empirical result that motivates the v5 roadmap above — see [Phase 1 results](docs/PHASE1_CALIBRATION_RESULTS.md) for the direct heuristic-vs-simulator confirmation of *why*.

### 3. Driver Characteristics
- **Pace Offset**: fractional lap-time delta from teammate-relative pace (e.g. Verstappen `-0.15s/lap`, Sargeant `+0.2s/lap`).
- **Consistency**: per-lap noise standard deviation. When `driver_id` is `"generic"`, the `random_std` request field controls this directly instead.

### 4. Stochastic Safety Car & Reactive Pitting
- **Trigger Probability**: track-dependent (e.g. $P(\text{SC}) = 0.04$ per lap).
- **Discounted Pit Loss**: pitting under SC reduces pit lane loss from `22.0s` down to `8.0s`.

### 5. Risk-Aware DP Optimization
`POST /optimize`'s `risk_aversion` (0-1) re-ranks the DP optimizer's starting-compound candidates
by `expected_time + risk_aversion * std_dev`, where `std_dev` comes from a real Monte Carlo run
per candidate — the same `mean + risk*std` convention `mcts_optimizer.risk_adjusted_reward` uses.
`0` = pick the fastest expected strategy; `1` = weigh a candidate's variance heavily against raw speed.

---

## 📊 FastF1 Validation (2023 Bahrain Grand Prix)

| Metric | FastF1 Recorded Actual | Monte Carlo Simulated Mean |
|---|---|---|
| **Race Winner Finish Time** | **5,635.8s** (1h 33m 55.8s) | **5,632.4s** (1h 33m 52.4s) |
| **Pit Lane Loss Delta** | `21.8s` | `22.0s` |
| **Track Baseline** | `96.2s` | `94.0s` |
| **Model Variance** | — | **$\pm 3.4\text{s}$ (99.94% accuracy)** |

---

## 🏃 Quick Start

### 1. Backend API (FastAPI)
```bash
cd backend
./venv/bin/uvicorn main:app --reload --port 8005
```
Swagger interactive docs available at `http://127.0.0.1:8005/docs`.

Endpoints available:
- `GET /tracks` — Retrieve configured track data
- `GET /drivers` — Retrieve 21 configured driver profiles
- `POST /simulate` — 10,000-run Monte Carlo single strategy (includes Weather & Traffic)
- `POST /compare` — Head-to-head strategy comparison
- `POST /optimize` — Dynamic Programming strategy optimizer (with risk-aware ranking)
- `POST /optimize-mcts` — Dynamic MCTS rolling optimizer
- `POST /undercut-analysis` — 2-car undercut effectiveness curve
- `GET /fastf1/calibrate` — Empirical FastF1 calibration data

### 2. Frontend Dashboard (React + Vite)
```bash
cd frontend
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## 🧪 Running Tests

```bash
# Run engine unit tests (Safety Car, Undercut, Degradation)
backend/venv/bin/python backend/test_simulator.py

# Run API endpoint integration tests
backend/venv/bin/pytest backend/test_api.py -v

# Run the full backend test suite
backend/venv/bin/pytest backend/ -v

# v5 Phase 1: heuristic-vs-simulator calibration harness (~2s)
backend/venv/bin/python backend/calibration_harness.py

# MCTS vs. DP empirical comparison (~4min for 100 races)
backend/venv/bin/python backend/evaluate_mcts.py
```

---

## 📚 Documentation Index

| Doc | What it's for |
|---|---|
| [`docs/V5_DESIGN.md`](docs/V5_DESIGN.md) | Full v5 Hybrid Strategic Search Engine design — goals, architecture, phases, research questions, definition of done |
| [`docs/PHASE1_CALIBRATION_RESULTS.md`](docs/PHASE1_CALIBRATION_RESULTS.md) | v5 Phase 1 deliverable: quantitative evidence of where the MCTS heuristic disagrees with the real simulator |
| [`docs/archive/PROJECT_STATUS_v4.md`](docs/archive/PROJECT_STATUS_v4.md) | Detailed v4 snapshot at the v4→v5 turning point: architecture, every bug found/fixed, honest metrics |
| [`docs/archive/README_v4.md`](docs/archive/README_v4.md) | The v4 README, frozen for reference |
| [`DEPLOYMENT.md`](DEPLOYMENT.md) | Render (backend) + Vercel (frontend) deployment guide |
