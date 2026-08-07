# cascade
An engineer renames a column in an upstream table. Cascade reads DataHub’s column-level lineage, works out exactly which downstream SQL files, Python pipelines and DAGs actually reference that column, rewrites each one, checks its own work compiles, and opens a single reviewable pull request.
