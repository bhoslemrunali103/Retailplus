-- =====================================================================
-- RETAILPULSE: ADVANCED SQL ANALYSIS
-- Portfolio queries demonstrating CTEs, window functions, cohort
-- analysis, RFM segmentation, and business-focused reporting.
-- Run against retailpulse.db
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1. MONTHLY REVENUE TREND WITH MONTH-OVER-MONTH GROWTH %
-- Business question: Is revenue growing, and by how much month to month?
-- ---------------------------------------------------------------------
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
    LAG(revenue) OVER (ORDER BY month) AS prev_month_revenue,
    ROUND(
        100.0 * (revenue - LAG(revenue) OVER (ORDER BY month)) / NULLIF(LAG(revenue) OVER (ORDER BY month), 0),
        2
    ) AS mom_growth_pct,
    ROUND(SUM(revenue) OVER (ORDER BY month), 2) AS running_total_revenue
FROM monthly_revenue
ORDER BY month;


-- ---------------------------------------------------------------------
-- 2. RFM CUSTOMER SEGMENTATION (Recency, Frequency, Monetary)
-- Business question: Who are our best vs. at-risk customers?
-- Uses NTILE() to score each dimension 1-4, then combines into a segment.
-- ---------------------------------------------------------------------
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
        CAST(julianday('2025-06-30') - julianday(last_order_date) AS INTEGER) AS recency_days,
        frequency,
        ROUND(monetary, 2) AS monetary,
        NTILE(4) OVER (ORDER BY julianday(last_order_date) DESC) AS recency_score,   -- 4 = most recent
        NTILE(4) OVER (ORDER BY frequency ASC) AS frequency_score,                    -- 4 = most frequent
        NTILE(4) OVER (ORDER BY monetary ASC) AS monetary_score                       -- 4 = highest spend
    FROM customer_orders
)
SELECT
    customer_id,
    recency_days,
    frequency,
    monetary,
    recency_score,
    frequency_score,
    monetary_score,
    (recency_score + frequency_score + monetary_score) AS rfm_total,
    CASE
        WHEN recency_score >= 3 AND frequency_score >= 3 AND monetary_score >= 3 THEN 'Champion'
        WHEN recency_score >= 3 AND frequency_score >= 2 THEN 'Loyal Customer'
        WHEN recency_score <= 2 AND frequency_score >= 3 THEN 'At Risk (was frequent)'
        WHEN recency_score = 1 AND frequency_score = 1 THEN 'Lost Customer'
        ELSE 'Developing Customer'
    END AS customer_segment
FROM rfm_scores
ORDER BY rfm_total DESC;


-- ---------------------------------------------------------------------
-- 3. COHORT RETENTION ANALYSIS
-- Business question: Of customers who signed up in month X, what % are
-- still ordering in each subsequent month? (classic cohort retention grid)
-- ---------------------------------------------------------------------
WITH cohorts AS (
    SELECT
        customer_id,
        strftime('%Y-%m', signup_date) AS cohort_month
    FROM customers
),
customer_activity AS (
    SELECT DISTINCT
        o.customer_id,
        strftime('%Y-%m', o.order_date) AS active_month
    FROM orders o
    WHERE o.order_status = 'Completed'
),
cohort_activity AS (
    SELECT
        c.cohort_month,
        ca.active_month,
        -- month index = how many months after signup this activity happened
        (CAST(strftime('%Y', ca.active_month || '-01') AS INTEGER) * 12 + CAST(strftime('%m', ca.active_month || '-01') AS INTEGER))
        - (CAST(strftime('%Y', c.cohort_month || '-01') AS INTEGER) * 12 + CAST(strftime('%m', c.cohort_month || '-01') AS INTEGER))
        AS month_index,
        c.customer_id
    FROM cohorts c
    JOIN customer_activity ca ON c.customer_id = ca.customer_id
),
cohort_size AS (
    SELECT cohort_month, COUNT(DISTINCT customer_id) AS num_customers
    FROM cohorts
    GROUP BY cohort_month
)
SELECT
    ca.cohort_month,
    cs.num_customers AS cohort_size,
    ca.month_index,
    COUNT(DISTINCT ca.customer_id) AS active_customers,
    ROUND(100.0 * COUNT(DISTINCT ca.customer_id) / cs.num_customers, 1) AS retention_pct
FROM cohort_activity ca
JOIN cohort_size cs ON ca.cohort_month = cs.cohort_month
WHERE ca.month_index BETWEEN 0 AND 6   -- first 6 months post-signup
GROUP BY ca.cohort_month, ca.month_index
ORDER BY ca.cohort_month, ca.month_index;


-- ---------------------------------------------------------------------
-- 4. TOP PRODUCTS BY REVENUE, RANKED WITHIN EACH CATEGORY
-- Business question: What are the best sellers in each category?
-- ---------------------------------------------------------------------
WITH product_revenue AS (
    SELECT
        p.category,
        p.product_name,
        ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0)), 2) AS revenue,
        SUM(oi.quantity) AS units_sold
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    JOIN orders o ON oi.order_id = o.order_id
    WHERE o.order_status = 'Completed'
    GROUP BY p.category, p.product_name
),
ranked AS (
    SELECT
        category,
        product_name,
        revenue,
        units_sold,
        RANK() OVER (PARTITION BY category ORDER BY revenue DESC) AS category_rank
    FROM product_revenue
)
SELECT * FROM ranked
WHERE category_rank <= 3
ORDER BY category, category_rank;


-- ---------------------------------------------------------------------
-- 5. CUSTOMER LIFETIME VALUE (CLV) LEADERBOARD
-- Business question: Who are our highest-value customers overall?
-- ---------------------------------------------------------------------
SELECT
    c.customer_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    c.customer_segment,
    c.region,
    COUNT(DISTINCT o.order_id) AS total_orders,
    ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0)), 2) AS lifetime_value,
    RANK() OVER (ORDER BY SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0)) DESC) AS clv_rank
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'Completed'
GROUP BY c.customer_id
ORDER BY lifetime_value DESC
LIMIT 20;


-- ---------------------------------------------------------------------
-- 6. YEAR-OVER-YEAR REVENUE COMPARISON BY REGION
-- Business question: Which regions are growing vs. declining YoY?
-- ---------------------------------------------------------------------
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
SELECT
    region,
    year,
    revenue,
    LAG(revenue) OVER (PARTITION BY region ORDER BY year) AS prev_year_revenue,
    ROUND(
        100.0 * (revenue - LAG(revenue) OVER (PARTITION BY region ORDER BY year))
        / NULLIF(LAG(revenue) OVER (PARTITION BY region ORDER BY year), 0), 2
    ) AS yoy_growth_pct
FROM yearly_regional_revenue
ORDER BY region, year;


-- ---------------------------------------------------------------------
-- 7. MARKET BASKET ANALYSIS (PRODUCTS FREQUENTLY BOUGHT TOGETHER)
-- Business question: Which product pairs should we bundle/cross-sell?
-- Uses a self-join on order_items to find co-occurring products.
-- ---------------------------------------------------------------------
SELECT
    p1.product_name AS product_a,
    p2.product_name AS product_b,
    COUNT(*) AS times_bought_together
FROM order_items oi1
JOIN order_items oi2
    ON oi1.order_id = oi2.order_id AND oi1.product_id < oi2.product_id
JOIN products p1 ON oi1.product_id = p1.product_id
JOIN products p2 ON oi2.product_id = p2.product_id
GROUP BY p1.product_name, p2.product_name
HAVING times_bought_together >= 5
ORDER BY times_bought_together DESC
LIMIT 15;


-- ---------------------------------------------------------------------
-- 8. CHURN RISK LIST: CUSTOMERS WHO HAVEN'T ORDERED IN 90+ DAYS
-- Business question: Who should the marketing/retention team target?
-- ---------------------------------------------------------------------
WITH last_order AS (
    SELECT
        customer_id,
        MAX(order_date) AS last_order_date
    FROM orders
    WHERE order_status = 'Completed'
    GROUP BY customer_id
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


-- ---------------------------------------------------------------------
-- 9. STORE PERFORMANCE: ONLINE VS PHYSICAL
-- Business question: Are online or physical stores driving more revenue
-- and higher average order value?
-- ---------------------------------------------------------------------
SELECT
    s.store_type,
    COUNT(DISTINCT o.order_id) AS total_orders,
    ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0)), 2) AS total_revenue,
    ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100.0))
          / COUNT(DISTINCT o.order_id), 2) AS avg_order_value
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN stores s ON o.store_id = s.store_id
WHERE o.order_status = 'Completed'
GROUP BY s.store_type;


-- ---------------------------------------------------------------------
-- 10. RETURN/CANCELLATION RATE BY CATEGORY
-- Business question: Which product categories have quality/fit issues?
-- ---------------------------------------------------------------------
SELECT
    p.category,
    COUNT(*) AS total_line_items,
    SUM(CASE WHEN o.order_status = 'Returned' THEN 1 ELSE 0 END) AS returned_items,
    ROUND(100.0 * SUM(CASE WHEN o.order_status = 'Returned' THEN 1 ELSE 0 END) / COUNT(*), 2) AS return_rate_pct
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
JOIN products p ON oi.product_id = p.product_id
GROUP BY p.category
ORDER BY return_rate_pct DESC;
