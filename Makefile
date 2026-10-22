# Minimal integration helpers for live OCI ansible-test runs.
SHELL := /bin/bash

PYTHON_BIN ?= python3
UNIT_PYTHON_VERSION ?= 3.12
UNIT_TARGETS ?=
INTEGRATION_TARGETS ?=
# Where ansible-galaxy installs the collection when we're running from outside
# the ansible_collections/ansible/oci tree.
INSTALLED_COLLECTION_ROOT ?= $(HOME)/.ansible/collections/ansible_collections/ansible/oci

# If we're already inside the collection tree, use it directly; otherwise point
# at the installed copy that upgrade-collections populates. This is decided here
# (make parse time) because $(eval) inside a recipe cannot be gated by a shell if.
ifeq ($(patsubst %/ansible_collections/ansible/oci,MATCH,$(realpath $(CURDIR))),MATCH)
COLLECTION_ROOT ?= .
IN_COLLECTION_TREE := 1
else
COLLECTION_ROOT ?= $(INSTALLED_COLLECTION_ROOT)
IN_COLLECTION_TREE :=
endif

.PHONY: generate-integration-runtime
generate-integration-runtime:
	chmod +x "$(COLLECTION_ROOT)/tests/integration/generate_integration_runtime.sh"
	PYTHON_BIN="$(PYTHON_BIN)" "$(COLLECTION_ROOT)/tests/integration/generate_integration_runtime.sh"

.PHONY: upgrade-collections
upgrade-collections:
ifndef IN_COLLECTION_TREE
	ansible-galaxy collection install --upgrade -p ~/.ansible/collections .
endif

# python reqs need to be installed manually since this is not using --docker
.PHONY: integration-ci
integration-ci: upgrade-collections generate-integration-runtime
	cd "$(COLLECTION_ROOT)"; \
	pip install -r requirements.txt; \
	ansible --version; \
	ansible-test --version; \
	ansible-test integration --allow-destructive $(INTEGRATION_TARGETS)

.PHONY: units
units: upgrade-collections
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
sanity: upgrade-collections
	cd $(COLLECTION_ROOT); \
	ansible-test sanity -v --color --coverage --junit \
		--docker default; \
