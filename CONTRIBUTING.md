# Contributing to this project

Thank you for your interest in contributing to `oracle.oci`.

## Before you start

* Read the [Ansible community guide](https://docs.ansible.com/projects/ansible/devel/community/index.html).
* Review the [Ansible collection development guide](https://docs.ansible.com/projects/ansible/devel/dev_guide/developing_collections.html#contributing-to-collections).
* Use [GitHub Issues](https://github.com/ansible-collections/oracle.oci/issues) for bugs, feature requests, and design discussions.

If you are planning a larger change, open an issue first so the approach can be
discussed before implementation.

## Using AI tools for assistance

This project follows the [Ansible Community Policy for AI-Assisted Contributions](https://docs.ansible.com/projects/ansible/devel/community/ai_policy.html).

In practice, that means:

* You may use AI tools to assist with contributions.
* You remain responsible for the correctness, security, and maintainability of what you submit.
* Significant AI-generated contributions should be disclosed in the pull request.

## Contribution expectations

Please keep contributions focused and reviewable:

* Submit one logical change per pull request.
* Use conventional commit prefixes such as `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, or `ci:`.
* Update documentation when behavior, interfaces, or contributor workflow changes.
* Add a changelog fragment under `changelogs/fragments/` for user-facing behavior changes.

## Collection conventions

When changing collection metadata or runtime dependencies:

* Keep `galaxy.yml` aligned with the repository identity and supported collection metadata.
* Keep `requirements.txt` and `meta/ee-requirements.txt` in sync for controller-side Python dependencies.
* The current OCI SDK floor for this collection is `oci>=2.183.0`.

## Local validation

GitHub Actions runs the main repository checks, including `ansible-lint`,
`Sanity`, `Units`, docsite linting, and SonarCloud analysis. Local validation
still stays lightweight; when the required Python tooling is available in your
environment, use `nox` to run the configured local checks:

```bash
python noxfile.py -l
```

Also validate the files you touch directly, especially YAML and Markdown
content.

To generate the same unit-test coverage XML that the SonarCloud job publishes:

```bash
python3 -m pip install ansible-core pytest pytest-cov pytest-ansible-units
pytest tests/unit -v --cov-report xml --cov=./
```

### Running live OCI integration targets locally

Required runtime input:

* `OCI_TEST_COMPARTMENT_ID`

Optional overrides when you do not want the defaults:

* `OCI_CONFIG_FILE`
* `OCI_CONFIG_PROFILE`

The integration target defaults already map `OCI_TEST_COMPARTMENT_ID` to the
module `compartment_id` parameter, so if your OCI auth environment is already
prepared, that is the only required run-time export.

```bash

ansible-test integration --allow-destructive oci_network_vcn -vvv
ansible-test integration --allow-destructive oci_network_subnet -vvv
```

To run both current live OCI targets in one command:

```bash
ansible-test integration --allow-destructive oci_network_vcn oci_network_subnet -vvv
```

## Review references

The following references are useful when preparing or reviewing changes:

* [Collection review checklist](https://docs.ansible.com/projects/ansible/devel/community/collection_contributors/collection_reviewing.html)
* [Ansible development guide](https://docs.ansible.com/projects/ansible/devel/dev_guide/index.html)
