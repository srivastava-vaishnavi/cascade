# Cascade

Schema changed upstream. The fix PR is already open.

Cascade reads column-level lineage in a SQL warehouse, works out what breaks
when an upstream column changes, rewrites the affected files, verifies the
rewrite, and hands back one reviewable diff.

## Design principle

Deterministic AST transformation where correctness is provable, LLM only
where judgment is needed.

In practice: sqlglot's AST decides *which* tokens change, and the original
file is edited only at those exact positions. Comments, formatting and
output aliases stay as written, so the diff reads like a careful human edit.
Anything that can't be resolved with certainty is reported, never guessed.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

python3 demo_warehouse/init.py                     # build the demo warehouse
cascade scan --table customers --column customer_email
```

### The full demo loop

```bash
# 1. Upstream owner renames the column (the trigger event)
python3 scripts/simulate_upstream_rename.py --table customers --old customer_email --new email_address

# 2. Warehouse is now broken
python3 demo_warehouse/init.py      # Failed: column "customer_email" does not exist

# 3. Cascade fixes it
cascade rename --table customers --old customer_email --new email_address --diff

# 4. Warehouse builds again
python3 demo_warehouse/init.py      # Demo warehouse initialized successfully.

# Reset
git checkout -- demo_source_db demo_warehouse
```

Use `--dry-run` to see the diff without writing anything.

## What `cascade rename` does

1. Loads every model under `demo_warehouse/models`, orders them upstream first
2. Resolves each column reference to the relation it really comes from
   (aliases, joins, `JOIN ... ON`, `GROUP BY`, expressions, `SELECT *`)
3. Rewrites references to the renamed column. A model that passes the column
   through under its own name now exposes the new name, so its readers are
   rewritten too. An aliased output (`c.customer_email AS email`) keeps its
   alias, so propagation stops there.
4. Verifies: every rewritten file parses, and re-planning the same rename
   finds nothing left
5. Writes only the changed files and prints the blast radius

Example output on the demo warehouse:

```
Affected (4):
  - demo_warehouse/models/stage/stg_customers.sql  (1 ref, line 5)  [output column renamed]
  - demo_warehouse/models/marts/dim_customers.sql  (1 ref, line 5)  [output column renamed]
  - demo_warehouse/models/marts/fct_customer_activity.sql  (2 ref, line 9, 15)
  - demo_warehouse/models/marts/fct_orders_enriched.sql  (1 ref, line 12)

Reads an affected table, never the column (1):
  - demo_warehouse/models/marts/fct_daily_revenue.sql
```

`fct_daily_revenue.sql` reads `stg_customers` but never the column, and is
left alone. That is the proof the blast radius is column-level, not
table-level guessing.

### Sent for review instead of rewritten

- Unqualified column with several tables in scope
- Columns read from a subquery or CTE
- Any reference whose position in the source text can't be confirmed

## Layout

```
cascade/
  lineage.py    models, scopes, column resolution, dependency order
  rewrite.py    rename planning, position-based edits, verification, diffs
  cli.py        `cascade scan`, `cascade rename`
demo_source_db/ raw tables and seed data (the upstream, not edited by Cascade)
demo_warehouse/
  init.py       rebuilds the warehouse in Postgres
  models/stage  passthrough views
  models/marts  4 reference styles + control case
scripts/        demo helpers (simulate_upstream_rename, test_lineage)
tests/          python3 -m pytest -q
```

<img width="1324" height="654" alt="image" src="https://github.com/user-attachments/assets/6489768d-292a-4481-835e-358123f4ac4e" />

## Status

### Done

- Package, CLI (`scan`, `rename`), installable with `pip install -e .`
- Demo warehouse: source, stage and mart layers, seed data, idempotent rebuild
- Lineage resolution through direct selects, join aliases, `JOIN ... ON`,
  expressions, `GROUP BY` and `SELECT *`, with multi-hop propagation
- Position-based rewrite that preserves comments and layout
- Verification (parse + residual check) and unified diffs
- 15 unit tests, plus the full demo loop verified against Postgres 16

### Next

- Open the PR automatically (GitHub API, token from `GITHUB_TOKEN`)
- LLM pass for the needs-review cases, proposing a fix a human approves
- Read lineage from DataHub instead of parsing files only
- More change types: column drop, type change, table rename

See `TODO.md` for infrastructure items.
