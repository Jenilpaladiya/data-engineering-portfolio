import os
from typing import Optional, List, Tuple

import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse


app = FastAPI(title="Serving Service", version="1.1")

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "warehouse")
DB_USER = os.getenv("DB_USER", "de_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "de_password")

POOL: Optional[ThreadedConnectionPool] = None


@app.on_event("startup")
def startup():
    global POOL
    # Small pool is enough for a demo dashboard
    POOL = ThreadedConnectionPool(
        minconn=1,
        maxconn=5,
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


@app.on_event("shutdown")
def shutdown():
    global POOL
    if POOL:
        POOL.closeall()
        POOL = None


def _get_conn():
    if POOL is None:
        raise RuntimeError("DB pool is not initialized")
    return POOL.getconn()


def _put_conn(conn):
    if POOL is not None and conn is not None:
        POOL.putconn(conn)


def _fetch_one(sql: str, params: tuple = ()) -> Optional[dict]:
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        _put_conn(conn)


def _fetch_all(sql: str, params: tuple = ()) -> List[dict]:
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    finally:
        _put_conn(conn)


@app.get("/")
def root():
    return {"message": "Serving Service running. Open /dashboard or /docs."}


@app.get("/health")
def health():
    # quick DB check as well
    try:
        row = _fetch_one("SELECT 1 AS ok;")
        return {"status": "ok", "db": bool(row and row.get("ok") == 1)}
    except Exception:
        return {"status": "ok", "db": False}


@app.get("/metrics/daily")
def metrics_daily(limit: int = 30):
    rows = _fetch_all(
        """
        SELECT day, total_invoices, total_items, total_revenue
        FROM daily_metrics
        ORDER BY day DESC
        LIMIT %s;
        """,
        (limit,),
    )

    # Ensure JSON-friendly types
    out = []
    for r in rows:
        out.append(
            {
                "day": str(r["day"]),
                "total_invoices": int(r["total_invoices"]),
                "total_items": int(r["total_items"]),
                "total_revenue": float(r["total_revenue"]),
            }
        )
    return out


@app.get("/metrics/top-products")
def metrics_top_products(day: str, limit: int = 10):
    rows = _fetch_all(
        """
        SELECT day, stockcode, units_sold, revenue
        FROM top_products_daily
        WHERE day = %s
        ORDER BY revenue DESC, units_sold DESC
        LIMIT %s;
        """,
        (day, limit),
    )

    out = []
    for r in rows:
        out.append(
            {
                "day": str(r["day"]),
                "stockcode": r["stockcode"],
                "units_sold": int(r["units_sold"]),
                "revenue": float(r["revenue"]),
            }
        )
    return out


def _fmt_eur(x: float) -> str:
    return f"€{x:,.2f}"


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(day: Optional[str] = None):
    # If no metrics yet, show a friendly message
    latest = _fetch_one("SELECT MAX(day) AS max_day FROM daily_metrics;")
    if not latest or latest["max_day"] is None:
        return HTMLResponse(
            """
            <html><body style="font-family:system-ui;padding:24px;">
              <h2>Serving Dashboard</h2>
              <p><b>No metrics found yet.</b></p>
              <p>Run ingestion + processing first, then refresh:</p>
              <pre>docker compose run --rm ingestion
docker compose run --rm processing</pre>
              <p><a href="/docs">Open API docs</a></p>
            </body></html>
            """,
            status_code=200,
        )

    default_day = str(latest["max_day"])
    selected_day = day or default_day

    # Day selector list (last 30 days available)
    days = _fetch_all(
        """
        SELECT day
        FROM daily_metrics
        ORDER BY day DESC
        LIMIT 30;
        """
    )
    day_options = [str(d["day"]) for d in days]

    # Summary for selected day (from daily_metrics)
    summary = _fetch_one(
        """
        SELECT day, total_invoices, total_items, total_revenue
        FROM daily_metrics
        WHERE day = %s;
        """,
        (selected_day,),
    )

    # Last 7 days revenue for mini chart
    last7 = _fetch_all(
        """
        SELECT day, total_revenue
        FROM daily_metrics
        ORDER BY day DESC
        LIMIT 7;
        """
    )
    last7_rows: List[Tuple[str, float]] = [(str(r["day"]), float(r["total_revenue"])) for r in last7]
    max_rev = max([rev for _, rev in last7_rows], default=1.0)

    # Top products for selected day
    top_day = _fetch_all(
        """
        SELECT stockcode, units_sold, revenue
        FROM top_products_daily
        WHERE day = %s
        ORDER BY revenue DESC, units_sold DESC
        LIMIT 10;
        """,
        (selected_day,),
    )

    # Top 5 all-time by revenue
    top_all = _fetch_all(
        """
        SELECT stockcode,
               SUM(revenue) AS total_rev,
               SUM(units_sold) AS total_units
        FROM top_products_daily
        GROUP BY stockcode
        ORDER BY total_rev DESC
        LIMIT 5;
        """
    )

    # Build HTML
    css = """
    <style>
      :root{
        --bg:#0b1020;
        --card:#111a33;
        --text:#e9eefc;
        --muted:#a9b4d0;
        --line:rgba(233,238,252,.12);
        --accent:#7aa2ff;
      }
      body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;background:linear-gradient(180deg,#0b1020,#070a14);color:var(--text);}
      .wrap{max-width:980px;margin:0 auto;padding:24px;}
      h1{margin:0 0 10px 0;font-size:28px;}
      .muted{color:var(--muted);}
      .grid{display:grid;grid-template-columns:repeat(12,1fr);gap:14px;margin-top:14px;}
      .card{background:rgba(17,26,51,.92);border:1px solid var(--line);border-radius:14px;padding:14px;}
      .span4{grid-column:span 4;}
      .span6{grid-column:span 6;}
      .span12{grid-column:span 12;}
      @media (max-width:860px){.span4,.span6{grid-column:span 12;}}
      .kpi{font-size:22px;font-weight:700;margin-top:6px;}
      .row{display:flex;align-items:center;justify-content:space-between;gap:10px;}
      select{background:#0f1730;color:var(--text);border:1px solid var(--line);padding:8px 10px;border-radius:10px;}
      table{width:100%;border-collapse:collapse;margin-top:8px;font-size:14px;}
      th,td{padding:10px;border-bottom:1px solid var(--line);text-align:left;}
      th{color:var(--muted);font-weight:600;}
      .barwrap{display:flex;align-items:center;gap:10px;}
      .bar{height:10px;border-radius:999px;background:linear-gradient(90deg,var(--accent),#9b7aff);min-width:6px;}
      a{color:var(--accent);text-decoration:none;}
      a:hover{text-decoration:underline;}
      .pill{display:inline-block;padding:4px 10px;border:1px solid var(--line);border-radius:999px;color:var(--muted);font-size:12px;}
      .footer{margin-top:14px;color:var(--muted);font-size:12px;}
    </style>
    """

    header = f"""
    <div class="wrap">
      <div class="row">
        <div>
          <h1>Serving Dashboard</h1>
          <div class="muted">Batch analytics outputs (PostgreSQL) served via FastAPI</div>
        </div>
        <div class="pill">Selected day: {selected_day}</div>
      </div>
    """

    selector = """
      <div class="card" style="margin-top:14px;">
        <div class="row">
          <div>
            <b>Choose a day</b>
            <div class="muted" style="font-size:12px;">Changes the “Top Products (Selected day)” table</div>
          </div>
          <form method="get" action="/dashboard">
            <select name="day" onchange="this.form.submit()">
    """
    for d in day_options:
        selected_attr = "selected" if d == selected_day else ""
        selector += f'<option value="{d}" {selected_attr}>{d}</option>'
    selector += """
            </select>
          </form>
        </div>
      </div>
    """

    # Summary cards
    if summary:
        inv = int(summary["total_invoices"])
        items = int(summary["total_items"])
        rev = float(summary["total_revenue"])
    else:
        inv, items, rev = 0, 0, 0.0

    cards = f"""
      <div class="grid">
        <div class="card span4">
          <div class="muted">Invoices (selected day)</div>
          <div class="kpi">{inv:,}</div>
        </div>
        <div class="card span4">
          <div class="muted">Items sold (selected day)</div>
          <div class="kpi">{items:,}</div>
        </div>
        <div class="card span4">
          <div class="muted">Revenue (selected day)</div>
          <div class="kpi">{_fmt_eur(rev)}</div>
        </div>
      </div>
    """

    # Last 7 days table with bars
    last7_html = """
      <div class="card span12" style="margin-top:14px;">
        <div class="row">
          <div><b>Last 7 Days Revenue</b><div class="muted" style="font-size:12px;">From daily_metrics.total_revenue</div></div>
          <div class="muted">Endpoint: <a href="/metrics/daily?limit=7" target="_blank">/metrics/daily?limit=7</a></div>
        </div>
        <table>
          <thead><tr><th>Day</th><th>Revenue</th><th style="width:45%;">Trend</th></tr></thead>
          <tbody>
    """
    for d, r in last7_rows:
        width = int((r / max_rev) * 100) if max_rev else 0
        last7_html += f"""
          <tr>
            <td>{d}</td>
            <td>{_fmt_eur(r)}</td>
            <td>
              <div class="barwrap">
                <div class="bar" style="width:{max(3, width)}%;"></div>
                <span class="muted" style="font-size:12px;">{width}%</span>
              </div>
            </td>
          </tr>
        """
    last7_html += """
          </tbody>
        </table>
      </div>
    """

    # Top products (selected day)
    top_day_html = f"""
      <div class="card span6" style="margin-top:14px;">
        <div class="row">
          <div><b>Top Products (Selected day)</b><div class="muted" style="font-size:12px;">From top_products_daily</div></div>
          <div class="muted" style="font-size:12px;">
            <a href="/metrics/top-products?day={selected_day}&limit=10" target="_blank">API</a>
          </div>
        </div>
        <table>
          <thead><tr><th>Stockcode</th><th>Units</th><th>Revenue</th></tr></thead>
          <tbody>
    """
    if not top_day:
        top_day_html += f"<tr><td colspan='3' class='muted'>No rows for {selected_day}.</td></tr>"
    else:
        for r in top_day:
            code = r["stockcode"]
            units = int(r["units_sold"])
            revenue = float(r["revenue"])
            top_day_html += f"<tr><td>{code}</td><td>{units:,}</td><td>{_fmt_eur(revenue)}</td></tr>"
    top_day_html += """
          </tbody>
        </table>
      </div>
    """

    # Top products all-time
    top_all_html = """
      <div class="card span6" style="margin-top:14px;">
        <div class="row">
          <div><b>Top 5 Products (All-time)</b><div class="muted" style="font-size:12px;">Grouped by stockcode</div></div>
          <div class="muted" style="font-size:12px;"><a href="/docs" target="_blank">/docs</a></div>
        </div>
        <table>
          <thead><tr><th>Stockcode</th><th>Units</th><th>Total revenue</th></tr></thead>
          <tbody>
    """
    for r in top_all:
        code = r["stockcode"]
        units = int(r["total_units"])
        total_rev = float(r["total_rev"])
        top_all_html += f"<tr><td>{code}</td><td>{units:,}</td><td>{_fmt_eur(total_rev)}</td></tr>"
    top_all_html += """
          </tbody>
        </table>
      </div>
    """

    footer = """
      <div class="footer">
        Useful links:
        <a href="/dashboard">/dashboard</a> ·
        <a href="/docs">/docs</a> ·
        <a href="/metrics/daily?limit=5" target="_blank">/metrics/daily</a>
      </div>
    </div>
    """

    html = f"<html><head><title>Serving Dashboard</title>{css}</head><body>{header}{selector}{cards}<div class='grid'>{last7_html}{top_day_html}{top_all_html}</div>{footer}</body></html>"
    return HTMLResponse(html, status_code=200)
