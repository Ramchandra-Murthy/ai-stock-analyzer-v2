.PHONY: install doctor run-web run-api run-cli test lint format typecheck clean

# Cross-platform (Linux, macOS, Windows with make). Uses uv and the locked dependencies
# declared in pyproject.toml / uv.lock, the same ones CI and the Docker image use.

install:
	uv sync --locked

doctor:
	uv run python scripts/check_providers.py

run-web:
	uv run streamlit run app.py

run-api:
	uv run uvicorn api.main:app --reload

run-cli:
	uv run python main.py --ticker AAPL

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check .
	uv run black --check .

format:
	uv run ruff check --fix .
	uv run black .

typecheck:
	uv run mypy services/ai_service.py services/fundamental_score_service.py services/recommendation_service.py services/score_service.py services/target_price_service.py services/technical_score_service.py services/trade_plan_service.py services/ui_formatters.py

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d \( -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache \) -prune -exec rm -rf {} +
