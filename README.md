# Cascade

Schema changed upstream. The fix PR is already open.

Cascade reads column-level lineage in a SQL warehouse, works out what breaks
when an upstream column changes, rewrites the affected files, verifies the
rewrite compiles, and opens one reviewable PR.

## Design principle

Deterministic AST transformation where correctness is provable, LLM only
where judgment is needed.

## Status: Phase 1 of 12

### Done

- **Package scaffold** — `cascade/__init__.py`, `cascade/cli.py`,
  `pyproject.toml`. Entry point `cascade` installs and runs (`pip install -e .`),
  prints version correctly.
- **Demo warehouse SQL** — three-layer structure:
  - `demo_source_db/` — raw tables (`customers`, `orders`), schema
    `demo_source_db`
  - `demo_warehouse/models/staging/` — passthrough views (`stg_customers`,
    `stg_orders`), schema `stage`
  - `demo_warehouse/models/marts/` — 4 views exercising different reference
    styles to `customer_email`:
    - `dim_customers.sql` — direct select
    - `fct_orders_enriched.sql` — join + alias
    - `fct_customer_activity.sql` — aggregation + expression (`LOWER()`,
      `GROUP BY`)
    - `fct_daily_revenue.sql` — control case, never references
      `customer_email`
- **`demo_warehouse/init.py`** — builds the whole warehouse end to end
  (creates schemas, runs source/staging/mart SQL in order). Idempotent:
  source tables use `DROP TABLE IF EXISTS ... CASCADE` so reruns don't fail.
- **Seed data** — `demo_source_db/seed_data.sql`, 5 customers / 8 orders,
  run automatically as part of `init.py`. Verified against
  `marts.fct_customer_activity` (aggregation and join confirmed correct).
- **`scripts/test_lineage.py`** — sqlglot-based scratch script proving
  column references can be traced through direct selects, joins/aliases,
  and expressions. Verified: finds `customer_email` correctly in all 3 real
  marts, correctly reports it absent in the control case.

### Pending

- **Rename detection + rewrite logic** — the real Cascade capability.
  Given an old column name and a new one, find every mart file that
  references the old name (across all reference styles already validated)
  and rewrite it in place, leaving unaffected files untouched. This is
  AST manipulation, not just detection.
- **Compile check** — verify rewritten SQL still parses/executes correctly
  before it's considered done.
- **PR generation** — collect only the changed files into one reviewable
  PR/diff.
- **`cascade`'s first real CLI command** (e.g. `cascade rename` or
  `cascade scan`) — wraps the above into the actual tool, currently `cli.py`
  only prints the version.
- **Flagged, revisit after project completion:** source DB separation is
  currently simulated via a Postgres schema (`demo_source_db`) in the same
  database. Real setup would use `postgres_fdw`/`dblink` or a genuinely
  separate database. See `TODO.md`.

## Remaining effort

Roughly 35–45 hours of engineering work across the pending items above.
