# Oracle OCI Collection for Ansible

The `oracle.oci` collection is being prepared to provide Ansible content for
Oracle Cloud Infrastructure automation. The repository currently contains the
collection metadata, changelog scaffolding, and contributor tooling that will
support OCI modules and plugins as they are added.

## Our mission

The Ansible `oracle.oci` collection aims to provide simple, reusable, and
well-documented automation content for common Oracle Cloud Infrastructure
workflows.

We welcome contributions that improve the collection's usability,
maintainability, and coverage of real OCI automation needs.

## Community standards

This project follows the Ansible community guidelines:

* [Ansible Code of Conduct](https://docs.ansible.com/projects/ansible/devel/community/code_of_conduct.html)
* [Ansible Community Policy for AI-Assisted Contributions](https://docs.ansible.com/projects/ansible/devel/community/ai_policy.html)

## Communication

* Use [GitHub Issues](https://github.com/ansible-collections/oracle.oci/issues) to report bugs, request features, or discuss collection changes.
* Use [Pull Requests](https://github.com/ansible-collections/oracle.oci/pulls) to propose code or documentation updates.

## Contributing

Contributions of all sizes are welcome.

To get started:

* Read the [contribution guide](CONTRIBUTING.md).
* Keep changes focused on one issue or feature at a time.
* Open an issue before large behavior or interface changes so the approach can be discussed first.

Useful upstream references:

* [Ansible community guide](https://docs.ansible.com/projects/ansible/devel/community/index.html)
* [Ansible development guide](https://docs.ansible.com/projects/ansible/devel/dev_guide/index.html)
* [Collection review checklist](https://docs.ansible.com/projects/ansible/devel/community/collection_contributors/collection_reviewing.html)

## Collection maintenance

The current maintainers are listed in the
[MAINTAINERS](https://github.com/ansible-collections/oracle.oci/blob/main/MAINTAINERS) file.

For maintainer-specific expectations, refer to
[MAINTAINING.md](https://github.com/ansible-collections/oracle.oci/blob/main/MAINTAINING.md).

## Governance

This collection is maintained through GitHub issues and pull requests.
Significant changes should be discussed before implementation, and the default
decision-making process is to work toward consensus on the issue or pull request
thread.

## Ansible compatibility

The collection currently declares support for `ansible-core` `>=2.16.0` in
`meta/runtime.yml`.

## External requirements

The collection depends on the Oracle Cloud Infrastructure Python SDK:

* `oci>=2.168.2`

## Included content

The repository is currently in its initial setup stage and does not yet publish
Ansible modules, plugins, or roles.

## Using this collection

Until packaged releases are published, use a local checkout in your Ansible
collections path during development:

```bash
mkdir -p ~/.ansible/collections/ansible_collections/oracle
git clone https://github.com/ansible-collections/oracle.oci.git \
  ~/.ansible/collections/ansible_collections/oracle/oci
```

Future content from this repository will use the `oracle.oci` namespace.

## Release notes

See [CHANGELOG.rst](CHANGELOG.rst) and [CHANGELOG.md](CHANGELOG.md) for release
history and changelog content.

## Licensing

GNU General Public License v3.0 or later.

See [LICENSE](LICENSE) for the full text.
