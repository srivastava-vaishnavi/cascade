# TODO

## Next features

- [ ] **PR creation**: push the branch and open one PR via the GitHub API, token read from `GITHUB_TOKEN`.
- [ ] **Needs-review cases**: LLM proposes a fix for unqualified/ambiguous references and subquery/CTE sources; a human approves it.
- [ ] **DataHub lineage**: read column-level lineage from DataHub instead of only parsing files.
- [ ] **More change types**: column drop, type change, table rename.

## Flagged (revisit after project completion)

- [ ] **Source DB separation**: Currently using a Postgres schema (`demo_source_db`) within the same database to simulate the source warehouse being separate from the Cascade-managed repo. For a realistic setup, replace with actual cross-database access via `postgres_fdw` or `dblink`, or a genuinely separate database/repo.
- [ ] **Cloud Postgres migration**: Currently running Postgres locally. Consider migrating the demo warehouse to a cloud provider (Neon is closest to plain Postgres, has a generous free tier) to enable MCP-based database connectors for direct querying during future sessions. AWS RDS for PostgreSQL is the alternative if AWS experience is the goal.
