"""
RETAILPULSE DASHBOARD
---------------------
A Streamlit BI dashboard on top of the SQLite database, powered directly
by SQL queries (no pandas-side aggregation — SQL does the heavy lifting).

Run with:
    pip install streamlit plotly pandas --break-system-packages
    streamlit run dashboard.py

NOTE: This file was written and code-reviewed against the tested queries
in analysis_queries.sql, but Streamlit/Plotly could not be installed or
rendered in the build sandbox (no internet access there). Please run it
locally and let me know if anything needs adjusting.
"""

import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px

DB_PATH = "retailpulse.db"

st.set_page_config(page_title="RetailPulse Dashboard", layout="wide")


@st.cache_resource
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


@st.cache_data(ttl=600)
def run_query(query):
    conn = get_connection()
    return pd.read_sql_query(query, conn)


st.title("📊 RetailPulse: E-Commerce Analytics Dashboard")
st.caption("End-to-end SQL analytics project — SQLite + Python + Streamlit")

# ---------------- Top-line KPIs ----------------
kpi_query = """
SELECT
    COUNT(DISTINCT o.order_id) AS total_orders,
    COUNT(DISTINCT o.customer_id) AS total_customers,
    ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0)), 2) AS total_revenue,
    ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0)) / COUNT(DISTINCT o.order_id), 2) AS avg_order_value
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'Completed';
"""
kpis = run_query(kpi_query).iloc[0]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Revenue", f"₹{kpis['total_revenue']:,.0f}")
col2.metric("Total Orders", f"{kpis['total_orders']:,}")
col3.metric("Unique Customers", f"{kpis['total_customers']:,}")
col4.metric("Avg Order Value", f"₹{kpis['avg_order_value']:,.0f}")

st.divider()

# ---------------- Monthly Revenue Trend ----------------
st.subheader("Monthly Revenue Trend & Growth")
monthly_query = """
WITH monthly_revenue AS (
    SELECT
        strftime('%Y-%m', o.order_date) AS month,
        ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0)), 2) AS revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'Completed'
    GROUP BY month
)
SELECT
    month,
    revenue,
    ROUND(SUM(revenue) OVER (ORDER BY month), 2) AS running_total_revenue
FROM monthly_revenue
ORDER BY month;
"""
monthly_df = run_query(monthly_query)
fig1 = px.bar(monthly_df, x="month", y="revenue", title="Monthly Revenue")
fig1.add_scatter(x=monthly_df["month"], y=monthly_df["running_total_revenue"],
                  mode="lines", name="Running Total", yaxis="y2")
fig1.update_layout(yaxis2=dict(overlaying="y", side="right", title="Running Total"))
st.plotly_chart(fig1, use_container_width=True)

st.divider()

# ---------------- RFM Segmentation ----------------
st.subheader("Customer Segmentation (RFM)")
rfm_query = """
WITH customer_orders AS (
    SELECT
        o.customer_id,
        MAX(o.order_date) AS last_order_date,
        COUNT(DISTINCT o.order_id) AS frequency,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0)) AS monetary
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'Completed'
    GROUP BY o.customer_id
),
rfm_scores AS (
    SELECT
        customer_id,
        frequency,
        monetary,
        NTILE(4) OVER (ORDER BY julianday(last_order_date) DESC) AS recency_score,
        NTILE(4) OVER (ORDER BY frequency ASC) AS frequency_score,
        NTILE(4) OVER (ORDER BY monetary ASC) AS monetary_score
    FROM customer_orders
)
SELECT
    CASE
        WHEN recency_score >= 3 AND frequency_score >= 3 AND monetary_score >= 3 THEN 'Champion'
        WHEN recency_score >= 3 AND frequency_score >= 2 THEN 'Loyal Customer'
        WHEN recency_score <= 2 AND frequency_score >= 3 THEN 'At Risk (was frequent)'
        WHEN recency_score = 1 AND frequency_score = 1 THEN 'Lost Customer'
        ELSE 'Developing Customer'
    END AS customer_segment,
    COUNT(*) AS num_customers,
    ROUND(AVG(monetary), 2) AS avg_lifetime_value
FROM rfm_scores
GROUP BY customer_segment
ORDER BY avg_lifetime_value DESC;
"""
rfm_df = run_query(rfm_query)
col_a, col_b = st.columns(2)
with col_a:
    fig2 = px.pie(rfm_df, names="customer_segment", values="num_customers",
                  title="Customers by Segment")
    st.plotly_chart(fig2, use_container_width=True)
with col_b:
    fig3 = px.bar(rfm_df, x="customer_segment", y="avg_lifetime_value",
                  title="Avg Lifetime Value by Segment")
    st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ---------------- Top Products by Category ----------------
st.subheader("Top-Selling Products by Category")
top_products_query = """
WITH product_revenue AS (
    SELECT
        p.category,
        p.product_name,
        ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0)), 2) AS revenue
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    JOIN orders o ON oi.order_id = o.order_id
    WHERE o.order_status = 'Completed'
    GROUP BY p.category, p.product_name
),
ranked AS (
    SELECT category, product_name, revenue,
           RANK() OVER (PARTITION BY category ORDER BY revenue DESC) AS category_rank
    FROM product_revenue
)
SELECT * FROM ranked WHERE category_rank <= 3 ORDER BY category, category_rank;
"""
top_products_df = run_query(top_products_query)
fig4 = px.bar(top_products_df, x="revenue", y="product_name", color="category",
              orientation="h", title="Top 3 Products per Category by Revenue")
st.plotly_chart(fig4, use_container_width=True)

st.divider()

# ---------------- Regional YoY Growth ----------------
st.subheader("Year-over-Year Revenue Growth by Region")
yoy_query = """
WITH yearly_regional_revenue AS (
    SELECT
        s.region,
        strftime('%Y', o.order_date) AS year,
        ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0)), 2) AS revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN stores s ON o.store_id = s.store_id
    WHERE o.order_status = 'Completed'
    GROUP BY s.region, year
)
SELECT * FROM yearly_regional_revenue ORDER BY region, year;
"""
yoy_df = run_query(yoy_query)
fig5 = px.line(yoy_df, x="year", y="revenue", color="region", markers=True,
               title="Revenue by Region Over Time")
st.plotly_chart(fig5, use_container_width=True)

st.divider()

# ---------------- Churn Risk Table ----------------
st.subheader("⚠️ Churn Risk: Customers Inactive 90+ Days")
churn_query = """
WITH last_order AS (
    SELECT customer_id, MAX(order_date) AS last_order_date
    FROM orders WHERE order_status = 'Completed' GROUP BY customer_id
)
SELECT
    c.customer_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    c.customer_segment,
    c.region,
    lo.last_order_date,
    CAST(julianday('2025-06-30') - julianday(lo.last_order_date) AS INTEGER) AS days_since_last_order
FROM last_order lo
JOIN customers c ON c.customer_id = lo.customer_id
WHERE julianday('2025-06-30') - julianday(lo.last_order_date) > 90
ORDER BY days_since_last_order DESC
LIMIT 25;
"""
st.dataframe(run_query(churn_query), use_container_width=True)
