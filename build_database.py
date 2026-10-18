"""
Builds retailpulse.db from schema.sql and loads the generated CSVs.
"""

import sqlite3
import pandas as pd
import os

DB_PATH = "retailpulse.db"


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    with open("schema.sql", "r") as f:
        cur.executescript(f.read())
    conn.commit()
    print("Schema created.")

    tables = ["customers", "stores", "products", "orders", "order_items"]
    for t in tables:
        df = pd.read_csv(f"{t}.csv")
        df.to_sql(t, conn, if_exists="append", index=False)
        print(f"Loaded {len(df):,} rows into {t}")

    # Sanity check: foreign key integrity
    cur.execute("PRAGMA foreign_key_check;")
    issues = cur.fetchall()
    if issues:
        print(f"WARNING: {len(issues)} foreign key issues found.")
    else:
        print("Foreign key integrity check passed.")

    conn.commit()
    conn.close()
    print(f"\nDatabase built successfully: {DB_PATH}")


if __name__ == "__main__":
    main()
