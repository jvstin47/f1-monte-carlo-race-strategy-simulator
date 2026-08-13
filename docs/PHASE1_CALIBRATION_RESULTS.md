# v5 Phase 1 — Calibration Harness Results

**Deliverable for:** [`docs/V5_DESIGN.md`](V5_DESIGN.md) §19 (Heuristic Calibration
Experiment), §27 Phase 1.
**Harness:** [`backend/calibration_harness.py`](../backend/calibration_harness.py)
**Reproduce:** `cd backend && ./venv/bin/python calibration_harness.py`
**Runtime:** ~2 seconds for 60 sampled states.

## What this measures

For 60 randomly sampled race states (spanning fresh/mid-stint/past-cliff tire ages, all three
dry+wet-adjacent compounds, all three weather states, ~15% with an active Safety Car, and a mix
of 0/1 stops already made), every legal action at that state was priced two ways:

1. **Heuristic cost** — exactly the formula `MCTSSolver._simulate()` uses while descending the
   tree: `base_lap_time + tire_age * 0.10 + pit_loss`, extrapolated across the remaining laps
   with the same flat, compound-agnostic degradation term.
2. **Real cost** — this lap's cost via the actual per-compound degradation curve
   (`calculate_tire_degradation`, wear-rate + quadratic cliff), plus the production rollout's
   Monte Carlo estimate (`MCTSSolver.rollout_eval`, the real simulator) for everything after.

If the heuristic were doing its job, it wouldn't need to match the real cost's *magnitude* —
that's what the expensive rollout is for. It would only need to rank actions in roughly the
same *order* the real simulator would, since that ranking is what UCB1 uses to decide where to
keep searching.

## Headline results

| Metric | Value |
|---|---|
| States sampled / evaluated | 60 / 60 |
| **Mean rank correlation** (heuristic vs. real, tie-averaged Spearman) | **0.101** |
| Median rank correlation | 0.866 |
| **Top-1 agreement rate** (heuristic's best action = real best action) | **41.7%** |
| Mean signed error (real − heuristic) | +433.6s |
| Mean absolute error | 445.9s |

## Interpretation

Most sampled states have exactly 3 legal actions, and the heuristic frequently ties two of
them (see root cause below), which constrains Spearman correlation to a small set of possible
values here. The actual per-state distribution across the 60 states:

| Rank correlation | # states | % |
|---|---|---|
| **-0.866** (heuristic ranks the actions essentially backwards) | 24 | 40.0% |
| 0.0 (no signal) | 5 | 8.3% |
| **+0.866** (heuristic ranks the actions essentially correctly) | 31 | 51.7% |

**This is not mild noise — it's closer to a coin flip with a thumb on the scale.** In 40% of
sampled states the heuristic's action ordering is close to *inverted* relative to what the real
simulator says, in 52% it's close to correct, and the rest carry no signal. The mean (0.101)
sitting far below the median (0.866) is a direct readout of that split, not a summary of
uniformly-mediocre performance.

**Top-1 agreement is 41.7%**, only modestly above what picking at random among ~3 average
options would give (~33%). The action the heuristic tells the tree to favor is right less than
half the time — worse than a coin flip on a binary choice, and barely better than chance across
the full multi-way action set.

### Root cause, confirmed directly

Pulling actual disagreement cases makes the mechanism concrete — the heuristic assigns
**identical cost to different pit compounds in the same state**, because compound identity
never enters its formula at all:

```text
L15 | MEDIUM (Age 15) | W:damp | SC:False | Stops:0
  actions:          ['stay_out', 'pit_soft', 'pit_hard']
  heuristic costs:  [4196.8, 4155.8, 4155.8]   <- pit_soft and pit_hard are IDENTICAL
  real costs:       [4832.15, 4886.64, 4842.4]
  heuristic picks:  pit_soft      real picks:  stay_out      rank_correlation: -0.866

L23 | HARD (Age 15) | W:dry | SC:False | Stops:0
  actions:          ['stay_out', 'pit_soft', 'pit_medium']
  heuristic costs:  [3402.0, 3373.0, 3373.0]   <- pit_soft and pit_medium are IDENTICAL
  real costs:       [3554.08, 3636.24, 3595.89]
  heuristic picks:  pit_soft      real picks:  stay_out      rank_correlation: -0.866

L25 | SOFT (Age 25) | W:damp | SC:False | Stops:1
  actions:          ['stay_out', 'pit_medium', 'pit_hard']
  heuristic costs:  [3237.3, 3179.3, 3179.3]   <- pit_medium and pit_hard are IDENTICAL
  real costs:       [3699.24, 3692.43, 3683.63]
  heuristic picks:  pit_medium    real picks:  pit_hard      rank_correlation: 0.866
```

Any two different compounds chosen at the same lap under the same conditions get the *exact
same* heuristic cost, because the formula only sees "tire age just reset to 1 (pit) or didn't
(stay out)" — never which compound was actually fitted. Soft (0.14s/lap wear, cliff at 15) and
hard (0.04s/lap wear, cliff at 38) are indistinguishable to the tree-traversal heuristic. It
can tell *whether* to pit, but has no real basis for choosing *what to pit for* — which is
exactly the kind of decision that determines whether a strategy is fast or merely
survivable.

The mean signed error (+433.6s, positive across all three compounds sampled: soft +456.0,
medium +426.8, hard +418.1) also shows the heuristic systematically *underestimates* total
race cost — expected, since a flat 0.10s/lap-age term is well below soft's real 0.14s/lap and
ignores every compound's cliff penalty entirely. But the near-zero rank correlation is the more
important finding: even a uniformly biased heuristic would preserve ranking (a constant offset
doesn't change relative order). This bias is *not* uniform across actions within a state, which
is what actually breaks the search.

## What this means for v5

This is direct, reproducible confirmation of the v4→v5 hypothesis in
[`docs/archive/PROJECT_STATUS_v4.md`](archive/PROJECT_STATUS_v4.md) §4: MCTS's underperformance
in ordinary conditions is not a search-budget problem (3× budget didn't help), it's that the
cheap heuristic guiding *where* the tree spends its budget is disconnected from the thing it's
supposed to approximate. Giving a disconnected heuristic more iterations just explores the
wrong branches more thoroughly.

This directly motivates **Phase 2** (§27 of the design doc): give the heuristic evaluator real
per-compound degradation awareness (at minimum, replace the flat `tire_age * 0.10` term with
`calculate_tire_degradation(compound, tire_age)`, which is already implemented and cheap to
call) before investing in the Phase 3 selective-high-fidelity-rollout machinery — a heuristic
that can't tell soft from hard doesn't need a smarter escalation policy yet, it needs to know
the difference between soft and hard.

## Caveats

- `real_action_cost` still uses `rollout_eval`'s existing simplification (resets tire age to 1
  for the rollout's own compound and adds back a one-off degradation correction) — it is the
  production engine's grounding, not a from-scratch physics recomputation, so this measures the
  heuristic against what MCTS *already trusts* at its leaves, not against an independent oracle.
- Rank correlation is computed per-state over a small action set (2-5 legal actions), so
  individual state correlations are coarse (only a handful of distinct rank orderings are
  possible); the aggregate mean/median across 60 states is the meaningful signal, not any one
  state's value in isolation.
- This run used `track_id="bahrain"`, `max_stops=2`, dry-tuned `available_compounds`. Not yet
  repeated across other tracks/compound sets — worth doing before Phase 2 lands, to confirm the
  finding isn't Bahrain-specific.
