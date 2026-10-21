# Oracle Cloud Infrastructure Collection for Ansible

[![Ansible lint](https://github.com/ansible-collections/ansible.oci/actions/workflows/ansible-lint.yml/badge.svg?branch=main)](https://github.com/ansible-collections/ansible.oci/actions/workflows/ansible-lint.yml) [![Sanity](https://github.com/ansible-collections/ansible.oci/actions/workflows/ansible-sanity.yml/badge.svg?branch=main)](https://github.com/ansible-collections/ansible.oci/actions/workflows/ansible-sanity.yml) [![Units](https://github.com/ansible-collections/ansible.oci/actions/workflows/ansible-unit.yml/badge.svg?branch=main)](https://github.com/ansible-collections/ansible.oci/actions/workflows/ansible-unit.yml) [![SonarCloud](https://sonarcloud.io/api/project_badges/measure?project=ansible-collections_ansible.oci&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=ansible-collections_ansible.oci)

This collection automates Oracle Cloud Infrastructure (OCI).

## Description

The `ansible.oci` collection provides Ansible modules for Oracle Cloud Infrastructure. It is intended for platform engineers, cloud administrators, and automation teams that want to manage OCI resources through repeatable playbooks.

## Requirements

The collection currently declares the following baseline requirements:

* `ansible-core >= 2.16.0`
* `python >= 3.8` (module execution)
* `oci >= 2.183.0`

This collection does not depend on other Ansible collections.

Use a controller or execution environment with a Python version supported by both `ansible-core` and the OCI Python SDK. Red Hat Ansible Automation Platform customers run `ansible-core` in execution environments; do not install `ansible-core` with `pip` in supported AAP environments. OCI authentication material and related configuration must also be available to the automation environment that runs the collection.

## Installation


### Installing a collection

Install this collection with the Ansible Galaxy command-line tool:

```bash
ansible-galaxy collection install ansible.oci
```

### Installing from a requirements file

You can include this collection in a `requirements.yml` file and install it with `ansible-galaxy collection install -r requirements.yml`:

```yaml
collections:
  - name: ansible.oci
```

### Installing a specific version

Use the following syntax to install version 1.0.0:

```bash
ansible-galaxy collection install ansible.oci:==1.0.0
```

See [using Ansible collections](https://docs.ansible.com/ansible/devel/user_guide/collections_using.html) for more details.

### Upgrading a collection

To upgrade the collection to the latest available version, run the following command:

```bash
ansible-galaxy collection install ansible.oci --upgrade
```

### Authentication defaults

OCI modules in this collection support shared authentication defaults so playbooks do not need to repeat the same auth arguments on every task.

Authentication settings are resolved in this order:

* `auth_type`: module parameter, then `OCI_AUTH_TYPE`, then `api_key`
* `config_file_location`: module parameter, then `OCI_CONFIG_FILE`, then `~/.oci/config`
* `config_profile_name`: module parameter, then `OCI_CONFIG_PROFILE`, then `DEFAULT`
* API key fields (`tenancy`, `api_user`, `region`, `api_user_fingerprint`, `api_user_key_file`, `api_user_key_pass_phrase`): module parameter, then the matching `OCI_*` environment variable, then the selected OCI config profile

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

For `session_token` authentication, the selected OCI profile must still include `security_token_file`.

#### module_defaults

The collection defines the action group `group/ansible.oci.oci` so a play or role can set shared OCI auth options once with `module_defaults`:

```yaml
- hosts: localhost
  gather_facts: false
  module_defaults:
    group/ansible.oci.oci:
      auth_type: api_key
      config_file_location: ~/.oci/config
      config_profile_name: PROD
  tasks:
    - ansible.oci.oci_network_vcn:
        state: present
        compartment_id: ocid1.compartment.oc1..example
        name: example-vcn
        cidr_blocks:
          - 10.0.0.0/16
```

## Use cases

### Provision a VCN and subnet

Create a Virtual Cloud Network and a subnet that later tasks can attach compute or gateways to:

```yaml
- name: Create a VCN
  ansible.oci.oci_network_vcn:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: example-vcn
    cidr_blocks:
      - 10.0.0.0/16
  register: example_vcn

- name: Create a subnet
  ansible.oci.oci_network_subnet:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: "{{ example_vcn.resource.id }}"
    name: example-subnet
    cidr_block: 10.0.1.0/24
  register: example_subnet
```

### Add internet and NAT gateways

Expose a VCN to the public internet and provide outbound NAT for private subnets:

```yaml
- name: Create an internet gateway
  ansible.oci.oci_network_internet_gateway:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: "{{ example_vcn.resource.id }}"
    name: example-internet-gateway

- name: Create a NAT gateway
  ansible.oci.oci_network_nat_gateway:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: "{{ example_vcn.resource.id }}"
    name: example-nat-gateway
```

### Launch a compute instance on that network

Place an instance on the subnet created above:

```yaml
- name: Launch an instance
  ansible.oci.oci_instance:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    name: example-instance
    shape: VM.Standard.E4.Flex
    shape_config:
      ocpus: 1
      memory_in_gbs: 16
    image_id: ocid1.image.oc1..example
    subnet_id: "{{ example_subnet.resource.id }}"
```

### Manage a block volume

Create additional block storage that can be attached to compute:

```yaml
- name: Create a block volume
  ansible.oci.oci_blockstorage_volume:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    name: example-volume
    size_in_gbs: 50
```

## Testing

This collection supports:

* ansible-core `>= 2.16.0` (CI currently covers 2.16 and 2.18)
* Python `>= 3.8` for modules (CI currently covers 3.11, 3.12, and 3.13)
* OCI Python SDK `>= 2.183.0`
* Live integration against Oracle Cloud Infrastructure

There are no additional known platform limitations beyond those OCI service constraints documented on each module.


CI workflow definitions (secondary):

* [`.github/workflows/ansible-lint.yml`](https://github.com/ansible-collections/ansible.oci/blob/main/.github/workflows/ansible-lint.yml)
* [`.github/workflows/ansible-sanity.yml`](https://github.com/ansible-collections/ansible.oci/blob/main/.github/workflows/ansible-sanity.yml)
* [`.github/workflows/ansible-unit.yml`](https://github.com/ansible-collections/ansible.oci/blob/main/.github/workflows/ansible-unit.yml)
* [`.github/workflows/ansible-integration-pr.yml`](https://github.com/ansible-collections/ansible.oci/blob/main/.github/workflows/ansible-integration-pr.yml)
* [`.github/workflows/ansible-integration-weekly.yml`](https://github.com/ansible-collections/ansible.oci/blob/main/.github/workflows/ansible-integration-weekly.yml)
* [`.github/workflows/sonarcloud.yml`](https://github.com/ansible-collections/ansible.oci/blob/main/.github/workflows/sonarcloud.yml)

## Contributing

Contribution guidelines are documented in [CONTRIBUTING.md](https://github.com/ansible-collections/ansible.oci/blob/main/CONTRIBUTING.md).

Contributors adding new OCI modules should start with the [Module Authoring Guide](https://github.com/ansible-collections/ansible.oci/blob/main/docs/module_development.md).

Project code of conduct information is available in [CODE_OF_CONDUCT.md](https://github.com/ansible-collections/ansible.oci/blob/main/CODE_OF_CONDUCT.md).

Use [repository issues](https://github.com/ansible-collections/ansible.oci/issues) for bugs, feature requests, and design discussion. Community discussion is also available on the [Ansible Forum](https://forum.ansible.com/).

## Support

This collection is maintained by the Red Hat Ansible Eco Engineering team.

As Red Hat Ansible Certified Content, this collection is entitled to support through Ansible Automation Platform (AAP) using the **Create issue** button on the top right corner of Automation Hub. If a support case cannot be opened with Red Hat and the collection has been obtained either from Galaxy or GitHub, community help may also be available on the [Ansible Forum](https://forum.ansible.com/) and through [GitHub issues](https://github.com/ansible-collections/ansible.oci/issues).

## Release notes and roadmap

Release notes are available at:

* [CHANGELOG.rst](https://github.com/ansible-collections/ansible.oci/blob/main/CHANGELOG.rst)
* [CHANGELOG.md](https://github.com/ansible-collections/ansible.oci/blob/main/CHANGELOG.md)

Current planning and future work can be tracked through repository issues and pull requests:

* [Issues](https://github.com/ansible-collections/ansible.oci/issues)
* [Pull requests](https://github.com/ansible-collections/ansible.oci/pulls)


## Related information

* [Ansible collections user guide](https://docs.ansible.com/ansible/devel/user_guide/collections_using.html)
* [Oracle Cloud Infrastructure documentation](https://docs.oracle.com/en-us/iaas/Content/home.htm)
* [OCI Python SDK documentation](https://docs.oracle.com/en-us/iaas/tools/python/latest/)

## License information

This collection is published under GNU General Public License v3.0 or later, an [OSI-approved license](https://opensource.org/licenses/). License details are available in [LICENSE](https://github.com/ansible-collections/ansible.oci/blob/main/LICENSE).
