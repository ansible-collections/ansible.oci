# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_vault_key_info
short_description: Retrieve OCI Vault master encryption keys
description:
  - Get a master encryption key by OCID or list the keys of a compartment in a vault.
  - Keys are served from the management endpoint of their vault, so either C(vault_id) or C(management_endpoint) is always required.
  - Listing returns key summaries, which contain a subset of the fields returned when a key is fetched with C(key_id).
  - This is a read-only module and does not modify resources.
version_added: "1.2.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  vault_id:
    description:
      - The OCID of the vault that contains the keys.
      - The module looks up the vault's management endpoint with this OCID.
      - Exactly one of C(vault_id) or C(management_endpoint) is required.
    type: str
  management_endpoint:
    description:
      - The management endpoint of the vault that contains the keys.
      - Exactly one of C(vault_id) or C(management_endpoint) is required.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment to list keys from.
      - Required unless C(key_id) is specified.
    type: str
  key_id:
    description:
      - The OCID of a specific key to retrieve.
      - When specified, returns the full details of a single key instead of a list of summaries.
    type: str
  name:
    description:
      - Only return listed keys with this exact name.
      - Ignored when C(key_id) is specified.
    type: str
  protection_mode:
    description:
      - Only list keys with this protection mode.
      - Ignored when C(key_id) is specified.
    type: str
    choices: [hsm, software, external]
  algorithm:
    description:
      - Only list keys that use this algorithm.
      - Ignored when C(key_id) is specified.
    type: str
    choices: [aes, rsa, ecdsa]
"""

EXAMPLES = r"""
- name: List keys in a compartment
  ansible.oci.oci_vault_key_info:
    vault_id: ocid1.vault.oc1..example
    compartment_id: ocid1.compartment.oc1..example

- name: List software-protected AES keys with a given name
  ansible.oci.oci_vault_key_info:
    vault_id: ocid1.vault.oc1..example
    compartment_id: ocid1.compartment.oc1..example
    name: example-key
    protection_mode: software
    algorithm: aes

- name: Get a key using the vault management endpoint
  ansible.oci.oci_vault_key_info:
    management_endpoint: https://example-management.kms.us-ashburn-1.oraclecloud.com
    key_id: ocid1.key.oc1..example
"""

RETURN = r"""
vault_keys:
  description:
    - List of keys that matched the query.
    - Fields marked as returned only for a key lookup are absent from the summaries returned by a list.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the key.
      type: str
      returned: always
      sample: ocid1.key.oc1..example
    name:
      description: The name of the key.
      type: str
      returned: always
      sample: example-key
    compartment_id:
      description: The OCID of the compartment containing the key.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    vault_id:
      description: The OCID of the vault that contains the key.
      type: str
      returned: always
      sample: ocid1.vault.oc1..example
    lifecycle_state:
      description: The current lifecycle state of the key.
      type: str
      returned: always
      sample: ENABLED
    protection_mode:
      description: Where the key material is stored and protected, such as C(HSM) or C(SOFTWARE).
      type: str
      returned: always
      sample: SOFTWARE
    algorithm:
      description: The algorithm of the key. Returned only when listing keys.
      type: str
      returned: when listing keys
      sample: AES
    key_shape:
      description: The cryptographic properties of the key. Returned only when fetching a key by C(key_id).
      type: dict
      returned: when I(key_id) is specified
      contains:
        algorithm:
          description: The algorithm of the key.
          type: str
          sample: AES
        length:
          description: The length of the key in bytes.
          type: int
          sample: 32
        curve_id:
          description: The curve of an ECDSA key.
          type: str
          sample: null
    current_key_version:
      description: The OCID of the current key version. Returned only when fetching a key by C(key_id).
      type: str
      returned: when I(key_id) is specified
      sample: ocid1.keyversion.oc1..example
    is_auto_rotation_enabled:
      description: Whether the key is rotated automatically.
      type: bool
      returned: always
      sample: false
    auto_key_rotation_details:
      description: The automatic rotation settings and status. Returned only when fetching a key by C(key_id).
      type: dict
      returned: when I(key_id) is specified
      contains:
        rotation_interval_in_days:
          description: The interval between automatic rotations, in days.
          type: int
          sample: 90
        time_of_schedule_start:
          description: When automatic rotation is scheduled to start, in RFC3339 format.
          type: str
          sample: "2026-01-01T00:00:00.000Z"
        time_of_next_rotation:
          description: When the next automatic rotation is scheduled, in RFC3339 format.
          type: str
          sample: "2026-04-01T00:00:00.000Z"
        time_of_last_rotation:
          description: When the last automatic rotation ran, in RFC3339 format.
          type: str
          sample: null
        last_rotation_status:
          description: The status of the last automatic rotation.
          type: str
          sample: null
        last_rotation_message:
          description: A message describing the last automatic rotation.
          type: str
          sample: null
    external_key_reference_details:
      description: Details of the external key backing an C(EXTERNAL) key.
      type: dict
      returned: always
      sample: null
    replica_details:
      description: Cross-region replication details. Returned only when fetching a key by C(key_id).
      type: dict
      returned: when I(key_id) is specified
      sample: null
    is_primary:
      description: Whether the key is the primary key of a replicated key. Returned only when fetching a key by C(key_id).
      type: bool
      returned: when I(key_id) is specified
      sample: true
    restored_from_key_id:
      description: The OCID of the key this key was restored from. Returned only when fetching a key by C(key_id).
      type: str
      returned: when I(key_id) is specified
      sample: null
    freeform_tags:
      description: Free-form tags applied to the key.
      type: dict
      returned: always
      sample: {"environment": "production"}
    defined_tags:
      description: Defined tags applied to the key.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
    time_created:
      description: The date and time the key was created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
    time_of_deletion:
      description: The date and time the key is scheduled for deletion, in RFC3339 format. Returned only when fetching a key by C(key_id).
      type: str
      returned: when I(key_id) is specified
      sample: null
  sample:
    - id: ocid1.key.oc1..example
      name: example-key
      compartment_id: ocid1.compartment.oc1..example
      vault_id: ocid1.vault.oc1..example
      lifecycle_state: ENABLED
      protection_mode: SOFTWARE
      algorithm: AES
      is_auto_rotation_enabled: false
      freeform_tags: {}
      time_created: "2026-01-01T00:00:00.000Z"
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    normalize_choice_parameters,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import (
    OciInfoBase,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_vault import (
    OCI_VAULT_ENDPOINT_ARGS,
    OCI_VAULT_ENDPOINT_MUTUALLY_EXCLUSIVE,
    OCI_VAULT_ENDPOINT_REQUIRED_ONE_OF,
    OciVaultManagementMixin,
)

CHOICE_VALUE_MAPS = {
    ("protection_mode",): {
        "hsm": "HSM",
        "software": "SOFTWARE",
        "external": "EXTERNAL",
    },
    ("algorithm",): {
        "aes": "AES",
        "rsa": "RSA",
        "ecdsa": "ECDSA",
    },
}


class OciVaultKeyInfoModule(OciVaultManagementMixin, OciInfoBase):
    """Concrete info adapter for OCI Vault master encryption keys."""

    results_key = "vault_keys"
    resource_id_param = "key_id"
    resource_get_method = "get_key"
    list_resource_method = "list_keys"
    list_filter_params = [
        "compartment_id",
        "protection_mode",
        "algorithm",
    ]


def main():
    """Run the OCI Vault key info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_VAULT_ENDPOINT_ARGS,
        compartment_id=dict(type="str"),
        key_id=dict(type="str"),
        name=dict(type="str"),
        protection_mode=dict(
            type="str", choices=list(CHOICE_VALUE_MAPS[("protection_mode",)])
        ),
        algorithm=dict(
            type="str", choices=list(CHOICE_VALUE_MAPS[("algorithm",)])
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "key_id"]]
        + OCI_VAULT_ENDPOINT_REQUIRED_ONE_OF,
        mutually_exclusive=OCI_VAULT_ENDPOINT_MUTUALLY_EXCLUSIVE,
    )
    normalize_choice_parameters(module, CHOICE_VALUE_MAPS)

    OciVaultKeyInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
