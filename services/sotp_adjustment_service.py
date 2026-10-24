from services.sotp_balance_sheet_detail_service import (
    get_sotp_balance_sheet_details,
)
from services.sotp_balance_sheet_service import (
    get_sotp_balance_sheet_data,
)
from services.sotp_financial_asset_overlap_service import (
    evaluate_financial_asset_overlap,
)
from services.sotp_investment_policy_service import (
    generate_sotp_investment_policy,
)
from services.sotp_liquidity_policy_service import (
    evaluate_short_term_investment_policy,
)
from services.sotp_new_energy_scenario_policy_service import (
    authorize_sotp_new_energy_scenarios,
)

# ==========================================================
# HELPERS
# ==========================================================


def _safe_float(value):
    """Convert value to float or return None."""

    try:
        if value is None:
            return None

        value = float(value)

        if value != value:
            return None

        return value

    except (TypeError, ValueError):
        return None


def _round(value, digits=2):
    """Round numeric value safely."""

    value = _safe_float(value)

    if value is None:
        return None

    return round(value, digits)


# ==========================================================
# SOTP ADJUSTMENT ENGINE
# ==========================================================


def build_sotp_adjustments(symbol):
    """
    Build the SOTP equity-bridge adjustment framework.

    Monetary values are INR crore.

    IMPORTANT ARCHITECTURE

    Operating / segment EV:
        O2C
        Digital
        Retail
        Upstream
        New Energy scenarios

    Equity bridge:
        - net debt
        + authorized non-operating assets
        - authorized ownership adjustments
        +/- other authorized bridge items

    New Energy scenario values are NOT equity-bridge
    adjustments. They belong in gross SOTP enterprise value.
    """

    # ======================================================
    # CORE DATA
    # ======================================================

    summary = get_sotp_balance_sheet_data(symbol)
    details = get_sotp_balance_sheet_details(symbol)

    if not isinstance(summary, dict):
        summary = {}

    if not isinstance(details, dict):
        details = {}

    if details.get("status") != "OK":
        return {
            "status": "UNAVAILABLE",
            "symbol": symbol,
            "message": details.get(
                "message",
                "Detailed balance-sheet data unavailable.",
            ),
        }

    # ======================================================
    # POLICY SERVICES
    # ======================================================

    try:
        liquidity_policy = evaluate_short_term_investment_policy(symbol)
    except Exception as exc:
        liquidity_policy = {
            "status": "UNAVAILABLE",
            "message": str(exc),
        }

    try:
        financial_asset_overlap = evaluate_financial_asset_overlap(symbol)
    except Exception as exc:
        financial_asset_overlap = {
            "status": "UNAVAILABLE",
            "message": str(exc),
        }

    try:
        investment_policy = generate_sotp_investment_policy(symbol)
    except Exception as exc:
        investment_policy = {
            "status": "UNAVAILABLE",
            "message": str(exc),
        }

    try:
        new_energy_policy = authorize_sotp_new_energy_scenarios(symbol)
    except Exception as exc:
        new_energy_policy = {
            "status": "UNAVAILABLE",
            "message": str(exc),
        }

    # ======================================================
    # EXTRACT DETAIL BLOCKS
    # ======================================================

    debt = details.get("debt", {})
    cash = details.get("cash", {})
    investments = details.get("investments", {})
    ownership = details.get("ownership", {})
    diagnostics = details.get("diagnostics", {})

    if not isinstance(debt, dict):
        debt = {}

    if not isinstance(cash, dict):
        cash = {}

    if not isinstance(investments, dict):
        investments = {}

    if not isinstance(ownership, dict):
        ownership = {}

    if not isinstance(diagnostics, dict):
        diagnostics = {}

    # ======================================================
    # DEBT
    # ======================================================

    total_debt = _safe_float(debt.get("total_debt"))
    provider_net_debt = _safe_float(debt.get("provider_net_debt"))

    lease_obligations = _safe_float(debt.get("capital_lease_obligations"))

    # ======================================================
    # CASH / LIQUIDITY
    # ======================================================

    cash_and_equivalents = _safe_float(cash.get("cash_and_equivalents"))

    restricted_cash = _safe_float(cash.get("restricted_cash"))

    short_term_investments = _safe_float(cash.get("short_term_investments"))

    cash_and_short_term_investments = _safe_float(cash.get("cash_and_short_term_investments"))

    # ======================================================
    # INVESTMENTS
    # ======================================================

    financial_investments = _safe_float(investments.get("financial_investments"))

    long_term_equity_investment = _safe_float(investments.get("long_term_equity_investment"))

    joint_venture_investments = _safe_float(investments.get("joint_venture_investments"))

    associate_investments = _safe_float(investments.get("associate_investments"))

    # ======================================================
    # OWNERSHIP
    # ======================================================

    minority_interest = _safe_float(ownership.get("minority_interest"))

    # ======================================================
    # CONSERVATIVE NET DEBT
    # ======================================================

    conservative_net_debt = None

    if total_debt is not None and cash_and_equivalents is not None:
        conservative_net_debt = total_debt - cash_and_equivalents

    base_equity_bridge_adjustment = None

    if conservative_net_debt is not None:
        base_equity_bridge_adjustment = -conservative_net_debt

    # ======================================================
    # PROVIDER NET-DEBT RECONCILIATION
    # ======================================================

    implied_provider_net_debt = None

    if conservative_net_debt is not None and lease_obligations is not None:
        implied_provider_net_debt = conservative_net_debt - lease_obligations

    provider_net_debt_gap = None

    if provider_net_debt is not None and implied_provider_net_debt is not None:
        provider_net_debt_gap = provider_net_debt - implied_provider_net_debt

    # ======================================================
    # SHORT-TERM INVESTMENT POLICY
    # ======================================================

    short_term_policy_block = {}

    if isinstance(liquidity_policy, dict):
        short_term_policy_block = liquidity_policy.get("sotp_policy", {})

    if not isinstance(short_term_policy_block, dict):
        short_term_policy_block = {}

    short_term_adjustment = _safe_float(short_term_policy_block.get("included_value"))

    if short_term_adjustment is None:
        short_term_adjustment = 0.0

    short_term_pending = _safe_float(short_term_policy_block.get("pending_value"))

    if short_term_pending is None:
        short_term_pending = 0.0

    # ======================================================
    # FINANCIAL-ASSET POLICY
    # ======================================================

    financial_adjustment_block = {}

    if isinstance(financial_asset_overlap, dict):
        financial_adjustment_block = financial_asset_overlap.get(
            "sotp_adjustment",
            {},
        )

    if not isinstance(financial_adjustment_block, dict):
        financial_adjustment_block = {}

    financial_asset_adjustment = _safe_float(financial_adjustment_block.get("included_value"))

    if financial_asset_adjustment is None:
        financial_asset_adjustment = 0.0

    financial_asset_pending = _safe_float(financial_adjustment_block.get("pending_value"))

    if financial_asset_pending is None:
        financial_asset_pending = 0.0

    financial_asset_bridge_ready = bool(
        financial_asset_overlap.get(
            "bridge_ready",
            False,
        )
        if isinstance(financial_asset_overlap, dict)
        else False
    )

    # ======================================================
    # LONG-TERM EQUITY INVESTMENT POLICY
    # ======================================================

    investment_policy_block = {}

    if isinstance(investment_policy, dict):
        investment_policy_block = investment_policy.get("policy", {})

    if not isinstance(investment_policy_block, dict):
        investment_policy_block = {}

    long_term_policy = investment_policy_block.get(
        "long_term_equity_investment",
        {},
    )

    if not isinstance(long_term_policy, dict):
        long_term_policy = {}

    long_term_equity_adjustment = _safe_float(long_term_policy.get("included_value"))

    if long_term_equity_adjustment is None:
        long_term_equity_adjustment = 0.0

    long_term_equity_pending = 0.0

    if long_term_policy.get("policy_status") == "PENDING":
        value = _safe_float(long_term_policy.get("reported_value"))

        if value is not None:
            long_term_equity_pending = value

    # ======================================================
    # MINORITY INTEREST
    # ======================================================

    #
    # Minority interest is factual but not yet authorized
    # for final deduction by the current ownership policy.
    #
    # Keep it visible but excluded from the executable
    # bridge until ownership treatment is finalized.
    #

    minority_interest_adjustment = 0.0
    minority_interest_pending = minority_interest if minority_interest is not None else 0.0

    minority_interest_authorized = False

    # ======================================================
    # NEW ENERGY SCENARIO CONTROL
    # ======================================================

    new_energy_scenarios = {}

    if isinstance(new_energy_policy, dict):
        values = new_energy_policy.get(
            "authorized_scenario_values",
            {},
        )

        if isinstance(values, dict):
            new_energy_scenarios = {
                key: _safe_float(value)
                for key, value in values.items()
                if _safe_float(value) is not None
            }

    new_energy_scenario_authorized = bool(
        new_energy_policy.get(
            "scenario_range_authorized",
            False,
        )
        if isinstance(new_energy_policy, dict)
        else False
    )

    # ======================================================
    # EXECUTABLE EQUITY BRIDGE
    # ======================================================

    #
    # Only authorized adjustments enter this value.
    #
    # New Energy is deliberately excluded because it belongs
    # in gross SOTP enterprise value, not the equity bridge.
    #

    final_equity_bridge_adjustment = None

    if base_equity_bridge_adjustment is not None:
        final_equity_bridge_adjustment = (
            base_equity_bridge_adjustment
            + short_term_adjustment
            + financial_asset_adjustment
            + long_term_equity_adjustment
            + minority_interest_adjustment
        )

    # ======================================================
    # PENDING EXPOSURE
    # ======================================================

    pending_exposure = (
        short_term_pending
        + financial_asset_pending
        + long_term_equity_pending
        + minority_interest_pending
    )

    pending_items = []

    if short_term_pending > 0:
        pending_items.append("SHORT_TERM_INVESTMENTS")

    if financial_asset_pending > 0:
        pending_items.append("FINANCIAL_INVESTMENTS")

    if long_term_equity_pending > 0:
        pending_items.append("LONG_TERM_EQUITY_INVESTMENT")

    if minority_interest_pending > 0:
        pending_items.append("MINORITY_INTEREST")

    # ======================================================
    # STATUS
    # ======================================================

    if final_equity_bridge_adjustment is None:
        bridge_status = "UNAVAILABLE"

    elif pending_items:
        bridge_status = "PROVISIONAL"

    else:
        bridge_status = "FINAL"

    # ======================================================
    # COVERAGE
    # ======================================================

    critical_values = [
        total_debt,
        cash_and_equivalents,
        minority_interest,
        short_term_investments,
    ]

    available_count = sum(value is not None for value in critical_values)

    coverage = available_count / len(critical_values) if critical_values else 0.0

    # ======================================================
    # RETURN
    # ======================================================

    return {
        "status": "OK",
        "version": "V5.0",
        "symbol": details.get(
            "symbol",
            symbol,
        ),
        "period": details.get("period"),
        "currency": "INR",
        "unit": "crore",
        "debt": {
            "total_debt": _round(total_debt),
            "lease_obligations": _round(lease_obligations),
            "provider_net_debt": _round(provider_net_debt),
        },
        "cash": {
            "cash_and_equivalents": _round(cash_and_equivalents),
            "restricted_cash": _round(restricted_cash),
            "short_term_investments": _round(short_term_investments),
            "cash_and_short_term_investments": _round(cash_and_short_term_investments),
        },
        "investments": {
            "financial_investments": _round(financial_investments),
            "long_term_equity_investment": _round(long_term_equity_investment),
            "joint_venture_investments": _round(joint_venture_investments),
            "associate_investments": _round(associate_investments),
        },
        "ownership": {
            "minority_interest": _round(minority_interest),
        },
        "policy_controls": {
            "short_term_investments": {
                "included_value": _round(short_term_adjustment),
                "pending_value": _round(short_term_pending),
                "status": short_term_policy_block.get("status"),
                "treatment": short_term_policy_block.get("treatment"),
            },
            "financial_investments": {
                "included_value": _round(financial_asset_adjustment),
                "pending_value": _round(financial_asset_pending),
                "bridge_ready": (financial_asset_bridge_ready),
            },
            "long_term_equity_investment": {
                "included_value": _round(long_term_equity_adjustment),
                "pending_value": _round(long_term_equity_pending),
                "status": long_term_policy.get("policy_status"),
                "treatment": long_term_policy.get("treatment"),
            },
            "minority_interest": {
                "reported_value": _round(minority_interest),
                "included_adjustment": 0.0,
                "authorized": (minority_interest_authorized),
                "status": "PENDING_OWNERSHIP_REVIEW",
            },
        },
        "new_energy": {
            "scenario_range_authorized": (new_energy_scenario_authorized),
            "scenario_values": (new_energy_scenarios),
            "equity_bridge_treatment": ("EXCLUDED_FROM_BRIDGE_" "INCLUDE_IN_GROSS_SOTP_EV"),
        },
        "equity_bridge": {
            "conservative_net_debt": _round(conservative_net_debt),
            "base_equity_bridge_adjustment": _round(base_equity_bridge_adjustment),
            "authorized_adjustments": {
                "short_term_investments": _round(short_term_adjustment),
                "financial_investments": _round(financial_asset_adjustment),
                "long_term_equity_investment": _round(long_term_equity_adjustment),
                "minority_interest": _round(minority_interest_adjustment),
            },
            "final_equity_bridge_adjustment": _round(final_equity_bridge_adjustment),
            "pending_exposure": _round(pending_exposure),
            "pending_items": pending_items,
            "pending_item_count": len(pending_items),
            "status": bridge_status,
        },
        "diagnostics": {
            "implied_provider_net_debt": _round(implied_provider_net_debt),
            "provider_net_debt_gap": _round(provider_net_debt_gap),
            "detail_service_diagnostics": diagnostics,
            "summary_reported_enterprise_value": (summary.get("reported_enterprise_value")),
            "summary_ev_reconciliation_gap": (summary.get("ev_reconciliation_gap")),
        },
        "treatment": {
            "total_debt": "DEDUCT",
            "cash_and_equivalents": "ADD",
            "restricted_cash": ("EXCLUDE_FROM_BASE_CASH"),
            "lease_obligations": ("DO_NOT_DOUBLE_COUNT"),
            "short_term_investments": ("POLICY_CONTROLLED"),
            "financial_investments": ("POLICY_CONTROLLED"),
            "long_term_equity_investment": ("POLICY_CONTROLLED"),
            "joint_venture_investments": ("COMPONENT_ONLY"),
            "associate_investments": ("COMPONENT_ONLY"),
            "minority_interest": ("PENDING_AUTHORIZATION"),
            "new_energy": ("SEGMENT_SCENARIO_EV"),
        },
        "coverage": round(
            coverage,
            4,
        ),
        "coverage_percent": round(
            coverage * 100.0,
            1,
        ),
        "warnings": [
            ("The executable equity bridge includes " "only authorized adjustments."),
            (
                "Pending investment balances are "
                "informational and are not added to "
                "equity value."
            ),
            (
                "Minority interest remains excluded "
                "from the executable bridge until "
                "ownership treatment is authorized."
            ),
            (
                "New Energy scenario values belong in "
                "gross SOTP enterprise value and must "
                "not also enter the equity bridge."
            ),
            (
                "Lease obligations are not separately "
                "deducted because the selected debt "
                "definition already incorporates them."
            ),
        ],
    }
