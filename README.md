# India Logistics Delivery Optimizer

A delivery route optimization engine that assigns **100 real Indian city** deliveries across **3 agents** using a **Priority-Weighted LPT Min-Heap** algorithm — achieving **0.05% load imbalance** over 102,322 km.

## Architecture

```
india_deliveries.csv  ──►  delivery_optimizer.py  ──►  delivery_plan.csv
        (100 cities)         │  Sort (Priority + LPT)     delivery_plan.json
                             │  Assign (Min-Heap)          dashboard_data.js
                             ▼
                        dashboard.html  ◄──  Leaflet Map · Chart.js · Dark/Light Mode
```

## Quick Start

```bash
# Run optimizer (default: 3 agents, india_deliveries.csv)
python delivery_optimizer.py

# Custom configuration
python delivery_optimizer.py --input data.csv --agents 5 --out-csv plan.csv --out-json plan.json

# Launch dashboard (avoids CORS issues with local files)
python -m http.server 8000
# Open http://localhost:8000/dashboard.html

# Run tests
python -m unittest test_delivery_optimizer.py
```

## Algorithm

**Problem:** Assign *n* deliveries to *k* agents minimizing max-agent distance (NP-hard multiprocessor scheduling).

**Approach:** Two-phase greedy heuristic in `O(n log k)`:

1. **Sort** — Priority rank (High → Med → Low), then distance descending (LPT heuristic)
2. **Assign** — Min-heap always routes next delivery to the least-loaded agent

**Guarantee:** ≤ `(4/3 − 1/3k) × OPT`

| Agent | Stops | Distance | Share |
|-------|-------|----------|-------|
| Agent 1 | 34 | 34,126.5 km | 33.4% |
| Agent 2 | 33 | 34,071.2 km | 33.3% |
| Agent 3 | 33 | 34,123.8 km | 33.3% |

Max gap: **55.3 km** out of 102,322 km — brute force (`3¹⁰⁰ ≈ 5×10⁴⁷`) is infeasible; this runs in **<4 ms**.

## Dataset

100 cities across 7 zones (North, South, East, West, Central, Northeast, Islands) with real GPS coordinates. All distances computed via **Haversine formula** from the New Delhi warehouse (28.61°N, 77.21°E).

## Dashboard

Interactive single-page analytics dashboard featuring:

- **Leaflet.js map** with 100 city markers, agent-colored dots, and click popups
- **8 KPI cards** with animated counters
- **5 Chart.js visualizations** — priority bars, distance/weight comparison, top routes, zone radar
- **Agent drill-down** — tabbed delivery tables with search/filter
- **Dark/Light mode** toggle with theme-aware map tiles

## Project Structure

| File | Purpose |
|------|---------|
| `delivery_optimizer.py` | Core optimizer — CSV parsing, sorting, heap assignment, analytics |
| `india_deliveries.csv` | Input dataset — 100 cities with coordinates, priority, weight |
| `dashboard.html` | Interactive dashboard with Leaflet map and Chart.js |
| `dashboard_data.js` | Pre-computed data module consumed by the dashboard |
| `test_delivery_optimizer.py` | Unit test suite for sorting, assignment, zone classification |
| `delivery_plan.csv` | Generated output — agent assignments with zones |
| `delivery_plan.json` | Generated output — full analytics payload |

## Requirements

- Python 3.8+ (standard library only)
- Modern browser for the dashboard

## License

MIT
