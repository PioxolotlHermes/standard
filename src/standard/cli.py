"""Command line entry point: `standard check | baseline | ...`."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from standard import baseline
from standard.config import ConfigError, load_config
from standard.engine import CONFIG_FILE, analyze, run_check
from standard.files import list_files
from standard.init_repo import init_repo
from standard.model import Violation
from standard.security_gate import IGNORE_FILE, gate
from standard.sync import sync
from standard.tools import repo_adoption


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="standard", description="PioxolotlHermes code standard checker")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="create standard.toml, an empty baseline and synced configs")
    init.add_argument("--root", type=Path, default=Path.cwd())
    init.add_argument("--package", action="append", default=[], help="code root, repeatable (default: detect src/*)")
    init.add_argument("--front", action="append", default=[], help="front dir with package.json, repeatable")
    for name in ("check", "baseline", "sync", "tools"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--root", type=Path, default=Path.cwd())
        cmd.add_argument("--config", type=Path, default=None, help=f"default: <root>/{CONFIG_FILE}")
        if name == "check":
            cmd.add_argument("--base", default=None, help="git ref for the R7 diff guard (skipped when absent)")
        elif name == "baseline":
            cmd.add_argument("--shrink", action="store_true", help="drop paid-off entries, never add")
        elif name == "tools":
            cmd.add_argument("--json", action="store_true", help="print {ruff, format, mypy} adoption as JSON")
    scan = sub.add_parser("security-gate", help="fail on HIGH/CRITICAL fixable vulnerabilities and leaked secrets")
    scan.add_argument("--root", type=Path, default=Path.cwd())
    scan.add_argument("--reports", type=Path, default=Path(".security"), help="dir with osv*/gitleaks*/trivy*.json")
    scan.add_argument("--require", default="gitleaks", help="comma list of scanners that must have a report")
    scan.add_argument("--ignore-file", type=Path, default=None, help=f"default: <root>/{IGNORE_FILE}")
    return parser


def _security_gate(args: argparse.Namespace) -> int:
    ignore = args.ignore_file or args.root / IGNORE_FILE
    required = tuple(name for name in args.require.split(",") if name)
    problems = gate(args.root / args.reports, ignore, date.today(), required)
    print("reports read: " + (", ".join(sorted(p.name for p in (args.root / args.reports).glob("*.json"))) or "none"))
    for problem in problems:
        print(f"SECURITY {problem}")
    print(f"{len(problems)} security problem(s)")
    return 1 if problems else 0


def _check(args: argparse.Namespace) -> int:
    report = run_check(args.root, args.config, args.base)
    for violation in report.errors:
        print(violation.format())
    for line in report.overrides:
        print(line)
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


def _tools(args: argparse.Namespace) -> int:
    cfg = load_config(args.config or args.root / CONFIG_FILE)
    adopted = repo_adoption(args.root, cfg.format)
    print(
        json.dumps(adopted)
        if args.json
        else "\n".join(f"{tool}: {'yes' if on else 'no'}" for tool, on in adopted.items())
    )
    return 0


def _init(args: argparse.Namespace) -> int:
    written = init_repo(args.root, args.package, args.front)
    print("created: " + ", ".join(written))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    handlers = {
        "check": _check,
        "baseline": _baseline,
        "sync": _sync,
        "init": _init,
        "tools": _tools,
        "security-gate": _security_gate,
    }
    try:
        return handlers[args.command](args)
    except ConfigError as exc:
        print(f"standard: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
