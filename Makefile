.PHONY: all format lint test tests help clean build publish publish-test docs docs-live docs-check release-major release-minor release-micro release-rc rollback

# Default target executed when no arguments are given to make.
all: help

######################
# ENVIRONMENT
######################

# Install core dependencies
install:
	@echo "Installing core dependencies..."
	@poetry install --only main

# Install all development dependencies
install-dev:
	@echo "Installing development dependencies..."
	@poetry install --with dev,test,lint,typing,docs

# Install spec@ific dependency groups
install-test:
	@echo "Installing test dependencies..."
	@poetry install --with test

install-lint:
	@echo "Installing linting dependencies..."
	@poetry install --with lint

install-docs:
	@echo "Installing documentation dependencies..."
	@poetry install --with docs

install-all:
	@echo "Installing all dependencies..."
	@poetry install --with dev,test,lint,typing,docs

# Update all dependencies
update:
	@echo "Updating dependencies..."
	@poetry update

# Create a new virtual environment
venv:
	@echo "Creating virtual environment..."
	@poetry shell

# Lock dependencies without installing them
lock:
	@echo "Locking dependencies..."
	@poetry lock

# Create a new Jupyter kernel for the current project
kernel:
	@echo "Installing Jupyter kernel..."
	@$(eval PYTHON_VERSION := $(shell poetry run python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"))
	@$(eval PROJECT_NAME := $(shell poetry version | cut -d' ' -f1))
	@poetry run python -m ipykernel install --user \
		--name=$(PROJECT_NAME) \
		--display-name="Python $(PYTHON_VERSION) ($(PROJECT_NAME))"

# Remove the Jupyter kernel for the current project
remove-kernel:
	@echo "Removing Jupyter kernel..."
	@$(eval PROJECT_NAME := $(shell poetry version | cut -d' ' -f1))
	@poetry run jupyter kernelspec remove $(PROJECT_NAME) -y

# Export requirements.txt files
requirements:
	@echo "Exporting requirements.txt..."
	@if ! poetry export --help >/dev/null 2>&1; then \
		echo "Installing poetry-plugin-export..."; \
		poetry self add poetry-plugin-export; \
	fi
	@poetry export -f requirements.txt --output requirements.txt --without-hashes
	@poetry export -f requirements.txt --with dev,test,lint,typing,docs --output requirements-dev.txt --without-hashes
	@echo "Requirements files created successfully"

######################
# LINTING AND FORMATTING
######################

# Define variables for Python files and caches
PYTHON_FILES=./src/langchain_prolog/
MYPY_CACHE=.mypy_cache
lint-diff format-diff: PYTHON_FILES=$(shell git diff --name-only --diff-filter=d main | grep -E '\.py$$|\.ipynb$$')
lint-diff: MYPY_CACHE=.mypy_cache_diff
lint-tests format-tests: PYTHON_FILES=tests
lint-tests: MYPY_CACHE=.mypy_cache_test

# Linting
lint: lint_mypy lint_flake8 lint_pylint

lint_mypy:
	@echo "Running mypy..."
	@if [ ! -z "$(PYTHON_FILES)" ]; then \
		mkdir -p $(MYPY_CACHE) && poetry run mypy $(PYTHON_FILES) --cache-dir $(MYPY_CACHE); \
	else \
		echo "No Python files to check with mypy."; \
	fi

lint_flake8:
	@echo "Running flake8..."
	@if [ ! -z "$(PYTHON_FILES)" ]; then \
		poetry run flake8 $(PYTHON_FILES); \
	else \
		echo "No Python files to check with flake8."; \
	fi

lint_pylint:
	@echo "Running pylint..."
	@if [ ! -z "$(PYTHON_FILES)" ]; then \
		poetry run pylint $(PYTHON_FILES); \
	else \
		echo "No Python files to check with pylint."; \
	fi

# Run all linters on changed files
lint-diff: lint_mypy_diff lint_flake8_diff lint_pylint_diff

lint_mypy_diff:
	@echo "Running mypy on changed files..."
	@if [ ! -z "$(PYTHON_FILES)" ]; then \
		mkdir -p $(MYPY_CACHE) && poetry run mypy $(PYTHON_FILES) --cache-dir $(MYPY_CACHE); \
	else \
		echo "No changed Python files to check with mypy."; \
	fi

lint_flake8_diff:
	@echo "Running flake8 on changed files..."
	@if [ ! -z "$(PYTHON_FILES)" ]; then \
		poetry run flake8 $(PYTHON_FILES); \
	else \
		echo "No changed Python files to check with flake8."; \
	fi

lint_pylint_diff:
	@echo "Running pylint on changed files..."
	@if [ ! -z "$(PYTHON_FILES)" ]; then \
		poetry run pylint $(PYTHON_FILES); \
	else \
		echo "No changed Python files to check with pylint."; \
	fi

# Run all linters on test files
lint-tests: lint_mypy_tests lint_flake8_tests lint_pylint_tests

lint_mypy_tests:
	@echo "Running mypy on test files..."
	@if [ ! -z "$(PYTHON_FILES)" ]; then \
		mkdir -p $(MYPY_CACHE) && poetry run mypy $(PYTHON_FILES) --cache-dir $(MYPY_CACHE); \
	else \
		echo "No test files to check with mypy."; \
	fi

lint_flake8_tests:
	@echo "Running flake8 on test files..."
	@if [ ! -z "$(PYTHON_FILES)" ]; then \
		poetry run flake8 $(PYTHON_FILES); \
	else \
		echo "No test files to check with flake8."; \
	fi

lint_pylint_tests:
	@echo "Running pylint on test files..."
	@if [ ! -z "$(PYTHON_FILES)" ]; then \
		poetry run pylint $(PYTHON_FILES); \
	else \
		echo "No test files to check with pylint."; \
	fi

# Formatting
format: format_black format_isort

format_black:
	@echo "Running black..."
	@if [ ! -z "$(PYTHON_FILES)" ]; then \
		poetry run black $(PYTHON_FILES); \
	else \
		echo "No Python files to format with black."; \
	fi

format_isort:
	@echo "Running isort..."
	@if [ ! -z "$(PYTHON_FILES)" ]; then \
		poetry run isort $(PYTHON_FILES); \
	else \
		echo "No Python files to format with isort."; \
	fi

format-diff:
	@echo "Running formatters on changed files..."
	@if [ ! -z "$(PYTHON_FILES)" ]; then \
		poetry run black $(PYTHON_FILES); \
		poetry run isort $(PYTHON_FILES); \
	else \
		echo "No changed Python files to format."; \
	fi

format-tests:
	@echo "Running formatters on test files..."
	@if [ ! -z "$(PYTHON_FILES)" ]; then \
		poetry run black $(PYTHON_FILES); \
		poetry run isort $(PYTHON_FILES); \
	else \
		echo "No test files to format."; \
	fi

# Combined check (useful for CI)
check: format lint test

# Pre-commit check
pre-commit: format-diff lint-diff test


######################
# TESTING
######################

# Define variables for test settings
TEST_FILE ?= tests/
PYTEST_ARGS ?=

# Run tests
test:
	@echo "Running tests..."
	@poetry run pytest $(TEST_FILE) $(PYTEST_ARGS)

# Run tests with coverage
test-cov:
	@echo "Running tests with coverage..."
	@poetry run pytest $(TEST_FILE) --cov=langchain_prolog --cov-report=term --cov-report=html

# Run tests in verbose mode
test-verbose:
	@echo "Running tests in verbose mode..."
	@poetry run pytest $(TEST_FILE) -v

# Run tests that match a spec@ific pattern
test-pattern:
	@echo "Running tests matching pattern $(p)..."
	@poetry run pytest $(TEST_FILE) -k "$(p)"

# Run a spec@ific test file
test-file:
	@echo "Running tests from file $(f)..."
	@poetry run pytest $(f) $(PYTEST_ARGS)

# Generate coverage report
coverage:
	@echo "Generating coverage report..."
	@poetry run coverage report
	@poetry run coverage html
	@echo "HTML coverage report generated in htmlcov/"

# Help for pytest options
help-test:
	@echo '====== Pytest Options ======'
	@echo ''
	@echo 'Usage: make test PYTEST_ARGS="<options>"'
	@echo ''
	@echo 'Common pytest options:'
	@echo '  -v, --verbose           Show more detailed output'
	@echo '  -x, --exitfirst         Stop on first failure'
	@echo '  --pdb                   Start the Python debugger on errors'
	@echo '  -m MARK                 Only run tests with spec@ific markers'
	@echo '  -k EXPRESSION           Only run tests that match expression'
	@echo '  --log-cli-level=INFO    Show log messages in the console'
	@echo '  --cov=PACKAGE           Measure code coverage for a package'
	@echo '  --no-cov                Disable coverage measurement'
	@echo ''
	@echo 'Examples:'
	@echo '  make test PYTEST_ARGS="-v"'
	@echo '  make test PYTEST_ARGS="-k \"not slow\""'
	@echo '  make test PYTEST_ARGS="-v --log-cli-level=INFO"'
	@echo '  make test PYTEST_ARGS="--cov=langchain_prolog --cov-report=html"'
	@echo ''
	@echo 'Specialized test targets:'
	@echo '  make test-verbose       Run tests with verbose output'
	@echo '  make test-cov           Run tests with coverage report'
	@echo '  make test-pattern p=foo Run tests matching "foo" pattern'
	@echo '  make test-file f=file   Run tests in spec@ific file'


######################
# DOCUMENTATION
######################

# Generate documentation
# Generate API documentation automatically
docs-api:
	@echo "Generating API documentation..."
	@cd docs && poetry run sphinx-apidoc -o api ../src/langchain_prolog -f

docs:
	@echo "Building documentation..."
	@cd docs && poetry run make html
	@echo "Documentation built in docs/_build/html/"

# Live documentation server
docs-live:
	@echo "Starting live documentation server..."
	@poetry run sphinx-autobuild docs docs/_build/html --open-browser

# Check documentation quality
docs-check:
	@echo "Checking documentation quality..."
	@poetry run doc8 docs/
	cd docs && poetry run make linkcheck

# Clean and rebuild documentation
docs-clean:
	@echo "Cleaning documentation build files..."
	@cd docs && poetry run make clean
	@cd docs && poetry run make html


######################
# BUILDING AND PUBLISHING
######################

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	@rm -rf dist/
	@rm -rf build/
	@rm -rf *.egg-info/
	@rm -rf .pytest_cache
	@rm -rf .mypy_cache*
	@rm -rf .coverage
	@rm -rf htmlcov/
	@rm -rf docs/_build/
	@find . -type d -name __pycache__ -exec rm -rf {} +

# Build package
build: clean
	@echo "Building package..."
	@poetry build

# Publish to TestPyPI
publish-test: build
	@echo "Publishing to TestPyPI..."
	@poetry config repositories.testpypi https://test.pypi.org/legacy/
	@poetry publish -r testpypi

# Publish to PyPI
publish: build
	@echo "Publishing to PyPI..."
	@poetry publish

# Validate that package builds correctly
validate-build: build
	@echo "Validating build..."
	@poetry run pip install --force-reinstall dist/*.whl
	@echo "Package installed successfully"


######################
# RELEASE
######################

# Release versions
release-major:
	@echo "Creating major release..."
	@read -p "Enter changes: " changes; \
	python scripts/release.py create major --changes "$$changes"

release-minor:
	@echo "Creating minor release..."
	@read -p "Enter changes: " changes; \
	python scripts/release.py create minor --changes "$$changes"

release-micro:
	@echo "Creating micro release..."
	@read -p "Enter changes: " changes; \
	python scripts/release.py create micro --changes "$$changes"

release-rc:
	@echo "Creating release candidate..."
	@read -p "Enter changes: " changes; \
	python scripts/release.py create micro --pre rc --changes "$$changes"

release-beta:
	@echo "Creating beta release..."
	@read -p "Enter changes: " changes; \
	python scripts/release.py create micro --pre b --changes "$$changes"

release-alpha:
	@echo "Creating alpha release..."
	@read -p "Enter changes: " changes; \
	python scripts/release.py create micro --pre a --changes "$$changes"

# Rollback release
rollback:
	@echo "Rolling back last release..."
	python scripts/release.py rollback

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
	@echo '====== langchain_prolog Development Tool ======'
	@echo ''
	@echo 'Environment:'
	@echo '  make install              - Install core dependencies'
	@echo '  make install-dev          - Install all development dependencies'
	@echo '  make update               - Update dependencies'
	@echo '  make venv                 - Create and activate virtual environment'
	@echo ''
	@echo 'Linting & Formatting:'
	@echo '  make format               - Run all formatters'
	@echo '  make format-diff          - Run all formatters on changed files'
	@echo '  make format-tests         - Run all formatters on test files'
	@echo '  make lint                 - Run all linters'
	@echo '  make lint-diff            - Run all linters on changed files'
	@echo '  make lint-tests           - Run all linters on test files'
	@echo '  make check                - Run format, lint, and test'
	@echo '  make pre-commit           - Run format and lint on changed files'
	@echo ''
	@echo 'Testing:'
	@echo '  make test                 - Run tests'
	@echo '  make test-cov             - Run tests with coverage'
	@echo '  make test-verbose         - Run tests in verbose mode'
	@echo '  make test-pattern p=<pat> - Run tests matching pattern'
	@echo '  make coverage             - Generate coverage report'
	@echo '  make help-test            - Show help for pytest options'
	@echo ''
	@echo 'Documentation:'
	@echo '  make docs-api             - Build API documentation'
	@echo '  make docs                 - Build documentation'
	@echo '  make docs-live            - Start live documentation server'
	@echo '  make docs-check           - Check documentation quality'
	@echo '  make docs-clean           - Build documentation from scratch'
	@echo ''
	@echo 'Building & Publishing:'
	@echo '  make clean                - Clean build art@ifacts'
	@echo '  make build                - Build package'
	@echo '  make publish-test         - Publish to TestPyPI'
	@echo '  make publish              - Publish to PyPI'
	@echo ''
	@echo 'Release:'
	@echo '  make release-major        - Create major release'
	@echo '  make release-minor        - Create minor release'
	@echo '  make release-micro        - Create micro release'
	@echo ''
	@echo 'For more detailed help on release commands:'
	@echo '  make help-release         - Show detailed release commands'
