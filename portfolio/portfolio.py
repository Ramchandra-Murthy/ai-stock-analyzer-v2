import sqlite3

import pandas as pd

DATABASE = "stock_data.db"


_SCHEMA = """
    CREATE TABLE IF NOT EXISTS portfolio(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        quantity INTEGER,
        buy_price REAL
    )
"""


def _connect() -> sqlite3.Connection:
    """Open the database and make sure the table exists.

    The database file is not tracked in git, so a fresh deploy (Streamlit Cloud, a new
    clone) has no ``portfolio`` table; querying it used to crash the dashboard.
    """
    conn = sqlite3.connect(DATABASE)
    conn.execute(_SCHEMA)
    return conn


def create_portfolio_table():
    conn = _connect()
    conn.commit()
    conn.close()


def add_stock(symbol, quantity, buy_price):
    conn = _connect()

    conn.execute(
        "INSERT INTO portfolio(symbol, quantity, buy_price) VALUES (?, ?, ?)",
        (symbol, quantity, buy_price),
    )

    conn.commit()
    conn.close()


def load_portfolio():
    conn = _connect()

    df = pd.read_sql("SELECT * FROM portfolio", conn)

    conn.close()

    return df


def delete_stock(stock_id):
    conn = _connect()

    conn.execute("DELETE FROM portfolio WHERE id=?", (stock_id,))

    conn.commit()
    conn.close()


def update_stock(stock_id, quantity, buy_price):
    conn = _connect()

    conn.execute(
        """
        UPDATE portfolio
        SET quantity = ?, buy_price = ?
        WHERE id = ?
        """,
        (quantity, buy_price, stock_id),
    )

    conn.commit()
    conn.close()


def clear_portfolio():
    conn = _connect()

    conn.execute("DELETE FROM portfolio")

    conn.commit()
    conn.close()
