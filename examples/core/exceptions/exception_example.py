from __future__ import annotations

from core.exceptions import CalculationError, ValidationError


def run_example() -> None:
    print("--- CORE-002: Exception Framework Example ---")
    try:
        raise ValidationError("Sample validation error in financial input.")
    except ValidationError as e:
        print(f"Caught expected ValidationError: {e}")

    try:
        raise CalculationError("Sample calculation error in WACC estimation.")
    except CalculationError as e:
        print(f"Caught expected CalculationError: {e}")


if __name__ == "__main__":
    run_example()
