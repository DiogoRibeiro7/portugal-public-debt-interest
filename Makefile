.PHONY: install test lint typecheck quality all clean

install:
	python -m pip install -e '.[dev]'

test:
	pytest

lint:
	ruff check .

typecheck:
	mypy src

quality: lint typecheck test

all:
	pt-debt all --config config/default.yaml

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
