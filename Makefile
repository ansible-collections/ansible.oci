# Minimal integration helpers for live OCI ansible-test runs.
SHELL := /bin/bash

PYTHON_BIN ?= python3
ANSIBLE_REF ?= stable-2.18
INTEGRATION_TARGETS ?=
COLLECTION_ROOT ?= $(HOME)/.ansible/collections/ansible_collections/oracle/oci

.PHONY: install-integration-reqs
install-integration-reqs:
	$(PYTHON_BIN) -m pip install --upgrade pip wheel --disable-pip-version-check
	$(PYTHON_BIN) -m pip install "https://github.com/ansible/ansible/archive/$(ANSIBLE_REF).tar.gz" --disable-pip-version-check
	$(PYTHON_BIN) -m pip install -r requirements.txt --disable-pip-version-check

.PHONY: generate-integration-runtime
generate-integration-runtime:
	chmod +x ./tests/integration/generate_integration_runtime.sh
	PYTHON_BIN="$(PYTHON_BIN)" ./tests/integration/generate_integration_runtime.sh

.PHONY: upgrade-collections
upgrade-collections: generate-integration-runtime install-integration-reqs
	ansible-galaxy collection install --upgrade -p ~/.ansible/collections .

.PHONY: integration-ci
integration-ci: upgrade-collections
	cd "$(COLLECTION_ROOT)"; \
	ansible --version; \
	ansible-test --version; \
	ansible-test integration --allow-destructive $(INTEGRATION_TARGETS)
