from __future__ import annotations

"""
==========================================================
DCF FORECAST ENGINE
Module  : forecast
Version : V2.1
==========================================================

Generates explicit multi-year projections for Revenue, EBIT,
NOPAT, Reinvestment items, and Free Cash Flow to Firm (FCFF).

This module contains no valuation or discounting logic.
"""

from dataclasses import dataclass

from services.valuation.dcf.dcf_input import DCFInput


@dataclass(slots=True)
class ForecastSchedule:
    """
    Container holding itemized line-item forecasts across the
    explicit projection period.
    """

    projected_revenue: list[float]
    projected_ebit: list[float]
    projected_nopat: list[float]
    projected_depreciation: list[float]
    projected_capex: list[float]
    projected_delta_nwc: list[float]
    projected_fcff: list[float]


def forecast_revenue(last_revenue: float, growth_rates: list[float]) -> list[float]:
    """
    Forecasts revenue recursively from the most recent historical base revenue.

    R_t = R_{t-1} * (1 + g_t)
    """
    revenues: list[float] = []
    current_revenue = last_revenue

    for rate in growth_rates:
        current_revenue = current_revenue * (1.0 + rate)
        revenues.append(current_revenue)

    return revenues


def build_forecast_schedule(data: DCFInput) -> ForecastSchedule:
    """
    Main forecaster entry point. Computes all operating and cash flow line-items
    for each year in the explicit forecast horizon.
    """
    last_rev = data.last_historical_revenue
    revenues = forecast_revenue(last_rev, data.revenue_growth_rates)

    ebit_list: list[float] = []
    nopat_list: list[float] = []
    depreciation_list: list[float] = []
    capex_list: list[float] = []
    delta_nwc_list: list[float] = []
    fcff_list: list[float] = []

    prev_revenue = last_rev

    for t, rev in enumerate(revenues):
        # 1. Operating Performance
        ebit = rev * data.ebit_margin_forecast[t]
        nopat = ebit * (1.0 - data.tax_rate)

        # 2. Non-Cash Additions & Reinvestment
        depr = rev * data.dna_pct_rev[t]
        capex = rev * data.capex_pct_rev[t]

        # Working Capital Investment based on incremental revenue change
        revenue_change = rev - prev_revenue
        delta_nwc = revenue_change * data.nwc_pct_rev[t]

        # 3. Free Cash Flow to Firm (FCFF)
        # FCFF = NOPAT + Depreciation - CapEx - ΔNWC
        fcff = nopat + depr - capex - delta_nwc

        ebit_list.append(ebit)
        nopat_list.append(nopat)
        depreciation_list.append(depr)
        capex_list.append(capex)
        delta_nwc_list.append(delta_nwc)
        fcff_list.append(fcff)

        prev_revenue = rev

    return ForecastSchedule(
        projected_revenue=revenues,
        projected_ebit=ebit_list,
        projected_nopat=nopat_list,
        projected_depreciation=depreciation_list,
        projected_capex=capex_list,
        projected_delta_nwc=delta_nwc_list,
        projected_fcff=fcff_list,
    )
