SPHINXBUILD ?= sphinx-build
SOURCEDIR = .
BUILDDIR = _build

.PHONY: html bundle
html:
	$(SPHINXBUILD) -W --keep-going -b html -d $(BUILDDIR)/doctrees $(SOURCEDIR) $(BUILDDIR)/html

bundle:
	$(SPHINXBUILD) -W --keep-going -E -b html -d $(BUILDDIR)/doctrees $(SOURCEDIR) ../../src/scitex_live_paper/_sphinx_html
