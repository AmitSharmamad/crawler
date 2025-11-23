.PHONY: run test clean install

run:
	uv run main.py

test:
	uv run pytest tests/ -v

clean:
	rm -rf __pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

install:
	uv sync
	playwright install chromium
