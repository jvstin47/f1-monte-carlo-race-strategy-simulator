# Apex Strategy v4 — Project Status Snapshot

**Date:** 2026-08-13
**Purpose:** A frozen, detailed record of where the project stood at the end of v4 development,
immediately before v5 (Hybrid Strategic Search Engine) work began. See
[`docs/V5_DESIGN.md`](../V5_DESIGN.md) for what comes next.

---

## 1. What the project is

Apex Strategy is an F1 race-strategy simulator: a NumPy-vectorized Monte Carlo engine
(FastAPI backend) paired with a React/Vite dashboard. It models:

- Two-phase tire degradation (linear wear + quadratic cliff penalty past a threshold),
  per-compound (soft/medium/hard/intermediate/wet)
- Fuel burn (lap time speeds up as fuel load drops)
- Track evolution (grip improves over the race)
- Stochastic traffic loss
- Stochastic Safety Cars, with discounted pit-lane loss under caution
- Stochastic weather (Markov chain: dry/damp/wet transitions), with reactive pitting
- Two-car undercut/dirty-air modeling
- 21 driver profiles (teammate-delta pace offset + consistency/variance)
- 5 track presets (Bahrain, Silverstone, Monza, Monaco, Singapore)
- A Dynamic Programming optimizer (exact backward induction over a deterministic
  degradation model)
- A Monte Carlo Tree Search (MCTS) rolling replanner for mid-race, uncertainty-aware
  strategy decisions

## 2. Architecture

```
frontend/ (React + Vite, plain CSS, recharts)
  src/App.jsx                 -- top-level state, tab routing, API orchestration
  src/components/*.jsx         -- 13 components (forms, charts, selectors, panels)

backend/ (FastAPI + NumPy)
  main.py                      -- API routes
  models.py                    -- Pydantic request/response schemas
  simulator.py                 -- vectorized Monte Carlo engine (core physics)
  optimizer.py                 -- DP backward-induction optimizer
  mcts_optimizer.py            -- MCTS solver (UCB1, rollout via simulator.py)
  weather.py                   -- weather Markov chain + compound penalties
  drivers.py / tracks.py       -- static profile/preset data
  fastf1_calibrator.py         -- FastF1 telemetry calibration (with offline fallback)
  evaluate_mcts.py             -- MCTS vs. DP empirical comparison script
```

### API surface (all endpoints wired to a matching frontend consumer)

| Endpoint | Purpose |
|---|---|
| `GET /health`, `GET /` | liveness / cold-start detection |
| `GET /tracks`, `GET /drivers` | static preset data |
| `POST /simulate` | single-strategy Monte Carlo run |
| `POST /compare` | head-to-head strategy A vs. B |
| `POST /undercut-analysis` | 2-car undercut effectiveness curve |
| `POST /optimize` | DP-optimal strategy + risk-ranked alternatives |
| `POST /optimize-mcts` | MCTS rolling-replan recommendation |
| `GET /fastf1/calibrate` | empirical calibration data (2023 Bahrain GP) |

## 3. This session's review: what was found and fixed

A full-project review (code correctness + frontend/backend wiring audit) surfaced and fixed
11 real issues, roughly in order of severity:

1. **MCTS reward sign bug** (`mcts_optimizer.py`) — `_simulate()`'s backpropagation added a
   positive lap-time cost to a negative reward (`reward = lap_time + future_reward`),
   corrupting the accumulated reward's meaning as the tree deepened. Verified it caused the
   solver to recommend pitting on lap 1 for tires that were already fresh. Fixed the sign
   convention (`reward = -lap_time + future_reward`). **This affects the live
   `/optimize-mcts` endpoint**, not just internal tooling.
2. **Same-compound pit stops allowed** (`get_legal_actions`) — combined with (1), let the
   search burn both allowed stops in the first ~6 laps of a race, leaving nothing in reserve
   when weather later turned. Found by tracing a storm scenario MCTS should have won and
   didn't. Now excluded.
3. **`evaluate_mcts.py` never called the real engines** — the README's MCTS-vs-DP claim came
   from a hardcoded toy comparison with dead code paths (imported `MCTSSolver` but never
   instantiated it). Rewritten to genuinely execute `optimizer.optimize_strategy()`'s fixed
   schedule and `MCTSSolver` as a rolling replanner, both against identical per-race
   weather/SC/noise realizations and real per-lap physics.
4. **`random_std` was dead** (`main.py`) — `resolve_track_params()` always overwrote
   `driver_consistency` from the driver profile because `driver_id` defaults to `"generic"`
   (truthy), so the documented `random_std` field never took effect. Fixed to only override
   for a *named* driver.
5. **`/optimize`'s `monte_carlo_distribution` was never populated** — declared in the response
   schema, never filled in. The frontend's histogram on the Optimize tab was permanently
   empty. Wired up; also fixed the frontend reading the histogram from the wrong nesting
   level.
6. **Demo scenario used a nonexistent driver ID** (`'verstappen'` vs. the real key `'ver'`) —
   silently fell back to the generic driver profile.
7. **`RaceSimulatorTab`'s nested driver dropdown had no backend URL** — worked locally only
   by Vite dev-proxy coincidence; would 404 silently in the deployed (proxy-less) frontend.
   Fixed by centralizing driver-data fetching in `App.jsx` (matching the existing `tracks`
   pattern) and passing it down as a prop everywhere instead of independent fetches.
8. **Optimizer's "Risk Aversion" slider did nothing** — sent to `/optimize`, but
   `OptimizeInput` never declared the field (FastAPI silently dropped it) and
   `optimize_strategy()` had no risk concept at all. Wired up for real: candidates are now
   re-ranked by `expected_time + risk_aversion * std_dev`, with `std_dev` from an actual
   Monte Carlo run per candidate — the same `mean + risk*std` convention already used in
   `mcts_optimizer.risk_adjusted_reward`. Surfaced as a "Risk (σ)" column in the UI.
9. **`DriverImpactChart` showed raw driver-ID codes** (`"VER"`) instead of real names —
   had no access to driver profile data. Now shows full names plus pace/consistency
   character.
10. **MCTS rollout's tire-age correction scaled backwards** — a heuristic term meant to
    account for pre-existing tire wear scaled *up* with `remaining_laps`, penalizing a
    freshly-pitted tire with a long stint ahead more than a heavily-worn tire near the end of
    the race. Replaced with the real degradation formula, applied once.
11. **Repo hygiene** — deleted three dead one-off migration scripts (`modify_*.py`) and
    untracked 8.3MB of regenerable FastF1 cache data (including a stray `.sqlite-journal`
    file) from git.

All changes are merged directly to `main` (PR #1, fast-forwarded and closed).

## 4. Current, honestly-reported MCTS vs. DP result

After the fixes above, `evaluate_mcts.py` was re-run for real (100 paired races, Bahrain,
`sc_probability=0.08`, shared weather/SC/noise per race, MCTS re-queried on SC
appearance/weather change/periodic cadence with a reduced search budget of 100
rollouts/decision vs. the production default of 1,000):

| Metric | Value |
|---|---|
| MCTS win rate | 7% |
| DP win rate | 93% |
| Mean time saved by MCTS | **-124s/race** (MCTS slower on average, at this budget) |
| Best single-race MCTS outcome | **+2,731s** (the one race with a genuine sustained storm) |
| Worst single-race MCTS outcome | -1,065s (an unnecessary extra pit stop in ordinary conditions) |

**Diagnosis:** increasing the search budget 3× (300 rollouts/decision, 20-race sample) did
*not* close the gap. This is the key finding that motivates v5: the bottleneck is not search
volume, it's that the MCTS tree-traversal cost heuristic
(`lap_time = base_lap_time + tire_age * 0.10 + pit_loss`) is flat and compound-agnostic,
while the real degradation model is compound-specific with a quadratic cliff
(`soft: 0.14s/lap, cliff@15`; `medium: 0.08s/lap, cliff@24`; `hard: 0.04s/lap, cliff@38`).
A heuristic that misprices *which* tire is actually cheap to run can cause the search to
consistently favor the wrong branches no matter how many iterations it's given.

## 5. Known limitations / open items going into v5

- MCTS decision quality in ordinary (non-storm) conditions still trails DP — this is the
  primary problem v5's hybrid architecture is designed to address.
- The DP optimizer's "must use ≥2 compounds" F1 rule is enforced as a post-hoc filter on
  traced strategies, not as a hard constraint inside the backward induction itself. This can
  cause a starting-compound candidate to be dropped entirely (rather than replanned under the
  constraint) if its unconstrained-optimal policy happens to use only one compound. Not fixed
  this round; noted for future work.
- No frontend test suite exists (backend has 24 passing tests across 7 files).
- Bundle size warning on frontend build (single ~570KB JS chunk, no code-splitting) — cosmetic,
  not addressed.

## 6. Test status at this snapshot

- `pytest backend/` — 24 passed
- `npm run build` (frontend) — succeeds
- Manual browser verification — driver dropdown, risk-aversion ranking, and driver-impact
  naming all confirmed working end-to-end in Chrome via the dev server + FastAPI backend.
