# Oracle Cloud Infrastructure Collection for Ansible

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

The collection CI is configured to run sanity, unit, and integration testing.
The current workflow targets `ansible-core` `stable-2.18`, `stable-2.19`,
`stable-2.20`, `stable-2.21`, and `devel`. The integration matrix currently
tests supported combinations across Python `3.8` through `3.14`.

The workflow definition is available at
[`.github/workflows/ansible-test.yml`](https://github.com/ansible-collections/oracle.oci/blob/main/.github/workflows/ansible-test.yml).

## Contributing

Contribution guidelines are documented in
[CONTRIBUTING.md](https://github.com/ansible-collections/oracle.oci/blob/main/CONTRIBUTING.md).

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
