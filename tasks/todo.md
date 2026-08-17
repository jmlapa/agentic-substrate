# Tasks: Centralized Settings and Secrets Management

- [ ] Task 1: Create `AppSettings` class and `.env.example` template
  - Acceptance: `AppSettings` class in `src/kernel/infrastructure/app_settings.py` with `pydantic-settings`, `SecretStr` fields, DSN properties, and `.env.example` in repo root.
  - Verify: Mypy strict passes on `app_settings.py`.
  - Files: `src/kernel/infrastructure/app_settings.py`, `src/kernel/infrastructure/__init__.py`, `.env.example`

- [ ] Task 2: Integrate `AppSettings` with `AppContainer` and `migrations/env.py`
  - Acceptance: `AppContainer` and `migrations/env.py` use `AppSettings` instead of `os.getenv()`.
  - Verify: Container creation and Alembic initialization load configuration without errors.
  - Files: `src/api_gateway/container.py`, `src/api_gateway/main.py`, `migrations/env.py`

- [ ] Task 3: Implement unit tests for `AppSettings` and verify quality gates
  - Acceptance: Comprehensive test suite in `tests/unit/test_app_settings.py` covering masking, defaults, environment overrides, and DSN parsing.
  - Verify: `make pre-commit` passes with 100% tests green, 0 mypy issues, and 0 ruff errors.
  - Files: `tests/unit/test_app_settings.py`, `CHANGELOG.md`
