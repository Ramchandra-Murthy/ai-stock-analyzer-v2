import pytest

from algorithmic_trading.paper_trading import PaperPortfolio


def test_buy_and_mark_to_market() -> None:
    portfolio = PaperPortfolio(cash=100_000)
    fill = portfolio.submit_market_order("RELIANCE", 100, 1_000)

    assert fill.side == "BUY"
    assert fill.cost == pytest.approx(100_000)
    assert portfolio.cash == pytest.approx(0)
    assert portfolio.mark_to_market({"RELIANCE": 1_050}) == pytest.approx(105_000)


def test_sell_creates_short_position() -> None:
    portfolio = PaperPortfolio(cash=100_000)
    fill = portfolio.submit_market_order("TCS", -10, 4_000)

    assert fill.side == "SELL"
    assert portfolio.positions["TCS"] == -10
    assert portfolio.cash == pytest.approx(140_000)
    assert portfolio.mark_to_market({"TCS": 3_500}) == pytest.approx(105_000)


def test_insufficient_cash_is_rejected() -> None:
    portfolio = PaperPortfolio(cash=1_000)

    with pytest.raises(ValueError, match="insufficient"):
        portfolio.submit_market_order("INFY", 10, 2_000)


def test_invalid_order_is_rejected() -> None:
    portfolio = PaperPortfolio(cash=100_000)

    with pytest.raises(ValueError):
        portfolio.submit_market_order("", 1, 100)
    with pytest.raises(ValueError):
        portfolio.submit_market_order("INFY", 0, 100)
    with pytest.raises(ValueError):
        portfolio.submit_market_order("INFY", 1, 0)
