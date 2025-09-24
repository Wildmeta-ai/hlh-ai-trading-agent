# Repository Guidelines

## Project Structure & Module Organization
- Main orchestrator: `hive_dynamic_core_modular.py` — single entry point for Hivebot (1:N strategies). Start via `./start_hive.sh` or PM2 (`ecosystem.config.js`).
- Core code: `hummingbot/` (client, connector, core, strategy, strategy_v2, data_feed, model, logger, notifier, remote_iface, templates, user). V2 controllers in `/controllers`.
- Config: `conf/`; tests: `test/` (pytest mirroring package layout); logs: `logs/`.
- Tools: `bin/`, `scripts/`, Dockerfiles; dashboard: `hivebot-manager/` (Next.js + PM2).

## Build, Test, and Development Commands
- `make install` → bootstrap env (`./install`); `make build` → compile Cython; `make clean` → clean artifacts; `make docker` → build image.
- Run orchestrator: `python hive_dynamic_core_modular.py --monitor --port 8080` or `./start_hive.sh`.
- PM2: `pm2 start ecosystem.config.js`, `pm2 restart hive-orchestrator`, `pm2 logs hive-orchestrator`.
- Tests: `make test`, `make run_coverage`, `make development-diff-cover`.

## Coding Style & Naming Conventions
- Python 3, 4-space indent, 120-column lines.
- Lint/format: `flake8`, `isort`, `autopep8` (configured in `.pre-commit-config.yaml`); Black settings in `pyproject.toml` (120 cols).
- Install hooks: `pre-commit install`; run: `pre-commit run --all-files`.
- Naming: modules `snake_case.py`; classes `CapWords`; functions/vars `snake_case`. Cython under `hummingbot/core` (`.pyx`, `.pxd`).

## Testing Guidelines
- Use `pytest`; place tests in `test/` as `test_*.py`. Examples: `pytest -q`, `pytest test/hummingbot/strategy -k pmm`.
- Coverage: repo gate set to 70% (`.coveragerc`), but PRs are expected to achieve 80%+.
- Prefer deterministic unit tests; avoid mock market data for integration-level behavior.

## Commit & Pull Request Guidelines
- Branches: `feat/...`, `fix/...`, `refactor/...`, `doc/...`.
- Conventional commits (per history): `feat: implement dynamic pair subscription`.
- Open PRs against `development`; include clear description, linked issues, and test results; enable “Allow edits by maintainers”.

## Agent-Specific Instructions
- Use the single orchestrator entry point (`hive_dynamic_core_modular.py`); do not create new entry scripts or duplicate flows.
- No mock data: integrate with real connectors/strategies; verification scripts do not equal completion.
- Manage processes with PM2; keep secrets out of VCS (use `.env`/`.env.template`).
