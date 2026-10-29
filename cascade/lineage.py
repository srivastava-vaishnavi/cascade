"""Column-level lineage over a folder of SQL view models.

Each model file holds `DROP VIEW ...; CREATE VIEW <schema.name> AS SELECT ...`.
This module parses those files with sqlglot, works out which relations each
model reads, orders models so upstream ones come first, and resolves every
column reference to the relation it actually comes from.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

import sqlglot
from sqlglot import exp

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "demo_warehouse" / "models"
MART_DIR = MODELS_DIR / "marts"

DIALECT = "postgres"


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def load_sql_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse(sql_text: str) -> list[exp.Expression]:
    return [s for s in sqlglot.parse(sql_text, read=DIALECT) if s is not None]


def relation_name(table: exp.Table) -> str:
    """`stage.stg_customers AS c` -> `stage.stg_customers` (lowercased)."""
    parts = [p for p in (table.catalog, table.db, table.name) if p]
    return ".".join(parts).lower()


def matches_table(relation: str, table: str) -> bool:
    """`demo_source_db.customers` matches `customers` or the full name."""
    relation, table = relation.lower(), table.lower()
    return relation == table or relation.endswith("." + table)


def iter_selects(sql_text: str) -> Iterable[exp.Select]:
    for statement in parse(sql_text):
        yield from statement.find_all(exp.Select)


# --------------------------------------------------------------------------
# Scopes: one SELECT, the tables it reads, and the columns it owns
# --------------------------------------------------------------------------


@dataclass
class Scope:
    select: exp.Select
    aliases: dict[str, str]  # alias or bare table name -> relation
    relations: list[str]  # relations read directly, in FROM/JOIN order
    has_subquery_source: bool

    def columns(self) -> Iterator[exp.Column]:
        """Columns that belong to this SELECT, not to a nested one."""
        for column in self.select.find_all(exp.Column):
            if column.find_ancestor(exp.Select) is self.select:
                yield column

    def resolve(self, column: exp.Column) -> str | None:
        """Relation a column comes from, or None when it can't be proven."""
        qualifier = column.table.lower() if column.table else ""
        if qualifier:
            return self.aliases.get(qualifier)
        if len(self.relations) == 1 and not self.has_subquery_source:
            return self.relations[0]
        return None


def build_scope(select: exp.Select) -> Scope:
    aliases: dict[str, str] = {}
    relations: list[str] = []
    has_subquery_source = False

    # sqlglot renamed this arg from "from" to "from_" in newer releases.
    sources = [select.args.get("from_") or select.args.get("from")]
    sources += [j for j in select.args.get("joins") or []]
    for source in sources:
        if source is None:
            continue
        target = source.this
        if isinstance(target, exp.Table):
            rel = relation_name(target)
            relations.append(rel)
            aliases[(target.alias or target.name).lower()] = rel
            aliases.setdefault(rel, rel)
        else:
            has_subquery_source = True

    return Scope(select, aliases, relations, has_subquery_source)


def scopes(statement: exp.Expression) -> list[Scope]:
    return [build_scope(s) for s in statement.find_all(exp.Select)]


# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------


@dataclass
class Model:
    path: Path
    name: str  # relation this file creates, e.g. marts.dim_customers
    sql: str
    create: exp.Create
    reads: set[str] = field(default_factory=set)

    @property
    def body(self) -> exp.Expression:
        return self.create.expression


def load_model(path: Path, sql_text: str | None = None) -> Model | None:
    sql_text = load_sql_file(path) if sql_text is None else sql_text
    for statement in parse(sql_text):
        if isinstance(statement, exp.Create) and isinstance(statement.this, exp.Table):
            reads = {relation_name(t) for t in statement.expression.find_all(exp.Table)}
            return Model(path, relation_name(statement.this), sql_text, statement, reads)
    return None


def load_models(models_dir: Path, overrides: dict[Path, str] | None = None) -> list[Model]:
    """Load every .sql model under models_dir, upstream models first."""
    overrides = overrides or {}
    models = []
    for path in sorted(models_dir.rglob("*.sql")):
        model = load_model(path, overrides.get(path))
        if model is not None:
            models.append(model)
    return topo_sort(models)


def topo_sort(models: list[Model]) -> list[Model]:
    by_name = {m.name: m for m in models}
    ordered: list[Model] = []
    state: dict[str, int] = {}  # 1 = visiting, 2 = done

    def visit(model: Model) -> None:
        if state.get(model.name) == 2:
            return
        if state.get(model.name) == 1:
            raise ValueError(f"Cycle in model dependencies at {model.name}")
        state[model.name] = 1
        for dep in sorted(model.reads):
            if dep in by_name and dep != model.name:
                visit(by_name[dep])
        state[model.name] = 2
        ordered.append(model)

    for model in models:
        visit(model)
    return ordered


# --------------------------------------------------------------------------
# Simple detection (kept for scripts/test_lineage.py and scripts/detect_rename.py)
# --------------------------------------------------------------------------


def collect_column_reads(select: exp.Select) -> list[dict[str, str]]:
    """Every column a SELECT reads: select list, WHERE, GROUP BY, HAVING,
    QUALIFY, ORDER BY and JOIN ... ON conditions."""
    scope = build_scope(select)
    reads: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    for column in scope.columns():
        alias_node = column.find_ancestor(exp.Alias)
        alias = alias_node.alias if alias_node is not None and alias_node.parent is select else ""
        source = scope.resolve(column) or "<unresolved>"
        key = (column.name, source, alias)
        if key not in seen:
            seen.add(key)
            reads.append({"column": column.name, "source": source, "alias": alias})
    return reads


def find_column_in_sql(path: Path, column_names: Iterable[str]) -> tuple[bool, list[str]]:
    """Does this SQL file read any of column_names? Matches source columns
    only, never output aliases."""
    targets = {c.lower() for c in column_names}
    matches: list[str] = []
    for select in iter_selects(load_sql_file(path)):
        for read in collect_column_reads(select):
            if read["column"].lower() in targets:
                alias = read["alias"] or "n/a"
                matches.append(f"{read['source']}.{read['column']} (alias={alias})")
    return bool(matches), matches
