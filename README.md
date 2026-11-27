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

## Security scans (component security testing)

Tools, one per purpose (ADR `docs/adr/0001-security-tooling.md`, registered in `catalog.toml` `[ci.tools]`): **osv-scanner**
(dependency vulnerabilities: uv.lock, requirements.txt, package-lock.json, pnpm-lock.yaml), **gitleaks** (secrets, working
tree + history), **trivy** (base images of Dockerfile FROM lines, only repos that build an image). Template:
`templates/woodpecker-security-step.yaml` (images pinned by digest). The scanners write reports to `.security/`;
`standard security-gate` fails the pipeline on HIGH/CRITICAL (CVSS >= 7) vulnerabilities with a fix available and on any
secret. Ignore only through `security-ignore.toml` in the repo: `[[ignore]]` with `id`, `reason`, `expires` (YYYY-MM-DD);
without all three or past the date it fails.

Rollout per repo: paste the template (`variables:` + steps) into `.woodpecker.yaml`, set `STANDARD_REF` of `security-gate`
to the pinned sha, add `security-gate` to `depends_on` of the image build/push steps, add `cron` to the workflow events
(push/deploy steps keep `event: [push, manual]`) and create the cron `nightly-full` (`POST /api/repos/<id>/cron`).
Python (uv.lock) and npm (package-lock.json / pnpm-lock.yaml) repos need nothing else; repos without an image drop the
`security-image` step. Scans run on lockfile/Dockerfile changes, cron and manual runs; other pushes skip them.

## ESLint variants

`standard sync` writes `eslint.standard.js` into every `[front] dirs` entry: the TypeScript/Svelte variant when its
`package.json` lists `typescript` or `typescript-eslint`, otherwise the plain-JavaScript variant
(`configs/eslint.standard.plain.js`, same rules, needs only `eslint`, `@eslint/js`, `globals`). Usage:
`import { standardConfig } from './eslint.standard.js'; export default standardConfig({ sources: ['app/**/*.js'], extra: [...] });`
`sources` are the globs where the R2/R3/R4 limits apply (default `src/**`).

## Pinning and bumping

Callers pin `STANDARD_REF: <sha>` in the `standard` step. To bump: change the sha, run
`standard sync`, commit the synced configs together with the bump.

## Exceptions policy

Over a limit = split the code. Never raise a threshold, never add an exception on your own: `[[exceptions]]` in
`standard.toml` (path, rule, reason) and every new suppression need Piotrek's decision (`tasks ask`). Thresholds change only
here, in this repo.
