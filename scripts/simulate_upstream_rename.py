"""Simulate the upstream owner renaming a column in demo_source_db.

This is the trigger event Cascade reacts to, not part of Cascade itself:
it edits the source DDL (CREATE TABLE) and the seed INSERT column list.

    python3 scripts/simulate_upstream_rename.py --table customers --old customer_email --new email_address

Undo with: git checkout -- demo_source_db
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlglot import exp

from cascade.lineage import matches_table, parse, relation_name
from cascade.rewrite import Edit, apply_edits

SOURCE_DIR = PROJECT_ROOT / "demo_source_db"


def edits_for(sql: str, table: str, old: str, new: str) -> list[Edit]:
    edits = []
    for statement in parse(sql):
        target = statement.this
        if isinstance(target, exp.Schema):  # CREATE TABLE t (...) / INSERT INTO t (...)
            target = target.this
        if not isinstance(target, exp.Table) or not matches_table(relation_name(target), table):
            continue
        for ident in statement.find_all(exp.Identifier):
            parent = ident.parent
            in_column_list = isinstance(parent, exp.ColumnDef) or isinstance(parent, exp.Schema)
            if in_column_list and ident.name.lower() == old.lower():
                start, end = ident.meta.get("start"), ident.meta.get("end")
                if start is not None and sql[start : end + 1].lower() == old.lower():
                    edits.append(Edit(start, end, new, ident.meta.get("line", 0)))
    return edits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", required=True)
    parser.add_argument("--old", required=True)
    parser.add_argument("--new", required=True)
    args = parser.parse_args()

    for path in sorted(SOURCE_DIR.glob("*.sql")):
        sql = path.read_text(encoding="utf-8")
        edits = edits_for(sql, args.table, args.old, args.new)
        if edits:
            path.write_text(apply_edits(sql, edits), encoding="utf-8")
            print(f"{path.name}: renamed {len(edits)} occurrence(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
