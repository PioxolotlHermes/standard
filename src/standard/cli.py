"""Command line entry point: `standard check | baseline | ...`."""

import argparse
import sys
from pathlib import Path

from standard import baseline
from standard.config import ConfigError, load_config
from standard.engine import CONFIG_FILE, analyze, run_check
from standard.files import list_files
from standard.model import Violation
from standard.sync import sync


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="standard", description="PioxolotlHermes code standard checker")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "baseline", "sync"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--root", type=Path, default=Path.cwd())
        cmd.add_argument("--config", type=Path, default=None, help=f"default: <root>/{CONFIG_FILE}")
        if name == "check":
            cmd.add_argument("--base", default=None, help="git ref for the R7 diff guard (skipped when absent)")
        elif name == "baseline":
            cmd.add_argument("--shrink", action="store_true", help="drop paid-off entries, never add")
    return parser


def _check(args: argparse.Namespace) -> int:
    report = run_check(args.root, args.config, args.base)
    for violation in report.errors:
        print(violation.format())
    print(report.budget)
    print(f"baseline debt: {report.debt} violation group(s) still listed")
    print(f"{len(report.errors)} error(s)")
    return 1 if report.errors else 0


def _baseline(args: argparse.Namespace) -> int:
    config_path = args.config or args.root / CONFIG_FILE
    violations: list[Violation] = analyze(args.root, load_config(config_path), config_path.name)[0]
    current = baseline.totals(violations)
    known = baseline.load(args.root)
    entries = baseline.shrink(current, known) if args.shrink else current
    baseline.write(args.root, entries)
    print(f"baseline: {len(entries)} entr{'y' if len(entries) == 1 else 'ies'} written")
    return 0


def _sync(args: argparse.Namespace) -> int:
    cfg = load_config(args.config or args.root / CONFIG_FILE)
    changed = sync(args.root, list_files(args.root), cfg)
    print("synced: " + (", ".join(changed) if changed else "already up to date"))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    handlers = {"check": _check, "baseline": _baseline, "sync": _sync}
    try:
        return handlers[args.command](args)
    except ConfigError as exc:
        print(f"standard: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
