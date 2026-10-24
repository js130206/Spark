"""
Main Command Line Interface (CLI) entry point for Option B:
Domestic & Industrial Water Efficiency & Harvesting Tracker.
Course: SIM2011 Structured Programming.
"""
import sys
from database import init_db, seed_db
from crud import (
    list_all_premises,
    create_premise,
    update_premise,
    delete_premise,
    view_water_logs,
    create_water_log,
    update_water_log,
    delete_water_log,
)
from analytics import (
    show_sector_statistics,
    detect_inefficient_usage,
    run_rainwater_harvesting_simulation,
    export_stakeholder_reports,
)
from validators import get_choice


def print_banner() -> None:
    """Display the application header aligned with the W.A.T.E.R. initiative."""
    print("\n" + "=" * 72)
    print("   SPARK YOUTH WATER GRANT & W.A.T.E.R. PROJECT MANAGEMENT SYSTEM")
    print("   Option B: Domestic & Industrial Water Efficiency & RWHS Tracker")
    print("=" * 72)


def main_menu() -> None:
    """Run the primary interactive CLI loop."""
    init_db()
    seed_db()

    while True:
        print_banner()
        print("  [PREMISE MANAGEMENT]")
        print("    1. View All Registered Premises")
        print("    2. Register New Premise (Domestic / Industrial)")
        print("    3. Update Premise Details (Roof Area / Occupants)")
        print("    4. Delete Premise")
        print("\n  [WATER CONSUMPTION LOGS (CRUD)]")
        print("    5. View Monthly Water Consumption Logs")
        print("    6. Log New Monthly Water Usage (Auto-Tariff Calculation)")
        print("    7. Update Existing Water Log")
        print("    8. Delete Water Log")
        print("\n  [ANALYTICS, RWHS SIMULATION & STAKEHOLDER REPORTS]")
        print("    9. View Sector Summary Statistics (Avg, Min, Max, Total RM)")
        print("   10. Run Inefficiency & Consumption Spike Detector")
        print("   11. Simulate Rainwater Harvesting System (RWHS) Savings")
        print("   12. Export Stakeholder Reports (CSV & Executive TXT)")
        print("\n    0. Exit Application")
        print("-" * 72)

        choice = get_choice(
            "  Select Menu Option",
            ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
        )

        if choice == "1":
            list_all_premises()
        elif choice == "2":
            create_premise()
        elif choice == "3":
            update_premise()
        elif choice == "4":
            delete_premise()
        elif choice == "5":
            view_water_logs()
        elif choice == "6":
            create_water_log()
        elif choice == "7":
            update_water_log()
        elif choice == "8":
            delete_water_log()
        elif choice == "9":
            show_sector_statistics()
        elif choice == "10":
            detect_inefficient_usage()
        elif choice == "11":
            run_rainwater_harvesting_simulation()
        elif choice == "12":
            export_stakeholder_reports()
        elif choice == "0":
            print("\n  Thank you for using the W.A.T.E.R. Efficiency Tracker. Goodbye!\n")
            sys.exit(0)

        input("\n  Press [Enter] to return to the main menu...")


if __name__ == "__main__":
    main_menu()