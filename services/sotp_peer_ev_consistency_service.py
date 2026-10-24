from __future__ import annotations

from typing import Any

import yfinance as yf


def _num(value: Any):
    if isinstance(value, (int, float)):
        try:
            if value != value:  # NaN
                return None
        except Exception:
            pass
        return float(value)
    return None


def _to_crore(value: Any):
    value = _num(value)

    if value is None:
        return None

    return value / 1e7


def analyze_peer_ev_consistency(
    ticker: str,
) -> dict[str, Any]:
    """
    Reconstruct provider enterprise value and examine the
    treatment of debt, leases and cash.

    This service is diagnostic.

    It does NOT infer the treatment of spectrum or other
    debt-like liabilities unless those liabilities are
    explicitly identifiable from provider data.
    """

    ticker = ticker.upper().strip()

    try:
        t = yf.Ticker(ticker)

        info = t.info or {}
        bs = t.balance_sheet

    except Exception as exc:
        return {
            "status": "ERROR",
            "ticker": ticker,
            "message": str(exc),
        }

    if bs is None or bs.empty:
        return {
            "status": "ERROR",
            "ticker": ticker,
            "message": "Balance sheet unavailable.",
        }

    period = bs.columns[0]

    def bs_value(row: str):
        if row not in bs.index:
            return None

        return _to_crore(bs.loc[row, period])

    # -------------------------------------------------
    # PROVIDER VALUATION DATA
    # -------------------------------------------------

    market_cap = _to_crore(info.get("marketCap"))
    enterprise_value = _to_crore(info.get("enterpriseValue"))
    total_debt_info = _to_crore(info.get("totalDebt"))
    total_cash_info = _to_crore(info.get("totalCash"))
    ebitda = _to_crore(info.get("ebitda"))

    ev_ebitda = _num(info.get("enterpriseToEbitda"))

    # -------------------------------------------------
    # BALANCE-SHEET DATA
    # -------------------------------------------------

    total_debt_bs = bs_value("Total Debt")
    net_debt_bs = bs_value("Net Debt")

    lease_liabilities = bs_value("Capital Lease Obligations")

    cash_equivalents = bs_value("Cash And Cash Equivalents")

    cash_and_short_term = bs_value("Cash Cash Equivalents And Short Term Investments")

    short_term_investments = bs_value("Other Short Term Investments")

    restricted_cash = bs_value("Restricted Cash")

    # -------------------------------------------------
    # DEBT RECONCILIATION
    # -------------------------------------------------

    debt_ex_lease = None

    if total_debt_bs is not None and lease_liabilities is not None:
        debt_ex_lease = total_debt_bs - lease_liabilities

    calculated_net_debt_ex_lease = None

    if debt_ex_lease is not None and cash_equivalents is not None:
        calculated_net_debt_ex_lease = debt_ex_lease - cash_equivalents

    net_debt_gap = None

    if calculated_net_debt_ex_lease is not None and net_debt_bs is not None:
        net_debt_gap = calculated_net_debt_ex_lease - net_debt_bs

    net_debt_excludes_leases = False

    if net_debt_gap is not None:
        net_debt_excludes_leases = abs(net_debt_gap) <= 1.0

    # -------------------------------------------------
    # EV RECONSTRUCTION
    # -------------------------------------------------

    reconstructed_ev = None

    if market_cap is not None and total_debt_info is not None and total_cash_info is not None:
        reconstructed_ev = market_cap + total_debt_info - total_cash_info

    ev_residual = None
    ev_residual_percent = None

    if enterprise_value is not None and reconstructed_ev is not None:
        ev_residual = enterprise_value - reconstructed_ev

        if enterprise_value != 0:
            ev_residual_percent = ev_residual / enterprise_value * 100

    # -------------------------------------------------
    # MULTIPLE RECONCILIATION
    # -------------------------------------------------

    calculated_ev_ebitda = None
    multiple_gap = None

    if enterprise_value is not None and ebitda is not None and ebitda != 0:
        calculated_ev_ebitda = enterprise_value / ebitda

    if calculated_ev_ebitda is not None and ev_ebitda is not None:
        multiple_gap = calculated_ev_ebitda - ev_ebitda

    # -------------------------------------------------
    # CLASSIFICATION
    # -------------------------------------------------

    if (
        reconstructed_ev is not None
        and ev_residual_percent is not None
        and abs(ev_residual_percent) <= 2.0
    ):
        ev_construction_view = "CLOSE_TO_MARKET_CAP_PLUS_TOTAL_DEBT_MINUS_CASH"
    else:
        ev_construction_view = "ADDITIONAL_EV_ADJUSTMENTS_MATERIAL"

    lease_ev_evidence = (
        total_debt_info is not None
        and lease_liabilities is not None
        and total_debt_bs is not None
        and abs(total_debt_info - total_debt_bs) <= 1.0
    )

    # -------------------------------------------------
    # OUTPUT
    # -------------------------------------------------

    return {
        "status": "OK",
        "ticker": ticker,
        "period": str(period),
        "currency": "INR",
        "unit": "crore",
        "provider_valuation": {
            "market_cap": market_cap,
            "enterprise_value": enterprise_value,
            "enterprise_to_ebitda": ev_ebitda,
            "ebitda": ebitda,
            "total_debt": total_debt_info,
            "total_cash": total_cash_info,
        },
        "balance_sheet": {
            "total_debt": total_debt_bs,
            "lease_liabilities": lease_liabilities,
            "debt_ex_lease": debt_ex_lease,
            "net_debt": net_debt_bs,
            "cash_and_equivalents": cash_equivalents,
            "cash_and_short_term_investments": (cash_and_short_term),
            "short_term_investments": (short_term_investments),
            "restricted_cash": restricted_cash,
        },
        "net_debt_reconciliation": {
            "calculated_net_debt_ex_lease": (calculated_net_debt_ex_lease),
            "provider_net_debt": net_debt_bs,
            "gap": net_debt_gap,
            "net_debt_excludes_leases": (net_debt_excludes_leases),
        },
        "ev_reconciliation": {
            "reconstructed_ev": reconstructed_ev,
            "provider_ev": enterprise_value,
            "residual": ev_residual,
            "residual_percent": (ev_residual_percent),
            "view": ev_construction_view,
        },
        "multiple_reconciliation": {
            "provider_multiple": ev_ebitda,
            "calculated_multiple": (calculated_ev_ebitda),
            "gap": multiple_gap,
        },
        "lease_analysis": {
            "lease_liabilities": lease_liabilities,
            "included_in_provider_total_debt": (lease_ev_evidence),
            "provider_net_debt_excludes_leases": (net_debt_excludes_leases),
            "ev_consistency_evidence": ("STRONG" if lease_ev_evidence else "UNRESOLVED"),
        },
        "spectrum_analysis": {
            "explicit_spectrum_liability_found": False,
            "treatment": "UNRESOLVED",
            "reason": (
                "Provider balance-sheet taxonomy does not "
                "identify a spectrum liability explicitly. "
                "EV reconstruction therefore cannot establish "
                "the treatment of spectrum obligations."
            ),
        },
        "warnings": [
            (
                "Enterprise-value reconstruction is diagnostic "
                "and does not establish every provider EV "
                "adjustment."
            ),
            (
                "Total cash from provider valuation data may "
                "differ from balance-sheet cash and equivalents."
            ),
            (
                "Lease treatment can be investigated because "
                "lease liabilities are explicitly identified."
            ),
            ("Spectrum treatment must not be inferred from " "unclassified liability balances."),
        ],
    }
