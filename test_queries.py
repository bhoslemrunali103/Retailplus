import sqlite3
import pandas as pd
import re

conn = sqlite3.connect("retailpulse.db")

with open("analysis_queries.sql") as f:
    content = f.read()

# Split on the numbered section headers, keep the SQL after each header
sections = re.split(r"-- -{10,}\n-- (\d+)\. (.+?)\n", content)
# sections[0] is preamble; then triples of (num, title, sql_and_next_header...)
i = 1
results_summary = []
while i < len(sections):
    num, title, sql_block = sections[i], sections[i+1], sections[i+2]
    # strip trailing comment-only lines, keep valid SQL up to the actual query
    sql = sql_block.strip()
    try:
        df = pd.read_sql_query(sql, conn)
        results_summary.append((num, title, "OK", len(df)))
        print(f"\n=== Query {num}: {title} ===")
        print(f"Rows returned: {len(df)}")
        print(df.head(5).to_string(index=False))
    except Exception as e:
        results_summary.append((num, title, f"ERROR: {e}", 0))
        print(f"\n=== Query {num}: {title} ===")
        print(f"FAILED: {e}")
    i += 3

print("\n\n===== SUMMARY =====")
for num, title, status, rows in results_summary:
    print(f"{num}. {title[:50]:<50} -> {status if 'ERROR' in str(status) else 'OK, ' + str(rows) + ' rows'}")
