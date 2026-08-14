# 🏎️ Apex Strategy — F1 Race Strategy Engine

**Live:** v4 — NumPy-vectorized Monte Carlo engine, DP optimizer, MCTS rolling replanner, FastAPI + React dashboard.
**In development:** v5 — Hybrid Strategic Search Engine ([full design doc](docs/V5_DESIGN.md), [Phase 1 results](docs/PHASE1_CALIBRATION_RESULTS.md), [Phases 2-4 results](docs/PHASE2_4_RESULTS.md)).

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
- **v5 Phases 2-4 results (hybrid MCTS, done):** [`docs/PHASE2_4_RESULTS.md`](docs/PHASE2_4_RESULTS.md)

## 🚀 What's live today (v4)

1. **🌳 MCTS Strategy Optimizer** — Monte Carlo Tree Search capable of dynamically replanning mid-race, evaluating branching stochastic trees under uncertainty (Safety Cars & Weather).
2. **🏎️ Driver Characteristics Layer** — 21 F1 driver profiles built from a teammate-delta methodology: pace offsets, consistency (σ), and data-confidence flags.
3. **☔ Rolling Re-Optimization** — mid-race replanning that detects stochastic events (rain, Safety Car) and re-invokes the MCTS solver instead of executing a fixed pre-race plan.
4. **⚠️ Realism Layer** — fuel burn, track evolution, stochastic traffic loss.
5. **Everything from v3** — stochastic weather, DP strategy optimizer, 5 configurable circuits, two-car undercut engine, FastF1 telemetry validation.

## 🧭 v5 Roadmap: Hybrid Strategic Search Engine

**Status: Phases 1-4 of 7 complete.** Full detail in [`docs/V5_DESIGN.md`](docs/V5_DESIGN.md).

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
| 2. Heuristic Upgrade | Real per-compound tire evaluation replacing the flat traversal heuristic | ✅ **Done** — [results](docs/PHASE2_4_RESULTS.md) |
| 3. Hybrid Rollout Engine | Selective high-fidelity Monte Carlo evaluation inside the tree | ✅ **Done** — [results](docs/PHASE2_4_RESULTS.md) |
| 4. Adaptive Budgeting | Progressive rollout budgets by node importance | ✅ **Done** — [results](docs/PHASE2_4_RESULTS.md) |
| 5. Risk Integration | Risk Aversion wired into MCTS reward (DP already does this as of v4) | ⏳ Not started |
| 6. Benchmark Suite | Reproducible DP vs. v4 MCTS vs. v5 Hybrid MCTS report across scenario groups | ⏳ Not started |
| 7. Frontend | Search-mode controls, confidence/risk display, strategy explanations | ⏳ Not started |

**Phase 1 finding, in one line:** the traversal heuristic MCTS uses while descending the tree
(`base_lap_time + tire_age * 0.10`) assigns **identical cost to pitting for soft vs. hard** in
the same state — compound identity never enters the formula. Across 60 sampled states its
action ranking was close to *inverted* relative to the real simulator 40% of the time and close
to correct 52% of the time (mean rank correlation **0.101**, only **41.7%** top-1 agreement —
barely better than picking at random).

**Phases 2-4 result, in one line:** replacing that flat heuristic with real per-compound
degradation (Phase 2), selectively escalating only strategic-discontinuity/late-race leaves to
a real Monte Carlo rollout (Phase 3), and spending a small top-up refining the top candidates
after the main search (Phase 4) — all under the *same* iteration budget as before — cut MCTS's
mean deficit to DP from **-80.37s to -18.79s** (a ~76% reduction) and made the new hybrid
solver beat the old one head-to-head in **61%** of races vs. 33%. It still doesn't beat DP on
average yet, but this is real, measurable progress from a targeted fix, not from throwing more
compute at the problem. Full writeup, including a sign-convention bug caught before trusting
the numbers: [`docs/PHASE2_4_RESULTS.md`](docs/PHASE2_4_RESULTS.md).

---

## 📐 Mathematical Framework & Assumptions (v4, live)

### 1. Two-Phase Tire Degradation Model
$$\text{Degradation}(\text{compound}, \text{age}) = (\text{wear rate} \times \text{age}) + \begin{cases} 0 & \text{if } \text{age} \le \text{cliff threshold} \\ \text{cliff penalty} \times (\text{age} - \text{cliff threshold})^2 & \text{if } \text{age} > \text{cliff threshold} \end{cases}$$

- **Soft Compound (`soft`)**: Wear rate `0.14s/lap`, Cliff threshold Lap `15`, Cliff penalty `0.03`.
- **Medium Compound (`medium`)**: Wear rate `0.08s/lap`, Cliff threshold Lap `24`, Cliff penalty `0.02`.
- **Hard Compound (`hard`)**: Wear rate `0.04s/lap`, Cliff threshold Lap `38`, Cliff penalty `0.01`.

### 2. MCTS & Stochastic Replanning
- **UCB1 Algorithm**: min-max normalized exploitation term against a tuned exploration parameter ($C = 0.1$).
- **Dynamic Replanning Evidence**: `backend/evaluate_mcts.py` runs the *actual* production code paths head-to-head — `optimizer.optimize_strategy()`'s DP schedule executed as a fixed, non-reactive plan, against `mcts_optimizer.MCTSSolver` re-queried as a rolling replanner (on Safety Car appearance, weather regime change, and a periodic cadence), both against identical per-race Safety Car/weather/noise realizations and using the same tire-degradation and weather-penalty physics as the main engine. Over 100 paired races at `sc_probability=0.08` (elevated to stress-test replanning value) with a reduced search budget for tractability (100 rollouts/decision vs. the `/optimize-mcts` endpoint's production default of 1,000), comparing DP against both MCTS variants:
  - **v4 classic MCTS** (every leaf gets a real Monte Carlo rollout): **12%** win rate vs. DP's 88%, mean **-80.4s/race** (slower on average).
  - **v5 hybrid MCTS** (Phases 2-4: real per-compound heuristic, selective escalation, adaptive top-K refinement — see [Phases 2-4 results](docs/PHASE2_4_RESULTS.md)): **16%** win rate vs. DP's 84%, mean **-18.8s/race** — roughly a 76% reduction in the gap to DP versus v4 classic, and v5 beats v4 classic head-to-head in 61% of races.
  - **Best single-race outcome for MCTS**: **+3,055s** (v5) / **+2,731s** (v4), both in the one race with a genuine sustained storm — the rolling replanner reacted by pitting to intermediates when the rain hit, while the rigid DP schedule stayed on slicks (a 2.5x lap-time penalty in full wet) for the entire wet stretch.
  - Neither MCTS variant beats DP on average yet. This progression (v4 losing badly → v5 losing by much less, from a targeted architecture change under the *same* compute budget) is the empirical throughline of the v5 roadmap — see [Phase 1 results](docs/PHASE1_CALIBRATION_RESULTS.md) for the diagnosis and [Phases 2-4 results](docs/PHASE2_4_RESULTS.md) for the fix.

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

# v5 Phases 2-4: DP vs. v4-classic-MCTS vs. v5-hybrid-MCTS (~8.5min for 100 races, all 3 arms)
backend/venv/bin/python backend/evaluate_mcts.py
```

---

## 📚 Documentation Index

| Doc | What it's for |
|---|---|
| [`docs/V5_DESIGN.md`](docs/V5_DESIGN.md) | Full v5 Hybrid Strategic Search Engine design — goals, architecture, phases, research questions, definition of done |
| [`docs/PHASE1_CALIBRATION_RESULTS.md`](docs/PHASE1_CALIBRATION_RESULTS.md) | v5 Phase 1 deliverable: quantitative evidence of where the MCTS heuristic disagrees with the real simulator |
| [`docs/PHASE2_4_RESULTS.md`](docs/PHASE2_4_RESULTS.md) | v5 Phases 2-4 deliverable: the hybrid MCTS implementation and its real DP vs. v4 vs. v5 benchmark |
| [`docs/archive/PROJECT_STATUS_v4.md`](docs/archive/PROJECT_STATUS_v4.md) | Detailed v4 snapshot at the v4→v5 turning point: architecture, every bug found/fixed, honest metrics |
| [`docs/archive/README_v4.md`](docs/archive/README_v4.md) | The v4 README, frozen for reference |
| [`DEPLOYMENT.md`](DEPLOYMENT.md) | Render (backend) + Vercel (frontend) deployment guide |
