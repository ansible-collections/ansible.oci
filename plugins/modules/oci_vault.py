# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_vault
short_description: Manage an Oracle Cloud Infrastructure Vault
description:
  - Create, update, schedule for deletion, and restore OCI Vaults.
version_added: "1.2.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_name_lookup_options
  - ansible.oci.oci_wait_options
  - ansible.oci.oci_tags_options
options:
  state:
    description:
      - The desired state of the vault.
      - C(present) creates the vault when it does not exist and applies updates.
        A vault that is pending deletion is restored by cancelling the
        scheduled deletion.
      - C(absent) schedules the vault for deletion. OCI never deletes a vault
        immediately, so a vault that is already pending deletion is reported as
        unchanged.
    type: str
    choices: [present, absent]
    default: present
  vault_id:
    description:
      - The OCID of the vault.
      - When provided, the module manages this exact vault.
      - When omitted, the module uses C(compartment_id + name) to find an
        existing vault. If more than one vault matches, the task fails and the
        caller must supply C(vault_id).
      - Create requests must omit C(vault_id).
    type: str
  name:
    description:
      - Human-readable name for the vault.
      - Required when creating a vault.
      - Can be changed after create.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the vault.
      - Required when creating a vault.
      - The module does not move an existing vault to another compartment.
      - Also scopes name-based vault lookups when C(vault_id) is omitted.
    type: str
  deletion_days:
    description:
      - The number of days from now until OCI deletes the vault when C(state=absent).
      - OCI accepts values from 7 to 30. When omitted, OCI uses 30 days.
      - The vault and the keys it holds remain in C(PENDING_DELETION) until
        then and can be restored by running the task again with C(state=present).
    type: int
notes:
  - The module creates C(DEFAULT) vaults only. Existing vaults of any type can
    be renamed, retagged, scheduled for deletion, and restored.
"""

EXAMPLES = r"""
- name: Create a vault
  ansible.oci.oci_vault:
    compartment_id: ocid1.compartment.oc1..example
    name: example-vault
    freeform_tags:
      environment: dev
  register: created_vault

- name: Rename a vault
  ansible.oci.oci_vault:
    vault_id: "{{ created_vault.resource.id }}"
    name: renamed-vault

- name: Schedule a vault for deletion in 7 days
  ansible.oci.oci_vault:
    vault_id: "{{ created_vault.resource.id }}"
    state: absent
    deletion_days: 7

- name: Restore a vault that is pending deletion
  ansible.oci.oci_vault:
    vault_id: "{{ created_vault.resource.id }}"
    state: present
"""

RETURN = r"""
resource:
  description: The vault resource.
  returned: when state != absent
  type: dict
  contains:
    id:
      description: The OCID of the vault.
      type: str
      returned: always
    name:
      description: The name of the vault.
      type: str
      returned: always
    compartment_id:
      description: The OCID of the compartment containing the vault.
      type: str
      returned: always
    lifecycle_state:
      description: The lifecycle state of the vault, for example C(ACTIVE).
      type: str
      returned: always
    vault_type:
      description: The type of the vault, for example C(DEFAULT).
      type: str
      returned: always
    management_endpoint:
      description: The endpoint used for key management operations in the vault.
      type: str
      returned: always
    crypto_endpoint:
      description: The endpoint used for cryptographic operations in the vault.
      type: str
      returned: always
    time_created:
      description: The time the vault was created.
      type: str
      returned: always
    time_of_deletion:
      description: The time OCI deletes the vault, set while the vault is pending deletion.
      type: str
      returned: when the vault is pending deletion
    freeform_tags:
      description: Free-form tags of the vault.
      type: dict
      returned: always
    defined_tags:
      description: Defined tags of the vault.
      type: dict
      returned: always
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_COMMON_ARGS,
    filter_none_values,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_vault import (
    OciScheduledDeletionMixin,
)

oci = import_oci_sdk()[0]


CREATE_REQUIRED_FIELDS = [
    "compartment_id",
    "name",
]
VAULT_TYPE_DEFAULT = "DEFAULT"
VAULT_STATE_ACTIVE = "ACTIVE"
READY_STATES = (VAULT_STATE_ACTIVE,)


def build_create_vault_details(params):
    """Build the OCI create-vault model from module parameters.

    Args:
        params: The validated module parameters.

    Returns:
        An ``oci.key_management.models.CreateVaultDetails`` instance for a
        ``DEFAULT`` vault.
    """
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "display_name": params.get("name"),
            "vault_type": VAULT_TYPE_DEFAULT,
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.key_management.models.CreateVaultDetails(**details)


class OciVaultModule(OciScheduledDeletionMixin, OciResourceBase):
    """Concrete resource adapter for OCI Vaults."""

    @property
    def client_class(self):
        """Return the regional vault client class.

        Returns:
            The ``oci.key_management.KmsVaultClient`` class.
        """
        return oci.key_management.KmsVaultClient

    resource_id_param = "vault_id"
    list_resource_method = "list_vaults"
    create_resource_name = "vault"
    create_required_fields = CREATE_REQUIRED_FIELDS
    update_method_name = "update_vault"
    update_details_name = "update_vault_details"
    update_wait_states = READY_STATES
    update_field_specs = (
        UpdateFieldSpec(
            param_name="name",
            is_mutable=True,
            resource_field="display_name",
            update_field="display_name",
        ),
        UpdateFieldSpec(
            param_name="compartment_id",
            is_mutable=False,
            immutable_reason="this module does not move vaults between compartments",
        ),
    )

    def get_resource_response(self, resource_id):
        """Return the raw ``get_vault`` response for ``resource_id``.

        Args:
            resource_id: The OCID of the vault.

        Returns:
            The OCI SDK response wrapper.
        """
        return self.call_with_retry(self.client.get_vault, vault_id=resource_id)

    def create_resource(self):
        """Create the vault and wait for it to become active.

        Returns:
            The created vault.
        """
        response = self.call_with_retry(
            self.client.create_vault,
            create_vault_details=build_create_vault_details(self.module.params),
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            READY_STATES,
        )

    def build_update_details(self, update_model_fields):
        """Build the OCI update-vault model from planned field changes.

        Args:
            update_model_fields: The planned changes keyed by update field.

        Returns:
            An ``oci.key_management.models.UpdateVaultDetails`` instance.
        """
        return oci.key_management.models.UpdateVaultDetails(**update_model_fields)

    def cancel_deletion(self, resource):
        """Cancel the scheduled deletion of ``resource``.

        Args:
            resource: The vault that is pending deletion.

        Returns:
            The restored vault.
        """
        response = self.call_with_retry(
            self.client.cancel_vault_deletion,
            vault_id=resource.id,
        )
        return self.get_mutation_result(response.data, resource.id, READY_STATES)

    def delete_resource(self, resource):
        """Schedule ``resource`` for deletion and wait until it is pending.

        Args:
            resource: The vault to delete.

        Returns:
            The vault in ``PENDING_DELETION``, or the raw response data when not waiting.
        """
        return self.delete_resource_and_wait(
            resource,
            self.client.schedule_vault_deletion,
            action_verb="schedule deletion of",
            vault_id=resource.id,
            schedule_vault_deletion_details=(
                oci.key_management.models.ScheduleVaultDeletionDetails(
                    **self.build_deletion_schedule()
                )
            ),
        )


def main():
    """Run the ``oci_vault`` module."""
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        vault_id=dict(type="str"),
        deletion_days=dict(type="int"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciVaultModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
