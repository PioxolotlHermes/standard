# ADR 0002: per-repo threshold overrides

Status: accepted (T-138). Date: 2026-11-28. Decision: Piotrek (owner).

## Context
Thresholds (R2 200/300 lines, R3 50 lines, R4 complexity 12, R6 test/code ratio 1.0) were hard-coded and equal for every
repo. A repo whose remaining tests are all critical (cori-core) cannot shrink below its ratio without deleting valuable
tests, and the only outlet was a baseline entry, which never ends and hides the reason.

## Decision
A repo may set `[overrides.<rule>]` in `standard.toml` (keys: R2 `file_lines`/`test_file_lines`, R3 `function_lines`,
R4 `complexity`, R6 `test_code_ratio`). Overrides may relax or tighten.

- `reason` (non-empty) and `adr` (a file that exists in the repo, where the owner's decision is documented) are mandatory.
- Unknown rule or key, missing reason/adr, non-numeric or non-positive value: config error, the check fails.
- Visibility: `standard check` prints every active override on each run; the R6 line shows the effective max.
- All limits flow through one `Limits` object. R4 and the ESLint limits are enforced by ruff/ESLint, so `standard sync`
  renders the effective values into the shipped config copies and the drift check compares against the rendered text.
- Defaults are unchanged; the defaults themselves change only in this repo on the owner's decision.

## Consequences
A deviation is explicit, justified, reviewed in the repo's diff (R7 flags standard.toml changes) and visible in CI logs.
An override does not replace splitting code: agents never add one on their own.
