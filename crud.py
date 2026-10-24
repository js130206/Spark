"""
CRUD (Create, Read, Update, Delete) operations for Premises and Water Logs.
"""
import sqlite3
from typing import Optional
from database import get_connection, calculate_water_bill
from validators import (
    get_non_empty_string,
    get_positive_float,
    get_positive_int,
    get_valid_month,
    get_choice,
)


def list_all_premises() -> list[sqlite3.Row]:
    """Fetch and display all registered premises in a formatted table."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM premises ORDER BY premise_id ASC;")
            rows = cursor.fetchall()

        if not rows:
            print("\n  [i] No premises found in the database.")
            return []

        print("\n" + "=" * 82)
        print(f"{'ID':<4} | {'Premise Name':<32} | {'Sector':<11} | {'Sub-Basin':<16} | {'Roof(m2)':<8} | {'Occ.'}")
        print("-" * 82)
        for r in rows:
            print(
                f"{r['premise_id']:<4} | {r['name'][:32]:<32} | {r['sector']:<11} | "
                f"{r['sub_basin'][:16]:<16} | {r['roof_area_sqm']:<8.1f} | {r['occupants']}"
            )
        print("=" * 82)
        return rows
    except sqlite3.Error as e:
        print(f"  [Database Error] Could not retrieve premises: {e}")
        return []


def get_premise_by_id(premise_id: int) -> Optional[sqlite3.Row]:
    """Return a single premise record by ID, or None if not found."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM premises WHERE premise_id = ?;", (premise_id,))
            return cursor.fetchone()
    except sqlite3.Error as e:
        print(f"  [Database Error] {e}")
        return None


def create_premise() -> None:
    """Interactive CLI prompt to create a new domestic or industrial premise."""
    print("\n--- Register New Premise ---")
    name = get_non_empty_string("  Enter Premise Name: ")
    sector = get_choice("  Select Sector", ["Domestic", "Industrial"])
    sub_basin = get_non_empty_string("  Enter River Sub-Basin (e.g., Sungai Selangor): ")
    roof_area = get_positive_float("  Enter Catchments Roof Area (sqm): ")
    occupants = get_positive_int("  Enter Number of Occupants/Staff: ")

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO premises (name, sector, sub_basin, roof_area_sqm, occupants)
                VALUES (?, ?, ?, ?, ?);
            """, (name, sector, sub_basin, roof_area, occupants))
            conn.commit()
            print(f"  [✓] Premise '{name}' added successfully (ID: {cursor.lastrowid}).")
    except sqlite3.Error as e:
        print(f"  [Database Error] Failed to add premise: {e}")


def update_premise() -> None:
    """Update roof area or occupant count for an existing premise."""
    rows = list_all_premises()
    if not rows:
        return

    pid = get_positive_int("\n  Enter Premise ID to update: ")
    premise = get_premise_by_id(pid)
    if not premise:
        print(f"  [!] Premise ID {pid} does not exist.")
        return

    print(f"  Updating '{premise['name']}' (Current Roof: {premise['roof_area_sqm']} sqm, Occupants: {premise['occupants']})")
    new_roof = get_positive_float("  Enter New Roof Area (sqm): ")
    new_occ = get_positive_int("  Enter New Number of Occupants/Staff: ")

    try:
        with get_connection() as conn:
            conn.execute("""
                UPDATE premises
                SET roof_area_sqm = ?, occupants = ?
                WHERE premise_id = ?;
            """, (new_roof, new_occ, pid))
            conn.commit()
            print(f"  [✓] Premise ID {pid} updated successfully.")
    except sqlite3.Error as e:
        print(f"  [Database Error] Failed to update premise: {e}")


def delete_premise() -> None:
    """Delete a premise and cascade-delete all associated logs and simulations."""
    rows = list_all_premises()
    if not rows:
        return

    pid = get_positive_int("\n  Enter Premise ID to DELETE: ")
    premise = get_premise_by_id(pid)
    if not premise:
        print(f"  [!] Premise ID {pid} not found.")
        return

    confirm = get_choice(
        f"  Are you sure you want to delete '{premise['name']}' and all its water logs?",
        ["yes", "no"]
    )
    if confirm == " no" or confirm == "no":
        print("  [i] Deletion cancelled.")
        return

    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM premises WHERE premise_id = ?;", (pid,))
            conn.commit()
            print(f"  [✓] Premise '{premise['name']}' and linked records deleted.")
    except sqlite3.Error as e:
        print(f"  [Database Error] Failed to delete premise: {e}")


def create_water_log() -> None:
    """Log monthly water consumption and auto-calculate tiered RM bill."""
    rows = list_all_premises()
    if not rows:
        return

    pid = get_positive_int("\n  Enter Premise ID to log water usage: ")
    premise = get_premise_by_id(pid)
    if not premise:
        print(f"  [!] Premise ID {pid} not found.")
        return

    month = get_valid_month("  Enter Billing Month (YYYY-MM): ")
    volume = get_positive_float("  Enter Water Consumption (m3): ")
    cost = calculate_water_bill(premise["sector"], volume)

    try:
        with get_connection() as conn:
            conn.execute("""
                INSERT INTO water_logs (premise_id, billing_month, consumption_m3, cost_rm)
                VALUES (?, ?, ?, ?);
            """, (pid, month, volume, cost))
            conn.commit()
            print(f"  [✓] Logged {volume} m3 for {month}. Projected Bill: RM {cost:.2f}")
    except sqlite3.IntegrityError:
        print(f"  [!] A log for Premise ID {pid} in {month} already exists. Use 'Update Log' instead.")
    except sqlite3.Error as e:
        print(f"  [Database Error] Failed to create water log: {e}")


def view_water_logs() -> list[sqlite3.Row]:
    """Display all water consumption logs joined with premise details."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT w.log_id, p.name, p.sector, w.billing_month, w.consumption_m3, w.cost_rm
                FROM water_logs w
                JOIN premises p ON w.premise_id = p.premise_id
                ORDER BY w.billing_month DESC, p.premise_id ASC;
            """)
            rows = cursor.fetchall()

        if not rows:
            print("\n  [i] No water consumption logs available.")
            return []

        print("\n" + "=" * 82)
        print(f"{'LogID':<6} | {'Premise Name':<30} | {'Sector':<10} | {'Month':<8} | {'Usage(m3)':<10} | {'Bill(RM)'}")
        print("-" * 82)
        for r in rows:
            print(
                f"{r['log_id']:<6} | {r['name'][:30]:<30} | {r['sector']:<10} | "
                f"{r['billing_month']:<8} | {r['consumption_m3']:<10.2f} | {r['cost_rm']:.2f}"
            )
        print("=" * 82)
        return rows
    except sqlite3.Error as e:
        print(f"  [Database Error] Could not read water logs: {e}")
        return []


def update_water_log() -> None:
    """Update consumption volume for an existing log and recalculate its RM cost."""
    logs = view_water_logs()
    if not logs:
        return

    lid = get_positive_int("\n  Enter Log ID to update: ")
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT w.log_id, w.billing_month, w.consumption_m3, p.name, p.sector
                FROM water_logs w
                JOIN premises p ON w.premise_id = p.premise_id
                WHERE w.log_id = ?;
            """, (lid,))
            record = cursor.fetchone()

            if not record:
                print(f"  [!] Log ID {lid} not found.")
                return

            print(f"  Updating {record['name']} ({record['billing_month']}) - Current: {record['consumption_m3']} m3")
            new_vol = get_positive_float("  Enter New Consumption Volume (m3): ")
            new_cost = calculate_water_bill(record["sector"], new_vol)

            cursor.execute("""
                UPDATE water_logs
                SET consumption_m3 = ?, cost_rm = ?
                WHERE log_id = ?;
            """, (new_vol, new_cost, lid))
            conn.commit()
            print(f"  [✓] Log ID {lid} updated! New Volume: {new_vol} m3 | Recalculated Bill: RM {new_cost:.2f}")
    except sqlite3.Error as e:
        print(f"  [Database Error] Failed to update log: {e}")


def delete_water_log() -> None:
    """Delete a specific water consumption log entry by ID."""
    logs = view_water_logs()
    if not logs:
        return

    lid = get_positive_int("\n  Enter Log ID to delete: ")
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM water_logs WHERE log_id = ?;", (lid,))
            if cursor.rowcount == 0:
                print(f"  [!] Log ID {lid} not found.")
            else:
                conn.commit()
                print(f"  [✓] Log ID {lid} deleted successfully.")
    except sqlite3.Error as e:
        print(f"  [Database Error] Failed to delete log: {e}")