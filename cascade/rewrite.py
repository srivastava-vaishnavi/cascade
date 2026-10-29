"""Plan and apply a column rename across SQL models.

Design: the AST decides *what* to change, the original text is edited only
at those exact token positions. Formatting, comments and aliases stay as the
author wrote them, so the diff reads like a careful human edit.

Rules:
- A reference is rewritten only when it provably resolves to a relation that
  exposes the renamed column (the source table, or a model downstream of it).
- `c.customer_email AS email` becomes `c.email_address AS email`: the source
  column changes, the output alias is a contract and is left alone.
- A model that passes the column through under its own name (no alias) now
  exposes the new name, so models reading it are rewritten too.
- References that can't be resolved deterministically (unqualified column
  with several tables in scope, subquery sources) are never guessed at. They
  are reported for review.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path

from sqlglot import exp

from cascade.lineage import Model, load_models, matches_table, parse, scopes


@dataclass
class Edit:
    start: int  # inclusive
    end: int  # inclusive
    replacement: str
    line: int


@dataclass
class ModelChange:
    model: Model
    edits: list[Edit] = field(default_factory=list)
    reads_affected: bool = False  # reads an affected relation at all
    exposes_new_name: bool = False  # output column renamed (contract change)
    needs_review: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.edits)


@dataclass
class RenamePlan:
    table: str
    old: str
    new: str
    source_relations: set[str]
    changes: list[ModelChange]

    @property
    def affected(self) -> list[ModelChange]:
        return [c for c in self.changes if c.changed]

    @property
    def untouched_readers(self) -> list[ModelChange]:
        """Models that read an affected relation but never the column.
        This is what proves the blast radius is column-level, not table-level."""
        return [c for c in self.changes if c.reads_affected and not c.changed]

    @property
    def needs_review(self) -> list[tuple[ModelChange, str]]:
        return [(c, note) for c in self.changes for note in c.needs_review]


# --------------------------------------------------------------------------
# Planning
# --------------------------------------------------------------------------


def _identifier_edit(sql: str, ident: exp.Identifier, new: str) -> Edit | None:
    meta = ident.meta or {}
    start, end = meta.get("start"), meta.get("end")
    if start is None or end is None:
        return None
    span = sql[start : end + 1]
    if ident.quoted:
        # Quoted identifiers are case-sensitive in Postgres; keep the quotes.
        if span != f'"{ident.name}"':
            return None
        return Edit(start, end, f'"{new}"', meta.get("line", 0))
    if span.lower() != ident.name.lower():  # positions don't line up, refuse
        return None
    return Edit(start, end, new, meta.get("line", 0))


def plan_model(model: Model, affected: set[str], old: str, new: str) -> ModelChange:
    change = ModelChange(model)
    old_l = old.lower()
    change.reads_affected = bool(model.reads & affected)
    if not change.reads_affected:
        return change

    for scope in scopes(model.body):
        if scope.has_subquery_source:
            for column in scope.columns():
                if column.name.lower() == old_l and scope.resolve(column) is None:
                    change.needs_review.append(
                        f"line {column.this.meta.get('line', '?')}: `{column.sql()}` reads from a "
                        "subquery or CTE; not rewritten"
                    )
        for column in scope.columns():
            if column.name.lower() != old_l:
                continue
            source = scope.resolve(column)
            if source is None:
                if not scope.has_subquery_source and any(r in affected for r in scope.relations):
                    change.needs_review.append(
                        f"line {column.this.meta.get('line', '?')}: unqualified `{column.sql()}` "
                        f"with several tables in scope ({', '.join(scope.relations)}); not rewritten"
                    )
                continue
            if source not in affected:
                continue
            edit = _identifier_edit(model.sql, column.this, new)
            if edit is None:
                change.needs_review.append(
                    f"`{column.sql()}`: could not locate it in the source text; not rewritten"
                )
                continue
            change.edits.append(edit)

    # Does this model pass the column through under its own name?
    body = model.body
    if isinstance(body, exp.Select):
        top = next((s for s in scopes(body) if s.select is body), None)
        if top is not None:
            for projection in body.expressions:
                if isinstance(projection, exp.Star):
                    if any(r in affected for r in top.relations):
                        change.exposes_new_name = True
                elif isinstance(projection, exp.Column):
                    if isinstance(projection.this, exp.Star):
                        if top.resolve(projection) in affected:
                            change.exposes_new_name = True
                    elif projection.name.lower() == old_l and top.resolve(projection) in affected:
                        change.exposes_new_name = True

    change.edits.sort(key=lambda e: e.start)
    return change


def plan_rename(
    models_dir: Path,
    table: str,
    old: str,
    new: str,
    overrides: dict[Path, str] | None = None,
) -> RenamePlan:
    models = load_models(models_dir, overrides)
    model_names = {m.name for m in models}

    # Upstream relations that match --table and are not themselves models.
    referenced = set().union(*(m.reads for m in models)) if models else set()
    sources = {r for r in referenced - model_names if matches_table(r, table)}
    sources |= {m.name for m in models if matches_table(m.name, table)}
    affected = set(sources)

    changes = []
    for model in models:  # upstream first, so propagation is one pass
        change = plan_model(model, affected, old, new)
        if change.exposes_new_name:
            affected.add(model.name)
        changes.append(change)

    return RenamePlan(table, old, new, sources, changes)


# --------------------------------------------------------------------------
# Applying and verifying
# --------------------------------------------------------------------------


def apply_edits(sql: str, edits: list[Edit]) -> str:
    out = sql
    for edit in sorted(edits, key=lambda e: e.start, reverse=True):
        out = out[: edit.start] + edit.replacement + out[edit.end + 1 :]
    return out


def rewritten_sources(plan: RenamePlan) -> dict[Path, str]:
    return {c.model.path: apply_edits(c.model.sql, c.edits) for c in plan.affected}


def unified_diff(path: Path, before: str, after: str, root: Path | None = None) -> str:
    label = str(path.relative_to(root)) if root else str(path)
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{label}",
            tofile=f"b/{label}",
        )
    )


def verify(models_dir: Path, plan: RenamePlan, new_sources: dict[Path, str]) -> list[str]:
    """Checks that need no database:
    1. every rewritten file still parses;
    2. re-planning the same rename over the rewritten files finds nothing
       left to change (no residual reference to the old name)."""
    problems: list[str] = []
    for path, sql in new_sources.items():
        try:
            parse(sql)
        except Exception as err:  # sqlglot raises ParseError subclasses
            problems.append(f"{path.name}: does not parse after rewrite ({err})")
    if problems:
        return problems

    again = plan_rename(models_dir, plan.table, plan.old, plan.new, overrides=new_sources)
    for change in again.affected:
        problems.append(
            f"{change.model.path.name}: {len(change.edits)} reference(s) to "
            f"`{plan.old}` still left after rewrite"
        )
    return problems
