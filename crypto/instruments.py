"""Crypto symbols, exchange-fee model and Indian VDA tax helpers."""

from __future__ import annotations

from dataclasses import dataclass

COINS = ("BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "LINK")
INR_QUOTED = ("BTC", "ETH")  # Yahoo Finance lists these against INR; others only against USD
PERIODS_PER_YEAR = 365  # crypto trades every day

# India: gains on virtual digital assets are taxed at a flat 30% (+4% cess), only the cost of
# acquisition is deductible, losses cannot be set off, and exchanges deduct 1% TDS (194S).
# Verified against a tax-guide summary on 2026-10-24: confirm with official sources/a CA.
VDA_TAX_RATE = 0.30
CESS_RATE = 0.04
TDS_RATE = 0.01
GST_ON_FEES = 0.18


def yahoo_symbol(coin: str, quote: str = "USD") -> str:
    c, q = coin.strip().upper(), quote.strip().upper()
    if not c.isalnum() or q not in ("USD", "INR"):
        raise ValueError("coin must be alphanumeric and quote USD or INR")
    if q == "INR" and c not in INR_QUOTED:
        raise ValueError(f"{c} has no INR quote on Yahoo Finance; use USD.")
    return f"{c}-{q}"


@dataclass(frozen=True)
class FeeModel:
    """Per-side trading cost in basis points of traded value."""

    taker_bps: float = 10.0
    maker_bps: float = 8.0
    slippage_bps: float = 10.0
    gst_rate: float = GST_ON_FEES  # charged on the exchange fee by Indian exchanges
    use_maker: bool = False

    def __post_init__(self) -> None:
        if min(self.taker_bps, self.maker_bps, self.slippage_bps, self.gst_rate) < 0:
            raise ValueError("fees, slippage and GST must be non-negative")

    def per_side_bps(self) -> float:
        fee = self.maker_bps if self.use_maker else self.taker_bps
        return fee * (1.0 + self.gst_rate) + self.slippage_bps

    def round_trip_bps(self) -> float:
        return 2.0 * self.per_side_bps()


def tax_on_gain(gain: float) -> float:
    """Tax on one transfer's gain under the VDA regime (no relief for losses)."""
    return max(gain, 0.0) * VDA_TAX_RATE * (1.0 + CESS_RATE)
