import sqlite3
from pathlib import Path

DB_FOLDER = Path("database")
DB_FOLDER.mkdir(exist_ok=True)

DB_NAME = DB_FOLDER / "stock_data.db"


def connect():

    return sqlite3.connect(DB_NAME)


def create_table():

    conn = connect()

    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_prices(

            Date TEXT,
            Symbol TEXT,

            Open REAL,
            High REAL,
            Low REAL,
            Close REAL,
            Volume INTEGER,

            PRIMARY KEY(Date, Symbol)

        )
    """)

    conn.commit()

    conn.close()
