import os
import psycopg2

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "warehouse")
DB_USER = os.getenv("POSTGRES_USER", "de_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "de_password")

def run_sql(cur, sql: str):
    cur.execute(sql)

def main():
    conn = psycopg2.connect(
        host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    conn.autocommit = True

    with conn.cursor() as cur:
        # 1) Daily metrics
        run_sql(cur, """
        TRUNCATE TABLE daily_metrics;
        INSERT INTO daily_metrics (day, total_invoices, total_items, total_revenue)
        SELECT
          DATE(invoicedate) AS day,
          COUNT(DISTINCT invoice) AS total_invoices,
          SUM(quantity) AS total_items,
          SUM(quantity * price) AS total_revenue
        FROM retail_raw
        WHERE invoicedate IS NOT NULL
        GROUP BY DATE(invoicedate)
        ORDER BY day;
        """)

        # 2) Top products daily (Top 10 by revenue per day)
        run_sql(cur, """
        TRUNCATE TABLE top_products_daily;
        INSERT INTO top_products_daily (day, stockcode, units_sold, revenue)
        WITH daily_product AS (
          SELECT
            DATE(invoicedate) AS day,
            stockcode,
            SUM(quantity) AS units_sold,
            SUM(quantity * price) AS revenue
          FROM retail_raw
          WHERE invoicedate IS NOT NULL
          GROUP BY DATE(invoicedate), stockcode
        ),
        ranked AS (
          SELECT
            day, stockcode, units_sold, revenue,
            ROW_NUMBER() OVER (PARTITION BY day ORDER BY revenue DESC) AS rn
          FROM daily_product
        )
        SELECT day, stockcode, units_sold, revenue
        FROM ranked
        WHERE rn <= 10
        ORDER BY day, revenue DESC;
        """)

        # 3) Customer features (quarterly-style features)
        # We'll compute features per customer overall and keep "last_purchase".
        run_sql(cur, """
        TRUNCATE TABLE customer_features_quarterly;
        INSERT INTO customer_features_quarterly (customer_id, order_count, total_spent, avg_basket_value, last_purchase)
        WITH per_invoice AS (
          SELECT
            customer_id,
            invoice,
            MAX(invoicedate) AS invoice_date,
            SUM(quantity * price) AS invoice_value
          FROM retail_raw
          WHERE customer_id IS NOT NULL
            AND customer_id <> 'nan'
            AND invoicedate IS NOT NULL
          GROUP BY customer_id, invoice
        )
        SELECT
          customer_id,
          COUNT(*) AS order_count,
          SUM(invoice_value) AS total_spent,
          AVG(invoice_value) AS avg_basket_value,
          MAX(invoice_date) AS last_purchase
        FROM per_invoice
        GROUP BY customer_id;
        """)

        # Quick counts for logs
        run_sql(cur, "SELECT COUNT(*) FROM daily_metrics;")
        dm = cur.fetchone()[0]
        run_sql(cur, "SELECT COUNT(*) FROM top_products_daily;")
        tp = cur.fetchone()[0]
        run_sql(cur, "SELECT COUNT(*) FROM customer_features_quarterly;")
        cf = cur.fetchone()[0]

        print(f"Processing DONE ✅ daily_metrics={dm}, top_products_daily={tp}, customer_features_quarterly={cf}")

    conn.close()

if __name__ == "__main__":
    main()
