from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cascade.lineage import MART_DIR, find_column_in_sql

TARGETS = {"customer_email"}


def main() -> int:
    mart_files = [
        MART_DIR / "dim_customers.sql",
        MART_DIR / "fct_orders_enriched.sql",
        MART_DIR / "fct_customer_activity.sql",
        MART_DIR / "fct_daily_revenue.sql",
    ]

    results = {path: find_column_in_sql(path, TARGETS) for path in mart_files}

    for path, (found, matches) in results.items():
        print(f"\n==== {path.name} ====")
        if found:
            print("FOUND customer_email in this mart:")
            for item in matches:
                print(f"  - {item}")
        else:
            print("ABSENT: customer_email not found in this mart")

    print("\nSummary:")
    for path, (found, _) in results.items():
        print(f"- {path.stem}: {'FOUND' if found else 'ABSENT'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
