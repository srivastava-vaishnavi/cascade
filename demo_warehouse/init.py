import os
import psycopg2

DB_CONFIG = {
    "dbname": os.environ.get("CASCADE_DB_NAME", "cascade_demo"),
    "user": os.environ.get("CASCADE_DB_USER", "vaishnavisrivastava"),
    "password": os.environ.get("CASCADE_DB_PASSWORD", ""),
    "host": os.environ.get("CASCADE_DB_HOST", "localhost"),
    "port": os.environ.get("CASCADE_DB_PORT", "5432"),
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SOURCE_FILES = [
    "../demo_source_db/customers.sql",
    "../demo_source_db/orders.sql",
    "../demo_source_db/seed_data.sql",
]

STAGING_FILES = [
    "models/stage/stg_customers.sql",
    "models/stage/stg_orders.sql",
]

MART_FILES = [
    "models/marts/dim_customers.sql",
    "models/marts/fct_orders_enriched.sql",
    "models/marts/fct_customer_activity.sql",
    "models/marts/fct_daily_revenue.sql",
]


def run_sql_file(cur, relative_path: str) -> None:
    full_path = os.path.join(BASE_DIR, relative_path)
    with open(full_path, "r") as f:
        sql = f.read()
    print(f"Running {relative_path}...")
    cur.execute(sql)


def main() -> int:
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()

    try:
        cur.execute("CREATE SCHEMA IF NOT EXISTS demo_source_db;")
        cur.execute("CREATE SCHEMA IF NOT EXISTS stage;")
        cur.execute("CREATE SCHEMA IF NOT EXISTS marts;")

        for f in SOURCE_FILES:
            run_sql_file(cur, f)
        for f in STAGING_FILES:
            run_sql_file(cur, f)
        for f in MART_FILES:
            run_sql_file(cur, f)

        print("Demo warehouse initialized successfully.")
        return 0

    except Exception as e:
        print(f"Failed: {e}")
        return 1

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())