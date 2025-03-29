.PHONY: all format lint test tests help clean build publish publish-test docs docs-live docs-check release-major release-minor release-micro release-rc rollback

# Default target executed when no arguments are given to make.
all: help

######################
# TESTING
######################

# Define a variable for the test file path.
TEST_FILE ?= tests/

# unit tests are run with the --disable-socket flag to prevent network calls
test tests:
	poetry run pytest $(TEST_FILE)

######################
# LINTING AND FORMATTING
######################

# Define a variable for Python and notebook files.
PYTHON_FILES=./src/
MYPY_CACHE=.mypy_cache
lint_diff format_diff: PYTHON_FILES=$(shell git diff --name-only --diff-filter=d main | grep -E '\.py$$|\.ipynb$$')
lint_diff: MYPY_CACHE=.mypy_cache_diff
lint_tests format_tests: PYTHON_FILES=tests
lint_tests: MYPY_CACHE=.mypy_cache_test

lint lint_diff lint_tests:
	[ "$(PYTHON_FILES)" = "" ] || mkdir -p $(MYPY_CACHE) && poetry run mypy $(PYTHON_FILES) --cache-dir $(MYPY_CACHE)

format format_diff format_tests:
	[ "$(PYTHON_FILES)" = "" ] || poetry run black  $(PYTHON_FILES)

######################
# BUILDING AND PUBLISHING
######################

clean:
	rm -rf dist/
	rm -rf build/
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +

build: clean
	poetry build

publish-test: build
	poetry config repositories.testpypi https://test.pypi.org/legacy/
	poetry publish -r testpypi

publish: build
	poetry publish

docs:
	cd docs && poetry run make html

docs-live:
	poetry run sphinx-autobuild docs docs/_build/html --open-browser

docs-check:
	poetry run doc8 docs/
	cd docs && poetry run make linkcheck

######################
# ENVIRONMENT
######################

install:
	poetry install

install-dev:
	poetry install --with dev,test,lint,docs

update:
	poetry update


######################
# RELEASE
######################

release-major:
	@read -p "Enter changes: " changes; \
	python scripts/version.py create major --changes "$$changes"

release-minor:
	@read -p "Enter changes: " changes; \
	python scripts/version.py create minor --changes "$$changes"

release-micro:
	@read -p "Enter changes: " changes; \
	python scripts/version.py create micro --changes "$$changes"

release-rc:
	@read -p "Enter changes: " changes; \
	python scripts/version.py create micro --pre rc --changes "$$changes"

release-beta:
	@read -p "Enter changes: " changes; \
	python scripts/version.py create micro --pre b --changes "$$changes"

release-alpha:
	@read -p "Enter changes: " changes; \
	python scripts/version.py create micro --pre a --changes "$$changes"

rollback:
	python scripts/version.py rollback

# Helper target to show available commands
help-release:
	@echo "Available release commands:"
	@echo "  make release-major  - Create major release"
	@echo "  make release-minor  - Create minor release"
	@echo "  make release-micro  - Create micro release"
	@echo "  make release-rc     - Create release candidate"
	@echo "  make release-beta   - Create beta release"
	@echo "  make release-alpha  - Create alpha release"
	@echo "  make rollback       - Rollback last release"


######################
# HELP
######################

help:
	@echo '----'
	@echo 'format                       - run code formatters'
	@echo 'lint                         - run linters'
	@echo 'test                         - run unit tests'
	@echo 'tests                        - run unit tests'
