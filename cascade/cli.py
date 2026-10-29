"""cascade: schema changed upstream, the fix is already written.

  cascade scan   --table customers --column customer_email
  cascade rename --table customers --old customer_email --new email_address [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from cascade.rewrite import plan_rename, rewritten_sources, unified_diff, verify

DEFAULT_MODELS_DIR = "demo_warehouse/models"


def _version() -> str:
    try:
        return version("cascade")
    except PackageNotFoundError:
        return "unknown"


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def _models_dir(arg: str) -> Path:
    path = Path(arg)
    if not path.is_dir():
        raise SystemExit(f"Models directory not found: {path}")
    return path


def cmd_scan(args: argparse.Namespace) -> int:
    """Show the blast radius of a column without changing anything."""
    plan = plan_rename(_models_dir(args.models_dir), args.table, args.column, args.column)
    _print_blast_radius(plan)
    return 0


def cmd_rename(args: argparse.Namespace) -> int:
    models_dir = _models_dir(args.models_dir)
    if args.old.lower() == args.new.lower():
        print("Old and new column names are the same; nothing to do.")
        return 0

    plan = plan_rename(models_dir, args.table, args.old, args.new)
    _print_blast_radius(plan)

    if not plan.affected:
        print("\nNo model references the column. Nothing to rewrite.")
        return 0

    new_sources = rewritten_sources(plan)

    print("\nVerification:")
    problems = verify(models_dir, plan, new_sources)
    if problems:
        for problem in problems:
            print(f"  FAIL {problem}")
        print("\nNo files were written.")
        return 1
    print("  ok   every rewritten file parses")
    print(f"  ok   no reference to `{plan.old}` left on affected relations")

    if args.dry_run or args.diff:
        print()
        for path, after in new_sources.items():
            print(unified_diff(Path(_rel(path)), path.read_text(encoding="utf-8"), after), end="")

    if args.dry_run:
        print("\nDry run: no files were written.")
        return 0

    for path, after in new_sources.items():
        path.write_text(after, encoding="utf-8")
    print(f"\nWrote {len(new_sources)} file(s). Review with `git diff`.")
    return 2 if plan.needs_review else 0


def _print_blast_radius(plan) -> None:
    sources = ", ".join(sorted(plan.source_relations)) or "(none found)"
    print(f"Column: {plan.table}.{plan.old}   source: {sources}")

    print(f"\nAffected ({len(plan.affected)}):")
    for change in plan.affected:
        lines = ", ".join(str(e.line) for e in change.edits)
        label = "output column renamed" if plan.old != plan.new else "passes column through"
        note = f"  [{label}]" if change.exposes_new_name else ""
        print(f"  - {_rel(change.model.path)}  ({len(change.edits)} ref, line {lines}){note}")

    readers = plan.untouched_readers
    print(f"\nReads an affected table, never the column ({len(readers)}):")
    for change in readers:
        print(f"  - {_rel(change.model.path)}")

    if plan.needs_review:
        print(f"\nNeeds review, not rewritten ({len(plan.needs_review)}):")
        for change, note in plan.needs_review:
            print(f"  - {_rel(change.model.path)}: {note}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cascade", description=__doc__.strip().splitlines()[0])
    parser.add_argument("--version", action="version", version=f"cascade {_version()}")
    sub = parser.add_subparsers(dest="command")

    scan = sub.add_parser("scan", help="show which models read a column")
    scan.add_argument("--table", required=True, help="upstream table, e.g. customers")
    scan.add_argument("--column", required=True)
    scan.add_argument("--models-dir", default=DEFAULT_MODELS_DIR)
    scan.set_defaults(func=cmd_scan)

    rename = sub.add_parser("rename", help="rewrite models after an upstream column rename")
    rename.add_argument("--table", required=True, help="upstream table, e.g. customers")
    rename.add_argument("--old", required=True)
    rename.add_argument("--new", required=True)
    rename.add_argument("--models-dir", default=DEFAULT_MODELS_DIR)
    rename.add_argument("--dry-run", action="store_true", help="show the diff, write nothing")
    rename.add_argument("--diff", action="store_true", help="also print the diff when writing")
    rename.set_defaults(func=cmd_rename)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
