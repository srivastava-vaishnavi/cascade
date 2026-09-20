from __future__ import annotations

from pathlib import Path
from typing import Iterable

import sqlglot
from sqlglot import exp

ROOT = Path(__file__).resolve().parents[1]
MART_DIR = ROOT / "demo_warehouse" / "models" / "marts"

TARGET_FIELD_NAMES = {"customer_email", "email"}


def load_sql_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def iter_selects(sql_text: str) -> Iterable[exp.Select]:
    parsed = sqlglot.parse(sql_text, read="postgres")
    for statement in parsed:
        for select in statement.find_all(exp.Select):
            yield select


def gather_table_aliases(select: exp.Select) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in [select.args.get("from"), *list(select.args.get("joins") or [])]:
        if node is None:
            continue
        for table in node.find_all(exp.Table):
            alias = table.alias_or_name
            aliases[alias] = table.sql()
    return aliases


def resolve_column_ref(column: exp.Column, aliases: dict[str, str]) -> str:
    source_table = column.table
    if source_table:
        return f"{aliases.get(source_table, source_table)}.{column.name}"
    if aliases:
        for alias, table_sql in aliases.items():
            return f"{table_sql}.{column.name}"
    return column.name


def collect_column_reads(select: exp.Select) -> list[dict[str, str]]:
    aliases = gather_table_aliases(select)
    reads: list[dict[str, str]] = []

    for expression in list(select.expressions or []):
        for node in expression.walk():
            if isinstance(node, exp.Column):
                reads.append(
                    {
                        "column": node.name,
                        "source": resolve_column_ref(node, aliases),
                        "alias": expression.alias_or_name if isinstance(expression, exp.Alias) else "",
                    }
                )

    for clause in [
        select.args.get("where"),
        select.args.get("group"),
        select.args.get("having"),
        select.args.get("qualify"),
        select.args.get("order"),
    ]:
        if clause is None:
            continue
        for node in clause.walk():
            if isinstance(node, exp.Column):
                reads.append(
                    {
                        "column": node.name,
                        "source": resolve_column_ref(node, aliases),
                        "alias": "",
                    }
                )

    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for read in reads:
        key = (read["column"], read["source"], read["alias"])
        if key not in seen:
            deduped.append(read)
            seen.add(key)
    return deduped


def find_customer_email_in_sql(path: Path) -> tuple[bool, list[str]]:
    sql_text = load_sql_file(path)
    matches: list[str] = []
    found = False

    for select in iter_selects(sql_text):
        for read in collect_column_reads(select):
            field = read["column"]
            alias = read["alias"]
            if field in TARGET_FIELD_NAMES or alias in TARGET_FIELD_NAMES:
                found = True
                matches.append(f"{read['source']} (field={field}, alias={alias or 'n/a'})")

    return found, matches


def main() -> int:
    mart_files = [
        MART_DIR / "dim_customers.sql",
        MART_DIR / "fct_orders_enriched.sql",
        MART_DIR / "fct_customer_activity.sql",
        MART_DIR / "fct_daily_revenue.sql",
    ]

    for mart_path in mart_files:
        print(f"\n==== {mart_path.name} ====")
        found, matches = find_customer_email_in_sql(mart_path)
        if found:
            print("FOUND customer_email/email in this mart:")
            for item in matches:
                print(f"  - {item}")
        else:
            print("ABSENT: customer_email/email not found in this mart")

    print("\nSummary:")
    for mart_path in mart_files:
        found, matches = find_customer_email_in_sql(mart_path)
        label = mart_path.stem
        status = "FOUND" if found else "ABSENT"
        print(f"- {label}: {status}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
