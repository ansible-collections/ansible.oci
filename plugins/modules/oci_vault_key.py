# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_vault_key
short_description: Manage a master encryption key in an Oracle Cloud Infrastructure Vault
description:
  - Create, update, rotate, schedule for deletion, and restore OCI Vault master encryption keys.
  - Uses the shared OCI helper layer for authentication, waiting, retry
    behavior, and result shaping.
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
      - The desired state of the key.
      - C(present) creates the key when it does not exist, applies updates, and
        rotates it when I(rotate=true). A key that is pending deletion is
        restored by cancelling the scheduled deletion.
      - C(absent) schedules the key for deletion. OCI never deletes a key
        immediately, so a key that is already pending deletion is reported as
        unchanged.
    type: str
    choices: [present, absent]
    default: present
  vault_id:
    description:
      - The OCID of the vault that holds the key.
      - The module looks up the vault's management endpoint with this value if
        O(management_endpoint) is not provided.
      - Mutually exclusive with O(management_endpoint). One of the two is required.
    type: str
  management_endpoint:
    description:
      - The management endpoint of the vault that holds the key.
      - The module looks up the vault's management endpoint with O(vault_id) if
        this parameter is not provided.
      - Mutually exclusive with O(vault_id). One of the two is required.
    type: str
  key_id:
    description:
      - The OCID of the key.
      - When provided, the module manages this exact key.
      - When omitted, the module uses C(compartment_id + name) to find an
        existing key in the vault. If more than one key matches, the task fails
        and the caller must supply C(key_id).
      - Create requests must omit C(key_id).
    type: str
  name:
    description:
      - Human-readable name for the key.
      - Required when creating a key.
      - Can be changed after create.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the key.
      - Required when creating a key.
      - The module does not move an existing key to another compartment.
      - Also scopes name-based key lookups when C(key_id) is omitted.
    type: str
  key_shape:
    description:
      - The cryptographic properties of the key.
      - Required when creating a key.
      - The module does not update this field after create.
    type: dict
    suboptions:
      algorithm:
        description:
          - The algorithm used by the key.
        type: str
        choices: [aes, rsa, ecdsa]
      length:
        description:
          - The length of the key in bytes, for example C(32) for a 256-bit AES key.
        type: int
      curve_id:
        description:
          - The curve used by an C(ecdsa) key.
        type: str
        choices: [nist_p256, nist_p384, nist_p521]
  protection_mode:
    description:
      - How the key is stored and where its cryptographic operations run.
      - The module does not update this field after create.
    type: str
    choices: [hsm, software, external]
  external_key_id:
    description:
      - The OCID or identifier of the external key to reference when
        I(protection_mode=external).
      - Used only when creating a key. The module does not update it afterward.
    type: str
  is_auto_rotation_enabled:
    description:
      - Whether OCI automatically rotates the key on the schedule in
        I(auto_key_rotation_details).
    type: bool
  auto_key_rotation_details:
    description:
      - The automatic rotation schedule of the key.
    type: dict
    suboptions:
      rotation_interval_in_days:
        description:
          - The interval, in days, between automatic rotations.
          - OCI accepts values from 60 to 365.
        type: int
  rotate:
    description:
      - Whether to create a new key version on every run of the task with C(state=present).
      - A new version is always created when this is true, so the task reports
        a change every time.
      - Ignored for a key created by the same task, because a new key already
        has a fresh version.
      - The key must be enabled. If the key is pending deletion, the module
        restores it first.
    type: bool
    default: false
  deletion_days:
    description:
      - The number of days from now until OCI deletes the key when C(state=absent).
      - OCI accepts values from 7 to 30. When omitted, OCI uses 30 days.
      - The key remains in C(PENDING_DELETION) until then and can be restored by
        running the task again with C(state=present).
    type: int
"""

EXAMPLES = r"""
- name: Create an AES key
  ansible.oci.oci_vault_key:
    vault_id: ocid1.vault.oc1..example
    compartment_id: ocid1.compartment.oc1..example
    name: example-key
    key_shape:
      algorithm: aes
      length: 32
    protection_mode: hsm
  register: created_key

- name: Create a key that rotates automatically every 90 days
  ansible.oci.oci_vault_key:
    vault_id: ocid1.vault.oc1..example
    compartment_id: ocid1.compartment.oc1..example
    name: example-rotating-key
    key_shape:
      algorithm: aes
      length: 32
    is_auto_rotation_enabled: true
    auto_key_rotation_details:
      rotation_interval_in_days: 90

- name: Rotate a key on demand by creating a new key version
  ansible.oci.oci_vault_key:
    management_endpoint: https://example-management.kms.us-ashburn-1.oraclecloud.com
    key_id: "{{ created_key.resource.id }}"
    rotate: true

- name: Schedule a key for deletion in 7 days
  ansible.oci.oci_vault_key:
    vault_id: ocid1.vault.oc1..example
    key_id: "{{ created_key.resource.id }}"
    state: absent
    deletion_days: 7

- name: Restore a key that is pending deletion
  ansible.oci.oci_vault_key:
    vault_id: ocid1.vault.oc1..example
    key_id: "{{ created_key.resource.id }}"
    state: present
"""

RETURN = r"""
resource:
  description: The key resource.
  returned: when state != absent
  type: dict
  contains:
    id:
      description: The OCID of the key.
      type: str
      returned: always
    name:
      description: The name of the key.
      type: str
      returned: always
    compartment_id:
      description: The OCID of the compartment containing the key.
      type: str
      returned: always
    vault_id:
      description: The OCID of the vault that holds the key.
      type: str
      returned: always
    current_key_version:
      description: The OCID of the current key version.
      type: str
      returned: always
    lifecycle_state:
      description: The lifecycle state of the key, for example C(ENABLED).
      type: str
      returned: always
    key_shape:
      description: The algorithm, length, and curve of the key.
      type: dict
      returned: always
    protection_mode:
      description: How the key is stored and where its cryptographic operations run.
      type: str
      returned: always
    is_auto_rotation_enabled:
      description: Whether OCI rotates the key automatically.
      type: bool
      returned: always
    auto_key_rotation_details:
      description: The automatic rotation schedule of the key.
      type: dict
      returned: when auto rotation is configured
    time_created:
      description: The time the key was created.
      type: str
      returned: always
    time_of_deletion:
      description: The time OCI deletes the key, set while the key is pending deletion.
      type: str
      returned: when the key is pending deletion
    freeform_tags:
      description: Free-form tags of the key.
      type: dict
      returned: always
    defined_tags:
      description: Defined tags of the key.
      type: dict
      returned: always
"""

from datetime import datetime, timedelta, timezone

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_COMMON_ARGS,
    filter_none_values,
    import_oci_sdk,
    normalize_choice_parameters,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_vault import (
    OCI_VAULT_ENDPOINT_ARGS,
    OCI_VAULT_ENDPOINT_MUTUALLY_EXCLUSIVE,
    OCI_VAULT_ENDPOINT_REQUIRED_ONE_OF,
    OciVaultManagementMixin,
)

oci = import_oci_sdk()[0]


CHOICE_VALUE_MAPS = {
    ("key_shape", "algorithm"): {
        "aes": "AES",
        "rsa": "RSA",
        "ecdsa": "ECDSA",
    },
    ("key_shape", "curve_id"): {
        "nist_p256": "NIST_P256",
        "nist_p384": "NIST_P384",
        "nist_p521": "NIST_P521",
    },
    ("protection_mode",): {
        "hsm": "HSM",
        "software": "SOFTWARE",
        "external": "EXTERNAL",
    },
}

CREATE_REQUIRED_FIELDS = [
    "compartment_id",
    "name",
    "key_shape",
]
KEY_STATE_ENABLED = "ENABLED"
KEY_STATE_DISABLED = "DISABLED"
KEY_STATE_PENDING_DELETION = "PENDING_DELETION"
KEY_STATE_SCHEDULING_DELETION = "SCHEDULING_DELETION"
KEY_STATE_DELETING = "DELETING"
KEY_STATE_DELETED = "DELETED"
CREATE_WAIT_STATES = (KEY_STATE_ENABLED,)
READY_STATES = (KEY_STATE_ENABLED, KEY_STATE_DISABLED)
MIN_DELETION_DAYS = 7
MAX_DELETION_DAYS = 30


def build_create_key_details(params):
    """Build the OCI create-key model from module parameters.

    Args:
        params: The validated module parameters, with choices already
            normalized to OCI values.

    Returns:
        An ``oci.key_management.models.CreateKeyDetails`` instance with nested
        key shape, rotation, and external key reference models.
    """
    models = oci.key_management.models
    key_shape = models.KeyShape(**filter_none_values(params["key_shape"]))

    auto_key_rotation_details = None
    if params.get("auto_key_rotation_details") is not None:
        auto_key_rotation_details = models.AutoKeyRotationDetails(
            **filter_none_values(params["auto_key_rotation_details"])
        )

    external_key_reference = None
    if params.get("external_key_id") is not None:
        external_key_reference = models.ExternalKeyReference(
            external_key_id=params["external_key_id"]
        )

    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "display_name": params.get("name"),
            "key_shape": key_shape,
            "protection_mode": params.get("protection_mode"),
            "is_auto_rotation_enabled": params.get("is_auto_rotation_enabled"),
            "auto_key_rotation_details": auto_key_rotation_details,
            "external_key_reference": external_key_reference,
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return models.CreateKeyDetails(**details)


class OciVaultKeyModule(OciVaultManagementMixin, OciResourceBase):
    """Concrete resource adapter for OCI Vault master encryption keys."""

    resource_id_param = "key_id"
    list_resource_method = "list_keys"
    create_resource_name = "key"
    create_required_fields = CREATE_REQUIRED_FIELDS
    update_method_name = "update_key"
    update_details_name = "update_key_details"
    update_wait_states = READY_STATES
    update_field_specs = (
        UpdateFieldSpec(
            param_name="name",
            is_mutable=True,
            resource_field="display_name",
            update_field="display_name",
        ),
        UpdateFieldSpec(
            param_name="is_auto_rotation_enabled",
            is_mutable=True,
        ),
        UpdateFieldSpec(
            param_name="auto_key_rotation_details",
            is_mutable=True,
            compare="subset_dict",
        ),
        UpdateFieldSpec(
            param_name="compartment_id",
            is_mutable=False,
            immutable_reason="this module does not move keys between compartments",
        ),
        UpdateFieldSpec(
            param_name="key_shape",
            is_mutable=False,
            compare="subset_dict",
        ),
        UpdateFieldSpec(
            param_name="protection_mode",
            is_mutable=False,
        ),
    )

    @property
    def dead_states(self):
        """Return the lifecycle states that count as "no such key".

        A key scheduled for deletion is not really gone: it can be restored
        until OCI deletes it. The inherited fixed set therefore cannot serve
        both states. For ``state=absent`` a key that is pending deletion is
        already as deleted as OCI allows, which keeps the task idempotent and
        makes ``delete_resource_and_wait`` wait for ``PENDING_DELETION``. For
        ``state=present`` a pending key must still be found so its deletion can
        be cancelled instead of a duplicate key being created.

        Returns:
            A frozenset of lifecycle state names.
        """
        dead_states = {KEY_STATE_DELETED, KEY_STATE_DELETING}
        if self.module.params.get("state", "present") == "absent":
            dead_states |= {KEY_STATE_PENDING_DELETION, KEY_STATE_SCHEDULING_DELETION}
        return frozenset(dead_states)

    def get_resource_response(self, resource_id):
        """Return the raw ``get_key`` response for ``resource_id``.

        Args:
            resource_id: The OCID of the key.

        Returns:
            The OCI SDK response wrapper.
        """
        return self.call_with_retry(self.client.get_key, key_id=resource_id)

    def hydrate_named_resource(self, resource):
        """Return the full key for a name-lookup match.

        ``list_keys`` returns a ``KeySummary`` that omits ``key_shape``,
        ``auto_key_rotation_details``, and ``time_of_deletion``, so a
        name-resolved match must be re-fetched with ``get_key`` before the
        update planner compares desired values against it.

        Args:
            resource: The ``KeySummary`` matched by name.

        Returns:
            The full key, or ``resource`` if it can no longer be fetched.
        """
        full_resource = self.get_resource_by_id(resource.id)
        return full_resource if full_resource is not None else resource

    def create_resource(self):
        """Create the key and wait for it to be enabled.

        Returns:
            The created key.
        """
        response = self.call_with_retry(
            self.client.create_key,
            create_key_details=build_create_key_details(self.module.params),
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            CREATE_WAIT_STATES,
        )

    def build_update_details(self, update_model_fields):
        """Build the OCI update-key model from planned field changes.

        Args:
            update_model_fields: The planned changes keyed by update field.

        Returns:
            An ``oci.key_management.models.UpdateKeyDetails`` instance.
        """
        fields = dict(update_model_fields)
        if "auto_key_rotation_details" in fields:
            fields["auto_key_rotation_details"] = (
                oci.key_management.models.AutoKeyRotationDetails(
                    **filter_none_values(fields["auto_key_rotation_details"])
                )
            )
        return oci.key_management.models.UpdateKeyDetails(**fields)

    @staticmethod
    def is_pending_deletion(resource):
        """Return ``True`` when ``resource`` is scheduled for deletion.

        Args:
            resource: The current key.

        Returns:
            Whether the key is in ``PENDING_DELETION``.
        """
        return getattr(resource, "lifecycle_state", None) == KEY_STATE_PENDING_DELETION

    def cancel_key_deletion(self, resource):
        """Cancel the scheduled deletion of ``resource``.

        OCI restores the state the key had before deletion was scheduled, so
        the wait accepts either ``ENABLED`` or ``DISABLED``.

        Args:
            resource: The key that is pending deletion.

        Returns:
            The restored key.
        """
        response = self.call_with_retry(
            self.client.cancel_key_deletion,
            key_id=resource.id,
        )
        return self.get_mutation_result(response.data, resource.id, READY_STATES)

    def update_resource(self, resource):
        """Restore a key pending deletion, then apply the shared update plan.

        The inherited implementation calls ``update_key``, which OCI rejects
        for a key that is pending deletion, so the deletion is cancelled first.

        Args:
            resource: The current key.

        Returns:
            The updated key.
        """
        if self.is_pending_deletion(resource):
            resource = self.cancel_key_deletion(resource)
        return super(OciVaultKeyModule, self).update_resource(resource)

    def extra_change_needed(self, resource):
        """Report whether a deletion must be cancelled or a rotation created.

        Neither is an update-field difference, so the shared update planner
        cannot see them.

        Args:
            resource: The current key.

        Returns:
            ``True`` when the key is pending deletion or ``rotate`` is set.
        """
        return self.is_pending_deletion(resource) or bool(self.module.params.get("rotate"))

    def apply_extra_change(self, resource):
        """Cancel a pending deletion that is still outstanding and rotate the key.

        The base flow calls this after ``update_resource``, which has already
        restored a pending key when an update was needed, so cancellation only
        happens here when no update ran.

        Args:
            resource: The current key.

        Returns:
            The key after cancellation and, when requested, rotation.
        """
        if self.is_pending_deletion(resource):
            resource = self.cancel_key_deletion(resource)
        if not self.module.params.get("rotate"):
            return resource
        response = self.call_with_retry(self.client.create_key_version, key_id=resource.id)
        if self.module.params.get("wait", True):
            self.wait_for_key_version(resource.id, response.data.id)
        return self.wait_for_resource_id(resource.id, READY_STATES)

    def wait_for_key_version(self, key_id, key_version_id):
        """Wait for a key version created by rotation to become enabled.

        The key itself can report a ready state while its new version is still
        being created, so the version is polled directly, as the SDK's
        ``create_key_version_and_wait_for_state`` composite operation does.

        Args:
            key_id: The OCID of the rotated key.
            key_version_id: The OCID of the key version created by rotation.
        """
        oci.wait_until(
            self.client,
            self.call_with_retry(
                self.client.get_key_version,
                key_id=key_id,
                key_version_id=key_version_id,
            ),
            "lifecycle_state",
            KEY_STATE_ENABLED,
            max_wait_seconds=self.module.params.get("wait_timeout", 1200),
            max_interval_seconds=self.module.params.get("wait_interval", 30),
        )

    def validate_delete_request(self):
        """Validate the target and ``deletion_days`` before scheduling deletion.

        The inherited check knows nothing about ``deletion_days``, whose range
        OCI enforces only after the request is sent.
        """
        super(OciVaultKeyModule, self).validate_delete_request()
        deletion_days = self.module.params.get("deletion_days")
        if deletion_days is not None and not (
            MIN_DELETION_DAYS <= deletion_days <= MAX_DELETION_DAYS
        ):
            self.module.fail_json(
                msg=(
                    f"deletion_days must be between {MIN_DELETION_DAYS} and "
                    f"{MAX_DELETION_DAYS}, got {deletion_days}"
                )
            )

    def delete_resource(self, resource):
        """Schedule ``resource`` for deletion and wait until it is pending.

        Args:
            resource: The key to delete.

        Returns:
            The key in ``PENDING_DELETION``, or the raw response data when not waiting.
        """
        deletion_details = {}
        deletion_days = self.module.params.get("deletion_days")
        if deletion_days is not None:
            deletion_details["time_of_deletion"] = (
                datetime.now(timezone.utc) + timedelta(days=deletion_days)
            )
        return self.delete_resource_and_wait(
            resource,
            self.client.schedule_key_deletion,
            action_verb="schedule deletion of",
            key_id=resource.id,
            schedule_key_deletion_details=(
                oci.key_management.models.ScheduleKeyDeletionDetails(**deletion_details)
            ),
        )


def main():
    """Run the ``oci_vault_key`` module."""
    argument_spec = dict(
        OCI_COMMON_ARGS,
        **OCI_VAULT_ENDPOINT_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        key_id=dict(type="str"),
        key_shape=dict(
            type="dict",
            no_log=False,
            options=dict(
                algorithm=dict(
                    type="str",
                    choices=list(CHOICE_VALUE_MAPS[("key_shape", "algorithm")]),
                ),
                length=dict(type="int"),
                curve_id=dict(
                    type="str",
                    choices=list(CHOICE_VALUE_MAPS[("key_shape", "curve_id")]),
                ),
            ),
        ),
        protection_mode=dict(
            type="str",
            choices=list(CHOICE_VALUE_MAPS[("protection_mode",)]),
        ),
        external_key_id=dict(type="str"),
        is_auto_rotation_enabled=dict(type="bool"),
        auto_key_rotation_details=dict(
            type="dict",
            no_log=False,
            options=dict(rotation_interval_in_days=dict(type="int")),
        ),
        rotate=dict(type="bool", default=False),
        deletion_days=dict(type="int"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=OCI_VAULT_ENDPOINT_REQUIRED_ONE_OF,
        mutually_exclusive=OCI_VAULT_ENDPOINT_MUTUALLY_EXCLUSIVE,
        supports_check_mode=True,
    )

    normalize_choice_parameters(module, CHOICE_VALUE_MAPS)

    OciVaultKeyModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
