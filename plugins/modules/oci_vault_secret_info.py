# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_vault_secret_info
short_description: Retrieve OCI Vault secrets
description:
  - Get a secret by OCID or list the secrets of a compartment, optionally with their content.
  - Listing returns secret summaries, which contain a subset of the fields returned when a secret is fetched with O(secret_id).
  - This is a read-only module and does not modify resources.
version_added: "1.3.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  secret_id:
    description:
      - The OCID of a specific secret to retrieve.
      - When specified, returns the full details of a single secret instead of a list of summaries.
      - The other filters are ignored.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment to list secrets from.
      - Required unless O(secret_id) is specified.
    type: str
  vault_id:
    description:
      - Only list secrets that belong to this vault.
      - Ignored when O(secret_id) is specified.
    type: str
  name:
    description:
      - Only return listed secrets with this exact name.
      - Ignored when O(secret_id) is specified.
    type: str
  lifecycle_state:
    description:
      - Only list secrets in this lifecycle state.
      - Ignored when O(secret_id) is specified.
    type: str
    choices:
      - creating
      - active
      - updating
      - deleting
      - deleted
      - scheduling_deletion
      - pending_deletion
      - cancelling_deletion
      - failed
  include_content:
    description:
      - Whether to add the content of each secret to the results as C(content).
      - Content is fetched only for secrets in the C(ACTIVE) lifecycle state. Other secrets, and secrets that have no
        version in the stage of O(content_stage), get C(content=null).
      - Content is returned in clear text and is not hidden by this module. Set C(no_log=true) on the task so it does
        not appear in logs.
      - Requires permission to C(read secret-bundles) in the compartment of the secrets.
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
  content_stage:
    description:
      - The rotation state of the secret version to read content from when O(include_content=true).
    type: str
    choices: [current, pending, latest, previous, deprecated]
    default: current
"""

EXAMPLES = r"""
- name: List the secrets of a vault
  ansible.oci.oci_vault_secret_info:
    compartment_id: ocid1.compartment.oc1..example
    vault_id: ocid1.vault.oc1..example

- name: Find an active secret by name
  ansible.oci.oci_vault_secret_info:
    compartment_id: ocid1.compartment.oc1..example
    vault_id: ocid1.vault.oc1..example
    name: example-secret
    lifecycle_state: active
  register: found_secret

- name: Get a secret by OCID
  ansible.oci.oci_vault_secret_info:
    secret_id: ocid1.vaultsecret.oc1..example

- name: Read the current content of a secret
  ansible.oci.oci_vault_secret_info:
    secret_id: ocid1.vaultsecret.oc1..example
    include_content: true
  no_log: true
  register: secret_content

- name: Read the pending content of a binary secret as base64
  ansible.oci.oci_vault_secret_info:
    secret_id: ocid1.vaultsecret.oc1..example
    include_content: true
    content_encoding: base64
    content_stage: pending
  no_log: true
"""

RETURN = r"""
vault_secrets:
  description:
    - List of secrets that matched the query.
    - Fields marked as returned only for a secret lookup are absent from the summaries returned by a list.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the secret.
      type: str
      returned: always
      sample: ocid1.vaultsecret.oc1..example
    name:
      description: The name of the secret.
      type: str
      returned: always
      sample: example-secret
    compartment_id:
      description: The OCID of the compartment containing the secret.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    vault_id:
      description: The OCID of the vault that contains the secret.
      type: str
      returned: always
      sample: ocid1.vault.oc1..example
    key_id:
      description: The OCID of the master encryption key that encrypts the secret.
      type: str
      returned: always
      sample: ocid1.key.oc1..example
    description:
      description: The description of the secret.
      type: str
      returned: always
      sample: Example secret
    lifecycle_state:
      description: The current lifecycle state of the secret.
      type: str
      returned: always
      sample: ACTIVE
    lifecycle_details:
      description: Additional information about the lifecycle state.
      type: str
      returned: always
      sample: null
    current_version_number:
      description: The version number of the secret version that is currently in use. Returned only when fetching a secret by O(secret_id).
      type: int
      returned: when O(secret_id) is specified
      sample: 1
    metadata:
      description: User-defined metadata of the secret. Returned only when fetching a secret by O(secret_id).
      type: dict
      returned: when O(secret_id) is specified
      sample: {"purpose": "example"}
    secret_rules:
      description: The expiry and reuse rules of the secret. Returned only when fetching a secret by O(secret_id).
      type: list
      elements: dict
      returned: when O(secret_id) is specified
      sample:
        - rule_type: SECRET_EXPIRY_RULE
          secret_version_expiry_interval: P30D
          is_secret_content_retrieval_blocked_on_expiry: false
    rotation_config:
      description: The rotation settings of the secret.
      type: dict
      returned: always
      sample: null
    rotation_status:
      description: The status of the secret rotation, such as C(NOT_ENABLED) or C(IN_PROGRESS).
      type: str
      returned: always
      sample: NOT_ENABLED
    last_rotation_time:
      description: When the secret was last rotated, in RFC3339 format.
      type: str
      returned: always
      sample: null
    next_rotation_time:
      description: When the next scheduled rotation runs, in RFC3339 format.
      type: str
      returned: always
      sample: null
    replication_config:
      description: The cross-region replication settings of the secret.
      type: dict
      returned: always
      sample: null
    is_replica:
      description: Whether the secret is a replica of a secret in another region.
      type: bool
      returned: always
      sample: false
    source_region_information:
      description: Details of the source region when the secret is a replica.
      type: dict
      returned: always
      sample: null
    secret_generation_context:
      description: The settings OCI uses to generate the content of the secret.
      type: dict
      returned: always
      sample: null
    is_auto_generation_enabled:
      description: Whether OCI generates the content of the secret.
      type: bool
      returned: always
      sample: false
    freeform_tags:
      description: Free-form tags applied to the secret.
      type: dict
      returned: always
      sample: {"environment": "production"}
    defined_tags:
      description: Defined tags applied to the secret.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
    system_tags:
      description: System tags applied to the secret. Returned only when listing secrets.
      type: dict
      returned: when listing secrets
      sample: {}
    time_created:
      description: The date and time the secret was created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
    time_of_current_version_expiry:
      description: The date and time the current secret version expires, in RFC3339 format.
      type: str
      returned: always
      sample: null
    time_of_deletion:
      description: The date and time the secret is scheduled for deletion, in RFC3339 format.
      type: str
      returned: always
      sample: null
    content:
      description:
        - The content of the secret, encoded as set by O(content_encoding).
        - The content is not hidden, so set C(no_log=true) on the task.
      type: str
      returned: when O(include_content=true) and the secret is C(ACTIVE) with a version in the requested stage
      sample: example-content
  sample:
    - id: ocid1.vaultsecret.oc1..example
      name: example-secret
      compartment_id: ocid1.compartment.oc1..example
      vault_id: ocid1.vault.oc1..example
      key_id: ocid1.key.oc1..example
      lifecycle_state: ACTIVE
      is_auto_generation_enabled: false
      freeform_tags: {}
      time_created: "2026-01-01T00:00:00.000Z"
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
    normalize_choice_parameters,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import (
    OciInfoBase,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_vault import (
    SECRET_CONTENT_ENCODINGS,
    OciSecretContentInfoMixin,
)

oci = import_oci_sdk()[0]

CHOICE_VALUE_MAPS = {
    ("lifecycle_state",): {
        "creating": "CREATING",
        "active": "ACTIVE",
        "updating": "UPDATING",
        "deleting": "DELETING",
        "deleted": "DELETED",
        "scheduling_deletion": "SCHEDULING_DELETION",
        "pending_deletion": "PENDING_DELETION",
        "cancelling_deletion": "CANCELLING_DELETION",
        "failed": "FAILED",
    },
    ("content_stage",): {
        "current": "CURRENT",
        "pending": "PENDING",
        "latest": "LATEST",
        "previous": "PREVIOUS",
        "deprecated": "DEPRECATED",
    },
}

SECRET_STATE_ACTIVE = "ACTIVE"


class OciVaultSecretInfoModule(OciSecretContentInfoMixin, OciInfoBase):
    """Concrete info adapter for OCI Vault secrets."""

    @property
    def client_class(self):
        """Return the vault client class that serves secret management calls.

        Returns:
            The ``oci.vault.VaultsClient`` class.
        """
        return oci.vault.VaultsClient

    results_key = "vault_secrets"
    resource_id_param = "secret_id"
    resource_get_method = "get_secret"
    list_resource_method = "list_secrets"
    list_filter_params = ["compartment_id", "vault_id", "lifecycle_state"]
    name_response_field = "secret_name"
    field_param_aliases = {"secret_name": "name"}

    def content_request(self, resource):
        """Return the bundle lookup for an ``ACTIVE`` secret.

        Args:
            resource: The secret.

        Returns:
            The secret OCID and requested stage, or None when the secret is
            not ``ACTIVE`` and its content cannot be read.
        """
        if resource.lifecycle_state != SECRET_STATE_ACTIVE:
            return None
        return resource.id, {"stage": self.module.params["content_stage"]}


def main():
    """Run the OCI Vault secret info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        secret_id=dict(type="str"),
        compartment_id=dict(type="str"),
        vault_id=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(
            type="str", choices=list(CHOICE_VALUE_MAPS[("lifecycle_state",)])
        ),
        include_content=dict(type="bool", default=False),
        content_encoding=dict(
            type="str", choices=list(SECRET_CONTENT_ENCODINGS), default="text"
        ),
        content_stage=dict(
            type="str",
            choices=list(CHOICE_VALUE_MAPS[("content_stage",)]),
            default="current",
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "secret_id"]],
    )
    normalize_choice_parameters(module, CHOICE_VALUE_MAPS)

    OciVaultSecretInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
