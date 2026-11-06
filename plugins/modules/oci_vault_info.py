# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_vault_info
short_description: Retrieve OCI Vaults
description:
  - Get a vault by OCID or list the vaults in a compartment.
  - Listing returns vault summaries, which contain a subset of the fields returned when a vault is fetched with C(vault_id).
  - This is a read-only module and does not modify resources.
version_added: "1.2.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  compartment_id:
    description:
      - The OCID of the compartment to list vaults from.
      - Required unless C(vault_id) is specified.
    type: str
  vault_id:
    description:
      - The OCID of a specific vault to retrieve.
      - When specified, returns the full details of a single vault instead of a list of summaries.
    type: str
  name:
    description:
      - Only return listed vaults with this exact name.
      - Ignored when C(vault_id) is specified.
    type: str
"""

EXAMPLES = r"""
- name: List vaults in a compartment
  ansible.oci.oci_vault_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List vaults with a given name
  ansible.oci.oci_vault_info:
    compartment_id: ocid1.compartment.oc1..example
    name: example-vault

- name: Get a vault by OCID
  ansible.oci.oci_vault_info:
    vault_id: ocid1.vault.oc1..example
"""

RETURN = r"""
vaults:
  description:
    - List of vaults that matched the query.
    - Fields marked as returned only for a vault lookup are absent from the summaries returned by a list.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the vault.
      type: str
      returned: always
      sample: ocid1.vault.oc1..example
    name:
      description: The name of the vault.
      type: str
      returned: always
      sample: example-vault
    compartment_id:
      description: The OCID of the compartment containing the vault.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    lifecycle_state:
      description: The current lifecycle state of the vault.
      type: str
      returned: always
      sample: ACTIVE
    vault_type:
      description: The type of the vault, such as C(DEFAULT) or C(VIRTUAL_PRIVATE).
      type: str
      returned: always
      sample: DEFAULT
    management_endpoint:
      description: The endpoint used for key management operations in the vault.
      type: str
      returned: always
      sample: https://example-management.kms.us-ashburn-1.oraclecloud.com
    crypto_endpoint:
      description: The endpoint used for cryptographic operations in the vault.
      type: str
      returned: always
      sample: https://example-crypto.kms.us-ashburn-1.oraclecloud.com
    external_key_manager_metadata_summary:
      description: Details of the external key manager backing an C(EXTERNAL) vault.
      type: dict
      returned: always
      sample: null
    time_of_deletion:
      description: The date and time the vault is scheduled for deletion, in RFC3339 format. Returned only when fetching a vault by C(vault_id).
      type: str
      returned: when I(vault_id) is specified
      sample: null
    wrappingkey_id:
      description: The OCID of the vault's wrapping key. Returned only when fetching a vault by C(vault_id).
      type: str
      returned: when I(vault_id) is specified
      sample: ocid1.key.oc1..example
    replica_details:
      description: Cross-region replication details. Returned only when fetching a vault by C(vault_id).
      type: dict
      returned: when I(vault_id) is specified
      sample: null
    is_primary:
      description: Whether the vault is the primary vault of a replicated vault. Returned only when fetching a vault by C(vault_id).
      type: bool
      returned: when I(vault_id) is specified
      sample: true
    is_vault_replicable:
      description: Whether the vault can be replicated to another region. Returned only when fetching a vault by C(vault_id).
      type: bool
      returned: when I(vault_id) is specified
      sample: false
    restored_from_vault_id:
      description: The OCID of the vault this vault was restored from. Returned only when fetching a vault by C(vault_id).
      type: str
      returned: when I(vault_id) is specified
      sample: null
    freeform_tags:
      description: Free-form tags applied to the vault.
      type: dict
      returned: always
      sample: {"environment": "production"}
    defined_tags:
      description: Defined tags applied to the vault.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
    time_created:
      description: The date and time the vault was created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
  sample:
    - id: ocid1.vault.oc1..example
      name: example-vault
      compartment_id: ocid1.compartment.oc1..example
      lifecycle_state: ACTIVE
      vault_type: DEFAULT
      management_endpoint: https://example-management.kms.us-ashburn-1.oraclecloud.com
      crypto_endpoint: https://example-crypto.kms.us-ashburn-1.oraclecloud.com
      freeform_tags: {}
      time_created: "2026-01-01T00:00:00.000Z"
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import (
    OciInfoBase,
)

oci = import_oci_sdk()[0]


class OciVaultInfoModule(OciInfoBase):
    """Concrete info adapter for OCI Vaults."""

    @property
    def client_class(self):
        """Return the regional vault client class.

        Returns:
            The ``oci.key_management.KmsVaultClient`` class.
        """
        return oci.key_management.KmsVaultClient

    results_key = "vaults"
    resource_id_param = "vault_id"
    resource_get_method = "get_vault"
    list_resource_method = "list_vaults"
    list_filter_params = ["compartment_id"]


def main():
    """Run the OCI Vault info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        vault_id=dict(type="str"),
        name=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "vault_id"]],
    )

    OciVaultInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
