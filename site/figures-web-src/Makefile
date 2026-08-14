# Web-only figures. Does not overwrite print figure PDFs.
PYTHON ?= python3

.PHONY: all data figures

all: data figures

data:
	$(PYTHON) export_frozen_data.py

figures:
	$(PYTHON) render_web_figures.py
