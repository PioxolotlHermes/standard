# ADR 0001: component security tooling

Status: accepted (T-138). Date: 2026-11-28.

## Context
Repos pin dependencies (uv.lock, requirements.txt, package-lock.json, pnpm-lock.yaml) and some build images from a
Dockerfile. Nothing checked them for known vulnerabilities or leaked secrets, and one repo (snake) ran an ad-hoc
`npm audit`. We want a minimal, uniform toolset: one tool per purpose, running in Woodpecker without docker.sock.

## Decision
| Purpose | Tool | Why |
|---|---|---|
| Dependency vulnerabilities | osv-scanner (Google) | one scanner and one database (OSV) for Python and npm lockfiles, no per-ecosystem tools (pip-audit, npm audit); static binary image |
| Secret scan | gitleaks | de-facto standard, scans working tree and git history, stable fingerprints for ignores |
| Image / Dockerfile scan (only repos that build an image) | trivy | scans the base images named in the Dockerfile for OS-package vulnerabilities, which osv-scanner does not see |

Images are pinned by digest; versions are registered in `catalog.toml` (`[ci.tools]`), one entry per purpose.
Scanners only write reports; `standard security-gate` (stdlib, tested) applies one policy to all of them:

- fail on HIGH/CRITICAL (CVSS >= 7.0) vulnerabilities that have a fixed version (nothing to do about unfixable ones),
- fail on any leaked secret,
- the only way to ignore a finding is `security-ignore.toml` in the repo (reviewed like code): `id`, `reason`,
  `expires` (YYYY-MM-DD). An entry without all three, or an expired one, fails the gate.

Dependency and image scans run when a lockfile, Dockerfile or the ignore file changes, and always on cron
(`nightly-full`) and manual runs; new advisories appear without a commit, so the nightly run is the real control.
Normal pushes skip them (green in seconds); gitleaks and the gate run every time (seconds). Skipped scans never block
the image push; a failing gate does.

## Amendment (T-138, 2026-11-28): permanent ignore for verified secret false positives
gitleaks scans the whole git history and history cannot be changed, so an expiring ignore for a false positive there
only makes the nightly run red later without any new information. Decision (CORI): a secret finding verified as a
false positive may be ignored by its gitleaks fingerprint with a mandatory `reason` and `kind = "false-positive"`
(no `expires`). The gate applies such an entry to secret findings only, matched by exact fingerprint; vulnerability
(osv/trivy) ignores keep the mandatory expiry. Unknown fields, an unknown kind, an empty reason or `expires` on a
permanent entry fail the gate, and a real secret always fails (rotate it, do not ignore it).
Reports go to `.security/`, which repos keep in `.gitignore` (`standard sync` adds it) so tests that need a clean
`git status` keep working.

## Consequences
- A new HIGH advisory turns the nightly run red until the dependency is bumped or an expiring ignore is reviewed.
- osv-scanner reads advisories online (deps.dev / osv.dev); steps have internet egress.
- Not covered: SAST, license checks, runtime image scan of the pushed image (needs registry credentials in the scan step).
