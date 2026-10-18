-- =====================================================
-- RETAILPULSE: E-COMMERCE ANALYTICS DATABASE SCHEMA
-- =====================================================

DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS stores;

CREATE TABLE customers (
    customer_id     INTEGER PRIMARY KEY,
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    email           TEXT UNIQUE,
    signup_date     DATE NOT NULL,
    city            TEXT,
    region          TEXT NOT NULL,
    customer_segment TEXT  -- 'New', 'Returning', 'VIP' (assigned at signup for realism)
);

CREATE TABLE stores (
    store_id        INTEGER PRIMARY KEY,
    store_name      TEXT NOT NULL,
    region          TEXT NOT NULL,
    store_type      TEXT NOT NULL  -- 'Online' or 'Physical'
);

CREATE TABLE products (
    product_id      INTEGER PRIMARY KEY,
    product_name    TEXT NOT NULL,
    category        TEXT NOT NULL,
    sub_category    TEXT,
    unit_cost       REAL NOT NULL,
    unit_price      REAL NOT NULL
);

CREATE TABLE orders (
    order_id        INTEGER PRIMARY KEY,
    customer_id     INTEGER NOT NULL,
    store_id        INTEGER NOT NULL,
    order_date      DATE NOT NULL,
    order_status    TEXT NOT NULL,  -- 'Completed', 'Cancelled', 'Returned'
    payment_method  TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (store_id) REFERENCES stores(store_id)
);

CREATE TABLE order_items (
    order_item_id   INTEGER PRIMARY KEY,
    order_id        INTEGER NOT NULL,
    product_id      INTEGER NOT NULL,
    quantity        INTEGER NOT NULL,
    unit_price      REAL NOT NULL,   -- price at time of sale (may differ from current product price)
    discount_pct    REAL DEFAULT 0,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- Indexes for performance on common analytical joins/filters
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_orders_store ON orders(store_id);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);
