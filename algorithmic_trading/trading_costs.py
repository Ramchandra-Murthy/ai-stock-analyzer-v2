"""Configurable India-equity transaction cost estimates for research backtests.

Rates are user-configurable basis points of traded notional. They are not a
live statutory rate feed; update them for the broker, exchange, product and
date being tested.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class IndiaEquityCostModel:
    """Estimate per-side equity trading costs as fractions of portfolio value."""

    brokerage_bps: float = 0.0
    exchange_transaction_bps: float = 0.0
    regulatory_bps: float = 0.0
    stt_buy_bps: float = 0.0
    stt_sell_bps: float = 0.0
    stamp_duty_buy_bps: float = 0.0
    slippage_bps: float = 0.0
    gst_rate: float = 0.18

    def __post_init__(self) -> None:
        rates = (
            self.brokerage_bps,
            self.exchange_transaction_bps,
            self.regulatory_bps,
            self.stt_buy_bps,
            self.stt_sell_bps,
            self.stamp_duty_buy_bps,
            self.slippage_bps,
        )
        if any(not np.isfinite(rate) or rate < 0 for rate in rates):
            raise ValueError("cost rates must be finite and non-negative")
        if not np.isfinite(self.gst_rate) or not 0 <= self.gst_rate <= 1:
            raise ValueError("gst_rate must be finite and between zero and one")

    def cost_fraction(
        self,
        buy_turnover: pd.Series,
        sell_turnover: pd.Series,
    ) -> pd.Series:
        """Return per-bar cost fractions for buy and sell traded notional."""
        brokerage = self.brokerage_bps / 10_000.0
        exchange = self.exchange_transaction_bps / 10_000.0
        regulatory = self.regulatory_bps / 10_000.0
        slippage = self.slippage_bps / 10_000.0
        gst = self.gst_rate * (brokerage + exchange + regulatory)
        buy_rate = (
            brokerage
            + exchange
            + regulatory
            + gst
            + self.stt_buy_bps / 10_000.0
            + self.stamp_duty_buy_bps / 10_000.0
            + slippage
        )
        sell_rate = (
            brokerage + exchange + regulatory + gst + self.stt_sell_bps / 10_000.0 + slippage
        )
        return buy_turnover * buy_rate + sell_turnover * sell_rate


# ----------------------------------------------------------------------------------------
# Ready-made presets for NSE cash-market equity
# ----------------------------------------------------------------------------------------
# Statutory and exchange rates, in basis points of traded value (1 bp = 0.01%).
# Cross-checked in October 2026 against the NSE investor page (updated 17 Apr 2026: STT, SEBI
# fee, stamp duty) and a broker rate card (modified 22 Jul 2026: exchange charge, IPFT, GST).
# These change by notification: re-verify before relying on them, and note that stamp duty
# can vary by state.
RATES_VERIFIED = "Oct 2026 (NSE investor page 17 Apr 2026; broker rate card 22 Jul 2026)"
NSE_EXCHANGE_TRANSACTION_BPS = 0.297  # 0.00297% of turnover
SEBI_TURNOVER_BPS = 0.01  # Rs 10 per crore
IPFT_BPS = 0.01  # NSE investor protection fund trust, Rs 10 per crore
STT_DELIVERY_BPS = 10.0  # 0.1% on both buy and sell
STT_INTRADAY_SELL_BPS = 2.5  # 0.025% on the sell side only
STAMP_DUTY_DELIVERY_BUY_BPS = 1.5  # 0.015% on the buy side
STAMP_DUTY_INTRADAY_BUY_BPS = 0.3  # 0.003% on the buy side
GST_RATE = 0.18  # on brokerage + exchange charges + SEBI fee

DEFAULT_SLIPPAGE_BPS = 5.0  # an assumption for liquid large caps; raise it for small caps
INTRADAY_BROKERAGE_BPS = 3.0  # upper bound for "Rs 20 or 0.03% per order, whichever is lower"


def india_cost_model(
    product: str = "delivery",
    *,
    brokerage_bps: float | None = None,
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
) -> IndiaEquityCostModel:
    """NSE equity cost model for ``product`` in {"delivery", "intraday"}.

    Brokerage defaults to 0 for delivery (typical of discount brokers) and 3 bps for intraday;
    pass your broker's real figure. Slippage is an assumption, not a published rate.
    """
    if product == "delivery":
        stt_buy, stt_sell = STT_DELIVERY_BPS, STT_DELIVERY_BPS
        stamp = STAMP_DUTY_DELIVERY_BUY_BPS
        default_brokerage = 0.0
    elif product == "intraday":
        stt_buy, stt_sell = 0.0, STT_INTRADAY_SELL_BPS
        stamp = STAMP_DUTY_INTRADAY_BUY_BPS
        default_brokerage = INTRADAY_BROKERAGE_BPS
    else:
        raise ValueError("product must be 'delivery' or 'intraday'")
    return IndiaEquityCostModel(
        brokerage_bps=default_brokerage if brokerage_bps is None else brokerage_bps,
        exchange_transaction_bps=NSE_EXCHANGE_TRANSACTION_BPS,
        regulatory_bps=SEBI_TURNOVER_BPS + IPFT_BPS,
        stt_buy_bps=stt_buy,
        stt_sell_bps=stt_sell,
        stamp_duty_buy_bps=stamp,
        slippage_bps=slippage_bps,
        gst_rate=GST_RATE,
    )


def round_trip_bps(model: IndiaEquityCostModel) -> float:
    """Total cost of buying then selling one unit of value, in basis points."""
    one = pd.Series([1.0])
    zero = pd.Series([0.0])
    buy = float(model.cost_fraction(one, zero).iloc[0])
    sell = float(model.cost_fraction(zero, one).iloc[0])
    return (buy + sell) * 10_000.0
