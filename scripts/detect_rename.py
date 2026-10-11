from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cascade.lineage import MART_DIR, find_customer_email_in_sql


MART_NAMES = (
    "dim_customers",
    "fct_orders_enriched",
    "fct_customer_activity",
    "fct_daily_revenue",
)


def main() -> int:
    print("Customer email rename detection:")
    for mart_name in MART_NAMES:
        found, matches = find_customer_email_in_sql(
            MART_DIR / f"{mart_name}.sql",
            {"customer_email", "email"},
        )
        status = "AFFECTED" if found else "UNAFFECTED"
        print(f"- {mart_name}: {status}")
        for match in matches:
            print(f"  - {match}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
