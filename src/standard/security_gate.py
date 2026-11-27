"""`standard security-gate`: decide from scanner reports (osv-scanner, gitleaks, trivy) whether the pipeline fails.

Fails on: a HIGH/CRITICAL vulnerability that has a fix available, any leaked secret, an invalid or expired entry in the
reviewed ignore file. Ignoring needs `security-ignore.toml` in the repo: `[[ignore]]` with id, reason and expires.
"""

import json
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

IGNORE_FILE = "security-ignore.toml"
HIGH = 7.0  # CVSS: HIGH starts at 7.0
LEVELS = {"HIGH", "CRITICAL"}


@dataclass(frozen=True)
class Finding:
    ids: frozenset[str]  # advisory id plus aliases (CVE, GHSA) or a gitleaks fingerprint
    text: str


def _score(value: object) -> float:
    try:
        return float(str(value))
    except ValueError:
        return 0.0


def _has_fix(vulns: list[dict[str, Any]], package: str) -> bool:
    for vuln in vulns:
        for affected in vuln.get("affected", []):
            if affected.get("package", {}).get("name") != package:
                continue
            events = [event for rng in affected.get("ranges", []) for event in rng.get("events", [])]
            if any("fixed" in event for event in events):
                return True
    return False


def osv_findings(data: dict[str, Any]) -> list[Finding]:
    """HIGH/CRITICAL (CVSS >= 7) vulnerability groups with a `fixed` version, per package."""
    out = []
    for result in data.get("results", []):
        for pkg in result.get("packages", []):
            name = pkg["package"]["name"]
            by_id = {v["id"]: v for v in pkg.get("vulnerabilities", [])}
            for group in pkg.get("groups", []):
                ids = frozenset(group.get("ids", [])) | frozenset(group.get("aliases", []))
                vulns = [by_id[i] for i in group.get("ids", []) if i in by_id]
                if _score(group.get("max_severity")) >= HIGH and _has_fix(vulns, name):
                    where = f"{name} {pkg['package']['version']} ({result['source']['path']})"
                    out.append(Finding(ids, f"{sorted(group['ids'])[0]} in {where}"))
    return out


def trivy_findings(data: dict[str, Any]) -> list[Finding]:
    out = []
    for result in data.get("Results") or []:
        for vuln in result.get("Vulnerabilities") or []:
            if vuln.get("Severity") in LEVELS and vuln.get("FixedVersion"):
                text = f"{vuln['VulnerabilityID']} in {vuln['PkgName']} {vuln.get('InstalledVersion', '')}"
                out.append(Finding(frozenset({vuln["VulnerabilityID"]}), f"{text} (fix {vuln['FixedVersion']})"))
    return out


def gitleaks_findings(data: list[dict[str, Any]]) -> list[Finding]:
    """Every leak counts; its id for the ignore file is the gitleaks fingerprint."""
    return [
        Finding(
            frozenset({str(leak.get("Fingerprint", ""))}),
            f"secret {leak.get('RuleID')} at {leak.get('File')}:{leak.get('StartLine')}",
        )
        for leak in data
    ]


def load_ignores(path: Path, today: date) -> tuple[dict[str, str], list[str]]:
    """Valid, unexpired ignore ids -> reason, and problems with the file itself."""
    if not path.is_file():
        return {}, []
    entries = tomllib.loads(path.read_text(encoding="utf-8")).get("ignore", [])
    ignored, problems = {}, []
    for entry in entries:
        ident, reason, expires = (str(entry.get(k, "")).strip() for k in ("id", "reason", "expires"))
        try:
            last_day = date.fromisoformat(expires)
        except ValueError:
            last_day = None
        if not (ident and reason and last_day):
            problems.append(f"{IGNORE_FILE}: entry {ident or '?'} needs id, reason and expires (YYYY-MM-DD)")
        elif last_day < today:
            problems.append(f"{IGNORE_FILE}: {ident} expired on {expires}; fix the finding or review and renew it")
        else:
            ignored[ident] = reason
    return ignored, problems


PARSERS: dict[str, Callable[[Any], list[Finding]]] = {
    "osv": osv_findings,
    "trivy": trivy_findings,
    "gitleaks": gitleaks_findings,
}


def collect(reports: Path, required: tuple[str, ...]) -> tuple[list[Finding], list[str]]:
    """Findings from osv*/gitleaks*/trivy*.json in `reports`; a required scanner without a report is a problem."""
    findings: list[Finding] = []
    problems = []
    for tool in required:
        paths = sorted(reports.glob(f"{tool}*.json"))
        if not paths:
            problems.append(f"no {tool} report in {reports}: the scanner did not run to the end")
        for path in paths:
            try:
                findings += PARSERS[tool](json.loads(path.read_text(encoding="utf-8")))
            except ValueError, KeyError, TypeError, AttributeError:
                problems.append(f"{path.name} is not a valid {tool} report")
    return findings, problems


def gate(reports: Path, ignore_file: Path, today: date, required: tuple[str, ...]) -> list[str]:
    """Problems that must fail the pipeline (empty list = green)."""
    ignored, problems = load_ignores(ignore_file, today)
    findings, broken = collect(reports, required)
    return problems + broken + [f.text for f in findings if not f.ids & ignored.keys()]
