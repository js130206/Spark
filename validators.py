"""
Input validation and error-handling utility module.
Ensures crash-free user input across CLI menus and CRUD operations.
"""
from datetime import datetime


def get_non_empty_string(prompt: str) -> str:
    """Prompt user until a non-empty text string is entered."""
    while True:
        try:
            value = input(prompt).strip()
            if value:
                return value
            print("  [!] Input cannot be empty. Please try again.")
        except (EOFError, KeyboardInterrupt):
            print("\n  [!] Input cancelled.")
            return "Unknown"


def get_positive_float(prompt: str, allow_zero: bool = False) -> float:
    """Prompt user until a valid positive floating-point number is entered."""
    while True:
        try:
            value = float(input(prompt).strip())
            if allow_zero and value >= 0:
                return round(value, 2)
            if not allow_zero and value > 0:
                return round(value, 2)
            condition = ">= 0" if allow_zero else "> 0"
            print(f"  [!] Value must be a number {condition}.")
        except ValueError:
            print("  [!] Invalid numeric entry. Please enter a valid number (e.g., 25.5).")


def get_positive_int(prompt: str) -> int:
    """Prompt user until a valid positive integer (> 0) is entered."""
    while True:
        try:
            value = int(input(prompt).strip())
            if value > 0:
                return value
            print("  [!] Value must be a whole number greater than 0.")
        except ValueError:
            print("  [!] Invalid input. Please enter a whole integer (e.g., 5).")


def get_valid_month(prompt: str) -> str:
    """Prompt user until a valid billing month in YYYY-MM format is entered."""
    while True:
        raw = input(prompt).strip()
        try:
            parsed = datetime.strptime(raw, "%Y-%m")
            return parsed.strftime("%Y-%m")
        except ValueError:
            print("  [!] Invalid date format. Please use YYYY-MM (e.g., 2026-09).")


def get_choice(prompt: str, valid_options: list[str]) -> str:
    """Prompt user until their selection matches one of the allowed options."""
    normalized_map = {opt.lower(): opt for opt in valid_options}
    options_str = "/".join(valid_options)
    while True:
        raw = input(f"{prompt} ({options_str}): ").strip().lower()
        if raw in normalized_map:
            return normalized_map[raw]
        print(f"  [!] Invalid selection. Choose from: {options_str}")