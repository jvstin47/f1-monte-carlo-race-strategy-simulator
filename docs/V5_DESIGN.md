# Apex Strategy v5 — Hybrid Strategic Search Engine

**Project:** Apex Strategy
**Version:** v5
**Status:** Proposed
**Primary Goal:** Improve MCTS decision quality in ordinary race conditions by replacing its
overly simplified traversal assumptions with a calibrated hybrid search architecture.

Related: [`docs/archive/PROJECT_STATUS_v4.md`](archive/PROJECT_STATUS_v4.md) records the v4
state and the empirical finding that motivates this design — a 3× search-budget increase did
not close MCTS's gap to the DP optimizer in ordinary conditions, implicating the traversal
heuristic rather than search volume.

---

## 1. Executive Summary

Apex Strategy v5 evolves the existing F1 race-strategy simulator from a collection of
optimization algorithms into a hybrid strategic decision engine.

The current system combines:

- NumPy-vectorized Monte Carlo simulation
- FastAPI backend
- React/Vite dashboard
- Dynamic Programming strategy optimization
- Monte Carlo Tree Search (MCTS)
- Rolling mid-race replanning
- Tire degradation modeling
- Fuel burn
- Safety Cars
- Stochastic weather
- Undercut / dirty-air effects
- Driver profiles
- Track presets

The major limitation identified in v4 is that the MCTS rolling replanner performs worse than
the DP optimizer in ordinary conditions even after substantially increasing its search budget.

This strongly suggests that the problem is not simply insufficient search.

The current MCTS traversal relies on a simplified tire-wear heuristic. If that heuristic
systematically ranks race states differently from the actual simulator, MCTS can spend more
computation exploring branches that are strategically inferior.

v5 therefore introduces a hybrid architecture:

MCTS performs strategic exploration. The existing high-fidelity Monte Carlo engine evaluates
promising states. The system should use cheap approximations for broad tree exploration and
selectively invoke expensive simulation where additional accuracy has meaningful strategic
value.

## 2. Problem Statement

The current MCTS implementation has successfully become a functional race-strategy optimizer,
but its decision quality remains inferior to DP under many ordinary race conditions.

Increasing the MCTS search budget by approximately 3× did not close this gap. This indicates
that additional computation alone is unlikely to solve the problem.

The suspected root cause is the simplified state-evaluation/traversal heuristic used inside
the MCTS tree. A heuristic that incorrectly estimates the relative value of:

- staying out,
- pitting,
- changing compounds,
- extending a stint,
- preserving a pit stop,
- reacting to degradation,

can cause MCTS to converge toward systematically inferior strategies.

**Core question for v5:** Can MCTS make better strategic decisions by combining inexpensive
heuristic search with selective high-fidelity Monte Carlo evaluation?

## 3. Goals

### 3.1 Primary Goals

**G1 — Improve MCTS decision quality.** The primary objective is to reduce the performance gap
between MCTS and the existing DP optimizer in ordinary conditions. MCTS does not necessarily
need to beat DP immediately. The first milestone is: MCTS should become consistently
competitive with DP rather than systematically trailing it.

**G2 — Validate the MCTS traversal heuristic.** Create an explicit experiment comparing
heuristic predicted branch value against actual simulator branch value. The system should
determine whether the heuristic correctly ranks candidate actions.

**G3 — Introduce selective high-fidelity evaluation.** Allow MCTS to invoke the existing Monte
Carlo simulator for promising states instead of relying entirely on simplified traversal
estimates. The expensive simulator should not be executed for every tree node.

**G4 — Preserve the existing simulator.** The existing NumPy Monte Carlo engine remains the
source of truth for race physics and stochastic evaluation. v5 should improve the decision
layer rather than unnecessarily rewriting the simulation engine.

**G5 — Make MCTS decisions explainable.** For each recommendation, the system should be able
to expose why the selected strategy won. Example:

```text
Stay out 4 laps
- Tire degradation remains manageable
- Current traffic makes an immediate pit inefficient
- Medium compound retains sufficient life
- Delayed pit creates a better weather-response window
- High-fidelity simulation predicts +6.8s advantage over immediate pit
```

## 4. Non-Goals

v5 will not attempt to:

- build a complete F1 race simulator
- reproduce real F1 telemetry
- model every aerodynamic effect
- create a neural-network strategy model
- replace DP entirely
- eliminate all heuristic approximations
- guarantee real-world race-optimal decisions
- optimize the entire frontend from scratch
- increase MCTS iterations without evidence that more search is useful

## 5. Core Design Principle

The most important architectural principle of v5 is:

**Search cheaply. Evaluate intelligently.**

MCTS should not spend the same computational effort on every node. Instead:

```text
                 Race State
                     │
                     ▼
                MCTS Search
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
     Stay Out     Pit Soft     Pit Medium
        │            │            │
      Cheap        Cheap        Cheap
     Estimate     Estimate     Estimate
        │            │            │
        └────────────┼────────────┘
                     ▼
              Candidate Ranking
                     │
                     ▼
          Select Promising Branches
                     │
                     ▼
        High-Fidelity Monte Carlo
               Evaluation
                     │
                     ▼
                  Reward
                     │
                     ▼
              MCTS Backprop
```

This architecture allows the expensive simulator to be used where it provides the greatest
information.

## 6. v5 Architecture

### 6.1 Existing Components

The following components remain:

**Frontend:** React, Vite, existing strategy dashboard, race configuration, optimizer
controls, strategy visualization, MCTS results.

**Backend:** FastAPI, NumPy simulation engine, existing `/optimize` endpoint, existing
`/optimize-mcts` endpoint, driver profiles, track presets.

**Existing Optimization:** Dynamic Programming optimizer, MCTS optimizer, Monte Carlo
simulation.

## 7. New Components

### 7.1 Heuristic Evaluator

A dedicated module responsible for inexpensive estimation of a race state. It should estimate
factors such as:

- tire performance
- tire age
- expected degradation
- fuel load
- pit-stop cost
- track position
- traffic
- weather state
- weather transition probability
- remaining pit stops
- compound availability

The evaluator must remain significantly cheaper than a full Monte Carlo rollout.

### 7.2 Branch Evaluator

The Branch Evaluator determines whether a candidate MCTS node deserves high-fidelity
simulation.

Possible inputs:

```text
state
heuristic_value
tree_depth
visit_count
uncertainty
action_type
weather_probability
tire_age
remaining_pit_stops
```

Possible output:

```text
evaluate_with_simulator = true / false
```

### 7.3 High-Fidelity Rollout Adapter

A new adapter layer between MCTS and the existing Monte Carlo engine. Its responsibility is to
translate:

```text
MCTS State
      ↓
Simulation Parameters
      ↓
Monte Carlo Engine
      ↓
Expected Race Result
      ↓
MCTS Reward
```

The MCTS engine should not need to know the internal details of the Monte Carlo simulator.

### 7.4 Calibration Harness

A dedicated experimental module used to compare heuristic prediction vs. actual Monte Carlo
outcome. This is a first-class component rather than an ad-hoc debugging script.

> **Status:** implemented as `backend/calibration_harness.py` — see
> [`docs/PHASE1_CALIBRATION_RESULTS.md`](PHASE1_CALIBRATION_RESULTS.md) for the first run's
> results.

## 8. MCTS Algorithm Changes

### 8.1 Existing Pipeline

```text
Selection → Expansion → Cheap Heuristic → Reward → Backpropagation
```

### 8.2 v5 Pipeline

```text
Selection → Expansion → Cheap Heuristic → Candidate Ranking →
Selective High-Fidelity Rollout → Reward → Backpropagation
```

## 9. Heuristic Evaluation Model

The initial heuristic should be decomposed into interpretable components. Example:

```text
state_score =
    tire_score
  + fuel_score
  + track_position_score
  + pit_cost_score
  + traffic_score
  + weather_score
  + strategic_flexibility_score
```

The exact weighting should be configurable.

**Important requirement:** the heuristic must not silently become another opaque optimizer.
Each component should have an understandable interpretation.

## 10. Tire Model Improvement

The tire model is the highest-priority area for investigation. The heuristic should consider:

- **Tire age** — older tires should generally become less valuable.
- **Compound characteristics** — different compounds should have different pace, degradation,
  usable lifetime, and warm-up behavior.
- **Remaining useful life** — instead of treating tire age as a simple linear penalty,
  estimate: `remaining_tire_value = expected_future_laps × expected_pace_advantage`
- **Degradation curve** — the heuristic should approximate the actual degradation curve rather
  than using a simplistic fixed penalty.

## 11. Strategic Flexibility

One of the major additions in v5 should be the concept of option value. A strategy is not
valuable only because it is currently fast. It can also be valuable because it preserves
future choices.

```text
Strategy A:
Pit now
→ 1 pit stop remaining

Strategy B:
Stay out
→ 2 pit stops available
→ weather uncertainty remains
→ future flexibility preserved
```

The heuristic should therefore account for: remaining pit stops, available compounds, tire
age, weather uncertainty, future pit windows. This is particularly important for storm
scenarios.

## 12. Weather-Aware Search

The MCTS engine should treat uncertain weather as a branching strategic factor.

```text
Current weather
      │
      ├── Dry continues
      │
      ├── Light rain
      │
      └── Heavy rain
```

The tree should be able to recognize that an apparently slower strategy may have greater
expected value because it preserves the ability to react to a weather transition.

## 13. Adaptive High-Fidelity Rollouts

High-fidelity simulation should be triggered selectively. Possible triggers:

- **Trigger A — Top candidate.** A branch ranks within the top N heuristic candidates.
- **Trigger B — High uncertainty.** Two branches have similar heuristic scores
  (e.g. 102.4 vs. 102.1) — a valuable situation for expensive evaluation.
- **Trigger C — Strategic discontinuity.** An action changes the strategic state
  significantly: pit stop, compound change, weather transition, Safety Car, loss of a
  remaining pit stop.
- **Trigger D — Late-race decisions.** As the remaining race distance becomes smaller, the
  cost of a wrong decision increases.

## 14. Progressive Evaluation

Not every branch needs the same Monte Carlo budget:

```text
Low importance    → 50 simulations
Medium importance → 250 simulations
High importance   → 1,000 simulations
Final candidate   → 5,000+ simulations
```

The exact numbers should be configurable and benchmarked. This creates a second layer of
adaptive computation.

## 15. Confidence-Aware Decisions

Each high-fidelity evaluation should produce more than a mean result. At minimum:
`expected_time`, `variance`, `confidence_interval`, `sample_count`.

The MCTS system can then distinguish:

```text
Strategy A: Expected +3.2s, Confidence: High
Strategy B: Expected +2.8s, Confidence: Low
```

This prevents MCTS from overreacting to noisy simulation results.

## 16. Risk-Aware Reward

The existing Risk Aversion control should become part of the MCTS reward model. Conceptually:

```text
reward = expected_performance - risk_aversion × uncertainty
```

A highly risk-averse driver should therefore prefer slightly slower but more predictable
strategies, while a low-risk-aversion configuration can accept higher variance for potentially
better race time.

> **Note:** the DP optimizer already implements this exact convention for its own risk
> control as of v4 (`expected_time + risk_aversion * std_dev`, ranking starting-compound
> candidates by a real Monte Carlo–derived `std_dev`). v5's MCTS risk model should stay
> consistent with it.

## 17. Benchmarking Framework

v5 requires a formal benchmark suite covering at least:

- **Group A — Ordinary dry races:** stable weather, normal degradation, no Safety Car.
- **Group B — Tire degradation:** aggressive degradation, long stints, multiple compounds.
- **Group C — Safety Car:** early, mid-race, late.
- **Group D — Weather:** light rain, sudden storm, gradual transition, false weather threat.
- **Group E — Traffic:** dirty air, undercut opportunities, overcut opportunities.
- **Group F — Edge cases:** fresh tires, worn tires, one pit stop remaining, zero pit stops
  remaining, unusual starting compound.

## 18. Evaluation Metrics

Every benchmark run should record:

- **Primary:** total race time, gap vs. DP, gap vs. baseline, strategy win rate.
- **MCTS-specific:** tree nodes, iterations, simulator rollouts, heuristic evaluations,
  rollout/evaluation ratio, average tree depth.
- **Quality:** decision agreement with high-fidelity simulation, heuristic ranking accuracy,
  action-ranking correlation, regret.
- **Efficiency:** execution time, simulations per second, memory usage.

## 19. Heuristic Calibration Experiment

Before fully integrating the hybrid engine, run a dedicated experiment. For every candidate
action:

```text
State → Heuristic prediction → Monte Carlo evaluation
```

Collect `heuristic_score`, `actual_expected_time`, `actual_variance`. Then calculate rank
correlation, mean absolute error, ordering accuracy, top-1 agreement, top-2 agreement.

**Success condition:** the heuristic does not need to predict exact race time. It must
reliably identify promising branches.

> **Status:** implemented — see [`docs/PHASE1_CALIBRATION_RESULTS.md`](PHASE1_CALIBRATION_RESULTS.md).

## 20. Baselines

Every v5 experiment should compare at least:

1. Simple heuristic strategy.
2. Current v4 MCTS.
3. Current DP optimizer.
4. v5 Hybrid MCTS.

This prevents improvements from being attributed incorrectly.

## 21. Success Criteria

**Minimum:** Hybrid MCTS consistently outperforms v4 MCTS; heuristic ranking is measurably
correlated with simulator outcomes; no regression in storm scenarios; all existing backend
tests continue to pass.

**Strong success:** Hybrid MCTS closes a substantial portion of the average gap to DP; Hybrid
MCTS achieves better results than DP in selected stochastic scenarios; computational cost
remains practical.

**Exceptional result:** Hybrid MCTS becomes competitive with or exceeds DP across a meaningful
benchmark suite while retaining its ability to replan during a race.

The final objective is not merely "MCTS wins." It is: MCTS makes good decisions quickly enough
to repeatedly replan as the race state changes.

## 22. API Design

The existing `/optimize-mcts` endpoint should remain backward compatible where practical.
Additional configuration may include: `search_budget`, `heuristic_mode`, `rollout_budget`,
`rollout_threshold`, `risk_aversion`, `weather_model`, `adaptive_rollouts`.

Example conceptual response:

```json
{
  "strategy": [],
  "expected_time": 0,
  "confidence": 0,
  "nodes_explored": 0,
  "high_fidelity_rollouts": 0,
  "heuristic_evaluations": 0,
  "risk_score": 0,
  "reasoning": []
}
```

The exact schema should be finalized during implementation based on the existing API
conventions.

## 23. Frontend Changes

The dashboard should expose the new MCTS architecture without overwhelming the user.

**Optimizer Controls:** add an optional Search Mode — Fast / Balanced / High Accuracy —
controlling the relationship between heuristic search and high-fidelity simulation.

**MCTS Results:** show recommended strategy, expected race time, confidence, risk, simulation
budget, high-fidelity rollouts.

**Strategy Explanation:** provide a compact explanation, e.g. *"Stay out — the current tire
has sufficient remaining life, while pitting now would consume a strategic stop. The simulator
also predicts a stronger future pit window."*

## 24. Observability

Every MCTS run should optionally generate a diagnostic object containing: `nodes_created`,
`nodes_pruned`, `heuristic_calls`, `simulation_calls`, `simulation_samples`,
`average_rollout_depth`, `best_action`, `runner_up_action`, `reward_difference`.

This makes future algorithm debugging significantly easier.

## 25. Testing Strategy

**Unit tests:** heuristic components, tire-value estimation, reward calculation, uncertainty
calculation, rollout triggering, risk-adjusted reward, state conversion, weather branching.

**Integration tests:** `/optimize-mcts`, MCTS → simulator adapter, frontend → backend
configuration, adaptive rollout configuration, risk-aversion propagation.

**Regression tests:** keep all currently passing v4 tests. Particularly preserve regression
coverage for: reward sign convention, duplicate compound pit prevention, pit-stop budget,
`random_std`, response nesting, driver IDs, backend URL wiring, risk aversion.

## 26. Deterministic Testing

MCTS experiments must support deterministic seeds. A benchmark should be reproducible using:
`seed`, `track`, `driver`, `starting_state`, `weather_seed`, `search_budget`,
`simulation_budget`. This is essential for comparing algorithm versions.

## 27. Development Phases

- **Phase 1 — Instrumentation.** Build the calibration harness. No major MCTS changes yet.
  Deliverable: quantitative evidence showing where the current heuristic disagrees with the
  simulator. *(In progress — see status note in §19.)*
- **Phase 2 — Heuristic Upgrade.** Improve tire, fuel, pit, weather and strategic-flexibility
  evaluation. Deliverable: better branch ranking without high-fidelity rollouts.
- **Phase 3 — Hybrid Rollout Engine.** Implement selective Monte Carlo evaluation.
  Deliverable: MCTS can selectively replace heuristic estimates with simulator-derived
  rewards.
- **Phase 4 — Adaptive Budgeting.** Implement progressive rollout budgets, uncertainty-based
  evaluation, candidate prioritization. Deliverable: computational effort concentrated on
  strategically important nodes.
- **Phase 5 — Risk Integration.** Integrate Risk Aversion into MCTS reward. Deliverable: MCTS
  produces different strategies according to risk preference.
- **Phase 6 — Benchmark Suite.** Run all scenario groups against baseline, v4 MCTS, DP, and v5
  Hybrid MCTS. Deliverable: reproducible performance report.
- **Phase 7 — Frontend.** Expose search mode, confidence, risk, rollout statistics, strategy
  explanation. Deliverable: user-facing hybrid optimizer experience.

## 28. Research Questions

- **RQ1** — Does the current heuristic correctly rank candidate strategies?
- **RQ2** — Does improving heuristic accuracy improve MCTS decision quality?
- **RQ3** — How many high-fidelity simulations are necessary to significantly improve
  decisions?
- **RQ4** — Is adaptive simulation more efficient than simply increasing MCTS iterations?
- **RQ5** — Does risk-aware MCTS produce meaningfully different strategies?
- **RQ6** — Does hybrid MCTS perform particularly well in environments where DP's assumptions
  are less suitable, such as stochastic weather?
- **RQ7** — Can MCTS provide better mid-race adaptability than a strategy optimized once
  before the race?

## 29. Key Engineering Principle

The project should avoid the trap of optimizing solely for a benchmark score. Apex Strategy is
fundamentally a decision system under uncertainty. Therefore, every algorithmic improvement
should be evaluated on three dimensions:

```text
             Decision Quality
                    ▲
                    │
      ┌─────────────┼─────────────┐
      │             │             │
   Accuracy      Robustness    Efficiency
```

A strategy that wins one deterministic benchmark but collapses under a weather transition is
not necessarily better.

## 30. Final Product Vision

Apex Strategy should ultimately become a system that behaves like a race strategist:

```text
                    LIVE RACE
                       │
                       ▼
                 Current State
                       │
                       ▼
               Strategic Search
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
       Cheap Exploration    High-Fidelity
             │               Simulation
             └─────────┬─────────┘
                       ▼
                 Risk Evaluation
                       │
                       ▼
              Best Current Action
                       │
                       ▼
                  Race Evolves
                       │
                       ▼
                  Replan Again
```

The defining feature of v5 is therefore not simply a faster or larger MCTS. It is adaptive
intelligence: use cheap reasoning to explore the strategic space, spend expensive simulation
only where it matters, quantify uncertainty, make a decision, observe how the race changes,
and repeat.

## 31. Definition of Done

- [ ] MCTS heuristic calibration is implemented.
- [ ] Heuristic-vs-simulator ranking can be measured.
- [ ] Tire evaluation is improved and validated.
- [ ] Strategic flexibility is represented in state evaluation.
- [ ] Weather uncertainty influences branch evaluation.
- [ ] MCTS can selectively invoke high-fidelity Monte Carlo simulation.
- [ ] Adaptive simulation budgets are implemented.
- [ ] Risk Aversion affects MCTS decisions.
- [ ] Deterministic benchmark runs are reproducible.
- [ ] v4 regression tests remain passing.
- [ ] DP, v4 MCTS and v5 Hybrid MCTS are directly comparable.
- [ ] Performance metrics are automatically collected.
- [ ] Frontend exposes meaningful hybrid-search controls.
- [ ] MCTS recommendations include confidence and diagnostic information.
- [ ] Ordinary-condition MCTS performance improves materially over v4.
- [ ] Storm/weather performance does not regress.
- [ ] README benchmarks use only genuine engine executions.
- [ ] Repository contains no generated caches or dead experimental scripts.

## 32. v5 North Star

Apex Strategy v5 is not about making MCTS search harder. It is about making MCTS know when it
needs to think harder. The system should combine:

- MCTS → strategic exploration
- Heuristics → cheap estimation
- Monte Carlo → high-fidelity evaluation
- Risk model → uncertainty-aware decisions
- Rolling replanning → adaptation to changing race conditions

Together, these form a hybrid strategy engine capable of making increasingly informed
decisions as the race unfolds.
