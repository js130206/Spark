"""
Data Analytics, Inefficiency Detection, Rainwater Harvesting Simulator,
and Stakeholder Report Export module.
"""
import csv
import os
import sqlite3
from datetime import datetime
from database import get_connection, calculate_water_bill
from crud import list_all_premises, get_premise_by_id
from validators import get_positive_int, get_positive_float

# Selangor Domestic Water Conservation Target: 180 Liters/Capita/Day (LCD)
# Alert threshold set at 230 LCD (~6.9 m3 per occupant per 30-day month)
DOMESTIC_LCD_LIMIT = 230.0
RUNOFF_COEFFICIENT = 0.85  # Standard pitched metal/tile roof runoff efficiency


def show_sector_statistics() -> list[sqlite3.Row]:
    """Compute and display aggregate water consumption metrics grouped by sector."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    p.sector,
                    COUNT(w.log_id) AS total_logs,
                    ROUND(AVG(w.consumption_m3), 2) AS avg_m3,
                    ROUND(MIN(w.consumption_m3), 2) AS min_m3,
                    ROUND(MAX(w.consumption_m3), 2) AS max_m3,
                    ROUND(SUM(w.consumption_m3), 2) AS total_m3,
                    ROUND(SUM(w.cost_rm), 2) AS total_cost_rm
                FROM water_logs w
                JOIN premises p ON w.premise_id = p.premise_id
                GROUP BY p.sector;
            """)
            rows = cursor.fetchall()

        print("\n" + "=" * 86)
        print("           SECTOR-LEVEL WATER CONSUMPTION & COST SUMMARY (SUNGAI SELANGOR)")
        print("=" * 86)
        print(f"{'Sector':<12} | {'Logs':<5} | {'Avg(m3)':<9} | {'Min(m3)':<9} | {'Max(m3)':<9} | {'Total(m3)':<11} | {'Total RM'}")
        print("-" * 86)
        for r in rows:
            print(
                f"{r['sector']:<12} | {r['total_logs']:<5} | {r['avg_m3']:<9.2f} | "
                f"{r['min_m3']:<9.2f} | {r['max_m3']:<9.2f} | {r['total_m3']:<11.2f} | RM {r['total_cost_rm']:.2f}"
            )
        print("=" * 86)
        return rows
    except sqlite3.Error as e:
        print(f"  [Database Error] Analytics query failed: {e}")
        return []


def detect_inefficient_usage() -> list[dict]:
    """
    Identify high-volume/inefficient usage patterns across two dimensions:
    1. Domestic Per-Capita Usage > 230 Liters/Capita/Day (LCD)
    2. Month-over-Month (MoM) consumption spikes > 15% for any premise.
    """
    alerts = []
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT w.premise_id, p.name, p.sector, p.occupants,
                       w.billing_month, w.consumption_m3, w.cost_rm
                FROM water_logs w
                JOIN premises p ON w.premise_id = p.premise_id
                ORDER BY w.premise_id ASC, w.billing_month ASC;
            """)
            logs = cursor.fetchall()

        prev_by_premise = {}
        for row in logs:
            pid = row["premise_id"]
            vol = row["consumption_m3"]
            occ = row["occupants"]
            month = row["billing_month"]

            # Check 1: Domestic Per-Capita Daily Consumption (LCD)
            # 1 m3 = 1,000 Liters; assuming 30-day billing cycle
            lcd = (vol * 1000.0) / (occ * 30.0)
            if row["sector"] == "Domestic" and lcd > DOMESTIC_LCD_LIMIT:
                alerts.append({
                    "premise": row["name"],
                    "sector": row["sector"],
                    "month": month,
                    "type": "High Per-Capita Usage",
                    "detail": f"{lcd:.1f} LCD (Exceeds {DOMESTIC_LCD_LIMIT:.0f} LCD limit)",
                })

            # Check 2: Month-over-Month Usage Spike (> 15%)
            if pid in prev_by_premise:
                prev_vol = prev_by_premise[pid]
                if prev_vol > 0:
                    pct_change = ((vol - prev_vol) / prev_vol) * 100.0
                    if pct_change > 15.0:
                        alerts.append({
                            "premise": row["name"],
                            "sector": row["sector"],
                            "month": month,
                            "type": "MoM Consumption Spike",
                            "detail": f"+{pct_change:.1f}% surge ({prev_vol} -> {vol} m3)",
                        })
            prev_by_premise[pid] = vol

        print("\n" + "=" * 90)
        print("                 INEFFICIENT WATER USAGE & ANOMALY DETECTION REPORT")
        print("=" * 90)
        if not alerts:
            print("  [✓] All premises are operating within efficient water consumption thresholds.")
        else:
            print(f"{'Premise Name':<30} | {'Sector':<10} | {'Month':<8} | {'Alert Type':<22} | {'Metric Details'}")
            print("-" * 90)
            for a in alerts:
                print(
                    f"{a['premise'][:30]:<30} | {a['sector']:<10} | {a['month']:<8} | "
                    f"{a['type']:<22} | {a['detail']}"
                )
        print("=" * 90)
        return alerts
    except sqlite3.Error as e:
        print(f"  [Database Error] Could not run inefficiency detection: {e}")
        return []


def run_rainwater_harvesting_simulation() -> None:
    """
    Simulate Rainwater Harvesting System (RWHS) water yield and monthly bill savings.
    Formula: Harvested (m3) = Roof Area (m2) * (Rainfall_mm / 1000) * Runoff_Coeff (0.85)
    """
    rows = list_all_premises()
    if not rows:
        return

    pid = get_positive_int("\n  Select Premise ID for Rainwater Harvesting Simulation: ")
    premise = get_premise_by_id(pid)
    if not premise:
        print(f"  [!] Premise ID {pid} not found.")
        return

    print(f"\n--- RWHS Simulator: {premise['name']} ({premise['sector']}) ---")
    print(f"  Roof Catchment Area: {premise['roof_area_sqm']} sqm | Runoff Coefficient: {RUNOFF_COEFFICIENT}")
    rainfall_mm = get_positive_float("  Enter Projected Monthly Rainfall in mm (Selangor avg is 200-250): ")
    tank_cap = get_positive_float("  Enter Storage Tank Capacity in m3 (e.g., 5 for Domestic, 150 for Industrial): ")

    # Calculate theoretical rainwater yield and cap at tank capacity
    raw_yield_m3 = premise["roof_area_sqm"] * (rainfall_mm / 1000.0) * RUNOFF_COEFFICIENT
    usable_harvest_m3 = round(min(raw_yield_m3, tank_cap), 2)

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT AVG(consumption_m3) AS avg_vol
                FROM water_logs
                WHERE premise_id = ?;
            """, (pid,))
            res = cursor.fetchone()
            avg_vol = res["avg_vol"] if res and res["avg_vol"] else 30.0

            current_bill = calculate_water_bill(premise["sector"], avg_vol)
            net_grid_vol = max(0.0, avg_vol - usable_harvest_m3)
            new_bill = calculate_water_bill(premise["sector"], net_grid_vol)
            savings_rm = round(current_bill - new_bill, 2)

            cursor.execute("""
                INSERT INTO harvesting_simulations
                (premise_id, rainfall_mm, tank_capacity_m3, harvested_m3, projected_savings_rm)
                VALUES (?, ?, ?, ?, ?);
            """, (pid, rainfall_mm, tank_cap, usable_harvest_m3, savings_rm))
            conn.commit()

        print("\n  " + "-" * 58)
        print("  RAINWATER HARVESTING SIMULATION RESULTS")
        print("  " + "-" * 58)
        print(f"  Baseline Avg Grid Consumption : {avg_vol:.2f} m3/month (RM {current_bill:.2f})")
        print(f"  Potential Roof Runoff Yield   : {raw_yield_m3:.2f} m3/month")
        print(f"  Usable Harvested Water (Capped): {usable_harvest_m3:.2f} m3/month")
        print(f"  New Grid Water Demand         : {net_grid_vol:.2f} m3/month (RM {new_bill:.2f})")
        print(f"  Projected Monthly Savings     : RM {savings_rm:.2f}/month (RM {savings_rm * 12:.2f}/year)")
        print("  " + "-" * 58)
        print("  [✓] Simulation saved to database.")
    except sqlite3.Error as e:
        print(f"  [Database Error] Simulation failed: {e}")


def export_stakeholder_reports() -> None:
    """Generate and export CSV and TXT summary reports into the /reports folder."""
    os.makedirs("reports", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join("reports", f"water_efficiency_report_{timestamp}.csv")
    txt_path = os.path.join("reports", f"executive_summary_{timestamp}.txt")

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.premise_id, p.name, p.sector, p.sub_basin,
                       w.billing_month, w.consumption_m3, w.cost_rm
                FROM water_logs w
                JOIN premises p ON w.premise_id = p.premise_id
                ORDER BY p.sector, p.name, w.billing_month;
            """)
            log_rows = cursor.fetchall()

            cursor.execute("""
                SELECT p.name, p.sector, s.rainfall_mm, s.tank_capacity_m3,
                       s.harvested_m3, s.projected_savings_rm
                FROM harvesting_simulations s
                JOIN premises p ON s.premise_id = p.premise_id
                ORDER BY s.sim_id DESC;
            """)
            sim_rows = cursor.fetchall()

        # 1. Export detailed CSV
        with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Premise ID", "Premise Name", "Sector", "Sub-Basin",
                "Billing Month", "Consumption (m3)", "Cost (RM)"
            ])
            for r in log_rows:
                writer.writerow([
                    r["premise_id"], r["name"], r["sector"], r["sub_basin"],
                    r["billing_month"], r["consumption_m3"], f"{r['cost_rm']:.2f}"
                ])

        # 2. Export Stakeholder Executive Summary TXT
        stats = show_sector_statistics()
        alerts = detect_inefficient_usage()

        with open(txt_path, mode="w", encoding="utf-8") as f:
            f.write("====================================================================\n")
            f.write("  W.A.T.E.R. PROJECT & SPARK YOUTH GRANT - STAKEHOLDER REPORT\n")
            f.write(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("====================================================================\n\n")

            f.write("1. SECTOR CONSUMPTION SUMMARY\n")
            f.write("-----------------------------\n")
            for s in stats:
                f.write(
                    f"- {s['sector']}: {s['total_logs']} logs | Avg: {s['avg_m3']} m3 | "
                    f"Total: {s['total_m3']} m3 | Total Bill: RM {s['total_cost_rm']:.2f}\n"
                )

            f.write("\n2. FLAGGED INEFFICIENCIES & ANOMALIES\n")
            f.write("-------------------------------------\n")
            if not alerts:
                f.write("- None. All premises within benchmark limits.\n")
            else:
                for a in alerts:
                    f.write(f"- [{a['month']}] {a['premise']} ({a['type']}): {a['detail']}\n")

            f.write("\n3. RAINWATER HARVESTING SIMULATIONS\n")
            f.write("-----------------------------------\n")
            for sim in sim_rows:
                f.write(
                    f"- {sim['name']} ({sim['sector']}): Harvested {sim['harvested_m3']} m3 "
                    f"@ {sim['rainfall_mm']}mm rainfall -> Saves RM {sim['projected_savings_rm']:.2f}/month\n"
                )

        print(f"\n  [✓] Stakeholder CSV exported to : {csv_path}")
        print(f"  [✓] Executive TXT exported to   : {txt_path}")
    except (sqlite3.Error, OSError) as e:
        print(f"  [Export Error] Failed to generate report files: {e}")