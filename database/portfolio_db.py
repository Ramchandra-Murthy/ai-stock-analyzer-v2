import sqlite3

DB_NAME = "database/stocks.db"


def create_portfolio_table():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            quantity REAL,
            buy_price REAL,
            buy_date TEXT
        )
    """)

    conn.commit()
    conn.close()


def add_stock(symbol, quantity, buy_price, buy_date):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO portfolio
        (symbol, quantity, buy_price, buy_date)
        VALUES (?, ?, ?, ?)
        """,
        (symbol, quantity, buy_price, buy_date),
    )

    conn.commit()
    conn.close()
