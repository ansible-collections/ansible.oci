# Oracle Cloud Infrastructure Collection for Ansible

[![Ansible lint](https://github.com/ansible-collections/oracle.oci/actions/workflows/ansible-lint.yml/badge.svg?branch=main)](https://github.com/ansible-collections/oracle.oci/actions/workflows/ansible-lint.yml) [![Sanity](https://github.com/ansible-collections/oracle.oci/actions/workflows/ansible-sanity.yml/badge.svg?branch=main)](https://github.com/ansible-collections/oracle.oci/actions/workflows/ansible-sanity.yml) [![Units](https://github.com/ansible-collections/oracle.oci/actions/workflows/ansible-unit.yml/badge.svg?branch=main)](https://github.com/ansible-collections/oracle.oci/actions/workflows/ansible-unit.yml) [![SonarCloud](https://sonarcloud.io/api/project_badges/measure?project=ansible-collections_oracle.oci&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=ansible-collections_oracle.oci)


## Description

The `oracle.oci` collection provides Ansible automation content for Oracle Cloud
Infrastructure (OCI). It is intended for platform engineers, cloud
administrators, and automation teams that want to manage OCI resources through
repeatable playbooks and workflows.

The collection is designed to support OCI automation across common service
areas, including compute, networking, database, identity and access management,
storage, security, and dynamic inventory use cases. The upstream project home is
[ansible-collections/oracle.oci](https://github.com/ansible-collections/oracle.oci).

## Requirements

The collection currently declares the following baseline requirements:

* `ansible-core >= 2.16.0`
* `python >= 3.8`
* `oci >= 2.168.2`

Use a controller or execution environment with a Python version supported by
both `ansible-core` and the OCI Python SDK. OCI authentication material and
related configuration must also be available to the automation environment that
runs the collection.

## Installation

Before using this collection, install it with the Ansible Galaxy command-line
tool:

```bash
ansible-galaxy collection install oracle.oci
```

You can also include it in a `requirements.yml` file and install it with
`ansible-galaxy collection install -r requirements.yml`, using the format:

```yaml
collections:
  - name: oracle.oci
```

To upgrade the collection to the latest available version, run:

```bash
ansible-galaxy collection install oracle.oci --upgrade
```

You can also install a specific version of the collection. For example, to
install version `1.0.0`:

```bash
ansible-galaxy collection install oracle.oci:==1.0.0
```

See [Using Ansible collections](https://docs.ansible.com/ansible/latest/user_guide/collections_using.html)
for more details.

## Authentication Defaults

OCI modules in this collection support shared authentication defaults so
playbooks do not need to repeat the same auth arguments on every task.

Authentication settings are resolved in this order:

* `auth_type`: module parameter, then `OCI_AUTH_TYPE`, then `api_key`
* `config_file_location`: module parameter, then `OCI_CONFIG_FILE`, then
  `~/.oci/config`
* `config_profile_name`: module parameter, then `OCI_CONFIG_PROFILE`, then
  `DEFAULT`
* API key fields such as tenancy, user, region, fingerprint, key file, and key
  pass phrase: module parameter, then the matching `OCI_*` environment
  variable, then the selected OCI config profile

Supported environment variables include:

* `OCI_AUTH_TYPE`
* `OCI_CONFIG_FILE`
* `OCI_CONFIG_PROFILE`
* `OCI_TENANCY_ID`
* `OCI_USER_ID`
* `OCI_REGION`
* `OCI_USER_FINGERPRINT`
* `OCI_USER_KEY_FILE`
* `OCI_USER_KEY_PASS_PHRASE`

For `session_token` authentication, the selected OCI profile must still include
`security_token_file`.

### module_defaults

The collection defines the action group `group/oracle.oci.oci` so a play or
role can set shared OCI auth options once with `module_defaults`:

```yaml
- hosts: localhost
  gather_facts: false
  module_defaults:
    group/oracle.oci.oci:
      auth_type: api_key
      config_file_location: ~/.oci/config
      config_profile_name: PROD
  tasks:
    - oracle.oci.oci_network_vcn:
        state: present
        compartment_id: ocid1.compartment.oc1..example
        name: example-vcn
        cidr_blocks:
          - 10.0.0.0/16
```

## Use Cases

Common use cases for this collection include:

* provisioning and updating OCI compute and networking resources as part of
  environment builds
* automating IAM configuration such as users, groups, policies, and compartment
  access controls
* managing OCI storage and database-related workflows in repeatable playbooks
* using dynamic inventory patterns to target OCI-hosted infrastructure in
  Ansible Automation Platform

## Testing

The collection CI is split across dedicated `ansible-lint`, `Sanity`, and
`Units` workflows. Integration testing is intentionally deferred for now and
will return in its own workflow later. SonarCloud analysis runs separately
after the `Units` workflow completes.

The workflow definitions are available at:

* [`.github/workflows/ansible-lint.yml`](https://github.com/ansible-collections/oracle.oci/blob/main/.github/workflows/ansible-lint.yml)
* [`.github/workflows/ansible-sanity.yml`](https://github.com/ansible-collections/oracle.oci/blob/main/.github/workflows/ansible-sanity.yml)
* [`.github/workflows/ansible-unit.yml`](https://github.com/ansible-collections/oracle.oci/blob/main/.github/workflows/ansible-unit.yml)
* [`.github/workflows/sonarcloud.yml`](https://github.com/ansible-collections/oracle.oci/blob/main/.github/workflows/sonarcloud.yml)

## Contributing

Contribution guidelines are documented in
[CONTRIBUTING.md](https://github.com/ansible-collections/oracle.oci/blob/main/CONTRIBUTING.md).

Contributors adding new OCI modules should start with the
[Module Authoring Guide](docs/module_development.md).

Project code of conduct information is available in
[CODE_OF_CONDUCT.md](https://github.com/ansible-collections/oracle.oci/blob/main/CODE_OF_CONDUCT.md).

Use [repository issues](https://github.com/ansible-collections/oracle.oci/issues)
for bugs, feature requests, and design discussion.

## Support

If this collection is consumed as Red Hat Ansible Certified Content, support is
available through Red Hat Ansible Automation Platform using the **Create issue**
button. If the collection is obtained from GitHub or Ansible Galaxy, community
help may also be available on the [Ansible Forum](https://forum.ansible.com/).

## Release Notes and Roadmap

Release notes are available at:

* [CHANGELOG.rst](https://github.com/ansible-collections/oracle.oci/blob/main/CHANGELOG.rst)
* [CHANGELOG.md](https://github.com/ansible-collections/oracle.oci/blob/main/CHANGELOG.md)

Current planning and future work can be tracked through repository issues and
pull requests:

* [Issues](https://github.com/ansible-collections/oracle.oci/issues)
* [Pull requests](https://github.com/ansible-collections/oracle.oci/pulls)

## Related Information

Additional OCI and collection-related documentation:

* [Oracle Cloud Infrastructure Ansible documentation](https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/ansible.htm)
* [OCI Ansible collection module documentation](https://docs.oracle.com/en-us/iaas/tools/oci-ansible-collection/latest/collections/oracle/oci/index.html)
* [Ansible collections user guide](https://docs.ansible.com/ansible/latest/user_guide/collections_using.html)

## License Information

This collection is published under GNU General Public License v3.0 or later.
License details are available in
[LICENSE](https://github.com/ansible-collections/oracle.oci/blob/main/LICENSE).
