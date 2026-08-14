# v5 Phases 2-4 — Hybrid MCTS Results

**Deliverable for:** [`docs/V5_DESIGN.md`](V5_DESIGN.md) Phases 2 (Heuristic Upgrade), 3
(Hybrid Rollout Engine), 4 (Adaptive Budgeting).
**Implementation:** [`backend/heuristic_evaluator.py`](../backend/heuristic_evaluator.py) (new),
[`backend/mcts_optimizer.py`](../backend/mcts_optimizer.py) (rewritten).
**Reproduce:** `cd backend && ./venv/bin/python -c "from evaluate_mcts import evaluate_mcts_vs_dp; evaluate_mcts_vs_dp(num_races=100)"`
(~8.5 minutes for 100 races across all three arms).

## What was built

### Phase 2 — Heuristic Evaluator
`heuristic_evaluator.py` replaces the old flat, compound-agnostic traversal cost
(`base_lap_time + tire_age * 0.10`) with a decomposed, interpretable per-lap cost:

- **tire_score** — the real per-compound degradation curve (`calculate_tire_degradation`),
  the direct fix for the Phase 1 finding that soft and hard priced identically.
- **fuel_score** — the same fuel-burn model the production simulator uses.
- **weather_score** — the real compound/weather mismatch penalty
  (`compute_weather_compound_penalty`).
- **track_score** — the same track-evolution curve the simulator uses.
- **strategic_flexibility_bonus** — a new "option value" term (design doc §11): a small
  reward for preserving pit stops while weather is dry but could turn, scaled by the real
  dry→rain transition probability, that vanishes once it's already wet/damp or no stops
  remain to preserve. Its weight (`flexibility_weight=0.5`) is a conservative default, not
  tuned to convergence — see Caveats.

`mcts_optimizer.MCTSSolver._edge_cost` now uses these components for every tree-traversal
step, replacing the old flat formula directly.

### Phase 3 — Hybrid Rollout Engine (selective escalation)
`MCTSSolver` now has two leaf-evaluation paths:

- `heuristic_eval` — a cheap, closed-form projection using Phase 2's components (no
  `simulate_strategy_vectorized` call). This is the **default**.
- `rollout_eval` — the original, expensive real Monte Carlo rollout (unchanged).

`_should_use_high_fidelity` (the Branch Evaluator) escalates a newly-expanded leaf to the
real rollout when: the action just taken was a pit stop, the state has an active Safety Car,
the weather is non-dry, or the race is inside `late_race_lap_threshold` (default 10) laps of
the end. Otherwise it uses the cheap heuristic. A `use_hybrid_evaluation=False` flag
reproduces the exact original (v4) behavior — every leaf gets a real rollout — so v4 and v5
can be benchmarked against identical code paths.

Trigger A/B from the design doc (top-N candidate, close heuristic scores) need sibling
comparison that isn't available at first expansion; that role is filled by Phase 4 instead.

### Phase 4 — Adaptive top-K refinement
After the main search budget completes, `search(..., refine_top_k=2)` spends a small top-up
of *real* Monte Carlo rollouts on just the most-visited root candidates (i.e. the ones the
cheap search already trusts most), blending each in as `refine_sample_weight` (default 3)
additional weighted samples into the running average — concentrating extra compute on the
decision that's about to actually be made, rather than spreading it uniformly across the
whole tree.

## Benchmark: DP vs. v4-classic MCTS vs. v5-hybrid MCTS

`evaluate_mcts.py` was extended to run all three arms against **identical** per-race
Safety Car / weather / noise realizations and an **identical** MCTS iteration budget (100
rollouts/decision, matching Phase 1-era runs), so the comparison isolates the algorithm
change, not compute or luck. 100 races, Bahrain, `sc_probability=0.08`.

| Comparison | Win rate | Mean time saved | Wall clock |
|---|---|---|---|
| v4 classic MCTS vs. DP | MCTS 12% / DP 88% | **-80.37s** (MCTS slower) | 251.5s |
| v5 hybrid MCTS vs. DP | MCTS 16% / DP 84% | **-18.79s** (MCTS slower) | 261.3s |
| **v5 hybrid vs. v4 classic** | **v5 61% / v4 33%** (6% ties) | **+61.58s** (v5 faster) | — |

*(Sign convention: `mean_time_saved_by_X` — positive means X was faster than the other side.)*

## Interpretation

**This is real, measurable progress, not yet a full close of the gap.** v5 hybrid:

- Wins head-to-head against v4 classic in 61% of races (v4 wins 33%, 6% tie) — a clear,
  consistent improvement from the same search budget.
- Cuts the average deficit to DP from -80.37s to -18.79s — roughly a **76% reduction** in
  the gap, using the *same* iteration budget.
- Achieves this without costing more compute: v5's total rollout count (37,285) plus
  heuristic evaluations (16,694) reflects that ~31% of leaf evaluations used the cheap path
  instead of a full Monte Carlo run, and the freed-up budget was reinvested via Phase 4's
  top-K refinement rather than simply saved — wall-clock time is comparable (251.5s vs.
  261.3s), not faster, because that reinvestment was deliberate.
- Still loses to DP more often than it wins (16% vs. 84%), and mean time saved is still
  negative. **v5 has not yet met the "consistently competitive with DP" bar from the design
  doc's G1**, though it's substantially closer than v4 was.

This confirms the core v5 hypothesis directly: the Phase 1 finding (a heuristic that
couldn't distinguish soft from hard) was a real, fixable bottleneck, and fixing it plus
adding selective escalation and adaptive refinement produced a real, non-trivial
improvement — not the diminishing-returns result a further pure search-budget increase gave
in v4 testing.

## What's likely still missing

- **The flexibility bonus weight is a guess, not a calibrated value.** It was not swept or
  tuned against this benchmark; a natural next experiment is a small grid search over
  `flexibility_weight` to see whether it's helping, hurting, or neutral at its current
  setting.
- **Phase 3's trigger set is coarse.** "Weather is non-dry" escalates on *every* non-dry lap
  regardless of whether the state actually needs a decision; a lap deep into a settled wet
  stint costs the same escalation as the lap it started raining. Trigger B (close heuristic
  scores between actions) was deferred to Phase 4's top-K mechanism rather than implemented
  at expansion time — worth revisiting if profiling shows escalation is firing more than it
  needs to.
- **`late_race_lap_threshold=10` and `refine_top_k=2` are untuned defaults**, same caveat as
  Phase 1's methodology note: configurable and benchmarked (design doc §14), not yet swept.
- Phases 5-7 (risk integration into MCTS reward, formal multi-track benchmark suite,
  frontend exposure) remain not started.

## A note on getting this number right

The first version of this benchmark's comparison helper had an inverted sign convention
(`diff = candidate - baseline` instead of `baseline - candidate`), which would have reported
v4 and v5 as *saving* time when they were actually losing it. It was caught by checking the
result against win-rate sanity (a 12% MCTS win rate cannot coexist with MCTS "saving" 80s on
average) before writing up this document, and fixed in `evaluate_mcts.py._compare` to use
explicit `baseline`/`candidate` naming instead of ambiguous `a`/`b`. The numbers above are
from the corrected code.
