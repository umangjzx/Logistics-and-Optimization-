<![CDATA[<div align="center">

# 🚚 India Logistics Delivery Optimizer

**Intelligent route optimization for last-mile delivery across India**

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Algorithm](https://img.shields.io/badge/Algorithm-LPT_Min--Heap-FF6F00?style=for-the-badge)
![Cities](https://img.shields.io/badge/Cities-100-00C853?style=for-the-badge)
![Imbalance](https://img.shields.io/badge/Load_Imbalance-0.05%25-7C4DFF?style=for-the-badge)
![Dashboard](https://img.shields.io/badge/Dashboard-Leaflet_+_Chart.js-0078D4?style=for-the-badge)

*Assigns 100 real Indian city deliveries across 3 agents with near-perfect load balance — 55.3 km gap over 102,322 km total distance.*

---

</div>

## 🏗️ System Architecture

```
                          ┌─────────────────────────────────────┐
                          │       delivery_optimizer.py          │
                          │                                     │
  india_deliveries.csv ──►│  1. Parse & Validate CSV            │──► delivery_plan.csv
     (100 cities)         │  2. Two-Level Sort (Priority + LPT) │──► delivery_plan.json
                          │  3. Min-Heap Agent Assignment       │──► dashboard_data.js
                          │  4. Analytics & Zone Classification  │
                          └──────────────┬──────────────────────┘
                                         │
                                         ▼
                          ┌─────────────────────────────────────┐
                          │         dashboard.html               │
                          │                                     │
                          │  ● Leaflet.js Interactive Map       │
                          │  ● Chart.js Visualizations (×5)     │
                          │  ● Agent Drill-down Tables          │
                          │  ● Dark / Light Theme Toggle        │
                          └─────────────────────────────────────┘
```

---

## ⚡ Quick Start

```bash
# 1. Run the optimizer
python delivery_optimizer.py

# 2. Launch the dashboard
python -m http.server 8000
# → Open http://localhost:8000/dashboard.html

# 3. Run tests
python -m unittest test_delivery_optimizer.py
```

### CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--input`, `-i` | `india_deliveries.csv` | Input dataset path |
| `--out-csv`, `-c` | `delivery_plan.csv` | Output CSV path |
| `--out-json`, `-j` | `delivery_plan.json` | Output JSON path |
| `--agents`, `-a` | `3` | Number of delivery agents |

```bash
# Example: 5 agents with custom paths
python delivery_optimizer.py --agents 5 --input my_data.csv --out-csv my_plan.csv
```

---

## 🧠 Algorithm

> **Problem:** Assign *n* weighted deliveries to *k* agents minimizing the maximum agent workload — a variant of the NP-hard multiprocessor scheduling problem.

### Two-Phase Greedy Heuristic — `O(n log k)`

```
Phase 1: SORT
┌─────────────────────────────────────────────────────┐
│  Primary Key   →  Priority Rank (High=1, Med=2, Low=3)  │
│  Secondary Key →  Distance DESCENDING (LPT heuristic)   │
└─────────────────────────────────────────────────────┘

Phase 2: ASSIGN (Min-Heap)
┌─────────────────────────────────────────────────────┐
│  heap = [(0, Agent_1), (0, Agent_2), (0, Agent_3)]  │
│  for each delivery in sorted order:                  │
│      pop least-loaded agent                          │
│      assign delivery → update total → push back      │
└─────────────────────────────────────────────────────┘
```

### Why LPT + Min-Heap?

| Approach | Time | Accuracy |
|----------|------|----------|
| **Brute Force** | `3¹⁰⁰ ≈ 5×10⁴⁷` combinations | Optimal but infeasible |
| **LPT Min-Heap** | **< 4 ms** | ≤ `(4/3 − 1/3k) × OPT` |

### Results

| Agent | Stops | Distance (km) | Load Share |
|-------|-------|---------------|------------|
| Agent 1 | 34 | 34,126.5 | 33.4% |
| Agent 2 | 33 | 34,071.2 | 33.3% |
| Agent 3 | 33 | 34,123.8 | 33.3% |
| **Total** | **100** | **102,321.5** | — |

```
Agent 1  ████████████████████████████████████████  34,126.5 km
Agent 2  ████████████████████████████████████████  34,071.2 km
Agent 3  ████████████████████████████████████████  34,123.8 km
         ─────────────────────────────────────────
         Max gap: 55.3 km (0.05% imbalance)
```

---

## 🗺️ Dataset — 100 Indian Cities

All distances computed using the **Haversine formula** from the **New Delhi warehouse** (28.61°N, 77.21°E).

| Zone | Cities | Examples |
|------|--------|----------|
| North | 18 | Delhi, Jaipur, Chandigarh, Shimla, Srinagar |
| South | 21 | Chennai, Bangalore, Kochi, Madurai |
| East | 19 | Kolkata, Guwahati, Bhubaneswar, Ranchi |
| West | 11 | Mumbai, Ahmedabad, Pune, Surat |
| Central | 19 | Nagpur, Bhopal, Indore, Lucknow |
| Northeast | 4 | Shillong, Imphal, Aizawl, Silchar |
| Islands | 1 | Port Blair (Andaman) |

**CSV Schema:** `Location_ID` · `City` · `Latitude` · `Longitude` · `Distance_km` · `Priority` · `Package_Weight_kg` · `Delivery_Deadline`

---

## 📊 Dashboard Features

| Feature | Technology | Description |
|---------|------------|-------------|
| **Interactive Map** | Leaflet.js + CartoDB tiles | 100 city markers with click popups, agent-colored dots, auto-fit bounds |
| **KPI Cards** | Vanilla JS | 8 animated counters — deliveries, distance, imbalance, fuel, weight, hours |
| **Priority Chart** | Chart.js | Stacked bar comparing High/Medium/Low across agents |
| **Distance & Weight** | Chart.js | Per-agent comparison bars |
| **Top 15 Routes** | Chart.js | Horizontal bar of longest delivery routes |
| **Zone Radar** | Chart.js | Radar chart of geographic zone coverage per agent |
| **Agent Tables** | Vanilla JS | Tabbed delivery tables with live search/filter |
| **Theme Toggle** | CSS Variables | Dark ↔ Light mode with theme-aware map tiles |

---

## 📈 Key Metrics

| Metric | Value |
|--------|-------|
| Total Distance | 102,321.5 km |
| Load Imbalance | 0.05% (55.3 km) |
| Total Weight | 1,165.9 kg |
| Est. Fuel Cost | ₹8,69,733 @ ₹8.50/km |
| Est. Travel Time | 2,273.8 hours @ 45 km/h |
| Optimization Runtime | < 4 ms |

---

## 📁 Project Structure

```
task CIT/
├── delivery_optimizer.py       # Core engine — parse, sort, assign, output
├── india_deliveries.csv        # 100-city input dataset
├── dashboard.html              # Interactive analytics dashboard
├── dashboard_data.js           # Pre-computed data for dashboard
├── test_delivery_optimizer.py  # Unit tests (sorting, assignment, zones)
├── delivery_plan.csv           # Generated — agent assignments
├── delivery_plan.json          # Generated — full analytics payload
└── README.md
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.8+ (standard library only — zero dependencies) |
| **Mapping** | Leaflet.js 1.9.4 + CartoDB Dark/Light tiles |
| **Charts** | Chart.js 4.4.1 |
| **Styling** | CSS Variables, Space Grotesk + JetBrains Mono fonts |
| **Testing** | Python `unittest` |

---

## 📝 License

MIT

---

<div align="center">
  <sub>Built for the CIT Logistics Optimization Task</sub>
</div>
]]>
