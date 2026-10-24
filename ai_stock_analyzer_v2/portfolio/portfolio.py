import sqlite3

import pandas as pd

DATABASE = "stock_data.db"


def create_portfolio_table():
    conn = sqlite3.connect(DATABASE)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS portfolio(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            quantity INTEGER,
            buy_price REAL
        )
    """)

    conn.commit()
    conn.close()


def add_stock(symbol, quantity, buy_price):
    conn = sqlite3.connect(DATABASE)

    conn.execute(
        "INSERT INTO portfolio(symbol, quantity, buy_price) VALUES (?, ?, ?)",
        (symbol, quantity, buy_price),
    )

    conn.commit()
    conn.close()


def load_portfolio():
    conn = sqlite3.connect(DATABASE)

    df = pd.read_sql("SELECT * FROM portfolio", conn)

    conn.close()

    return df


def delete_stock(stock_id):
    conn = sqlite3.connect(DATABASE)

    conn.execute("DELETE FROM portfolio WHERE id=?", (stock_id,))

    conn.commit()
    conn.close()


def update_stock(stock_id, quantity, buy_price):
    conn = sqlite3.connect(DATABASE)

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
    conn = sqlite3.connect(DATABASE)

    conn.execute("DELETE FROM portfolio")

    conn.commit()
    conn.close()
