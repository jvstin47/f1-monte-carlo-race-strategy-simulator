# v5 Phase 6 — Benchmark Suite Results

**Deliverable for:** [`docs/V5_DESIGN.md`](V5_DESIGN.md) §17 (Benchmarking Framework), §27 Phase 6.
**Implementation:** [`backend/benchmark_suite.py`](../backend/benchmark_suite.py)
**Reproduce:** `cd backend && ./venv/bin/python benchmark_suite.py` (~7 minutes)

## What this covers, and what it doesn't

Five scenarios spanning design-doc groups A (ordinary dry), B (aggressive degradation),
C (Safety Car), D (weather, two variants), each a 20-race DP vs. v4-classic vs. v5-hybrid
comparison via `evaluate_mcts.py`'s real production code paths, plus a Group F (edge cases)
section comparing v4-classic and v5-hybrid solver decisions directly at five hand-picked
tricky states.

**Group E (traffic / undercut opportunities) is not covered.** This codebase's undercut
model (`simulator.simulate_two_car_undercut`) is a separate two-car engine with no MCTS or DP
integration — neither solver has any notion of a rival car or track position. Benchmarking
"undercut scenarios" against DP/MCTS here would mean fabricating a comparison neither
algorithm can actually reason about.

**Sample size caveat:** 20 races/scenario (vs. the 100-race canonical run in
[Phase 2-4 results](PHASE2_4_RESULTS.md)) to keep total suite runtime bounded. At n=20, a
single storm-race outlier can swing a scenario's mean by hundreds of seconds — read
scenario-level numbers as directional, not precise. The 100-race Bahrain result remains the
more statistically stable reference point.

## Race-level scenario results

| Scenario | v4 classic vs DP | v5 hybrid vs DP | v5 vs v4 classic (win% / mean saved by v5) |
|---|---|---|---|
| A. Ordinary dry | 20% / -49.4s | 5% / -52.8s | 60% v5 / 35% v4 — **-3.4s** |
| B. Aggressive degradation (Silverstone) | 10% / +21.4s | 20% / +72.0s | 65% v5 / 25% v4 — **+50.6s** |
| C. Elevated Safety Car (0.15/lap) | 15% / +81.3s | 10% / +69.9s | 70% v5 / 30% v4 — **-11.3s** |
| D. Weather starts damp | 25% / +6.2s | 35% / +201.1s | 45% v5 / 40% v4 — **+194.9s** |
| D. Weather starts wet | 50% / -2.5s | 35% / -52.3s | 30% v5 / 40% v4 — **-49.9s** |

*(`mean saved` uses this project's standing convention: positive = that side was faster.
"vs DP" values are `mean_time_saved_by_<mcts_variant>`.)*

## Interpretation — this is genuinely mixed, not a clean win

Unlike the 100-race Bahrain result (Phase 2-4), which showed a consistent, substantial
improvement, this suite's smaller per-scenario samples show v5 **winning clearly in some
scenarios and losing in one**:

- **B (degradation-heavy Silverstone) and D-damp are clear v5 wins** — both by win rate and
  by a large mean-time margin. Damp-start in particular shows the strategic-flexibility bonus
  and real weather-penalty terms (Phase 2) doing real work: staying dry-tire-committed less
  stubbornly than v4's flat heuristic pays off substantially when the race actually needs a
  weather reaction.
- **A and C are split decisions**: v5 wins more *individual races* (60-70%) but v4 classic
  wins by a larger *margin* when it wins, netting out to a small mean disadvantage for v5
  (-3.4s, -11.3s). This is consistent with v5 winning the "typical" race by a little and
  occasionally losing a specific race by a lot — plausible given a 20-race sample and the
  known high-variance nature of storm/SC outlier races (Phase 2-4's canonical run had single
  races swinging by 1,000-3,000+ seconds).
- **D-wet is a genuine v5 regression** (30% vs. 40% win rate, -49.9s mean saved by v5). A
  plausible mechanism: `_should_use_high_fidelity` escalates on *any* non-dry weather, so in a
  scenario that starts wet, nearly every decision already gets the expensive real rollout —
  v5's main lever (spending less on uninteresting cheap leaves, reinvesting via Phase 4) has
  little room to operate when almost nothing is "uninteresting." The Phase 4 top-K refinement
  then adds extra rollouts *on top of* an already-mostly-high-fidelity search, which is pure
  overhead with no heuristic-quality upside in this regime. **This points at a genuine
  follow-up**: the discontinuity trigger for weather may need refining to distinguish "weather
  just changed" from "weather has already settled," rather than treating all non-dry laps
  identically (this exact gap was already flagged as a caveat in
  [Phase 2-4 results](PHASE2_4_RESULTS.md)).

## Group F: edge-case decisions (v4-classic vs. v5-hybrid, no DP baseline)

| State | v4 classic | v5 hybrid | Agree? |
|---|---|---|---|
| Fresh tires, race start | `pit_soft` (6134.4s) | `pit_hard` (6113.0s) | ❌ |
| Worn tires, one stop left | `pit_medium` (1738.4s) | `pit_soft` (1750.0s) | ❌ |
| Zero stops remaining, late race | `stay_out` (684.0s) | `stay_out` (684.6s) | ✅ |
| Unusual start compound (hard, lap 3) | `pit_medium` (5888.2s) | `stay_out` (5769.8s) | ❌ |
| Rain with stops in reserve | `pit_intermediate` (4464.3s) | `pit_intermediate` (4483.1s) | ✅ |

**Agreement rate: 40% (2/5).** The two solvers genuinely disagree more often than not on
these hand-picked tricky states — expected and, on balance, reassuring: it confirms the
hybrid architecture is actually searching differently, not just reproducing v4's decisions
faster. In the "unusual start compound" case, v5's own estimate favors its choice by a
meaningful margin (5769.8s vs. 5888.2s) — self-consistent with Phase 1's finding that v4's
flat heuristic misjudged which compound was actually worth pitting for. These are each single
searches, not repeated/averaged trials, so treat individual expected-time deltas as
illustrative rather than statistically robust.

## Honest summary

Phase 6 does not show v5 uniformly beating v4 classic — it shows v5 winning substantially in
degradation- and weather-transition-heavy conditions, roughly breaking even in ordinary/SC
conditions, and **losing** in a persistently-wet scenario where its main efficiency lever has
nowhere to apply. This is more informative than the single aggregate number from Phase 2-4:
it identifies a specific, plausible mechanism (the weather trigger not distinguishing
"changing" from "settled") worth fixing before claiming a general improvement, rather than
papering over it with a favorable-looking overall average.
