# standard

Shared code standard for the PioxolotlHermes repos: a stdlib-only checker (`standard`), shared tool configs, a library
catalog and a Woodpecker CI step template. Rules apply from the first commit; known debt is kept in a baseline that may
only shrink.

## Rules

| ID | Rule | Checked by |
|---|---|---|
| R1 | Modular monolith (production code only; tests may import any module, production must not import tests or `[tests] globs` dirs): module = top-level directory under a package root; no imports between modules. Roles in `standard.toml`: `shared`, `core` (needs an ADR), `root`, `migrations` | checker (Python AST, TS/Svelte imports) |
| R2 | Files <= 200 physical lines, tests <= 300 (migrations, `# generated` files, data exempt) | checker |
| R3 | Python functions <= 50 lines | checker (front: ESLint) |
| R4 | Cyclomatic complexity <= 12 | ruff C90 / ESLint `complexity` (via shared configs) |
| R5 | Code in English; Polish letters only in `[texts]` globs | checker |
| R6 | Only critical tests: each states `Defect:`; test lines <= code lines (an existing overrun is baselined by its excess lines, may only shrink) | checker |
| R7 | New suppressions (noqa, type: ignore, eslint-disable, skip, `.only`), new exceptions, baseline growth need Piotrek's decision | checker with `--base` |
| R8 | Shared tooling: `ruff.standard.toml`, `eslint.standard.js`, mypy strict, dev tools pinned exactly (not-yet-adopted tools and floating pins can be baselined; stale synced copies cannot) | checker (drift) |
| R9 | Dependencies must be registered in `src/standard/configs/catalog.toml` with a purpose; one library per purpose (a second one needs `duplicate_of_ok = "<reason>"`) | checker |

## Usage

```
uvx --from git+https://github.com/PioxolotlHermes/standard standard init      # new repo: standard.toml, baseline, configs
uvx --from git+https://github.com/PioxolotlHermes/standard standard check     # before every commit
standard check --base origin/master      # + R7 diff guard
standard check --config path/to/x.toml   # config outside the repo (read-only probing)
standard baseline [--shrink]             # write / shrink standard-baseline.json
standard sync                            # copy shared configs into the repo
standard tools --json                    # adopted lint tools: {"ruff": bool, "format": bool, "mypy": bool}
```

Output is one line per violation: `RULE path:line message`; exit code 1 on any error. A baselined violation passes while it
does not grow; a baseline entry that no longer fails is an error (run `standard baseline --shrink`).

CI on Woodpecker (ci.maszlanka.pl): copy the step from `templates/woodpecker-standard-step.yaml` (pin `STANDARD_REF` there) and put `templates/AGENTS-block.md` into the repo's `AGENTS.md`. The step runs
the checker and then ruff, `ruff format --check` and mypy, each only when the repo has adopted it (`standard tools --json`):
ruff = `ruff` dev dependency + `[tool.ruff] extend = "ruff.standard.toml"`; format = ruff + `[tool.standard] format = true` in
`standard.toml` (set it once the repo is formatted); mypy = `mypy` dev dependency + `[tool.mypy] strict = true` + `files` or
`packages`. A tool not adopted is R8 debt in the baseline, so adopting it is a one-line switch that the ratchet keeps.

Libraries: a dependency missing from the catalog is an R9 error. To add one, commit it to `catalog.toml` with a `purpose`. Front lint (ESLint, svelte-check, vitest) stays in the repo's
own job.

## Pinning and bumping

Callers pin `STANDARD_REF: <sha>` in the `standard` step. To bump: change the sha, run
`standard sync`, commit the synced configs together with the bump.

## Exceptions policy

Over a limit = split the code. Never raise a threshold, never add an exception on your own: `[[exceptions]]` in
`standard.toml` (path, rule, reason) and every new suppression need Piotrek's decision (`tasks ask`). Thresholds change only
here, in this repo.
