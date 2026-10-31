# Smart Traffic Congestion Predictor and Navigator (Bengaluru)

A full-stack, data-driven intelligent transportation system combining **Random Forest Machine Learning** for congestion estimation and the **A* Search Algorithm** for optimal, congestion-aware route navigation across Bengaluru's urban road network.

---

## ?? Project Overview

Urban traffic congestion in Bengaluru is among the most severe in the world. Commuters frequently face unpredictable bottlenecks around major transit junctions such as Silk Board, Koramangala, Indiranagar, and Electronic City. 

This project provides an end-to-end intelligent navigation and traffic intelligence platform:
1. **Traffic Congestion Estimation:** Uses an ensemble **Random Forest Classifier** trained on the real-world **Bangalore Traffic Pulse** dataset to estimate congestion levels (**LOW**, **MEDIUM**, **HIGH**) and compute confidence probabilities based on observed traffic volume, vehicle speed, road capacity utilization, weather conditions, temporal features, and incident reports.
2. **Congestion-Aware A* Routing:** Implements the **A* Graph Search Algorithm** on the road network graph (sourced from OpenStreetMap via OSMnx / NetworkX) using an **admissible heuristic** (Haversine distance divided by maximum permissible road speed) and a congestion-weighted edge cost function.
3. **Interactive Web Dashboard:** A responsive React (Vite + Tailwind CSS) application featuring interactive Leaflet maps, multi-route comparison (Recommended vs. Alternatives), real-time congestion overlays, exploratory data analytics, and model evaluation telemetry.

---

## ??? System Architecture

```
+-----------------------------------------------------------------------------+
¦                           REACT FRONTEND (Vite)                             ¦
¦  +---------------+  +------------------+  +--------------+  +-------------+ ¦
¦  ¦     Home      ¦  ¦  Route Planner   ¦  ¦  Analytics   ¦  ¦  Model Perf ¦ ¦
¦  ¦ (Hero & Intro)¦  ¦ (Leaflet MapView)¦  ¦  (Recharts)  ¦  ¦  (Metrics)  ¦ ¦
¦  +---------------+  +------------------+  +--------------+  +-------------+ ¦
+----------+-------------------+-------------------+-----------------+--------+
           ¦                   ¦ HTTP / JSON Axios ¦                 ¦
           ?                   ?                   ?                 ?
+-----------------------------------------------------------------------------+
¦                           FASTAPI BACKEND                                   ¦
¦  +---------------+  +------------------+  +--------------+  +-------------+ ¦
¦  ¦  GET /health  ¦  ¦   POST /routes   ¦  ¦ GET /traffic ¦  ¦ GET /model  ¦ ¦
¦  ¦               ¦  ¦  (A* Routing)    ¦  ¦  /summary    ¦  ¦  /metrics   ¦ ¦
¦  +---------------+  +------------------+  +--------------+  +-------------+ ¦
¦          ¦                   ¦                   ¦                 ¦        ¦
¦          ?                   ?                   ?                 ?        ¦
¦  +---------------+  +------------------+  +--------------+  +-------------+ ¦
¦  ¦  Core Config  ¦  ¦ Routing Service  ¦  ¦TrafficService¦  ¦  ML Service ¦ ¦
¦  ¦  & CORS       ¦  ¦ (OSMnx/NetworkX) ¦  ¦(Cleaned Data)¦  ¦(Joblib Model¦ ¦
¦  +---------------+  +------------------+  +--------------+  +-------------+ ¦
+------------------------------+-------------------------------------+--------+
                               ?                                     ?
                    +----------------------+              +------------------+
                    ¦ Bengaluru Road Graph ¦              ¦  Random Forest   ¦
                    ¦  (OpenStreetMap /    ¦              ¦ Pipeline (Sklearn¦
                    ¦   GraphML / OSMnx)   ¦              ¦   200 Trees)     ¦
                    +----------------------+              +------------------+
```

---

## ?? Algorithms & Mathematical Formulation

### 1. Random Forest Congestion Classifier
- **Algorithm:** Bagging ensemble of $B = 200$ decision trees with stratified bootstrap sampling.
- **Features ($X$):**
  - Continuous: `Traffic Volume`, `Average Speed (km/h)`, `Travel Time Index (TTI)`, `Road Capacity Utilization (%)`, `Incident Reports`, `DayOfWeek`, `Month`.
  - Categorical: `Weather Conditions` (Clear, Rainy, Cloudy, Foggy), `Roadwork and Construction Activity` (Yes, No).
- **Target ($y$):** Congestion category $\in \{\text{LOW}, \text{MEDIUM}, \text{HIGH}\}$.
- **Leakage Prevention:** Raw `Congestion Level` is strictly quarantined from input features. Features are standardized using `StandardScaler` and encoded via `OrdinalEncoder` wrapped in an sklearn `ColumnTransformer`.
- **Class Balancing:** `class_weight='balanced'` adjusts loss dynamically inversely proportional to class frequencies:
  $$w_j = \frac{N}{K \cdot n_j}$$

### 2. Congestion-Aware A* Routing
- **Graph Representation:** Directed multigraph $G = (V, E)$ where vertices $v \in V$ represent intersections and edges $e = (u, v) \in E$ represent navigable road segments.
- **Edge Cost Function:**
  $$c(u, v) = t_{(u, v)} \times \left(1 + \rho_{\text{congestion}}\right)$$
  where:
  - $t_{(u, v)} = \frac{\text{length}(u, v)}{\text{speed}(u, v)}$ is the baseline free-flow travel time.
  - $\rho_{\text{congestion}} \in \{0.0\ (\text{LOW}),\ 0.3\ (\text{MEDIUM}),\ 0.7\ (\text{HIGH})\}$.
- **Heuristic Function $h(u, v)$:**
  $$h(u, v) = \frac{D_{\text{Haversine}}(u, v)}{v_{\max}}$$
  Because $D_{\text{Haversine}}(u, v) \le \text{actual road distance}$ (triangle inequality on the Earth sphere) and $v_{\max} \ge \text{actual speed}$, $h(u, v) \le c^*(u, v)$ for all nodes.
  **Optimality Guarantee:** Since $h(n)$ is admissible ($h(n) \le h^*(n)$) and consistent ($h(u) \le c(u, v) + h(v)$), $A^*$ is guaranteed to find the optimal route.

---

## ?? Project Structure

```
smart-traffic-navigator/
+-- backend/
¦   +-- app/
¦   ¦   +-- api/               # API Routers (health, predict, routes, traffic, model)
¦   ¦   +-- core/              # Settings, CORS, path configurations
¦   ¦   +-- schemas/           # Pydantic v2 validation models
¦   ¦   +-- services/          # Business logic: ML, Routing (A*), Analytics
¦   ¦   +-- __init__.py
¦   ¦   +-- main.py            # FastAPI entry point & lifespan events
¦   +-- requirements.txt       # Backend dependencies
+-- frontend/
¦   +-- src/
¦   ¦   +-- components/        # MapView, CongestionBadge, DemoModeBanner, Navbar, etc.
¦   ¦   +-- pages/             # Home, RoutePlanner, Analytics, ModelPerformance
¦   ¦   +-- services/          # Axios HTTP client
¦   ¦   +-- App.jsx            # React Router setup
¦   ¦   +-- index.css          # Tailwind CSS styling
¦   ¦   +-- main.jsx           # React DOM root
¦   +-- index.html
¦   +-- package.json
¦   +-- tailwind.config.js
¦   +-- vite.config.js
+-- data/
¦   +-- raw/                   # Place Banglore_traffic_Dataset.csv here
¦   +-- processed/             # Cleaned dataset & feature_stats.json
¦   +-- maps/                  # Cached Bengaluru GraphML road network
+-- ml/
¦   +-- artifacts/             # Serialized model, preprocessor, metrics, feature importances
¦   +-- notebooks/             # 01_traffic_exploration.ipynb
¦   +-- preprocessing.py       # Cleaning, encoding & fallback generator
¦   +-- train.py               # Model training pipeline
¦   +-- evaluate.py            # Evaluation & metrics extraction
+-- tests/
¦   +-- conftest.py
¦   +-- test_preprocessing.py  # Unit tests for data cleaning & pipeline
¦   +-- test_routing.py        # A* optimality, admissibility & edge costs
¦   +-- test_api.py            # Integration tests for all 5 FastAPI endpoints
+-- .env.example
+-- .gitignore
+-- pytest.ini
+-- README.md
```

---

## ?? Dataset Details & Placement

### Primary Dataset: Bangalore's Traffic Pulse
- **Source:** Kaggle ([preethamgoud/bangalores-traffic-pulse](https://www.kaggle.com/datasets/preethamgoud/bangalores-traffic-pulse))
- **File Name:** `Banglore_traffic_Dataset.csv`
- **Destination:** Place the downloaded CSV into:
  ```
  smart-traffic-navigator/data/raw/Banglore_traffic_Dataset.csv
  ```
- **Observed Attributes:**
  - `Date`: Timestamp / observation date
  - `Area Name`: Urban cluster (Koramangala, Indiranagar, Whitefield, etc.)
  - `Road/Intersection Name`: Specific artery
  - `Traffic Volume`: Count of observed vehicles
  - `Average Speed (km/h)`: Mean velocity recorded
  - `Travel Time Index`: Ratio of actual travel time to free-flow travel time
  - `Congestion Level`: Target label (`Low`, `Medium`, `High`)
  - `Road Capacity Utilization (%)`: Percentage of roadway capacity consumed
  - `Incident Reports`: Count of breakdowns, minor collisions, stalls
  - `Weather Conditions`: Environmental state (`Clear`, `Rainy`, `Cloudy`, `Foggy`)
  - `Roadwork and Construction Activity`: Active work zones (`Yes`, `No`)

### ?? Transparent Data Handling & Demo Mode
- **No Fabrications:** If the raw Kaggle dataset is not found in `data/raw/`, the application **automatically activates Demo Mode**.
- In Demo Mode, statistically aligned records reflecting Bangalore traffic boundaries are generated and all frontend pages display clear amber **"Demo Mode"** banners and badges.
- Road-level congestion values are derived via area-level mapping and clearly labeled in the user interface as **"Area-level estimate"**.

---

## ?? Setup & Execution Guide

### Prerequisites
- Python 3.10 to 3.13
- Node.js 18+ and npm
- Git

---

### Step 1: Clone & Configure Environment

```bash
git clone <repo-url>
cd smart-traffic-navigator
```

Copy the environment file:
```bash
cp .env.example .env
```

---

### Step 2: Backend & ML Setup

1. **Activate Python Virtual Environment:**
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install Python Dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r backend/requirements.txt
   ```

3. **Preprocess Dataset & Train Model:**
   ```bash
   # Run data preprocessing (cleans raw CSV or generates demo data)
   python ml/preprocessing.py

   # Train the Random Forest Classifier
   python ml/train.py

   # Evaluate model and generate metrics.json & feature_importance.json
   python ml/evaluate.py
   ```

4. **Start the FastAPI Backend:**
   ```bash
   uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
   ```
   - Swagger Interactive Documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   - Alternative ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

### Step 3: Frontend Setup

1. **Navigate to Frontend Directory:**
   ```bash
   cd frontend
   ```

2. **Install Node Dependencies:**
   ```bash
   npm install
   ```

3. **Start Vite Development Server:**
   ```bash
   npm run dev
   ```
   - Access the application: [http://localhost:5173](http://localhost:5173)

---

## ?? Testing & Quality Assurance

Run the test suite spanning data preprocessing, routing admissibility, and API endpoints:

```bash
# From the project root (with venv activated)
pytest tests/ -v
```

### Test Coverage Highlights:
- `tests/test_preprocessing.py`: Validates cleaning routines, absence of target leakage, category encodings, and synthetic boundary constraints.
- `tests/test_routing.py`: Confirms Haversine calculations, graph connectivity, A* path finding, heuristic admissibility ($h \le c^*$), and congestion penalty divergence.
- `tests/test_api.py`: Tests `/api/health`, `/api/predict-congestion` (with schema boundaries and invalid payloads), `/api/routes`, `/api/traffic/summary`, and `/api/model/metrics`.

---

## ?? API Specification

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | `GET` | System health, model readiness, road network status. |
| `/api/predict-congestion` | `POST` | Accepts traffic parameters; returns predicted congestion (`LOW`, `MEDIUM`, `HIGH`) and probability distribution. |
| `/api/routes` | `POST` | Accepts source & destination coordinates; computes A* route and alternative paths with travel time and congestion penalties. |
| `/api/traffic/summary` | `GET` | Aggregated metrics for analytics charts (volume by day, speed by level, top hotspots). |
| `/api/model/metrics` | `GET` | Returns genuine evaluation metrics (accuracy, F1, confusion matrix, feature importances). |

---

## ?? Known Limitations
1. **Granularity:** The Kaggle dataset provides area-level observations rather than real-time telemetry from every individual street segment.
2. **Static vs. Live:** This platform operates on historical statistical models and does not stream live CCTV or GPS probe feeds.
3. **Graph Boundary:** The road network subgraph focuses primarily on major arterial clusters in Bengaluru (e.g., Koramangala, Indiranagar, Electronic City, Silk Board).
