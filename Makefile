sync: requirements.txt .venv
	uv pip sync requirements.txt

.venv:
	uv venv

requirements.txt: requirements.in pyproject.toml
	uv pip compile requirements.in -o requirements.txt

format:
	.venv/bin/ruff format src

lint:
	.venv/bin/ruff check --fix src

typecheck:
	.venv/bin/mypy src

clean: format lint typecheck

test:
	.venv/bin/pytest
