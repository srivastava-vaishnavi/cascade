from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cascade.lineage import MART_DIR, find_customer_email_in_sql


def main() -> int:
    mart_files = [
        MART_DIR / "dim_customers.sql",
        MART_DIR / "fct_orders_enriched.sql",
        MART_DIR / "fct_customer_activity.sql",
        MART_DIR / "fct_daily_revenue.sql",
    ]

    for mart_path in mart_files:
        print(f"\n==== {mart_path.name} ====")
        found, matches = find_customer_email_in_sql(mart_path, {"customer_email", "email"})
        if found:
            print("FOUND customer_email/email in this mart:")
            for item in matches:
                print(f"  - {item}")
        else:
            print("ABSENT: customer_email/email not found in this mart")

    print("\nSummary:")
    for mart_path in mart_files:
        found, _ = find_customer_email_in_sql(mart_path, {"customer_email", "email"})
        label = mart_path.stem
        status = "FOUND" if found else "ABSENT"
        print(f"- {label}: {status}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())