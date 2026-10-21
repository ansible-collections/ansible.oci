# Minimal integration helpers for live OCI ansible-test runs.
SHELL := /bin/bash

PYTHON_BIN ?= python3
UNIT_PYTHON_VERSION ?= 3.12
UNIT_TARGETS ?=
INTEGRATION_TARGETS ?=
COLLECTION_ROOT ?= $(HOME)/.ansible/collections/ansible_collections/ansible/oci

.PHONY: install-integration-reqs
install-integration-reqs:
	$(PYTHON_BIN) -m pip install --upgrade pip wheel --disable-pip-version-check
	$(PYTHON_BIN) -m pip install -r requirements.txt --disable-pip-version-check

.PHONY: install-collection
install-collection:
	ansible-galaxy collection install --force --upgrade -p ~/.ansible/collections .

.PHONY: generate-integration-runtime
generate-integration-runtime: install-collection
	chmod +x "$(COLLECTION_ROOT)/tests/integration/generate_integration_runtime.sh"
	PYTHON_BIN="$(PYTHON_BIN)" "$(COLLECTION_ROOT)/tests/integration/generate_integration_runtime.sh"

.PHONY: upgrade-collections
upgrade-collections: install-integration-reqs generate-integration-runtime

.PHONY: integration-ci
integration-ci: upgrade-collections
	cd "$(COLLECTION_ROOT)"; \
	ansible --version; \
	ansible-test --version; \
	ansible-test integration --allow-destructive $(INTEGRATION_TARGETS)

.PHONY: units
units: install-collection
		cd $(COLLECTION_ROOT); \
		ansible-test units --docker --python $(UNIT_PYTHON_VERSION) --coverage $(UNIT_TARGETS); \
		ansible-test coverage combine --requirements --export tests/output/coverage/; \
		ansible-test coverage report --requirements --docker --omit 'tests/*' --show-missing;

.PHONY: units-coverage
units-coverage: units
		cd $(COLLECTION_ROOT); \
		ansible-test coverage xml --requirements; \
		cp tests/output/reports/coverage.xml $(CURDIR)/coverage-units.xml;

.PHONY: sanity
sanity: install-collection
		cd $(COLLECTION_ROOT); \
		ansible-test sanity -v --color --coverage --junit \
				--docker default; \
