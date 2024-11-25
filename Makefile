.PHONY: clean clean-test clean-pyc clean-build docs help pytest
.DEFAULT_GOAL := help

define BROWSER_PYSCRIPT
import os, webbrowser, sys

from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BROWSER := python -c "$$BROWSER_PYSCRIPT"

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr .coverage.*
	rm -fr htmlcov/
	rm -fr report.html
	rm -fr report.xml
	rm -fr coverage.xml
	rm -fr .pytest_cache

lint: ## check for style issues
	@PRE_COMMIT_COLOR=never pre-commit run --all-files | tee tests/linting/pre-commit-output.txt 2>&1; \
    if [ $$? -eq 0 ]; then \
        echo "pre-commit passed successfully."; \
    else \
        echo "pre-commit failed. Please check tests/linting/pre-commit-output.txt for details."; \
        exit 1; \
    fi

urlcheck: ## check for dead URLs
	urlchecker check . --file-types .py,.rst,.md,.json \
    --exclude-urls \
            https://fernlab.gfz-potsdam.de/

test: ## run tests quickly with the default Python
	pytest

test-all: ## run tests on every Python version with tox
	tox

coverage: ## check code coverage quickly with the default Python
	coverage erase
	coverage run --source s2downloader -m pytest
	coverage combine 	# must be called in order to make coverage work in multiprocessing
	coverage report -m
	coverage html
	$(BROWSER) htmlcov/index.html

pytest: clean-test ## Runs pytest with coverage and creates coverage and test report
	## - puts the coverage results in the folder 'htmlcov'
	## - generates cobertura 'coverage.xml' (needed to show coverage in GitLab MR changes)
	## - generates 'report.html' based on pytest-reporter-html1
	## - generates JUnit 'report.xml' to show the test report as a new tab in a GitLab MR
	## NOTE: additional options pytest and coverage (plugin pyteest-cov) are defined in .pytest.ini and .coveragerc
	pytest tests \
		--verbosity=3 \
		--color=yes \
		--tb=short \
		--cov=s2downloader \
		--cov-report html:htmlcov \
		--cov-report term-missing \
		--cov-report xml:coverage.xml \
		--template=html1/index.html --report=report.html \
		--junitxml report.xml

docs: ## generate Sphinx HTML documentation, including API docs
	rm -f docs/s2downloader.rst
	rm -f docs/modules.rst
	sphinx-apidoc s2downloader -o docs/ --private --doc-project 'Python API reference'
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	$(BROWSER) docs/_build/html/index.html

servedocs: docs ## compile the docs watching for changes
	watchmedo shell-command -p '*.rst' -c '$(MAKE) -C docs html' -R -D .

release: dist ## package and upload a release
	twine upload dist/*

dist: clean ## builds source and wheel package
	python -m build --sdist
	twine check dist/*
	ls -l dist

install: clean ## install the package to the active Python's site-packages
	python setup.py install

gitlab_CI_docker:  ## Build a docker image for CI use within gitlab
	cd ./tests/CI_docker/; bash ./build_s2downloader_testsuite_image.sh
