.PHONY: setup lint test twin bench demo validate-menu clean

ifeq ($(OS),Windows_NT)
    VENV_DIR = .venv
    PYTHON = $(VENV_DIR)/Scripts/python.exe
else
    VENV_DIR = .venv
    PYTHON = $(VENV_DIR)/bin/python
endif

setup:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e .
	$(PYTHON) -m playwright install chromium

lint:
	$(PYTHON) -m ruff check .

test:
	$(PYTHON) -m pytest -v

twin:
	$(PYTHON) apps/shop_twin/backend/main.py

bench:
	$(PYTHON) -m proofbench.runner

demo:
	$(PYTHON) demo/demo_runner.py

validate-menu:
	$(PYTHON) demo/validate_menu.py

clean:
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info
