> **Archived snapshot.** This is the v4 README, frozen at the point v5 development began
> (see [`docs/V5_DESIGN.md`](../V5_DESIGN.md) and [`docs/archive/PROJECT_STATUS_v4.md`](PROJECT_STATUS_v4.md)).
> The live, current README is [`/README.md`](../../README.md).

# 🏎️ Apex Strategy v4 — F1 Monte Carlo Race Simulator

An advanced Formula 1 race strategy simulator powered by a high-performance **NumPy-vectorized Monte Carlo engine** in Python/FastAPI and an interactive **React telemetry dashboard**.

---

## 🚀 What's New in v4

1. **🌳 MCTS Strategy Optimizer**: Monte Carlo Tree Search optimization capable of dynamically replanning mid-race. Evaluates branching stochastic trees under uncertainty (Safety Cars & Weather) to constantly adjust to track conditions.
2. **🏎️ Driver Characteristics Layer**: 21 unique F1 driver profiles built using a teammate-delta methodology. Incorporates precise pace offsets, consistency metrics ($\sigma$), and data confidence flags based on the 2023 season.
3. **☔ Rolling Re-Optimization**: Mid-race replanning. Instead of blindly executing a rigid 0-lap strategy, the engine detects stochastic events (Rain, Safety Car) and intelligently calls the MCTS solver to dynamically adjust to changing realities.
4. **⚠️ Realism & Traffic**: Adds fuel burn effects, track evolution penalties over laps, and stochastic traffic loss.
5. *(Plus all v3 features: Stochastic Weather, DP Strategy Optimizer, 5 configurable circuits, Two-Car Undercut Engine, and FastF1 Telemetry Validation)*

---

## 📐 Mathematical Framework & Assumptions

### 1. Two-Phase Tire Degradation Model
$$\text{Degradation}(\text{compound}, \text{age}) = (\text{wear rate} \times \text{age}) + \begin{cases} 0 & \text{if } \text{age} \le \text{cliff threshold} \\ \text{cliff penalty} \times (\text{age} - \text{cliff threshold})^2 & \text{if } \text{age} > \text{cliff threshold} \end{cases}$$

- **Soft Compound (`soft`)**: Wear rate `0.14s/lap`, Cliff threshold Lap `15`, Cliff penalty `0.03`.
- **Medium Compound (`medium`)**: Wear rate `0.08s/lap`, Cliff threshold Lap `24`, Cliff penalty `0.02`.
- **Hard Compound (`hard`)**: Wear rate `0.04s/lap`, Cliff threshold Lap `38`, Cliff penalty `0.01`.

### 2. MCTS & Stochastic Replanning (v4)
- **UCB1 Algorithm**: Utilizes min-max normalized exploitation terms against a heavily tuned exploration parameter ($C = 0.1$) to find the mathematically optimal decision in highly-variable branching trees.
- **Dynamic Replanning Evidence**: `backend/evaluate_mcts.py` runs the *actual* production code paths head-to-head — `optimizer.optimize_strategy()`'s DP schedule executed as a fixed, non-reactive plan, against `mcts_optimizer.MCTSSolver` re-queried as a rolling replanner (on Safety Car appearance, weather regime change, and a periodic cadence), both against identical per-race Safety Car/weather/noise realizations and using the same tire-degradation and weather-penalty physics as the main engine. Over 100 paired races at `sc_probability=0.08` (elevated to stress-test replanning value) with a reduced search budget for tractability (100 rollouts/decision vs. the `/optimize-mcts` endpoint's production default of 1,000):
  - **MCTS Win Rate**: 7% — **DP Win Rate**: 93%
  - **Mean time saved by MCTS**: **-124s per race** (i.e. currently slower on average at this search budget)
  - **Best single-race outcome for MCTS**: **+2,731s**, in the one race with a genuine sustained storm — the rolling replanner reacted by pitting to intermediates when the rain hit, while the rigid DP schedule stayed on slicks (a 2.5x lap-time penalty in full wet) for the entire wet stretch.
  - **Worst single-race outcome for MCTS**: **-1,065s**, from an unnecessary extra pit stop taken in ordinary dry conditions.
  - **Honest takeaway**: the rolling-replan *mechanism* clearly works — it captured a massive, uncapped win in the one race that actually needed it — but at this reduced search budget, its decision quality in ordinary conditions isn't yet good enough to make it a net positive on average, and increasing the budget 3x (300 rollouts/decision, 20-race sample) did not close the gap, pointing to the simplified tire-degradation heuristic used for tree-traversal cost (`node.state.tire_age * 0.10`, uniform across compounds) rather than raw search noise. Production callers of `/optimize-mcts` use the full 1,000-rollout budget, which was not itself re-benchmarked at this scale due to runtime cost (a single 1,000-rollout decision takes ~15-20s).

### 3. Driver Characteristics (v4)
- **Pace Offset**: A fractional lap time multiplier based on teammate delta (e.g. Verstappen `-0.15s/lap`, Sargeant `+0.2s/lap`).
- **Consistency**: Modifies the per-lap noise standard deviation, allowing some drivers to hit hyper-consistent stints while rookies suffer higher variance. When `driver_id` is left as `"generic"`, the `random_std` request field controls this directly instead.

### 4. Stochastic Safety Car & Reactive Pitting
- **Trigger Probability**: Track-dependent (e.g. $P(\text{SC}) = 0.04$ per lap).
- **Discounted Pit Loss**: Pitting under SC reduces pit lane loss from `22.0s` down to `8.0s`.

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
- `POST /optimize` — Dynamic Programming strategy optimizer
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
```
