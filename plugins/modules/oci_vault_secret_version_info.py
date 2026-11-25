# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_vault_secret_version_info
short_description: Retrieve the versions of an OCI Vault secret
description:
  - Get one version of a secret by version number or list all versions of a secret, optionally with their content.
  - Listing returns version summaries, which contain a subset of the fields returned when a version is fetched with O(version_number).
  - This is a read-only module and does not modify resources.
version_added: "1.3.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  secret_id:
    description:
      - The OCID of the secret that owns the versions.
    type: str
    required: true
  version_number:
    description:
      - The number of a specific version to retrieve.
      - When specified, returns the full details of a single version instead of a list of summaries.
      - O(name) is ignored when this is specified.
    type: int
  name:
    description:
      - Only return listed versions with this exact version name.
      - Ignored when O(version_number) is specified.
    type: str
  include_content:
    description:
      - Whether to add the content of each version to the results as C(content).
      - Content is not fetched for versions that are scheduled for deletion, which get C(content=null).
      - Content is returned in clear text and is not hidden by this module. Set C(no_log=true) on the task so it does
        not appear in logs.
      - Requires permission to C(read secret-bundles) in the compartment of the secret.
    type: bool
    default: false
  content_encoding:
    description:
      - How to return content when O(include_content=true).
      - C(text) decodes the content as UTF-8 text and fails for content that is not valid UTF-8.
      - C(base64) returns the base64 content exactly as OCI stores it, which suits binary content.
    type: str
    choices: [text, base64]
    default: text
"""

EXAMPLES = r"""
- name: List the versions of a secret
  ansible.oci.oci_vault_secret_version_info:
    secret_id: ocid1.vaultsecret.oc1..example
  register: versions

- name: Find a version by name
  ansible.oci.oci_vault_secret_version_info:
    secret_id: ocid1.vaultsecret.oc1..example
    name: example-version

- name: Get one version of a secret
  ansible.oci.oci_vault_secret_version_info:
    secret_id: ocid1.vaultsecret.oc1..example
    version_number: 2

- name: Read the content of every version of a secret
  ansible.oci.oci_vault_secret_version_info:
    secret_id: ocid1.vaultsecret.oc1..example
    include_content: true
  no_log: true
  register: version_content

- name: Read the content of one version as base64
  ansible.oci.oci_vault_secret_version_info:
    secret_id: ocid1.vaultsecret.oc1..example
    version_number: 1
    include_content: true
    content_encoding: base64
  no_log: true
"""

RETURN = r"""
secret_versions:
  description:
    - List of secret versions that matched the query.
    - Fields marked as returned only for a version lookup are absent from the summaries returned by a list, and the other way around.
  returned: always
  type: list
  elements: dict
  contains:
    secret_id:
      description: The OCID of the secret that owns the version.
      type: str
      returned: always
      sample: ocid1.vaultsecret.oc1..example
    version_number:
      description: The number of the version.
      type: int
      returned: always
      sample: 1
    name:
      description: The name of the version.
      type: str
      returned: always
      sample: example-version
    content_type:
      description: The content type of the version, such as C(BASE64).
      type: str
      returned: always
      sample: BASE64
    stages:
      description:
        - The rotation states of the version, such as C(CURRENT), C(PENDING), C(LATEST), C(PREVIOUS), and C(DEPRECATED).
        - Only a version in the C(DEPRECATED) stage can be scheduled for deletion.
      type: list
      elements: str
      returned: always
      sample: [CURRENT, LATEST]
    is_content_auto_generated:
      description: Whether OCI generated the content of the version.
      type: bool
      returned: always
      sample: false
    time_created:
      description: The date and time the version was created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
    time_of_deletion:
      description: The date and time the version is scheduled for deletion, in RFC3339 format.
      type: str
      returned: always
      sample: null
    time_of_current_version_expiry:
      description:
        - The date and time the version expires while it is the current version, in RFC3339 format.
        - Returned only when fetching a version by O(version_number).
      type: str
      returned: when O(version_number) is specified
      sample: null
    time_of_expiry:
      description: The date and time the version expires, in RFC3339 format. Returned only when listing versions.
      type: str
      returned: when listing versions
      sample: null
    system_tags:
      description: System tags applied to the version. Returned only when listing versions.
      type: dict
      returned: when listing versions
      sample: {}
    content:
      description:
        - The content of the version, encoded as set by O(content_encoding).
        - The content is not hidden, so set C(no_log=true) on the task.
      type: str
      returned: when O(include_content=true) and the version is not scheduled for deletion
      sample: example-content
  sample:
    - secret_id: ocid1.vaultsecret.oc1..example
      version_number: 1
      name: example-version
      content_type: BASE64
      stages: [CURRENT, LATEST]
      is_content_auto_generated: false
      time_created: "2026-01-01T00:00:00.000Z"
      time_of_deletion: null
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import (
    OciInfoBase,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_vault import (
    SECRET_CONTENT_ENCODINGS,
    OciSecretContentInfoMixin,
)

oci = import_oci_sdk()[0]


class OciVaultSecretVersionInfoModule(OciSecretContentInfoMixin, OciInfoBase):
    """Concrete info adapter for OCI Vault secret versions."""

    @property
    def client_class(self):
        """Return the vault client class that serves secret management calls.

        Returns:
            The ``oci.vault.VaultsClient`` class.
        """
        return oci.vault.VaultsClient

    results_key = "secret_versions"
    resource_id_param = "version_number"
    resource_id_kwarg = "secret_version_number"
    resource_get_method = "get_secret_version"
    list_resource_method = "list_secret_versions"
    list_filter_params = ["secret_id"]
    name_response_field = "name"

    def get_resource_by_id(self, resource_id, get_fn, **kwargs):
        """Fetch one secret version, scoped to the secret that owns it.

        The inherited implementation passes only the version number to the
        getter, but a version number identifies a version only within its
        secret, so ``secret_id`` is added to every lookup.

        Args:
            resource_id: The version number.
            get_fn: The ``get_secret_version`` operation.
            **kwargs: Arguments passed to ``get_fn``.

        Returns:
            A one-item list with the version, or an empty list when it does not exist.
        """
        return super(OciVaultSecretVersionInfoModule, self).get_resource_by_id(
            resource_id,
            get_fn,
            secret_id=self.module.params["secret_id"],
            **kwargs,
        )

    def content_request(self, resource):
        """Return the bundle lookup for a version not scheduled for deletion.

        Args:
            resource: The secret version.

        Returns:
            The secret OCID and version number, or None when the version is
            scheduled for deletion and its content cannot be read.
        """
        if resource.time_of_deletion is not None:
            return None
        return (
            self.module.params["secret_id"],
            {"version_number": resource.version_number},
        )


def main():
    """Run the OCI Vault secret version info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        secret_id=dict(type="str", required=True),
        version_number=dict(type="int"),
        name=dict(type="str"),
        include_content=dict(type="bool", default=False),
        content_encoding=dict(
            type="str", choices=list(SECRET_CONTENT_ENCODINGS), default="text"
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciVaultSecretVersionInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
