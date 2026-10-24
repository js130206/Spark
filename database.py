"""
Database initialization, tariff calculation, and seed data module.
Aligned with SPARK Youth Water Grant & W.A.T.E.R. Project (Sungai Selangor).
"""
import sqlite3
from typing import Optional

DB_NAME = "water_tracker.db"


def get_connection() -> sqlite3.Connection:
    """Establish and return a SQLite connection with foreign keys enabled."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def calculate_water_bill(sector: str, consumption_m3: float) -> float:
    """
    Calculate monthly water tariff in RM based on Selangor tiered rates.
    
    Parameters:
        sector (str): 'Domestic' or 'Industrial'
        consumption_m3 (float): Total water volume in cubic meters (m3)
        
    Returns:
        float: Total projected cost in RM rounded to 2 decimal places.
    """
    if consumption_m3 <= 0:
        return 0.0

    if sector == "Domestic":
        # Tier 1: 0 - 20 m3 @ RM 0.65/m3
        # Tier 2: 20.01 - 35 m3 @ RM 1.32/m3
        # Tier 3: > 35 m3 @ RM 2.63/m3
        if consumption_m3 <= 20:
            cost = consumption_m3 * 0.65
        elif consumption_m3 <= 35:
            cost = (20 * 0.65) + ((consumption_m3 - 20) * 1.32)
        else:
            cost = (20 * 0.65) + (15 * 1.32) + ((consumption_m3 - 35) * 2.63)
        return round(max(cost, 6.50), 2)  # Minimum RM 6.50 domestic charge
    else:
        # Industrial flat tariff @ RM 2.95/m3 (Min RM 35.00)
        cost = consumption_m3 * 2.95
        return round(max(cost, 35.00), 2)


def init_db() -> None:
    """Create relational database tables if they do not exist."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # 1. Parent Table: Premises
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS premises (
                    premise_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    sector TEXT NOT NULL CHECK(sector IN ('Domestic', 'Industrial')),
                    sub_basin TEXT NOT NULL,
                    roof_area_sqm REAL NOT NULL CHECK(roof_area_sqm > 0),
                    occupants INTEGER NOT NULL CHECK(occupants > 0)
                );
            """)

            # 2. Child Table: Monthly Water Logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS water_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    premise_id INTEGER NOT NULL,
                    billing_month TEXT NOT NULL,
                    consumption_m3 REAL NOT NULL CHECK(consumption_m3 >= 0),
                    cost_rm REAL NOT NULL CHECK(cost_rm >= 0),
                    FOREIGN KEY (premise_id) REFERENCES premises(premise_id) ON DELETE CASCADE,
                    UNIQUE(premise_id, billing_month)
                );
            """)

            # 3. Child Table: Rainwater Harvesting Simulations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS harvesting_simulations (
                    sim_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    premise_id INTEGER NOT NULL,
                    rainfall_mm REAL NOT NULL,
                    tank_capacity_m3 REAL NOT NULL,
                    harvested_m3 REAL NOT NULL,
                    projected_savings_rm REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (premise_id) REFERENCES premises(premise_id) ON DELETE CASCADE
                );
            """)
            conn.commit()
    except sqlite3.Error as e:
        print(f"[Database Error] Failed to initialize tables: {e}")


def seed_db() -> None:
    """Populate initial Sungai Selangor basin dataset if database is empty."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM premises;")
            if cursor.fetchone()[0] > 0:
                return  # Already seeded

            premises_seed = [
                ("Taman Sri Muda Residence 12", "Domestic", "Sungai Selangor", 140.0, 5),
                ("Rawang Perdana Terrace 88", "Domestic", "Sungai Selangor", 110.0, 4),
                ("Bukit Jelutong Semi-D 04", "Domestic", "Sungai Damansara", 220.0, 6),
                ("Kundang Jaya Glove Manufacturing", "Industrial", "Sungai Selangor", 2500.0, 120),
                ("Batang Kali Food Processing Hub", "Industrial", "Sungai Selangor", 1800.0, 85),
            ]
            cursor.executemany("""
                INSERT INTO premises (name, sector, sub_basin, roof_area_sqm, occupants)
                VALUES (?, ?, ?, ?, ?);
            """, premises_seed)

            # Seed monthly water logs (premise_id, month, consumption_m3)
            raw_logs = [
                # Premise 1: High domestic usage (inefficient spike in 2026-08)
                (1, "2026-06", 38.0, "Domestic"),
                (1, "2026-07", 41.5, "Domestic"),
                (1, "2026-08", 52.0, "Domestic"),
                # Premise 2: Efficient domestic usage
                (2, "2026-06", 18.5, "Domestic"),
                (2, "2026-07", 19.0, "Domestic"),
                (2, "2026-08", 17.8, "Domestic"),
                # Premise 3: Moderate-high domestic usage
                (3, "2026-06", 32.0, "Domestic"),
                (3, "2026-07", 34.0, "Domestic"),
                (3, "2026-08", 44.5, "Domestic"),
                # Premise 4: Heavy industrial usage
                (4, "2026-06", 1450.0, "Industrial"),
                (4, "2026-07", 1520.0, "Industrial"),
                (4, "2026-08", 1890.0, "Industrial"),
                # Premise 5: Moderate industrial usage
                (5, "2026-06", 820.0, "Industrial"),
                (5, "2026-07", 805.0, "Industrial"),
                (5, "2026-08", 790.0, "Industrial"),
            ]

            logs_to_insert = [
                (pid, month, vol, calculate_water_bill(sec, vol))
                for pid, month, vol, sec in raw_logs
            ]
            cursor.executemany("""
                INSERT INTO water_logs (premise_id, billing_month, consumption_m3, cost_rm)
                VALUES (?, ?, ?, ?);
            """, logs_to_insert)

            # Seed 2 baseline Rainwater Harvesting Simulations
            cursor.execute("""
                INSERT INTO harvesting_simulations 
                (premise_id, rainfall_mm, tank_capacity_m3, harvested_m3, projected_savings_rm)
                VALUES 
                (1, 240.0, 5.0, 5.0, 13.15),
                (4, 240.0, 150.0, 150.0, 442.50);
            """)
            conn.commit()
            print("[System] Database initialized and seeded with Sungai Selangor sample data.")
    except sqlite3.Error as e:
        print(f"[Database Error] Failed to seed data: {e}")