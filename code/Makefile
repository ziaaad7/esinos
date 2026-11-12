PYTHON ?= python3

.PHONY: run demo test help

help:
	@echo "make run   - ouvrir le menu interactif"
	@echo "make demo  - lancer la demonstration reproductible"
	@echo "make test  - executer les tests unitaires"

run:
	$(PYTHON) -m esinos

demo:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m esinos demo

test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests -v
