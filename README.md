# 🏎️ Apex Strategy v3 — F1 Monte Carlo Race Simulator

An advanced Formula 1 race strategy simulator powered by a high-performance **NumPy-vectorized Monte Carlo engine** in Python/FastAPI and an interactive **React telemetry dashboard**.

---

## 🚀 What's New in v3

1. **🌍 Track-Specific Parameters**: 5 distinct F1 circuits with accurate base lap times, pit stop losses, SC probabilities, and tire wear multipliers.
2. **🌧️ Stochastic Weather Engine**: Markov chain modeling for changing track conditions (Dry $\rightarrow$ Damp $\rightarrow$ Wet), with compound crossover penalties and reactive weather pitting.
3. **🧠 DP Strategy Optimizer**: Deterministic backward induction optimizer evaluating ~20,000 states in milliseconds to compute the mathematically optimal race strategy and top 5 alternatives.
4. *(Plus all v2 features: Safety Cars, Two-Car Undercut Engine, and FastF1 Telemetry Calibration)*

---

## 📐 Mathematical Framework & Assumptions

### 1. Two-Phase Tire Degradation Model
$$\text{Degradation}(\text{compound}, \text{age}) = (\text{wear\_rate} \times \text{age}) + \begin{cases} 0 & \text{if } \text{age} \le \text{cliff\_threshold} \\ \text{cliff\_penalty} \times (\text{age} - \text{cliff\_threshold})^2 & \text{if } \text{age} > \text{cliff\_threshold} \end{cases}$$

- **Soft Compound (`soft`)**: Wear rate `0.14s/lap`, Cliff threshold Lap `15`, Cliff penalty `0.03`.
- **Medium Compound (`medium`)**: Wear rate `0.08s/lap`, Cliff threshold Lap `24`, Cliff penalty `0.02`.
- **Hard Compound (`hard`)**: Wear rate `0.04s/lap`, Cliff threshold Lap `38`, Cliff penalty `0.01`.

### 2. Stochastic Safety Car & Reactive Pitting
- **Trigger Probability**: $P(\text{SC}) = 0.04$ per lap.
- **SC Pace**: Fixed bunched pace (~135% of base lap time).
- **Discounted Pit Loss**: Pitting under SC reduces pit lane loss from `22.0s` down to `8.0s`.
- **Reactive Strategy**: If a driver enables *Reactive SC Pitting*, the engine dynamically pits the driver immediately upon SC deployment if the SC occurs within 8 laps of their target pit lap.

### 3. Two-Car Undercut & Dirty Air
- **Dirty Air Penalty**: If $\text{Gap}(A, B) \le 1.5\text{s}$, the trailing car suffers a $+0.25\text{s/lap}$ aerodynamic penalty.
- **Undercut Curve**: Evaluates track position win rate across relative pit timing deltas (pitting 4 laps before rival to 3 laps after).

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
- `POST /simulate` — 10,000-run Monte Carlo single strategy (includes Weather)
- `POST /compare` — Head-to-head strategy comparison
- `POST /optimize` — Dynamic Programming strategy optimizer
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
backend/venv/bin/python backend/test_api.py
```
