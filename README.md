# RetailPulse — End-to-End SQL Analytics Project

An end-to-end e-commerce analytics pipeline: synthetic-but-realistic transactional data →
relational SQLite database → advanced SQL analysis → interactive BI dashboard.

Built to demonstrate practical, business-focused SQL and analytics skills beyond basic
SELECT/GROUP BY queries — including window functions, CTEs, cohort analysis, and RFM
customer segmentation, all backed by a properly normalized relational schema.

## Project Architecture

```
data_generator.py  -->  CSV files  -->  build_database.py  -->  retailpulse.db (SQLite)
                                                                       |
                                                                       v
                                                          analysis_queries.sql (10 business questions)
                                                                       |
                                                                       v
                                                              dashboard.py (Streamlit + Plotly)
```

## Database Schema (5 tables, normalized)

```
customers ──┐
            ├──< orders >──┐
stores ─────┘              ├──< order_items >──── products
```

- **customers** (2,000 rows) — signup date, region, segment (New/Returning/VIP)
- **stores** (15 rows) — Online vs. Physical, by region
- **products** (221 rows) — 6 categories, cost & price for margin analysis
- **orders** (21,419 rows) — status (Completed/Cancelled/Returned), payment method
- **order_items** (53,750 rows) — quantity, price at time of sale, discount %

Includes foreign keys, indexes on join/filter columns, and a foreign-key integrity check
run automatically at build time.

## Key Numbers (from the actual generated dataset)

- **₹26.08M** total completed revenue across **19,494 orders** from **1,985 customers**
- Realistic patterns baked in: holiday-season spikes (Nov/Dec), customer churn, a small
  VIP segment driving disproportionate revenue, 4–9% return/cancellation rates by category

## The 10 Business Questions Answered in SQL (`analysis_queries.sql`)

| # | Question | SQL Technique |
|---|----------|----------------|
| 1 | Is revenue growing month over month? | `LAG()`, running total window function |
| 2 | Who are our best vs. at-risk customers? | RFM segmentation via `NTILE()` |
| 3 | Do customers stick around after signup? | Cohort retention grid, self-join |
| 4 | What are the best sellers per category? | `RANK() OVER (PARTITION BY ...)` |
| 5 | Who are our highest-value customers? | CLV ranking |
| 6 | Which regions are growing vs. declining? | YoY growth with `LAG()` per partition |
| 7 | Which products sell well together? | Self-join market basket analysis |
| 8 | Who's at risk of churning? | Recency filtering with `julianday()` |
| 9 | Online vs. physical store performance | Aggregation + AOV calculation |
| 10 | Which categories have quality issues? | Return-rate-by-category analysis |

Every query in this file was executed against the live database and verified to return
correct results before being included here — see `test_queries.py`.

## Dashboard (`dashboard.py`)

A Streamlit app with Plotly visuals covering: KPI summary cards, monthly revenue trend
with running total, RFM segment breakdown (pie + bar), top products by category,
regional YoY growth lines, and a live churn-risk table — all powered directly by the
SQL queries above (no pre-computed pandas aggregation).

## How to Run This Project

```bash
# 1. Install dependencies
pip install pandas streamlit plotly --break-system-packages

# 2. Generate the synthetic dataset
python data_generator.py

# 3. Build the SQLite database
python build_database.py

# 4. (Optional) Verify all analysis queries run correctly
python test_queries.py

# 5. Launch the dashboard
streamlit run dashboard.py
```

## Skills Demonstrated

- **SQL**: window functions (`RANK`, `NTILE`, `LAG`, running totals), CTEs, self-joins,
  multi-table joins, date arithmetic, schema design, indexing, referential integrity
- **Python**: synthetic data generation with realistic statistical patterns (seasonality,
  churn modeling), ETL scripting, automated testing of SQL logic
- **BI/Visualization**: Streamlit + Plotly dashboard translating SQL output into
  business-consumable visuals
- **Business acumen**: every query is framed around an actual business question
  (retention, churn, CLV, cross-sell, regional performance) rather than generic queries

## Suggested Resume Bullet

> Built an end-to-end SQL analytics pipeline (SQLite, Python, Streamlit) on a 75K-row
> relational e-commerce dataset; used window functions and CTEs to deliver RFM customer
> segmentation, cohort retention analysis, and YoY regional growth reporting, surfaced
> through an interactive BI dashboard.

## Possible Extensions

- Swap SQLite for PostgreSQL to demonstrate a "production-grade" RDBMS on your resume
- Add a scheduled ETL (e.g., Airflow) to simulate daily data refreshes
- Connect Power BI or Tableau directly to the SQLite file as an alternative to the
  Streamlit dashboard, to show both BI tools in your stack
- Push to GitHub with a screenshot of the dashboard in the README — recruiters skim,
  and a visual makes this project 10x more likely to get a second look
