from data.database import create_table
from data.downloader import download_stock
from data.loader import save_dataframe
from data.reader import load_stock
from engine.breakout_engine import detect_breakout
from engine.signal_engine import generate_signal
from indicators.atr import calculate_atr
from indicators.bollinger import calculate_bollinger
from indicators.macd import calculate_macd
from indicators.macd_histogram import calculate_histogram
from indicators.moving_average import calculate_ema, calculate_sma
from indicators.rsi import calculate_rsi
from indicators.support_resistance import calculate_support_resistance
from indicators.trend import detect_trend
from services.market_service import get_latest_available_price


def analyze_stock(symbol):

    create_table()

    df = download_stock(symbol)

    save_dataframe(df, symbol)

    df = load_stock(symbol)

    df = df.dropna(subset=["Open", "High", "Low", "Close"])

    df = df.reset_index(drop=True)

    df = calculate_sma(df, 20)
    df = calculate_sma(df, 50)

    df = calculate_ema(df, 20)

    df = calculate_rsi(df, 14)

    df = calculate_macd(df)
    df = calculate_histogram(df)

    df = calculate_bollinger(df)

    df = calculate_atr(df)

    df = calculate_support_resistance(df)

    trend = detect_trend(df)

    signal = generate_signal(df)

    # Reconcile the analysis with the canonical freshest market observation.
    # Historical indicators remain historical; the current price is explicitly
    # identified so downstream consumers cannot mistake it for a tick quote.
    observation = get_latest_available_price(symbol)
    if observation.get("price") is not None:
        signal["MarketObservation"] = observation

    breakout = detect_breakout(df)

    return {
        "df": df,
        "last": df.iloc[-1],
        "trend": trend,
        "signal": signal,
        "breakout": breakout,
    }
