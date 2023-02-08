.PHONY:
html:
	tox -e html

.PHONY:
clean:
	rm -rf _build

.PHONY:
refresh-bib:
	refresh-lsst-bib -d lsstbib
	@echo
	@echo "Commit the new bibliographies: git add lsstbib && git commit -m \"Update bibliographies.\""
