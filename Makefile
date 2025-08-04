SHELL := bash

PYTHON := python3
PIP := .venv/bin/pip
VENV_ACTIVATE := . .venv/bin/activate

# Colored output
GREEN = \033[0;32m
NC = \033[0m

.PHONY: all
all: run

.PHONY: venv
venv:
	$(PYTHON) -m venv .venv

.PHONY: install
install: venv requirements.txt
	$(VENV_ACTIVATE) && $(PIP) install --upgrade pip
	$(VENV_ACTIVATE) && $(PIP) install -r requirements.txt
	$(VENV_ACTIVATE) && $(PIP) install black

.PHONY: run
run: install
	@echo "$(GREEN)Starting FastAPI proxy on http://localhost:8666$(NC)"
	$(VENV_ACTIVATE) && python node_proxy_bridge.py

.PHONY: format
format: install
	@echo "$(GREEN)Formatting Python code with Black$(NC)"
	$(VENV_ACTIVATE) && black *.py

.PHONY: clean
clean:
	rm -rf .venv __pycache__ .pytest_cache .mypy_cache *.egg-info
