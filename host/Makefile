SHELL := /bin/bash
VENV := venv/bin/activate

.PHONY: all test format lint installer clean

venv/marker: pyproject.toml
	virtualenv venv
	. $(VENV) && pip install -e.[installer,hsm,gui]
	@touch venv/marker

venv/marker-dev: pyproject.toml
	virtualenv venv
	. $(VENV) && pip install -e.[dev,hsm]
	@touch venv/marker-dev

dev-virtualenv: venv/marker-dev
inst-virtualenv: venv/marker

test: dev-virtualenv
	. $(VENV) && ./entrypoints/pytest_entrypoint.sh

format: dev-virtualenv
	. $(VENV) && black src/tisecprov/ src/apps/spt/ tests/

lint: dev-virtualenv
	. $(VENV) && pylint src/tisecprov/ src/apps/spt/ tests/

installer: inst-virtualenv
	. $(VENV) && pyinstaller spt.spec
	. $(VENV) && pyinstaller qtgui.spec

clean:
	rm -rf venv
	rm -rf *.egg-info
	rm -rf __pycache__ .pytest_cache
	find . -type d -name -_pycache__ -exec rm -rf {} +
	rm -rf dist/*
