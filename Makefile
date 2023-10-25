.PHONY:
init:
	pip install tox pre-commit
	pre-commit install

.PHONY:
html:
	tox run -e html

.PHONY:
clean:
	rm -rf _build

.PHONY:
refresh-bib:
	tox run -e refresh-bib
	@echo
	@echo "Commit the new bibliographies: git add lsstbib && git commit -m \"Update bibliographies.\""
