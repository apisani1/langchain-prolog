# Minimal makefile for Sphinx documentation

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= poetry run sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build
PACKAGEDIR    = ../src/langchain_prolog

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile apidoc livehtml open github

# Custom target for generating API documentation
apidoc:
	poetry run sphinx-apidoc -o api $(PACKAGEDIR) -f
	@echo "API documentation generated. Don't forget to include 'api/modules' in your index.rst."

# Live documentation server with auto-reload
livehtml:
	poetry run sphinx-autobuild "$(SOURCEDIR)" "$(BUILDDIR)/html" --open-browser $(SPHINXOPTS) $(O)

# Open built documentation in browser
open:
	@if [ -f "$(BUILDDIR)/html/index.html" ]; then \
		python -m webbrowser -t "file://$(shell pwd)/$(BUILDDIR)/html/index.html"; \
	else \
		echo "Documentation not built yet. Run 'make html' first."; \
		exit 1; \
	fi

# Deploy documentation to GitHub Pages (if using GitHub Pages)
github:
	@make html
	@cp -a $(BUILDDIR)/html/. ../docs/
	@touch ../docs/.nojekyll
	@echo "Documentation copied to ../docs/ for GitHub Pages."
	@echo "Don't forget to commit and push the changes."

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
