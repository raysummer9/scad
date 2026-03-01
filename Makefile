PYTHON ?= python3
VENV_PYTHON ?= .venv/bin/python
PYTHONPATH_ENV = PYTHONPATH="."

.PHONY: install install-dev lint test smoke ci-local

install:
	$(VENV_PYTHON) -m pip install -r requirements.txt

install-dev:
	$(VENV_PYTHON) -m pip install -r requirements-dev.txt

lint:
	.venv/bin/ruff check .

test:
	$(PYTHONPATH_ENV) $(VENV_PYTHON) -m unittest discover -s tests -p "test_*.py" -v

smoke:
	$(PYTHONPATH_ENV) $(VENV_PYTHON) -m gov_procurement_framework.cli --help

ci-local: lint test smoke
