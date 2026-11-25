- R1 modules are directories under the package roots; no imports between modules (roles: shared, core+ADR, root, migrations).
- R2 files <= 200 lines (tests <= 300); migrations and `generated` files are exempt.
- R3 Python functions <= 50 lines (front: ESLint max-lines-per-function).
- R4 cyclomatic complexity <= 12 (ruff C90 / ESLint complexity).
- R5 code, comments and names in English; Polish only in declared UI text files.
- R6 only critical tests: each has `Defect: ...`; test lines <= code lines.
- R7 no new noqa/type: ignore/eslint-disable/skip/.only/exceptions/baseline growth without Piotrek's decision.
- R8 shared tooling (ruff, mypy strict, ESLint config) synced by `standard sync`; dev tools pinned exactly.
- R9 dependencies must be registered in the catalog with a purpose; one library per purpose.
  Run `uvx --from git+https://github.com/PioxolotlHermes/standard standard check` before every commit; over a limit = split.
