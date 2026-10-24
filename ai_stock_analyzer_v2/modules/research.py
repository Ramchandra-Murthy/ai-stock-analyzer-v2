import streamlit as st

from components.charts.candlestick_chart import plot_candlestick
from components.technical_summary import show_technical_summary
from services.ai_service import get_ai_recommendation
from services.fundamental_score_service import calculate_fundamental_score
from services.investment_thesis_service import generate_investment_thesis
from services.news_service import get_company_news
from services.recommendation_service import generate_recommendation
from services.research_service import get_stock_profile
from services.scenario_service import generate_scenario_analysis
from services.score_service import calculate_investment_score
from services.technical_score_service import calculate_technical_score
from services.technical_service import get_price_history
from services.trade_plan_service import generate_trade_plan
from services.ui_formatters import (
    format_debt_to_equity,
    format_large_rupees,
    format_market_cap,
    format_percent,
    format_price,
    format_ratio,
    safe_progress,
)
from services.valuation_service import generate_valuation_analysis
from services.valuation_v43_service import generate_valuation_v43


def show():
    st.title("Stock Research Terminal")
    st.caption("Professional Equity Research Platform")

    st.divider()

    search_col, button_col = st.columns([3, 1])

    with search_col:
        entered_symbol = st.text_input(
            "Enter NSE Symbol",
            value="RELIANCE",
            key="research_symbol_input",
        )
        entered_symbol = entered_symbol.strip().upper()

    with button_col:
        st.write("")
        st.write("")
        analyze = st.button(
            "Analyze",
            use_container_width=True,
            key="research_analyze_button",
        )

    if "research_analyzed" not in st.session_state:
        st.session_state["research_analyzed"] = False

    if "research_active_symbol" not in st.session_state:
        st.session_state["research_active_symbol"] = None

    if analyze:
        if not entered_symbol:
            st.warning("Please enter an NSE symbol.")
            return
        st.session_state["research_analyzed"] = True
        st.session_state["research_active_symbol"] = entered_symbol
        st.session_state.pop("research_pdf", None)
        st.session_state.pop("research_pdf_symbol", None)
        st.session_state.pop("research_pdf_name", None)

    if not st.session_state["research_analyzed"]:
        return

    symbol = st.session_state.get("research_active_symbol")
    if not symbol:
        return

    if entered_symbol and entered_symbol != symbol:
        st.info(f"Showing analysis for {symbol}. " f"Click Analyze to load {entered_symbol}.")

    try:
        with st.spinner("Fetching stock information..."):
            data = get_stock_profile(symbol)
            history = get_price_history(symbol)
    except Exception as error:
        st.error(f"Unable to fetch stock information: {error}")
        return

    if not data:
        st.error("Unable to fetch stock information.")
        return

    try:
        ai_result = get_ai_recommendation(data, history)
        if not isinstance(ai_result, dict):
            ai_result = {}
    except Exception as error:
        st.warning(f"AI recommendation unavailable: {error}")
        ai_result = {}

    try:
        news = get_company_news(symbol)
        if not news:
            news = []
    except Exception as error:
        st.warning(f"Company news unavailable: {error}")
        news = []

    try:
        if history is not None and not history.empty:
            technical_score, technical_reasons = calculate_technical_score(history)
        else:
            technical_score = None
            technical_reasons = ["Historical price data unavailable."]
    except Exception as error:
        technical_score = None
        technical_reasons = [f"Technical scoring unavailable: {error}"]

    try:
        fundamental_score, fundamental_reasons = calculate_fundamental_score(data)
    except Exception as error:
        fundamental_score = None
        fundamental_reasons = [f"Fundamental scoring unavailable: {error}"]

    try:
        investment_score, score_breakdown = calculate_investment_score(
            technical_score=technical_score,
            fundamental_score=fundamental_score,
            ai_result=ai_result,
            data=data,
        )
    except Exception as error:
        st.warning(f"Investment score unavailable: {error}")
        investment_score = None
        score_breakdown = {}

    try:
        recommendation_result = generate_recommendation(
            investment_score=investment_score,
        )
        if not isinstance(recommendation_result, dict):
            recommendation_result = {}
    except Exception as error:
        st.warning(f"Recommendation engine unavailable: {error}")
        recommendation_result = {}

    try:
        trade_plan = generate_trade_plan(
            history=history,
            technical_score=technical_score,
            symbol=symbol,
        )
        if not isinstance(trade_plan, dict):
            trade_plan = {
                "status": "ERROR",
                "message": "Invalid trade plan result.",
            }
        elif trade_plan.get("status") == "INSUFFICIENT DATA":
            trade_plan.setdefault("signal", "INSUFFICIENT DATA")
    except Exception as error:
        st.warning(f"Trade planning engine unavailable: {error}")
        trade_plan = {
            "status": "ERROR",
            "message": str(error),
        }

    try:
        investment_thesis = generate_investment_thesis(
            data=data,
            investment_score=investment_score,
            technical_score=technical_score,
            fundamental_score=fundamental_score,
            ai_result=ai_result,
            score_breakdown=score_breakdown,
            technical_reasons=technical_reasons,
            fundamental_reasons=fundamental_reasons,
            trade_plan=trade_plan,
        )
        if not isinstance(investment_thesis, dict):
            investment_thesis = {}
    except Exception as error:
        st.warning(f"Investment thesis unavailable: {error}")
        investment_thesis = {}

    try:
        scenario_analysis = generate_scenario_analysis(
            data=data,
            investment_score=investment_score,
            technical_score=technical_score,
            fundamental_score=fundamental_score,
            ai_result=ai_result,
            score_breakdown=score_breakdown,
            trade_plan=trade_plan,
        )
        if not isinstance(scenario_analysis, dict):
            scenario_analysis = {}
    except Exception as error:
        st.warning(f"Scenario analysis unavailable: {error}")
        scenario_analysis = {}

    try:
        valuation_analysis = generate_valuation_analysis(
            data=data,
            fundamental_score=fundamental_score,
            investment_score=investment_score,
        )
        if not isinstance(valuation_analysis, dict):
            valuation_analysis = {
                "status": "UNAVAILABLE",
                "message": "Invalid valuation result.",
            }
    except Exception as error:
        st.warning(f"Valuation analysis unavailable: {error}")
        valuation_analysis = {
            "status": "UNAVAILABLE",
            "message": str(error),
        }

    try:
        valuation_v43 = generate_valuation_v43(
            symbol=symbol,
            company_data=data,
        )
        if not isinstance(valuation_v43, dict):
            valuation_v43 = {
                "status": "UNAVAILABLE",
                "message": "Invalid V4.3 valuation result.",
            }
    except Exception as error:
        st.warning(f"Valuation V4.3 unavailable: {error}")
        valuation_v43 = {
            "status": "UNAVAILABLE",
            "message": str(error),
        }

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Overview", "Financials", "Technical", "AI Analysis", "News"]
    )

    with tab1:
        st.subheader("Company Profile")
        profile_col, market_col = st.columns([3, 2])
        with profile_col:
            st.write("**Company**")
            st.write(data.get("company") or "N/A")
            st.write("**Sector**")
            st.write(data.get("sector") or "N/A")
            st.write("**Industry**")
            st.write(data.get("industry") or "N/A")
        with market_col:
            st.metric("Current Price", format_price(data.get("price")))
            st.metric("Market Cap", format_market_cap(data.get("market_cap")))
            st.metric("Currency", data.get("currency", "N/A"))

    with tab2:
        st.subheader("Financial Ratios")
        c1, c2 = st.columns(2)
        with c1:
            st.metric("P/E", data.get("pe", "N/A"))
            st.metric("EPS", data.get("eps", "N/A"))
        with c2:
            st.metric("P/B", data.get("pb", "N/A"))
            st.metric("Beta", data.get("beta", "N/A"))

        st.write("### Profitability & Financial Health")
        a1, a2 = st.columns(2)
        with a1:
            st.metric("ROA", format_percent(data.get("roa")))
            st.metric("Current Ratio", format_ratio(data.get("current_ratio")))
        with a2:
            st.metric("Debt / Equity", format_debt_to_equity(data.get("debt_to_equity")))

        st.write("### Growth")
        g1, g2 = st.columns(2)
        with g1:
            st.metric("Revenue Growth", format_percent(data.get("revenue_growth")))
        with g2:
            st.metric("Earnings Growth", format_percent(data.get("earnings_growth")))

        st.write("### Balance Sheet")
        b1, b2 = st.columns(2)
        with b1:
            st.metric("Total Debt", format_large_rupees(data.get("total_debt")))
        with b2:
            st.metric("Total Cash", format_large_rupees(data.get("total_cash")))

        st.write("### Cash Flow")
        cf1, cf2 = st.columns(2)
        with cf1:
            st.metric("Operating Cash Flow", format_large_rupees(data.get("operating_cash_flow")))
        with cf2:
            st.metric("Free Cash Flow", format_large_rupees(data.get("free_cash_flow")))

    with tab3:
        st.subheader("Technical Analysis")
        if history is not None and not history.empty:
            try:
                st.plotly_chart(plot_candlestick(history), use_container_width=True)
            except Exception as error:
                st.error(f"Unable to display price chart: {error}")
            st.divider()
            try:
                show_technical_summary(history)
            except Exception as error:
                st.error(f"Unable to display technical summary: {error}")
        else:
            st.warning("No historical price data available.")

    with tab4:
        st.subheader("AI Investment Analysis")
        recommendation = recommendation_result.get("recommendation", "INSUFFICIENT DATA")
        st.metric(
            "Overall Investment Score",
            f"{investment_score}/100" if investment_score is not None else "N/A",
        )
        st.metric("Recommendation", recommendation)

        st.write("### Component Scores")
        for label, value in (
            ("Technical", score_breakdown.get("Technical", technical_score)),
            ("Fundamental", score_breakdown.get("Fundamental", fundamental_score)),
            ("AI Model", score_breakdown.get("AI")),
            ("Stability", score_breakdown.get("Stability")),
        ):
            st.metric(label, f"{value:.0f}/100" if value is not None else "N/A")

        confidence = recommendation_result.get("confidence")
        overall_score = recommendation_result.get("overall_score")
        st.metric("Confidence", f"{confidence}%" if confidence is not None else "N/A")
        st.progress(safe_progress(confidence))
        st.metric("Overall Score", f"{overall_score}/100" if overall_score is not None else "N/A")

        st.subheader("Target Price & Trade Plan")
        if trade_plan.get("status") == "OK":
            for label, value in (
                ("Current Price", trade_plan.get("current_price")),
                ("Target Price", trade_plan.get("target_price")),
                ("Stop Loss", trade_plan.get("stop_loss")),
                ("ATR", trade_plan.get("atr")),
                ("Support", trade_plan.get("support")),
                ("Resistance", trade_plan.get("resistance")),
            ):
                st.metric(label, format_price(value))
        else:
            st.warning(trade_plan.get("message", "Trade planning data unavailable."))

        st.subheader("AI Model Analysis")
        ai_score = ai_result.get("score")
        st.metric("AI Score", f"{ai_score}/100" if ai_score is not None else "N/A")
        st.metric("Risk Level", ai_result.get("risk", "Unknown"))
        st.metric("AI Verdict", ai_result.get("recommendation", "INSUFFICIENT DATA"))

        st.subheader("Technical Reasons")
        for reason in technical_reasons:
            st.write(f"- {reason}")
        st.subheader("Fundamental Reasons")
        for reason in fundamental_reasons:
            st.write(f"- {reason}")
        st.subheader("Final Recommendation")
        st.metric("Investment Verdict", recommendation)

    with tab5:
        st.subheader("Company News")
        if news:
            for item in news:
                if isinstance(item, dict):
                    title = item.get("title", "Untitled")
                    link = item.get("link")
                    st.markdown(f"- [{title}]({link})" if link else f"- {title}")
                else:
                    st.write(f"- {item}")
        else:
            st.info("No company news available.")
