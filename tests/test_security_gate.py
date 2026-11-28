import json
from datetime import date
from pathlib import Path
from typing import Any

from standard.cli import main
from standard.security_gate import gate

TODAY = date(2026, 11, 28)


def osv_report(score: str, fixed: bool) -> dict[str, Any]:
    events: list[dict[str, str]] = [{"introduced": "0"}] + ([{"fixed": "2.0"}] if fixed else [])
    vuln = {"id": "GHSA-1", "affected": [{"package": {"name": "lib"}, "ranges": [{"events": events}]}]}
    group = {"ids": ["GHSA-1"], "aliases": ["CVE-1", "GHSA-1"], "max_severity": score}
    package = {"package": {"name": "lib", "version": "1.0"}, "vulnerabilities": [vuln], "groups": [group]}
    return {"results": [{"source": {"path": "uv.lock"}, "packages": [package]}]}


def reports(tmp_path: Path, osv: dict[str, Any], leaks: list[dict[str, Any]] | None = None) -> Path:
    (tmp_path / "osv.json").write_text(json.dumps(osv), encoding="utf-8")
    (tmp_path / "gitleaks.json").write_text(json.dumps(leaks or []), encoding="utf-8")
    return tmp_path


def run(tmp_path: Path, ignore: str = "") -> list[str]:
    ignore_file = tmp_path / "ignore.toml"
    ignore_file.write_text(ignore, encoding="utf-8")
    return gate(tmp_path, ignore_file, TODAY, ("osv", "gitleaks"))


def test_only_fixable_high_findings_and_secrets_fail(tmp_path: Path) -> None:
    """Defect: the gate passes a fixable HIGH vulnerability or a leaked secret, or fails on LOW / unfixable noise."""
    assert run(reports(tmp_path, osv_report("9.8", fixed=True)))[0].startswith("GHSA-1 in lib 1.0")
    assert run(reports(tmp_path, osv_report("5.0", fixed=True))) == []
    assert run(reports(tmp_path, osv_report("9.8", fixed=False))) == []
    leak = [{"RuleID": "aws-key", "File": "a.py", "StartLine": 3, "Fingerprint": "a.py:aws-key:3"}]
    assert len(run(reports(tmp_path, osv_report("1", fixed=False), leak))) == 1


def test_ignore_needs_reason_and_unexpired_date(tmp_path: Path) -> None:
    """Defect: an ignore without reason/expiry, or one past its date, keeps hiding a vulnerability forever."""
    reports(tmp_path, osv_report("9.8", fixed=True))
    entry = '[[ignore]]\nid = "CVE-1"\nreason = "not reachable"\nexpires = "{}"\n'
    assert run(tmp_path, entry.format("2026-12-31")) == []
    assert len(run(tmp_path, entry.format("2026-11-01"))) == 2  # the expired entry and the finding it no longer hides
    assert len(run(tmp_path, entry.format("").replace('reason = "not reachable"', ""))) == 2


def test_missing_report_fails_the_gate(tmp_path: Path, capsys: Any) -> None:
    """Defect: a scanner that crashed leaves no report and the pipeline goes green without having scanned."""
    assert main(["security-gate", "--root", str(tmp_path), "--reports", "none"]) == 1
    assert "no gitleaks report" in capsys.readouterr().out


LEAK = [{"RuleID": "generic-api-key", "File": "t.py", "StartLine": 3, "Fingerprint": "abc123:t.py:generic-api-key:3"}]
PERMANENT = '[[ignore]]\nid = "abc123:t.py:generic-api-key:3"\nreason = "test fixture"\nkind = "false-positive"\n'


def test_false_positive_secret_is_ignored_forever_but_only_by_exact_fingerprint(tmp_path: Path) -> None:
    """Defect: a history false positive turns red after a date, or its entry hides a different secret."""
    reports(tmp_path, osv_report("1", fixed=False), LEAK)
    assert run(tmp_path, PERMANENT) == []
    other = PERMANENT.replace("abc123", "def456")
    assert len(run(tmp_path, other)) == 1  # a new secret in the same file still fails
    assert len(run(tmp_path)) == 1


def test_false_positive_kind_cannot_hide_a_vulnerability(tmp_path: Path) -> None:
    """Defect: a permanent entry is used to silence a vulnerability, which must keep an expiry."""
    reports(tmp_path, osv_report("9.8", fixed=True))
    assert len(run(tmp_path, PERMANENT.replace("abc123:t.py:generic-api-key:3", "CVE-1"))) == 1


def test_malformed_permanent_entries_fail(tmp_path: Path) -> None:
    """Defect: an empty reason, unknown field/kind or expiry on a permanent entry is accepted and hides the leak."""
    reports(tmp_path, osv_report("1", fixed=False), LEAK)
    bad = [
        PERMANENT.replace("test fixture", ""),
        PERMANENT + 'note = "x"\n',
        PERMANENT.replace("false-positive", "whatever"),
        PERMANENT + 'expires = "2030-01-01"\n',
    ]
    for text in bad:
        assert len(run(tmp_path, text)) == 2, text  # the entry problem and the unhidden leak
