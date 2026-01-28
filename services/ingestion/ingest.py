import os
import glob
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "warehouse")
DB_USER = os.getenv("POSTGRES_USER", "de_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "de_password")

DATA_DIR = os.getenv("DATA_DIR", "/data")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "50000"))  # safe for MacBook

def connect():
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Handle possible column name differences
    df.columns = [c.strip() for c in df.columns]
    # Rename common variants
    rename_map = {
        "InvoiceDate": "invoicedate",
        "Invoice": "invoice",
        "StockCode": "stockcode",
        "Description": "description",
        "Quantity": "quantity",
        "Price": "price",
        "Customer ID": "customer_id",
        "CustomerID": "customer_id",
        "Country": "country"
    }
    df = df.rename(columns=rename_map)

    # Keep only expected columns
    keep = ["invoice", "stockcode", "description", "quantity", "invoicedate", "price", "customer_id", "country"]
    df = df[[c for c in keep if c in df.columns]]

    # Parse timestamp
    df["invoicedate"] = pd.to_datetime(df["invoicedate"], errors="coerce")

    # Clean nulls
    df = df.dropna(subset=["invoicedate", "invoice", "stockcode"])

    # Types
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)
    df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0)

    # customer_id optional
    if "customer_id" in df.columns:
        df["customer_id"] = df["customer_id"].astype(str)

    return df

def insert_chunk(conn, df: pd.DataFrame):
    rows = list(df.itertuples(index=False, name=None))
    if not rows:
        return 0
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO retail_raw (invoice, stockcode, description, quantity, invoicedate, price, customer_id, country)
            VALUES %s
            """,
            rows,
            page_size=10000
        )
    conn.commit()
    return len(rows)

def main():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
    if not files:
        raise SystemExit(f"No CSV files found in {DATA_DIR}")

    conn = connect()
    total_inserted = 0

    for f in files:
        print(f"Reading: {f}")
        for chunk in pd.read_csv(
    f,
    chunksize=CHUNK_SIZE,
    encoding="utf-8",
    encoding_errors="ignore"
):

            chunk = normalize_columns(chunk)
            # Ensure all columns exist
            for col in ["description", "country", "customer_id"]:
                if col not in chunk.columns:
                    chunk[col] = None
            chunk = chunk[["invoice", "stockcode", "description", "quantity", "invoicedate", "price", "customer_id", "country"]]
            inserted = insert_chunk(conn, chunk)
            total_inserted += inserted
            print(f"Inserted {inserted} rows (total: {total_inserted})")

    conn.close()
    print(f"DONE. Total rows inserted: {total_inserted}")

if __name__ == "__main__":
    main()
