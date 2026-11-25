# standard

Shared code standard for the PioxolotlHermes repos: a stdlib-only checker (`standard`), shared tool configs, a library
catalog and a reusable GitHub Actions workflow. Rules apply from the first commit; known debt is kept in a baseline that may
only shrink.

## Rules

| ID | Rule | Checked by |
|---|---|---|
| R1 | Modular monolith: module = top-level directory under a package root; no imports between modules. Roles in `standard.toml`: `shared`, `core` (needs an ADR), `root`, `migrations` | checker (Python AST, TS/Svelte imports) |
| R2 | Files <= 200 physical lines, tests <= 300 (migrations, `# generated` files, data exempt) | checker |
| R3 | Python functions <= 50 lines | checker (front: ESLint) |
| R4 | Cyclomatic complexity <= 12 | ruff C90 / ESLint `complexity` (via shared configs) |
| R5 | Code in English; Polish letters only in `[texts]` globs | checker |
| R6 | Only critical tests: each states `Defect:`; test lines <= code lines | checker |
| R7 | New suppressions (noqa, type: ignore, eslint-disable, skip, `.only`), new exceptions, baseline growth need Piotrek's decision | checker with `--base` |
| R8 | Shared tooling: `ruff.standard.toml`, `eslint.standard.js`, mypy strict, dev tools pinned exactly | checker (drift) |
| R9 | Dependencies only from `src/standard/configs/catalog.toml` | checker |

## Usage

```
uvx --from git+https://github.com/PioxolotlHermes/standard standard init      # new repo: standard.toml, baseline, configs
uvx --from git+https://github.com/PioxolotlHermes/standard standard check     # before every commit
standard check --base origin/master      # + R7 diff guard
standard check --config path/to/x.toml   # config outside the repo (read-only probing)
standard baseline [--shrink]             # write / shrink standard-baseline.json
standard sync                            # copy shared configs into the repo
```

Output is one line per violation: `RULE path:line message`; exit code 1 on any error. A baselined violation passes while it
does not grow; a baseline entry that no longer fails is an error (run `standard baseline --shrink`).

CI: copy `templates/ci-caller.yml`, put `templates/AGENTS-block.md` into the repo's `AGENTS.md`. The reusable workflow runs
the checker and, when `pyproject.toml` exists, ruff and mypy. Front lint (ESLint, svelte-check, vitest) stays in the repo's
own job.

## Pinning and bumping

Callers pin `uses: ...standard.yml@<sha>` and `with: ref: <sha>` (the same commit). To bump: change both shas, run
`standard sync`, commit the synced configs together with the bump.

## Exceptions policy

Over a limit = split the code. Never raise a threshold, never add an exception on your own: `[[exceptions]]` in
`standard.toml` (path, rule, reason) and every new suppression need Piotrek's decision (`tasks ask`). Thresholds change only
here, in this repo.
