# standard - agent notes

Shared code standard for all PioxolotlHermes repos: checker (`src/standard/`, stdlib only), tool configs and library
catalog (`src/standard/configs/`, symlinked as `configs/`), templates (`templates/`), reusable workflow
(`.github/workflows/standard.yml`).

- Setup/run: `export PATH=/opt/data/.local/bin:$PATH`; `uv sync`, `uv run pytest`, `uv run ruff check .`,
  `uv run ruff format --check .`, `uv run mypy`, `uv run standard check`.
- This repo obeys its own standard (empty baseline). Over a limit = split the module, never raise a limit.
- Thresholds and the rule set change only on Piotrek's decision. The library catalog is a register: add a library with a
  `purpose` in a commit to `catalog.toml` (a second one for the same purpose needs `duplicate_of_ok`).
- Tests are critical-only: each docstring starts the defect it catches (`Defect: ...`).
- Runtime dependencies: none (stdlib). Dev tools pinned with `==`.
- Changing `src/standard/configs/*` changes every repo after its next `standard sync` + SHA bump; commit and push to master,
  CI must be green.
- Code, comments, commits in English; markdown for people may be Polish.
