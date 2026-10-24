from __future__ import annotations

from core.exceptions import DomainError, ValidationError


def validate_ticker(ticker: str) -> None:
    if not ticker or not isinstance(ticker, str):
        raise ValidationError("Ticker must be a non-empty string.")
    if ticker != ticker.upper():
        raise DomainError("Ticker symbols must be uppercase.")


def run_example() -> None:
    print("--- CORE-002: Exception Framework Example ---")
    try:
        validate_ticker("reliance")
    except (ValidationError, DomainError) as e:
        print(f"Caught expected platform exception: {type(e).__name__}: {e}")


if __name__ == "__main__":
    run_example()
