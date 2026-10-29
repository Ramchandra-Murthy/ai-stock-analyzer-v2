"""AI Stock Analyzer Pro - lazy-loaded Streamlit application entrypoint."""

import streamlit as st

from config.env import load_environment

load_environment()  # make .env credentials (Dhan, Supabase, ...) visible before any page runs


def show_dashboard() -> None:
    """Import the dashboard only when the user opens it."""
    from modules.dashboard import show

    show()


def show_market() -> None:
    from modules.market import show

    show()


def show_portfolio() -> None:
    from modules.portfolio import show

    show()


def show_scanner() -> None:
    from modules.scanner import show

    show()


def show_live_top10_scanner() -> None:
    from components.top10_live import show_live_top10_scanner

    show_live_top10_scanner()


def show_intraday() -> None:
    from modules.intraday import show

    show()


def show_market_movers() -> None:
    """Load the intraday market movers scanner only when opened."""
    from modules.market_movers import show

    show()


def show_research() -> None:
    from modules.research import show

    show()


def show_fundamentals() -> None:
    from modules.fundamentals import show

    show()


def show_prediction() -> None:
    from modules.prediction import show

    show()


def show_backtesting() -> None:
    from modules.backtesting import show

    show()


def show_settings() -> None:
    from modules.settings import show

    show()


def load_css() -> None:
    """Load the shared application theme."""
    with open("assets/styles.css", encoding="utf-8") as css_file:
        st.markdown(f"<style>{css_file.read()}</style>", unsafe_allow_html=True)


st.set_page_config(
    page_title="AI Stock Analyzer Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_css()

settings_page = st.Page(show_settings, title="Settings", icon="⚙️", url_path="settings")

pages = {
    "📊 Core": [
        st.Page(show_dashboard, title="Dashboard", icon="🏠", default=True, url_path="dashboard"),
        st.Page(show_market, title="Market", icon="📈", url_path="market"),
        st.Page(show_portfolio, title="Portfolio", icon="💼", url_path="portfolio"),
        st.Page(show_scanner, title="Scanner", icon="🔍", url_path="scanner"),
        st.Page(
            "pages/Personal_Stock_Watchlist.py",
            title="Stocks Watchlist",
            icon="📋",
            url_path="stocks-watchlist",
        ),
    ],
    "🔴 Live Market": [
        st.Page(
            show_live_top10_scanner,
            title="Live Top-10 Scanner",
            icon="📡",
            url_path="live-top-10-scanner",
        ),
        st.Page(
            show_market_movers,
            title="Intraday Market Movers",
            icon="⚡",
            url_path="intraday-market-movers",
        ),
        st.Page(show_intraday, title="Intraday Trading", icon="⏱️", url_path="intraday-trading"),
    ],
    "🔎 Research": [
        st.Page(show_research, title="Stock Research", icon="🔍", url_path="stock-research"),
        st.Page(show_fundamentals, title="Fundamentals", icon="📊", url_path="fundamentals"),
        st.Page(show_prediction, title="AI Prediction", icon="🤖", url_path="ai-prediction"),
        st.Page(show_backtesting, title="Backtesting", icon="📉", url_path="backtesting"),
        st.Page(
            "pages/Fibonacci_Gann_Research_Lab.py",
            title="Fibonacci-Gann Research Lab",
            icon="📐",
            url_path="fibonacci-gann-research-lab",
        ),
        st.Page(
            "pages/Gann_Fibonacci_Time_Price_Lab.py",
            title="Gann–Fibonacci Time & Price Lab",
            icon="🧭",
            url_path="gann-fibonacci-time-price-lab",
        ),
    ],
    "🤖 Algorithmic Trading": [
        st.Page("pages/Algorithmic_Scanner.py", title="Algorithmic Scanner", icon="📊"),
        st.Page("pages/Algorithmic_Backtest.py", title="Algorithmic Backtest", icon="📈"),
        st.Page(
            "pages/Algorithmic_Paper_Trading.py",
            title="Algorithmic Paper Trading",
            icon="🧪",
        ),
        st.Page(
            "pages/Algorithmic_Performance.py",
            title="Algorithmic Performance",
            icon="📊",
        ),
        st.Page(
            "pages/Strategy_Lab.py",
            title="Strategy Lab",
            icon="🧪",
            url_path="strategy-lab",
        ),
        st.Page(
            "pages/Walk_Forward_Lab.py",
            title="Walk-Forward Lab",
            icon="🔬",
            url_path="walk-forward-lab",
        ),
        st.Page(
            "pages/Volatility_Forecast.py",
            title="Volatility Forecast",
            icon="🌪️",
            url_path="volatility-forecast",
        ),
        st.Page(
            "pages/Sector_Rotation.py",
            title="Sector Rotation",
            icon="🔄",
            url_path="sector-rotation",
        ),
        st.Page(
            "pages/ML_Signal_Lab.py",
            title="ML Signal Lab",
            icon="🧬",
            url_path="ml-signal-lab",
        ),
        st.Page(
            "pages/Strategy_Robustness.py",
            title="Strategy Robustness",
            icon="🎲",
            url_path="strategy-robustness",
        ),
        st.Page(
            "pages/Portfolio_Optimizer.py",
            title="Portfolio Optimizer",
            icon="⚖️",
            url_path="portfolio-optimizer",
        ),
        st.Page(
            "pages/Advanced_Portfolio_Lab.py",
            title="Advanced Portfolio Lab",
            icon="🧮",
            url_path="advanced-portfolio-lab",
        ),
        st.Page(
            "pages/Momentum_Portfolio.py",
            title="Momentum Portfolio",
            icon="🚀",
            url_path="momentum-portfolio",
        ),
        st.Page(
            "pages/Pairs_Research.py",
            title="Pairs Research",
            icon="🔗",
            url_path="pairs-research",
        ),
        st.Page(
            "pages/Risk_Dashboard.py",
            title="Risk Dashboard",
            icon="🛡️",
            url_path="risk-dashboard",
        ),
        st.Page(
            "pages/Portfolio_Risk_Allocation.py",
            title="Portfolio Risk & Allocation",
            icon="🛡️",
        ),
        st.Page(
            "pages/Day_Trader_Opportunity_Scanner.py",
            title="Day Trader Opportunity Scanner",
            icon="⚡",
        ),
    ],
    "🧠 AI Trading Intelligence": [
        st.Page(
            "pages/AI_Trading_Command_Center.py",
            title="AI Trading Command Center",
            icon="🎯",
            url_path="ai-trading-command-center",
        ),
        st.Page(
            "pages/AI_Trading_Intelligence.py",
            title="AI Trading Scanner",
            icon="🧠",
        ),
        st.Page("pages/AI_Paper_Trading.py", title="AI Paper Trading", icon="🧪"),
        st.Page("pages/AI_Paper_Performance.py", title="AI Paper Performance", icon="📊"),
        st.Page("pages/AI_Paper_Risk.py", title="AI Paper Risk", icon="🛡️"),
        st.Page("pages/AI_Paper_Trade_Journal.py", title="AI Paper Trade Journal", icon="📒"),
        st.Page(
            "pages/AI_Model_Monitoring.py",
            title="AI Model Monitoring",
            icon="🎯",
            url_path="ai-model-monitoring-calibration",
        ),
        st.Page(
            "pages/AI_Signal_History.py",
            title="AI Signal History",
            icon="🗂️",
            url_path="ai-signal-history",
        ),
        st.Page(
            "pages/AI_Adaptive_Performance.py",
            title="AI Adaptive Performance",
            icon="📊",
            url_path="ai-adaptive-performance",
        ),
        st.Page(
            "pages/AI_Adaptive_Learning.py",
            title="AI Adaptive Learning",
            icon="🔄",
            url_path="ai-adaptive-learning",
        ),
        st.Page(
            "pages/AI_Self_Improving_Model.py",
            title="AI Self-Improving Model",
            icon="🧠",
            url_path="ai-self-improving-model",
        ),
        st.Page("pages/AI_News_Sentiment.py", title="AI News & Sentiment", icon="📰"),
        st.Page(
            "pages/AI_Fundamental_Intelligence.py",
            title="AI Fundamental Intelligence",
            icon="📊",
            url_path="ai-fundamental-intelligence",
        ),
        st.Page("pages/AI_Feature_Factory.py", title="AI Feature Factory", icon="🧩"),
        st.Page("pages/AI_Ensemble_ML.py", title="AI Ensemble ML", icon="🤖"),
        st.Page(
            "pages/AI_Sequence_Deep_Learning.py",
            title="AI Sequence / Deep Learning",
            icon="🧠",
        ),
        st.Page("pages/AI_Feature_Drift.py", title="AI Feature Drift", icon="📐"),
    ],
    "📈 Options Trading": [
        st.Page(
            "pages/Options_Pricing_Analytics.py",
            title="Options Pricing Analytics",
            icon="🧮",
            url_path="options-pricing-analytics",
        ),
        st.Page(
            "pages/NIFTY_V2_Paper_Trading.py",
            title="NIFTY Options V2 Paper Trading",
            icon="📈",
            url_path="nifty-v2-paper-trading",
        ),
        st.Page(
            "pages/Options_Strategy_Builder.py",
            title="Options Strategy Builder",
            icon="🧩",
            url_path="options-strategy-builder",
        ),
    ],
    "🏦 Funds & Currencies": [
        st.Page(
            "pages/Mutual_Fund_Analysis.py",
            title="Mutual Fund Analysis",
            icon="🏦",
            url_path="mutual-fund-analysis",
        ),
        st.Page(
            "pages/Forex_Lab.py",
            title="Forex Lab",
            icon="💱",
            url_path="forex-lab",
        ),
        st.Page(
            "pages/Crypto_Lab.py",
            title="Crypto Lab",
            icon="🪙",
            url_path="crypto-lab",
        ),
    ],
    "⚙️ System": [
        st.Page("pages/Alerts.py", title="Alerts", icon="🔔", url_path="alerts"),
        settings_page,
    ],
}

pg = st.navigation(pages, position="sidebar", expanded=True)


st.sidebar.markdown("---")
st.sidebar.markdown("### 📈 AI Stock Analyzer Pro")
st.sidebar.caption("Professional Investment Platform")
st.sidebar.success(f"Current: {pg.title}")
st.sidebar.metric("Pages", sum(len(group) for group in pages.values()))
st.sidebar.metric("Version", "3.7")
st.sidebar.caption(
    "Research and educational use only. Model outputs use third-party data that may be "
    "delayed or incomplete. Not investment advice."
)
st.sidebar.caption("© 2026 AI Stock Analyzer Pro")

pg.run()
