# TODO

## Flagged (revisit after project completion)

- [ ] **Source DB separation**: Currently using a Postgres schema (`demo_source_db`) within the same database to simulate the source warehouse being separate from the Cascade-managed repo. For a realistic setup, replace with actual cross-database access via `postgres_fdw` or `dblink`, or a genuinely separate database/repo.
- [ ] **Cloud Postgres migration**: Currently running Postgres locally. Consider migrating the demo warehouse to a cloud provider (Neon is closest to plain Postgres, has a generous free tier) to enable MCP-based database connectors for direct querying during future sessions.