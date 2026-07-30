# Minimal integration helpers for live OCI ansible-test runs.
SHELL := /bin/bash

PYTHON_BIN ?= python3
ANSIBLE_REF ?= stable-2.18
INTEGRATION_TARGETS ?=
ANSIBLE_TEST_COLLECTION_DIR ?= $(CURDIR)/tests/output/ansible_collections/oracle/oci

.PHONY: install-integration-reqs
install-integration-reqs:
	$(PYTHON_BIN) -m pip install --upgrade pip wheel --disable-pip-version-check
	$(PYTHON_BIN) -m pip install "https://github.com/ansible/ansible/archive/$(ANSIBLE_REF).tar.gz" --disable-pip-version-check
	$(PYTHON_BIN) -m pip install -r requirements.txt --disable-pip-version-check

.PHONY: list-integration-targets
list-integration-targets:
	@$(PYTHON_BIN) -c 'from pathlib import Path; targets = sorted(path.parent.parent.name for path in Path("tests/integration/targets").glob("*/meta/main.yml")); assert targets, "No integration targets discovered under tests/integration/targets"; print(" ".join(targets))'

.PHONY: integration-ci
integration-ci: install-integration-reqs
	@set -euo pipefail; \
	targets="$${INTEGRATION_TARGETS:-$$( $(MAKE) --no-print-directory PYTHON_BIN='$(PYTHON_BIN)' list-integration-targets )}"; \
	cleanup() { \
		rm -rf "$(ANSIBLE_TEST_COLLECTION_DIR)/tests/integration/.runtime" \
			"$(ANSIBLE_TEST_COLLECTION_DIR)/tests/integration/integration_config.yml"; \
	}; \
	trap cleanup EXIT; \
	rm -rf "$(ANSIBLE_TEST_COLLECTION_DIR)"; \
	mkdir -p "$(ANSIBLE_TEST_COLLECTION_DIR)"; \
	rsync -a --delete \
		--exclude='tests/output' \
		--exclude='.venv*/' \
		--exclude='.nox/' \
		--exclude='.pytest_cache/' \
		--exclude='.mypy_cache/' \
		--exclude='.idea/' \
		--exclude='.vscode/' \
		--exclude='*.tar.gz' \
		./ "$(ANSIBLE_TEST_COLLECTION_DIR)/"; \
	echo "Running integration targets: $$targets"; \
	cd "$(ANSIBLE_TEST_COLLECTION_DIR)"; \
	bash ./tests/integration/generate_integration_runtime.sh; \
	ansible --version; \
	ansible-test --version; \
	ansible-test integration --allow-destructive $$targets
