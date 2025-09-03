PY?=python3
VENV=.venv
PIP=$(VENV)/bin/pip
UVICORN=$(VENV)/bin/uvicorn
PORT ?= 8000

.PHONY: help venv install run dev clean

help:
	@echo "Targets:"
	@echo "  venv     - create virtual environment"
	@echo "  install  - install dependencies"
	@echo "  run      - run the API server"
	@echo "  dev      - venv + install + run"
	@echo "  clean    - remove venv and caches"

venv:
	$(PY) -m venv $(VENV)

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run:
	$(UVICORN) app:app --host 0.0.0.0 --port $(PORT) --reload

dev: install run

clean:
	rm -rf $(VENV) __pycache__ .pytest_cache .mypy_cache
