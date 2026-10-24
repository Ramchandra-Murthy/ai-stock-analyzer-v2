"""
AI Stock Analyzer - CLI Entry Point.

Uses the same canonical scoring services as the Streamlit application.
"""

from config.env import load_environment
from services.fundamental_score_service import calculate_fundamental_score
from services.recommendation_service import generate_recommendation
from services.research_service import get_stock_profile
from services.score_service import calculate_investment_score
from services.technical_score_service import calculate_technical_score
from services.technical_service import get_price_history

load_environment()


def run_analysis(ticker: str) -> dict:
    """Run the canonical stock-analysis scoring pipeline."""
    symbol = ticker.strip().upper()
    if not symbol:
        raise ValueError("Ticker cannot be empty.")

    data = get_stock_profile(symbol)
    if not data:
        raise RuntimeError(f"Unable to fetch stock profile for {symbol}.")

    history = get_price_history(symbol)

    if history is not None and not history.empty:
        technical_score, technical_reasons = calculate_technical_score(history)
    else:
        technical_score = None
        technical_reasons = ["Historical price data unavailable."]

    fundamental_score, fundamental_reasons = calculate_fundamental_score(data)

    # AI is optional evidence. When unavailable, the score service excludes it
    # rather than substituting a fabricated neutral value.
    investment_score, score_breakdown = calculate_investment_score(
        technical_score=technical_score,
        fundamental_score=fundamental_score,
        ai_result=None,
        data=data,
    )

    recommendation = generate_recommendation(investment_score)

    return {
        "symbol": data.get("symbol", symbol),
        "company": data.get("company", "N/A"),
        "investment_score": investment_score,
        "recommendation": recommendation,
        "technical_score": technical_score,
        "fundamental_score": fundamental_score,
        "score_breakdown": score_breakdown,
        "technical_reasons": technical_reasons,
        "fundamental_reasons": fundamental_reasons,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI Stock Analyzer CLI")
    parser.add_argument(
        "--ticker",
        type=str,
        default="RELIANCE.NS",
        help="NSE stock ticker, e.g. RELIANCE or RELIANCE.NS",
    )
    args = parser.parse_args()

    result = run_analysis(args.ticker)
    print(f"[AI Stock Analyzer] {result['symbol']}")
    print(f"Investment Score: {result['investment_score']}/100")
    print(f"Recommendation: {result['recommendation']['recommendation']}")
    print(f"Confidence: {result['recommendation']['confidence']}%")
