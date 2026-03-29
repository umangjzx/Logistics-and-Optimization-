"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    INDIA LOGISTICS DELIVERY OPTIMIZER                       ║
║          Real-world dataset · 100 Indian cities · 3 Delivery Agents        ║
║          Algorithm: Priority-Weighted Greedy Min-Heap Balancing (LPT)      ║
╚══════════════════════════════════════════════════════════════════════════════╝

APPROACH:
─────────
1. READ   — Parse CSV with validation (Location_ID, Distance_km, Priority required)
2. SORT   — Two-level sort: Priority rank (High→Med→Low), then Distance DESC (LPT)
3. ASSIGN — Greedy Min-Heap: always give next delivery to least-loaded agent
4. BALANCE— LPT heuristic guarantees ≤ (4/3 − 1/3k) × OPT for k agents
5. OUTPUT — Delivery plan as CSV + JSON + rich console report + HTML dashboard data

COMPLEXITY: O(n log k) where n = deliveries, k = agents
DATASET:    100 major Indian cities, Haversine distances from New Delhi warehouse

Author : Umang Jaiswal
Version: 2.0  (Enhanced Edition — 100 cities, zones, fuel estimation, analytics)
"""

import argparse
import csv
import heapq
import json
import os
import sys
import math
import time
from collections import defaultdict
from typing import Any

# ─── CONFIGURATION ──────────────────────────────────────────────────────────

PRIORITY_ORDER: dict[str, int] = {"High": 1, "Medium": 2, "Low": 3}
PRIORITY_LABELS: dict[int, str] = {1: "High", 2: "Medium", 3: "Low"}
NUM_AGENTS: int = 3
INPUT_FILE: str = "india_deliveries.csv"
OUTPUT_CSV: str = "delivery_plan.csv"
OUTPUT_JSON: str = "delivery_plan.json"

# Fuel cost estimation constants
FUEL_RATE_PER_KM: float = 8.50   # INR per km (diesel delivery van avg)
AVG_SPEED_KMPH: float = 45.0     # Average speed in India for delivery vehicles

# Geographic zone classification (approximate bounding boxes)
ZONES: dict[str, dict[str, tuple[float, float]]] = {
    "North":   {"lat": (28.0, 37.0), "lon": (73.0, 82.0)},
    "South":   {"lat": (8.0, 16.0),  "lon": (73.0, 81.0)},
    "East":    {"lat": (20.0, 28.0), "lon": (83.0, 95.0)},
    "West":    {"lat": (19.0, 24.0), "lon": (68.0, 76.0)},
    "Central": {"lat": (20.0, 28.0), "lon": (75.0, 83.0)},
}

# ─── TERMINAL COLOURS ──────────────────────────────────────────────────────

RESET = "\033[0m"
BOLD  = "\033[1m"
DIM   = "\033[2m"
RED   = "\033[91m"
YEL   = "\033[93m"
GRN   = "\033[92m"
CYN   = "\033[96m"
MAG   = "\033[95m"
BLU   = "\033[94m"
WHT   = "\033[97m"
AGENT_COLORS = [CYN, MAG, YEL]


# ═══════════════════════════════════════════════════════════════════════════
#  1. DATA LOADING & VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

def load_deliveries(filepath: str) -> list[dict[str, Any]]:
    """
    Read delivery data from CSV file with comprehensive validation.

    Required columns: Location_ID, Distance_km, Priority
    Optional columns: City, Latitude, Longitude, Package_Weight_kg, Delivery_Deadline

    Args:
        filepath: Path to the input CSV file.

    Returns:
        List of delivery dictionaries with validated data.

    Raises:
        FileNotFoundError: If the CSV file doesn't exist.
        ValueError: If required columns are missing or data is invalid.
    """
    required_columns = {"Location_ID", "Distance_km", "Priority"}
    optional_columns = ["City", "Latitude", "Longitude", "Package_Weight_kg", "Delivery_Deadline"]
    deliveries: list[dict[str, Any]] = []

    with open(filepath, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        headers = set(reader.fieldnames or [])

        # Validate required columns exist
        missing = required_columns - headers
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        for row_num, row in enumerate(reader, start=2):
            # ── Validate Priority ──
            priority = row["Priority"].strip().capitalize()
            if priority not in PRIORITY_ORDER:
                raise ValueError(
                    f"Row {row_num}: Invalid priority '{priority}'. "
                    f"Must be one of: High, Medium, Low."
                )

            # ── Validate Distance ──
            try:
                distance = float(row["Distance_km"])
            except (ValueError, TypeError):
                raise ValueError(
                    f"Row {row_num}: Distance_km '{row['Distance_km']}' is not a valid number."
                )
            if distance < 0:
                raise ValueError(f"Row {row_num}: Distance cannot be negative ({distance}).")

            # ── Build delivery entry ──
            entry: dict[str, Any] = {
                "Location_ID": row["Location_ID"].strip(),
                "Distance_km": distance,
                "Priority": priority,
            }

            # ── Parse optional fields ──
            for col in optional_columns:
                entry[col] = row.get(col, "").strip() if row.get(col) else ""

            # ── Parse numeric optionals ──
            if entry.get("Latitude"):
                try:
                    entry["Latitude"] = float(entry["Latitude"])
                except ValueError:
                    entry["Latitude"] = 0.0
            if entry.get("Longitude"):
                try:
                    entry["Longitude"] = float(entry["Longitude"])
                except ValueError:
                    entry["Longitude"] = 0.0
            if entry.get("Package_Weight_kg"):
                try:
                    entry["Package_Weight_kg"] = float(entry["Package_Weight_kg"])
                except ValueError:
                    entry["Package_Weight_kg"] = 0.0

            deliveries.append(entry)

    return deliveries


# ═══════════════════════════════════════════════════════════════════════════
#  2. SORTING — TWO-LEVEL PRIORITY + DISTANCE
# ═══════════════════════════════════════════════════════════════════════════

def sort_deliveries(deliveries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Sort deliveries using a two-level key for optimal LPT assignment:

    Level 1: Priority rank — High (1) → Medium (2) → Low (3)
             Ensures high-priority deliveries are assigned first.

    Level 2: Distance DESCENDING within each priority group.
             This is the Largest-Processing-Time (LPT) heuristic —
             assigning longest jobs first produces better load balance.

    Args:
        deliveries: List of delivery dictionaries.

    Returns:
        New sorted list (original list is not modified).
    """
    return sorted(
        deliveries,
        key=lambda d: (PRIORITY_ORDER[d["Priority"]], -d["Distance_km"])
    )


# ═══════════════════════════════════════════════════════════════════════════
#  3. ASSIGNMENT — GREEDY MIN-HEAP (LPT ALGORITHM)
# ═══════════════════════════════════════════════════════════════════════════

def assign_deliveries(
    sorted_deliveries: list[dict[str, Any]],
    num_agents: int = NUM_AGENTS
) -> tuple[dict[int, list[dict]], dict[int, float]]:
    """
    Assign deliveries to agents using the Greedy Min-Heap algorithm.

    Strategy:
    ─────────
    • Maintain a min-heap of (total_distance, agent_id) pairs.
    • For each delivery (processed in LPT order), pop the least-loaded agent,
      assign the delivery to that agent, update total, and push back.

    Complexity: O(n log k) — n deliveries, k agents
    Approximation: ≤ (4/3 − 1/(3k)) × OPT for identical-machine scheduling

    Why not brute force?
    ─────────────────────
    Optimal assignment is NP-hard (partition problem variant).
    For 3 agents and 100 deliveries: 3^100 ≈ 5 × 10^47 combinations.
    LPT achieves near-optimal balance in O(n log k) time.

    Args:
        sorted_deliveries: Pre-sorted list of deliveries (by priority + distance).
        num_agents: Number of delivery agents (default: 3).

    Returns:
        Tuple of (assignments dict, totals dict):
        - assignments: {agent_id: [list of deliveries]}
        - totals: {agent_id: total_distance_km}
    """
    # Initialize min-heap: (total_distance, agent_id)
    heap: list[tuple[float, int]] = [(0.0, i) for i in range(1, num_agents + 1)]
    heapq.heapify(heap)

    assignments: dict[int, list[dict]] = {i: [] for i in range(1, num_agents + 1)}
    totals: dict[int, float] = {i: 0.0 for i in range(1, num_agents + 1)}

    for delivery in sorted_deliveries:
        # Pop agent with minimum total distance
        current_total, agent_id = heapq.heappop(heap)

        # Assign delivery to this agent
        assignments[agent_id].append(delivery)
        totals[agent_id] = current_total + delivery["Distance_km"]

        # Push updated total back into heap
        heapq.heappush(heap, (totals[agent_id], agent_id))

    return assignments, totals


# ═══════════════════════════════════════════════════════════════════════════
#  4. ANALYTICS & METRICS
# ═══════════════════════════════════════════════════════════════════════════

def classify_zone(lat: float, lon: float) -> str:
    """Classify a city into a geographic zone based on coordinates."""
    if not lat or not lon:
        return "Unknown"
    for zone_name, bounds in ZONES.items():
        lat_range = bounds["lat"]
        lon_range = bounds["lon"]
        if lat_range[0] <= lat <= lat_range[1] and lon_range[0] <= lon <= lon_range[1]:
            return zone_name
    # Northeast or island territories
    if lat > 22 and lon > 88:
        return "Northeast"
    if lat < 15 and lon > 90:
        return "Islands"
    return "Other"


def compute_analytics(
    assignments: dict[int, list[dict]],
    totals: dict[int, float],
    num_agents: int = NUM_AGENTS
) -> dict[str, Any]:
    """
    Compute comprehensive analytics for the delivery plan.

    Returns dictionary with:
    - overall metrics (total distance, imbalance, delivery count)
    - per-agent breakdowns (priority counts, zones, weights)
    - fuel cost estimations
    - efficiency scores
    """
    overall_distance = sum(totals.values())
    distances = list(totals.values())
    imbalance_km = max(distances) - min(distances)
    imbalance_pct = (imbalance_km / overall_distance * 100) if overall_distance else 0

    # Per-agent analytics
    agent_analytics: list[dict] = []
    all_deliveries: list[dict] = []

    for agent_id in sorted(assignments.keys()):
        stops = assignments[agent_id]
        priority_counts: dict[str, int] = defaultdict(lambda: 0)
        zone_counts: dict[str, int] = defaultdict(lambda: 0)
        total_weight: float = 0.0

        for d in stops:
            priority_counts[d["Priority"]] += 1
            lat = d.get("Latitude", 0)
            lon = d.get("Longitude", 0)
            zone = classify_zone(lat, lon) if lat and lon else "Unknown"
            d["Zone"] = zone
            zone_counts[zone] += 1
            
            try:
                wt = float(d.get("Package_Weight_kg", 0.0) or 0.0)
                total_weight += wt
            except (ValueError, TypeError):
                pass
                
            all_deliveries.append({**d, "agent_id": agent_id})

        fuel_cost = totals[agent_id] * FUEL_RATE_PER_KM
        est_hours = totals[agent_id] / AVG_SPEED_KMPH

        agent_analytics.append({
            "agent_id": agent_id,
            "stops": len(stops),
            "total_distance": round(totals[agent_id], 1),
            "share_pct": round(totals[agent_id] / overall_distance * 100, 1),
            "priority_counts": dict(priority_counts),
            "zone_counts": dict(zone_counts),
            "total_weight": round(total_weight, 1),
            "fuel_cost_inr": round(fuel_cost, 0),
            "est_travel_hours": round(est_hours, 1),
        })

    # Zone summary across all deliveries
    zone_summary: dict[str, int] = defaultdict(lambda: 0)
    for d in all_deliveries:
        zone_summary[d.get("Zone", "Unknown")] += 1

    return {
        "total_deliveries": sum(len(v) for v in assignments.values()),
        "total_distance_km": round(overall_distance, 1),
        "imbalance_km": round(imbalance_km, 1),
        "imbalance_pct": round(imbalance_pct, 2),
        "ideal_per_agent": round(overall_distance / num_agents, 1) if num_agents else 0.0,
        "total_fuel_cost_inr": round(overall_distance * FUEL_RATE_PER_KM, 0),
        "total_est_hours": round(overall_distance / AVG_SPEED_KMPH, 1),
        "agent_analytics": agent_analytics,
        "zone_summary": dict(zone_summary),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  5. CONSOLE OUTPUT — RICH FORMATTED REPORT
# ═══════════════════════════════════════════════════════════════════════════

def _pri_color(priority: str) -> str:
    """Return colored priority label for terminal display."""
    colors = {
        "High":   f"{RED}High  {RESET}",
        "Medium": f"{YEL}Medium{RESET}",
        "Low":    f"{GRN}Low   {RESET}",
    }
    return colors.get(priority, priority)


def print_plan(
    assignments: dict[int, list[dict]],
    totals: dict[int, float],
    analytics: dict[str, Any]
) -> None:
    """Print a comprehensive delivery optimization report to the console."""
    overall = analytics["total_distance_km"]

    # ── Header ──
    print(f"\n{BOLD}{CYN}{'═' * 78}{RESET}")
    print(f"{BOLD}{CYN}  ╔══════════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYN}  ║         INDIA LOGISTICS — DELIVERY OPTIMIZATION REPORT              ║{RESET}")
    print(f"{BOLD}{CYN}  ║         100 Cities · 3 Agents · LPT Min-Heap Algorithm              ║{RESET}")
    print(f"{BOLD}{CYN}  ╚══════════════════════════════════════════════════════════════════════╝{RESET}")
    print(f"{BOLD}{CYN}{'═' * 78}{RESET}")

    # ── Summary KPIs ──
    print(f"\n  {BOLD}{WHT}OVERVIEW{RESET}")
    print(f"  {'─' * 50}")
    print(f"  Warehouse       : {CYN}New Delhi{RESET}")
    print(f"  Total Deliveries: {BOLD}{analytics['total_deliveries']}{RESET}")
    print(f"  Total Distance  : {BOLD}{overall:,.1f} km{RESET}")
    print(f"  Load Imbalance  : {BOLD}{GRN}{analytics['imbalance_pct']:.2f}%{RESET} "
          f"({analytics['imbalance_km']:.1f} km gap)")
    print(f"  Ideal per Agent : {analytics['ideal_per_agent']:,.1f} km")
    print(f"  Est. Fuel Cost  : {YEL}₹{analytics['total_fuel_cost_inr']:,.0f}{RESET}")
    print(f"  Est. Travel Time: {analytics['total_est_hours']:.1f} hours total")
    print(f"  Algorithm       : Priority-Weighted Greedy Min-Heap (LPT)")
    print(f"  Complexity      : O(n log k) — n={analytics['total_deliveries']}, k={len(assignments)}")

    # ── Per-Agent Detail ──
    for agent_data in analytics["agent_analytics"]:
        aid = agent_data["agent_id"]
        ac = AGENT_COLORS[aid - 1]
        stops = assignments[aid]
        pri = agent_data["priority_counts"]

        print(f"\n{BOLD}{ac}{'─' * 78}{RESET}")
        print(f"{BOLD}{ac}  AGENT {aid}{RESET}   "
              f"Stops: {agent_data['stops']}   "
              f"Distance: {agent_data['total_distance']:,.1f} km   "
              f"Share: {agent_data['share_pct']}%   "
              f"Weight: {agent_data['total_weight']:.1f} kg")
        print(f"  Priority: {RED}H:{pri.get('High', 0)}{RESET}  "
              f"{YEL}M:{pri.get('Medium', 0)}{RESET}  "
              f"{GRN}L:{pri.get('Low', 0)}{RESET}   "
              f"Fuel: ₹{agent_data['fuel_cost_inr']:,.0f}   "
              f"Travel: ~{agent_data['est_travel_hours']:.0f}h")
        print(f"  {'─' * 78}")
        print(f"  {'#':<4}{'ID':<10}{'City':<22}{'Priority':<16}"
              f"{'Dist(km)':>9}{'Weight':>8}{'Deadline':>13}")
        print(f"  {'─' * 4} {'─' * 9} {'─' * 21} {'─' * 15} "
              f"{'─' * 9} {'─' * 7} {'─' * 12}")

        for n, d in enumerate(stops, 1):
            city = d.get("City", d["Location_ID"])[:20]
            weight_str = str(d.get("Package_Weight_kg", "─"))
            if isinstance(d.get("Package_Weight_kg"), float):
                weight_str = f"{d['Package_Weight_kg']:.1f}"
            deadline = d.get("Delivery_Deadline", "─")
            print(f"  {n:<4}{d['Location_ID']:<10}{city:<22}"
                  f"{_pri_color(d['Priority']):<16}"
                  f"{d['Distance_km']:>9.1f}{weight_str:>8}{deadline:>13}")

    # ── Load Balance Visualization ──
    bar_width = 40
    print(f"\n{BOLD}{CYN}{'═' * 78}{RESET}")
    print(f"{BOLD}  LOAD BALANCE REPORT{RESET}")
    print(f"  {'─' * 60}")

    max_dist = max(totals.values())
    for agent_data in analytics["agent_analytics"]:
        aid = agent_data["agent_id"]
        ac = AGENT_COLORS[aid - 1]
        dist = agent_data["total_distance"]
        share = agent_data["share_pct"]
        bar = int(share / 100 * bar_width)
        print(f"  Agent {aid}  {ac}{'█' * bar}{RESET}{'░' * (bar_width - bar)}  "
              f"{dist:>8,.1f} km  {share:.1f}%")

    print(f"\n  Total Distance : {overall:,.1f} km")
    print(f"  Max Imbalance  : {analytics['imbalance_km']:.1f} km "
          f"({GRN}{analytics['imbalance_pct']:.2f}%{RESET})")
    print(f"  Ideal per Agent: {analytics['ideal_per_agent']:,.1f} km")

    # ── Zone Coverage ──
    print(f"\n{BOLD}  ZONE COVERAGE{RESET}")
    print(f"  {'─' * 40}")
    for zone, count in sorted(analytics["zone_summary"].items(), key=lambda x: -x[1]):
        zone_bar = '█' * count
        print(f"  {zone:<12} {GRN}{zone_bar}{RESET} {count}")

    print(f"\n{BOLD}{CYN}{'═' * 78}{RESET}\n")


# ═══════════════════════════════════════════════════════════════════════════
#  6. FILE OUTPUTS — CSV & JSON
# ═══════════════════════════════════════════════════════════════════════════

def save_csv(
    assignments: dict[int, list[dict]],
    totals: dict[int, float],
    filepath: str
) -> None:
    """
    Save the delivery plan as a structured CSV file.

    CSV columns: Agent_ID, Stop_Number, Location_ID, City, Priority,
                 Distance_km, Package_Weight_kg, Delivery_Deadline,
                 Zone, Agent_Total_Distance_km
    """
    fields = [
        "Agent_ID", "Stop_Number", "Location_ID", "City", "Priority",
        "Distance_km", "Package_Weight_kg", "Delivery_Deadline",
        "Zone", "Agent_Total_Distance_km"
    ]
    rows: list[dict] = []

    for agent_id in sorted(assignments.keys()):
        for stop_num, delivery in enumerate(assignments[agent_id], start=1):
            rows.append({
                "Agent_ID": f"Agent_{agent_id}",
                "Stop_Number": stop_num,
                "Location_ID": delivery["Location_ID"],
                "City": delivery.get("City", ""),
                "Priority": delivery["Priority"],
                "Distance_km": delivery["Distance_km"],
                "Package_Weight_kg": delivery.get("Package_Weight_kg", ""),
                "Delivery_Deadline": delivery.get("Delivery_Deadline", ""),
                "Zone": delivery.get("Zone", ""),
                "Agent_Total_Distance_km": round(totals[agent_id], 1),
            })

    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"  ✅ CSV saved  → {filepath}")


def save_json(
    assignments: dict[int, list[dict]],
    totals: dict[int, float],
    analytics: dict[str, Any],
    filepath: str
) -> None:
    """
    Save the delivery plan as a comprehensive JSON file.
    Includes all analytics, zone data, fuel costs, and efficiency metrics.
    """
    overall = sum(totals.values())

    # Build agent payloads
    agents_payload: list[dict] = []
    for agent_id in sorted(assignments.keys()):
        deliveries_clean: list[dict] = []
        for d in assignments[agent_id]:
            entry = {
                "location_id": d["Location_ID"],
                "city": d.get("City", ""),
                "latitude": d.get("Latitude", 0),
                "longitude": d.get("Longitude", 0),
                "distance_km": d["Distance_km"],
                "priority": d["Priority"],
                "package_weight_kg": d.get("Package_Weight_kg", 0),
                "delivery_deadline": d.get("Delivery_Deadline", ""),
                "zone": d.get("Zone", "Unknown"),
            }
            deliveries_clean.append(entry)

        agent_data = next(
            (a for a in analytics["agent_analytics"] if a["agent_id"] == agent_id),
            {}
        )

        agents_payload.append({
            "agent_id": f"Agent_{agent_id}",
            "total_stops": len(assignments[agent_id]),
            "total_distance_km": round(totals[agent_id], 1),
            "share_pct": round(totals[agent_id] / overall * 100, 1),
            "total_weight_kg": agent_data.get("total_weight", 0),
            "fuel_cost_inr": agent_data.get("fuel_cost_inr", 0),
            "est_travel_hours": agent_data.get("est_travel_hours", 0),
            "priority_breakdown": agent_data.get("priority_counts", {}),
            "zone_breakdown": agent_data.get("zone_counts", {}),
            "deliveries": deliveries_clean,
        })

    payload: dict = {
        "metadata": {
            "title": "India Logistics Delivery Optimization Plan",
            "warehouse": "New Delhi",
            "algorithm": "Priority-Weighted Greedy Min-Heap (LPT)",
            "complexity": "O(n log k)",
            "num_agents": NUM_AGENTS,
            "generated_by": "delivery_optimizer.py v2.0",
        },
        "summary": {
            "total_deliveries": analytics["total_deliveries"],
            "total_distance_km": analytics["total_distance_km"],
            "max_imbalance_km": analytics["imbalance_km"],
            "imbalance_pct": analytics["imbalance_pct"],
            "ideal_per_agent_km": analytics["ideal_per_agent"],
            "total_fuel_cost_inr": analytics["total_fuel_cost_inr"],
            "total_est_hours": analytics["total_est_hours"],
            "zone_coverage": analytics["zone_summary"],
        },
        "agents": agents_payload,
    }

    with open(filepath, "w", encoding="utf-8") as jsonfile:
        json.dump(payload, jsonfile, indent=2, ensure_ascii=False)

    print(f"  ✅ JSON saved → {filepath}")


# ═══════════════════════════════════════════════════════════════════════════
#  7. MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    """
    Main execution pipeline:
    1. Load deliveries from CSV
    2. Sort by priority + distance (LPT)
    3. Assign to agents via min-heap
    4. Compute analytics
    5. Print report + save outputs
    """
    # Enable ANSI escape sequences on Windows
    if os.name == 'nt':
        os.system("")

    parser = argparse.ArgumentParser(description="India Logistics Delivery Optimizer")
    parser.add_argument("--input", "-i", type=str, default=INPUT_FILE, help="Path to input CSV file")
    parser.add_argument("--out-csv", "-c", type=str, default=OUTPUT_CSV, help="Path to output CSV file")
    parser.add_argument("--out-json", "-j", type=str, default=OUTPUT_JSON, help="Path to output JSON file")
    parser.add_argument("--agents", "-a", type=int, default=NUM_AGENTS, help="Number of delivery agents")
    args = parser.parse_args()

    input_file = args.input
    output_csv = args.out_csv
    output_json = args.out_json
    num_agents = args.agents

    start_time = time.perf_counter()

    try:
        # ── Step 1: Load ──
        print(f"\n  📂 Loading deliveries from: {input_file}")
        deliveries = load_deliveries(input_file)
        print(f"     Loaded {len(deliveries)} deliveries successfully.")

        # ── Step 2: Sort ──
        sorted_deliveries = sort_deliveries(deliveries)
        print(f"  🔀 Sorted by Priority (H→M→L) + Distance (DESC — LPT heuristic)")

        # ── Step 3: Assign ──
        assignments, totals = assign_deliveries(sorted_deliveries, num_agents)
        print(f"  📦 Assigned {len(deliveries)} deliveries to {num_agents} agents via Min-Heap")

        # ── Step 4: Analytics ──
        analytics = compute_analytics(assignments, totals, num_agents)

        elapsed = time.perf_counter() - start_time
        print(f"  ⏱️  Optimization completed in {elapsed * 1000:.2f} ms")

        # ── Step 5: Output ──
        print_plan(assignments, totals, analytics)
        save_csv(assignments, totals, output_csv)
        save_json(assignments, totals, analytics, output_json)

        # ── Final summary ──
        print(f"\n  {'═' * 60}")
        print(f"  {BOLD}{GRN}✅ OPTIMIZATION COMPLETE{RESET}")
        print(f"  {'─' * 60}")
        print(f"  Deliveries : {analytics['total_deliveries']}")
        print(f"  Agents     : {num_agents}")
        print(f"  Distance   : {analytics['total_distance_km']:,.1f} km")
        print(f"  Imbalance  : {analytics['imbalance_km']:.1f} km "
              f"({GRN}{analytics['imbalance_pct']:.2f}%{RESET})")
        print(f"  Fuel Cost  : ₹{analytics['total_fuel_cost_inr']:,.0f}")
        print(f"  Runtime    : {elapsed * 1000:.2f} ms")
        print(f"  {'═' * 60}\n")

    except FileNotFoundError:
        print(f"\n  {BOLD}{RED}❌ ERROR: Input file '{input_file}' not found.{RESET}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n  {BOLD}{RED}❌ ERROR: {str(e)}{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
