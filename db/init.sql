-- =========================
-- Data Engineering Portfolio (IU) - Phase 2
-- Warehouse schema (PostgreSQL)
-- =========================

-- 1) RAW TABLE (ingestion target)
CREATE TABLE IF NOT EXISTS retail_raw (
  invoice TEXT,
  stockcode TEXT,
  description TEXT,
  quantity INTEGER,
  invoicedate TIMESTAMP,
  price NUMERIC,
  customer_id TEXT,
  country TEXT
);

-- Helpful indexes (optional but good for performance)
CREATE INDEX IF NOT EXISTS idx_retail_raw_invoicedate ON retail_raw (invoicedate);
CREATE INDEX IF NOT EXISTS idx_retail_raw_invoice ON retail_raw (invoice);
CREATE INDEX IF NOT EXISTS idx_retail_raw_stockcode ON retail_raw (stockcode);
CREATE INDEX IF NOT EXISTS idx_retail_raw_customer_id ON retail_raw (customer_id);

-- 2) DAILY METRICS (processing output)
CREATE TABLE IF NOT EXISTS daily_metrics (
  day DATE PRIMARY KEY,
  total_invoices INTEGER,
  total_items INTEGER,
  total_revenue NUMERIC
);

-- 3) TOP PRODUCTS DAILY (processing output)
CREATE TABLE IF NOT EXISTS top_products_daily (
  day DATE,
  stockcode TEXT,
  units_sold INTEGER,
  revenue NUMERIC
);

CREATE INDEX IF NOT EXISTS idx_top_products_daily_day ON top_products_daily (day);
CREATE INDEX IF NOT EXISTS idx_top_products_daily_stockcode ON top_products_daily (stockcode);

-- 4) CUSTOMER FEATURES (processing output)
CREATE TABLE IF NOT EXISTS customer_features_quarterly (
  customer_id TEXT PRIMARY KEY,
  order_count INTEGER,
  total_spent NUMERIC,
  avg_basket_value NUMERIC,
  last_purchase TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_customer_features_last_purchase ON customer_features_quarterly (last_purchase);
