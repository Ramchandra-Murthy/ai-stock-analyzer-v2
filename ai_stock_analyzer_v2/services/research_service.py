import math

import yfinance as yf

from services.market_service import get_latest_available_price


def _get_fast_info(ticker):
    """Return Yahoo's fast quote snapshot when available."""
    try:
        fast_info = ticker.fast_info
        return fast_info if fast_info is not None else {}
    except Exception:
        return {}


def _safe_float(value):
    """Convert a value to a finite float or return None."""
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def _get_mapping_value(mapping, *keys):
    """Return the first usable value from a mapping-like object."""
    for key in keys:
        try:
            value = mapping.get(key)
        except Exception:
            value = None
        if value is not None:
            return value
    return None


def _get_statement_value(statement, possible_names, column):
    """Return the first matching financial-statement value."""
    if statement is None or statement.empty:
        return None
    for name in possible_names:
        if name in statement.index:
            try:
                return _safe_float(statement.loc[name, column])
            except Exception:
                continue
    return None


def _get_statement_values(statement, possible_names, limit=2):
    """Return the latest statement values for growth calculations."""
    if statement is None or statement.empty:
        return []
    for name in possible_names:
        if name in statement.index:
            values = []
            for column in list(statement.columns)[:limit]:
                value = _safe_float(statement.loc[name, column])
                if value is not None:
                    values.append(value)
            return values
    return []


def _calculate_roe(ticker):
    """Calculate ROE when Yahoo does not provide it."""
    try:
        income = ticker.financials
        balance = ticker.balance_sheet
        if income is None or income.empty or balance is None or balance.empty:
            return None
        common = [column for column in income.columns if column in balance.columns]
        if not common:
            return None
        latest = common[0]
        net_income = _get_statement_value(
            income,
            [
                "Net Income",
                "Net Income Common Stockholders",
                "Net Income Including Noncontrolling Interests",
            ],
            latest,
        )
        equity_names = [
            "Stockholders Equity",
            "Total Stockholder Equity",
            "Common Stock Equity",
        ]
        current = _get_statement_value(balance, equity_names, latest)
        if net_income is None or current is None or current <= 0:
            return None
        previous = None
        try:
            position = list(balance.columns).index(latest)
            if position + 1 < len(balance.columns):
                previous = _get_statement_value(
                    balance, equity_names, balance.columns[position + 1]
                )
        except Exception:
            previous = None
        average = (current + previous) / 2 if previous and previous > 0 else current
        roe = net_income / average if average > 0 else None
        return roe if roe is not None and math.isfinite(roe) else None
    except Exception as error:
        print(f"ROE Calculation Error: {error}")
        return None


def _calculate_roa(ticker):
    """Calculate ROA when Yahoo does not provide it."""
    try:
        income = ticker.financials
        balance = ticker.balance_sheet
        if income is None or income.empty or balance is None or balance.empty:
            return None
        common = [column for column in income.columns if column in balance.columns]
        if not common:
            return None
        latest = common[0]
        net_income = _get_statement_value(
            income,
            [
                "Net Income",
                "Net Income Common Stockholders",
                "Net Income Including Noncontrolling Interests",
            ],
            latest,
        )
        assets = _get_statement_value(balance, ["Total Assets"], latest)
        if net_income is None or assets is None or assets <= 0:
            return None
        previous = None
        try:
            position = list(balance.columns).index(latest)
            if position + 1 < len(balance.columns):
                previous = _get_statement_value(
                    balance, ["Total Assets"], balance.columns[position + 1]
                )
        except Exception:
            previous = None
        average = (assets + previous) / 2 if previous and previous > 0 else assets
        roa = net_income / average if average > 0 else None
        return roa if roa is not None and math.isfinite(roa) else None
    except Exception as error:
        print(f"ROA Calculation Error: {error}")
        return None


def _calculate_current_ratio(ticker):
    """Calculate current assets divided by current liabilities."""
    try:
        balance = ticker.balance_sheet
        if balance is None or balance.empty:
            return None
        latest = balance.columns[0]
        assets = _get_statement_value(balance, ["Current Assets", "Total Current Assets"], latest)
        liabilities = _get_statement_value(
            balance,
            ["Current Liabilities", "Total Current Liabilities"],
            latest,
        )
        if assets is None or liabilities is None or liabilities <= 0:
            return None
        ratio = assets / liabilities
        return ratio if math.isfinite(ratio) else None
    except Exception as error:
        print(f"Current Ratio Calculation Error: {error}")
        return None


def _calculate_operating_cash_flow(ticker):
    """Retrieve operating cash flow from the latest annual statement."""
    try:
        cash_flow = ticker.cashflow
        if cash_flow is None or cash_flow.empty:
            return None
        latest = cash_flow.columns[0]
        return _get_statement_value(
            cash_flow,
            [
                "Operating Cash Flow",
                "Total Cash From Operating Activities",
                "Cash Flow From Continuing Operating Activities",
            ],
            latest,
        )
    except Exception as error:
        print(f"Operating Cash Flow Calculation Error: {error}")
        return None


def _calculate_free_cash_flow(ticker):
    """Retrieve or calculate free cash flow."""
    try:
        cash_flow = ticker.cashflow
        if cash_flow is None or cash_flow.empty:
            return None
        latest = cash_flow.columns[0]
        value = _get_statement_value(cash_flow, ["Free Cash Flow"], latest)
        if value is not None:
            return value
        operating = _get_statement_value(
            cash_flow,
            [
                "Operating Cash Flow",
                "Total Cash From Operating Activities",
                "Cash Flow From Continuing Operating Activities",
            ],
            latest,
        )
        capex = _get_statement_value(
            cash_flow,
            ["Capital Expenditure", "Capital Expenditures"],
            latest,
        )
        if operating is None or capex is None:
            return None
        value = operating + capex if capex < 0 else operating - capex
        return value if math.isfinite(value) else None
    except Exception as error:
        print(f"Free Cash Flow Calculation Error: {error}")
        return None


def get_stock_profile(symbol):
    """Return the canonical company, quote, valuation and fundamental data contract."""
    symbol = symbol.strip().upper()
    if "." not in symbol:
        symbol = f"{symbol}.NS"

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        fast_info = _get_fast_info(ticker)
        exchange = "BSE" if symbol.endswith(".BO") else "NSE"
        market_quote = get_latest_available_price(symbol)

        price = _safe_float(market_quote.get("price"))
        previous_close = _safe_float(market_quote.get("previous_close"))
        observed_at = market_quote.get("observed_at")
        if observed_at is not None and not isinstance(observed_at, str):
            observed_at = str(observed_at)

        income = ticker.financials
        balance = ticker.balance_sheet

        equity_names = [
            "Stockholders Equity",
            "Total Stockholder Equity",
            "Common Stock Equity",
        ]
        shares_names = [
            "Ordinary Shares Number",
            "Share Issued",
            "Common Stock Shares Outstanding",
        ]
        debt_names = ["Total Debt", "Total Debt And Capital Lease Obligations"]
        cash_names = [
            "Cash And Cash Equivalents",
            "Cash Cash Equivalents And Short Term Investments",
            "Other Short Term Investments",
        ]
        revenue_names = ["Total Revenue", "Operating Revenue", "Revenue"]
        net_income_names = [
            "Net Income",
            "Net Income Common Stockholders",
            "Net Income Including Noncontrolling Interests",
        ]
        operating_income_names = ["Operating Income", "Operating Income As Reported"]

        balance_latest = balance.columns[0] if balance is not None and not balance.empty else None
        income_latest = income.columns[0] if income is not None and not income.empty else None

        shares_outstanding = _safe_float(info.get("sharesOutstanding"))
        if shares_outstanding is None:
            shares_outstanding = _safe_float(
                _get_mapping_value(fast_info, "shares", "shares_outstanding")
            )
        if shares_outstanding is None and balance_latest is not None:
            shares_outstanding = _get_statement_value(balance, shares_names, balance_latest)

        equity = None
        if balance_latest is not None:
            equity = _get_statement_value(balance, equity_names, balance_latest)
        total_debt = _safe_float(info.get("totalDebt"))
        if total_debt is None and balance_latest is not None:
            total_debt = _get_statement_value(balance, debt_names, balance_latest)
        total_cash = _safe_float(info.get("totalCash"))
        if total_cash is None and balance_latest is not None:
            total_cash = _get_statement_value(balance, cash_names, balance_latest)

        revenue = _safe_float(info.get("totalRevenue"))
        if revenue is None and income_latest is not None:
            revenue = _get_statement_value(income, revenue_names, income_latest)
        net_income = _safe_float(info.get("netIncomeToCommon"))
        if net_income is None and income_latest is not None:
            net_income = _get_statement_value(income, net_income_names, income_latest)
        operating_income = _safe_float(info.get("operatingIncome"))
        if operating_income is None and income_latest is not None:
            operating_income = _get_statement_value(income, operating_income_names, income_latest)

        market_cap = _safe_float(info.get("marketCap"))
        if market_cap is None:
            market_cap = _safe_float(_get_mapping_value(fast_info, "market_cap"))
        if market_cap is None and price is not None and shares_outstanding is not None:
            market_cap = price * shares_outstanding

        eps = _safe_float(info.get("trailingEps"))
        if eps is None and net_income is not None and shares_outstanding:
            eps = net_income / shares_outstanding
        pe = _safe_float(info.get("trailingPE"))
        if pe is None and price is not None and eps is not None and eps > 0:
            pe = price / eps

        book_value_per_share = None
        if equity is not None and shares_outstanding:
            book_value_per_share = equity / shares_outstanding
        pb = _safe_float(info.get("priceToBook"))
        if pb is None and price is not None and book_value_per_share and book_value_per_share > 0:
            pb = price / book_value_per_share

        roe = _safe_float(info.get("returnOnEquity"))
        if roe is None:
            roe = _calculate_roe(ticker)
        roa = _safe_float(info.get("returnOnAssets"))
        if roa is None:
            roa = _calculate_roa(ticker)

        current_ratio = _safe_float(info.get("currentRatio"))
        if current_ratio is None:
            current_ratio = _calculate_current_ratio(ticker)

        operating_cash_flow = _safe_float(info.get("operatingCashflow"))
        if operating_cash_flow is None:
            operating_cash_flow = _calculate_operating_cash_flow(ticker)

        free_cash_flow = _safe_float(info.get("freeCashflow"))
        if free_cash_flow is None:
            free_cash_flow = _calculate_free_cash_flow(ticker)

        volume = _safe_float(_get_mapping_value(fast_info, "last_volume"))
        if volume is None:
            volume = _safe_float(info.get("volume"))

        profit_margin = _safe_float(info.get("profitMargins"))
        if profit_margin is None and revenue and net_income is not None:
            profit_margin = net_income / revenue

        operating_margin = _safe_float(info.get("operatingMargins"))
        if operating_margin is None and revenue and operating_income is not None:
            operating_margin = operating_income / revenue

        revenue_growth = _safe_float(info.get("revenueGrowth"))
        if revenue_growth is None:
            revenue_values = _get_statement_values(income, revenue_names)
            if len(revenue_values) >= 2 and revenue_values[1] != 0:
                revenue_growth = (revenue_values[0] - revenue_values[1]) / abs(revenue_values[1])

        earnings_growth = _safe_float(info.get("earningsGrowth"))
        if earnings_growth is None:
            earnings_values = _get_statement_values(income, net_income_names)
            if len(earnings_values) >= 2 and earnings_values[1] != 0:
                earnings_growth = (earnings_values[0] - earnings_values[1]) / abs(
                    earnings_values[1]
                )

        debt_to_equity = _safe_float(info.get("debtToEquity"))
        if debt_to_equity is None and total_debt is not None and equity and equity != 0:
            debt_to_equity = total_debt / equity

        dividend_yield = _safe_float(info.get("dividendYield"))
        if dividend_yield is None and price is not None:
            try:
                dividends = ticker.dividends
                if dividends is not None and not dividends.empty:
                    cutoff = dividends.index.max() - dividends.index.max().__class__(days=365)
                    annual_dividends = float(dividends[dividends.index >= cutoff].sum())
                    if annual_dividends > 0:
                        dividend_yield = annual_dividends / price
            except Exception:
                dividend_yield = None

        return {
            "company": info.get("longName") or info.get("shortName") or symbol,
            "symbol": symbol,
            "exchange": exchange,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "currency": info.get("currency", "INR"),
            "price": price,
            "previous_close": previous_close,
            "price_source": market_quote.get("source", "Yahoo Finance"),
            "price_observed_at": observed_at,
            "quote_timestamp": observed_at,
            "quote_frequency": market_quote.get("frequency", "unavailable"),
            "is_intraday": market_quote.get("is_intraday", False),
            "is_tick_live": market_quote.get("is_tick_live", False),
            "volume": volume,
            "market_cap": market_cap,
            "pe": pe,
            "forward_pe": _safe_float(info.get("forwardPE")),
            "pb": pb,
            "eps": eps,
            "forward_eps": _safe_float(info.get("forwardEps")),
            "beta": _safe_float(info.get("beta")),
            "dividend_yield": dividend_yield,
            "roe": roe,
            "roa": roa,
            "profit_margin": profit_margin,
            "operating_margin": operating_margin,
            "revenue_growth": revenue_growth,
            "earnings_growth": earnings_growth,
            "debt_to_equity": debt_to_equity,
            "current_ratio": current_ratio,
            "total_debt": total_debt,
            "total_cash": total_cash,
            "operating_cash_flow": operating_cash_flow,
            "free_cash_flow": free_cash_flow,
            "ebitda": _safe_float(info.get("ebitda")),
            "enterprise_value": _safe_float(info.get("enterpriseValue")),
            "shares_outstanding": shares_outstanding,
            "total_revenue": revenue,
            "net_income": net_income,
            "enterprise_to_ebitda": _safe_float(info.get("enterpriseToEbitda")),
            "enterprise_to_revenue": _safe_float(info.get("enterpriseToRevenue")),
            "market_state": "UNKNOWN",
        }
    except Exception as error:
        print(f"Stock Profile Error: {error}")
        return None
