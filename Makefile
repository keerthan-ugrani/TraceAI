export UV_CACHE_DIR ?= $(abspath $(CURDIR)/../.traceai-cache/uv)
export XDG_CACHE_HOME ?= $(abspath $(CURDIR)/../.traceai-cache)

.PHONY: setup format lint typecheck security test test-unit test-integration test-verification coverage analyze trace dashboard build audit ci

setup:
	uv sync --extra dev

format:
	uv run ruff format .
	uv run ruff check --fix .

lint:
	uv run ruff format --check .
	uv run ruff check .

typecheck:
	uv run mypy src/traceai

security:
	uv run bandit -c pyproject.toml -r src/traceai -q

test: coverage

test-unit:
	uv run pytest -m "not integration" -q

test-integration:
	uv run pytest -m integration -q

test-verification:
	uv run pytest -m verification -q

coverage:
	uv run pytest --cov=traceai --cov-report=term-missing --cov-report=xml -q

analyze:
	uv run traceai analyze --input data/requirements.csv --output-dir outputs

trace:
	uv run traceai trace SWE-REQ-014 --data data/engineering_data.json --output outputs/engineering_intelligence_report.json

dashboard:
	uv run streamlit run app.py

build:
	uv build

audit:
	uv run pip-audit

ci: lint typecheck security coverage build
