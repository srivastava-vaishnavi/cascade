"""Unit tests for lineage resolution and the rename rewrite.

Run: python3 -m pytest -q
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from cascade.cli import main
from cascade.rewrite import plan_rename, rewritten_sources, verify

DEMO_MODELS = Path(__file__).resolve().parents[1] / "demo_warehouse" / "models"


def write(dir_: Path, name: str, sql: str) -> Path:
    path = dir_ / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(sql, encoding="utf-8")
    return path


@pytest.fixture
def demo(tmp_path: Path) -> Path:
    models = tmp_path / "models"
    shutil.copytree(DEMO_MODELS, models)
    return models


def rename(models: Path, old="customer_email", new="email_address", table="customers"):
    plan = plan_rename(models, table, old, new)
    return plan, rewritten_sources(plan)


# --- the demo warehouse -----------------------------------------------------


def test_demo_blast_radius(demo):
    plan, _ = rename(demo)
    affected = {c.model.path.name for c in plan.affected}
    assert affected == {
        "stg_customers.sql",
        "dim_customers.sql",
        "fct_orders_enriched.sql",
        "fct_customer_activity.sql",
    }
    assert [c.model.path.name for c in plan.untouched_readers] == ["fct_daily_revenue.sql"]
    assert not plan.needs_review


def test_direct_select(demo):
    _, new = rename(demo)
    sql = new[demo / "marts" / "dim_customers.sql"]
    assert "    email_address,\n" in sql and "customer_email" not in sql


def test_join_alias_keeps_output_alias(demo):
    _, new = rename(demo)
    sql = new[demo / "marts" / "fct_orders_enriched.sql"]
    assert "c.email_address AS email" in sql


def test_expression_and_group_by(demo):
    _, new = rename(demo)
    sql = new[demo / "marts" / "fct_customer_activity.sql"]
    assert "LOWER(c.email_address) AS customer_email_normalized" in sql
    assert "GROUP BY c.customer_id, c.email_address;" in sql


def test_control_case_untouched(demo):
    _, new = rename(demo)
    assert demo / "marts" / "fct_daily_revenue.sql" not in new


def test_comments_and_layout_preserved(demo):
    _, new = rename(demo)
    path = demo / "marts" / "fct_customer_activity.sql"
    before, after = path.read_text().splitlines(), new[path].splitlines()
    assert len(before) == len(after)
    changed = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
    assert len(changed) == 2  # the LOWER() line and the GROUP BY line, nothing else
    assert after[0] == before[0]  # comment mentioning customer_email left alone


def test_verify_passes_and_is_idempotent(demo):
    plan, new = rename(demo)
    assert verify(demo, plan, new) == []
    for path, sql in new.items():
        path.write_text(sql)
    again, _ = rename(demo)
    assert again.affected == []


# --- edge cases -------------------------------------------------------------


def test_join_on_condition_is_rewritten(tmp_path):
    write(tmp_path, "s.sql", "CREATE VIEW stage.s AS SELECT customer_email, id FROM src.customers;")
    write(
        tmp_path,
        "m.sql",
        "CREATE VIEW marts.m AS SELECT a.id FROM stage.s a JOIN other.t b ON a.customer_email = b.email;",
    )
    _, new = rename(tmp_path)
    assert "ON a.email_address = b.email" in new[tmp_path / "m.sql"]


def test_same_name_on_unrelated_table_is_left_alone(tmp_path):
    write(tmp_path, "m.sql", "CREATE VIEW marts.m AS SELECT v.customer_email FROM src.vendors v;")
    plan, new = rename(tmp_path)
    assert new == {} and plan.untouched_readers == []


def test_aliased_output_stops_propagation(tmp_path):
    write(tmp_path, "s.sql", "CREATE VIEW stage.s AS SELECT customer_email AS email FROM src.customers;")
    write(tmp_path, "m.sql", "CREATE VIEW marts.m AS SELECT email FROM stage.s;")
    plan, new = rename(tmp_path)
    assert set(new) == {tmp_path / "s.sql"}
    assert "email_address AS email" in new[tmp_path / "s.sql"]


def test_ambiguous_unqualified_column_needs_review(tmp_path):
    write(
        tmp_path,
        "m.sql",
        "CREATE VIEW marts.m AS SELECT customer_email FROM src.customers c JOIN src.orders o ON c.id = o.cid;",
    )
    plan, new = rename(tmp_path)
    assert new == {}
    assert len(plan.needs_review) == 1


def test_select_star_propagates(tmp_path):
    write(tmp_path, "s.sql", "CREATE VIEW stage.s AS SELECT * FROM src.customers;")
    write(tmp_path, "m.sql", "CREATE VIEW marts.m AS SELECT customer_email FROM stage.s;")
    _, new = rename(tmp_path)
    assert set(new) == {tmp_path / "m.sql"}


def test_quoted_identifier(tmp_path):
    write(tmp_path, "m.sql", 'CREATE VIEW marts.m AS SELECT c."customer_email" FROM src.customers c;')
    _, new = rename(tmp_path)
    assert 'c."email_address"' in new[tmp_path / "m.sql"]


# --- CLI --------------------------------------------------------------------


def test_cli_dry_run_writes_nothing(demo, capsys):
    before = {p: p.read_text() for p in demo.rglob("*.sql")}
    code = main(["rename", "--table", "customers", "--old", "customer_email",
                 "--new", "email_address", "--models-dir", str(demo), "--dry-run"])
    assert code == 0
    assert {p: p.read_text() for p in demo.rglob("*.sql")} == before
    assert "+    c.email_address AS email" in capsys.readouterr().out


def test_cli_rename_writes_files(demo):
    code = main(["rename", "--table", "customers", "--old", "customer_email",
                 "--new", "email_address", "--models-dir", str(demo)])
    assert code == 0
    assert "c.email_address AS email" in (demo / "marts" / "fct_orders_enriched.sql").read_text()
