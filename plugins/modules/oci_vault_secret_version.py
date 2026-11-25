# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_vault_secret_version
short_description: Manage the deletion schedule of an OCI Vault secret version
description:
  - Schedule an existing secret version for deletion and cancel a scheduled deletion.
  - This module never creates a secret version. A version is created whenever the content of a secret changes,
    which you do with M(ansible.oci.oci_vault_secret).
version_added: "1.3.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_wait_options
options:
  state:
    description:
      - The desired state of the secret version.
      - C(present) requires the version to exist and cancels its scheduled deletion when it has one.
      - C(absent) schedules the version for deletion. OCI never deletes a version immediately, so a version that is
        already scheduled for deletion, or that does not exist, is reported as unchanged.
    type: str
    choices: [present, absent]
    default: present
  secret_id:
    description:
      - The OCID of the secret that owns the version.
    type: str
    required: true
  version_number:
    description:
      - The number of the secret version.
      - Exactly one of O(version_number) or O(version_name) is required.
    type: int
  version_name:
    description:
      - The name of the secret version, used to find the version in the secret.
      - If more than one version matches, the task fails and you must supply O(version_number).
      - Exactly one of O(version_number) or O(version_name) is required.
    type: str
  deletion_days:
    description:
      - The number of days from now until OCI deletes the version when O(state=absent).
      - OCI accepts values from 1 to 30. When omitted, OCI uses 30 days.
      - The version stays scheduled for deletion until then and can be restored by running the task again with O(state=present).
      - Only a version in the C(DEPRECATED) stage can be scheduled for deletion. The task fails for any other version.
    type: int
"""

EXAMPLES = r"""
- name: Schedule a deprecated secret version for deletion in 7 days
  ansible.oci.oci_vault_secret_version:
    secret_id: ocid1.vaultsecret.oc1..example
    version_number: 1
    state: absent
    deletion_days: 7

- name: Schedule a secret version for deletion by name
  ansible.oci.oci_vault_secret_version:
    secret_id: ocid1.vaultsecret.oc1..example
    version_name: example-version
    state: absent

- name: Cancel the scheduled deletion of a secret version
  ansible.oci.oci_vault_secret_version:
    secret_id: ocid1.vaultsecret.oc1..example
    version_number: 1
    state: present
"""

RETURN = r"""
resource:
  description: The secret version.
  returned: when O(state=present)
  type: dict
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
      description: The rotation states of the version, such as C(CURRENT), C(PENDING), C(LATEST), C(PREVIOUS), and C(DEPRECATED).
      type: list
      elements: str
      returned: always
      sample: [DEPRECATED]
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
      description: The date and time the version expires while it is the current version, in RFC3339 format.
      type: str
      returned: always
      sample: null
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    OCI_WAIT_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    _fetch_during_wait,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_vault import (
    MAX_DELETION_DAYS,
    SECRET_MIN_DELETION_DAYS,
    build_deletion_schedule,
    validate_deletion_days,
)

oci = import_oci_sdk()[0]

STAGE_DEPRECATED = "DEPRECATED"
SECRET_STATE_ACTIVE = "ACTIVE"


class OciVaultSecretVersionModule(OciResourceBase):
    """Concrete resource adapter for the deletion schedule of OCI Vault secret versions."""

    @property
    def client_class(self):
        """Return the vault client class that serves secret management calls.

        Returns:
            The ``oci.vault.VaultsClient`` class.
        """
        return oci.vault.VaultsClient

    resource_id_param = "version_number"
    resource_id_field = "version_number"
    list_resource_method = "list_secret_versions"
    common_list_filter_params = ("secret_id",)
    name_lookup_param = "version_name"
    name_response_field = "name"
    create_resource_name = "secret version"
    update_field_specs = ()
    common_update_field_specs = ()

    def get_resource_response(self, resource_id):
        """Return the raw ``get_secret_version`` response.

        Args:
            resource_id: The version number.

        Returns:
            The OCI SDK response wrapper.
        """
        return self.call_with_retry(
            self.client.get_secret_version,
            secret_id=self.module.params["secret_id"],
            secret_version_number=resource_id,
        )

    def hydrate_named_resource(self, resource):
        """Return the full version for a name-lookup match.

        ``list_secret_versions`` returns a ``SecretVersionSummary`` whose
        expiry field has a different name than the ``SecretVersion`` returned
        by ``get_secret_version``, so a name-resolved match is re-fetched to
        give the module one result shape.

        Args:
            resource: The ``SecretVersionSummary`` matched by name.

        Returns:
            The full version, or ``resource`` if it can no longer be fetched.
        """
        full_resource = self.get_resource_by_id(resource.version_number)
        return full_resource if full_resource is not None else resource

    def resolve_target_resource(self):
        """Return the version to manage, or None when there is nothing to delete.

        For ``state=absent`` a missing version and a version that is already
        scheduled for deletion both mean the task is done, and a version
        that cannot be scheduled must fail the task. Both are decided here,
        because the inherited absent flow exits in check mode right after this
        lookup and would otherwise report a change that the real run rejects.

        Returns:
            The current version, or None when ``state=absent`` has nothing to
            schedule.
        """
        resource = super(OciVaultSecretVersionModule, self).resolve_target_resource()
        if self.module.params["state"] != "absent" or resource is None:
            return resource
        if resource.time_of_deletion is not None:
            return None
        if STAGE_DEPRECATED not in (resource.stages or []):
            self.module.fail_json(
                msg=(
                    f"Secret version {resource.version_number} cannot be scheduled "
                    f"for deletion because only a {STAGE_DEPRECATED} version can be "
                    f"deleted, and its stages are: {', '.join(resource.stages or [])}"
                )
            )
        return resource

    def validate_create_request(self):
        """Fail because a secret version cannot be created by this module.

        The inherited implementation validates a create request, but versions
        are only created by changing the content of the secret.
        """
        identifier = (
            f"version_number={self.resource_id}"
            if self.resource_id
            else f"version_name={self.name_lookup_value}"
        )
        self.module.fail_json(
            msg=(
                f"No secret version was found for {identifier} in secret "
                f"{self.module.params['secret_id']}. This module cannot create "
                "secret versions; update the content of the secret with "
                "ansible.oci.oci_vault_secret to create one"
            )
        )

    def fail_missing_update_target(self):
        """Fail because the requested version number does not exist.

        The inherited message advises creating the resource without its ID,
        which is not possible for a secret version.
        """
        self.validate_create_request()

    def create_resource(self):
        """Reject creation, which ``validate_create_request`` already prevents.

        Raises:
            NotImplementedError: Always, because secret versions are created
                by changing the content of the secret.
        """
        raise NotImplementedError(
            "Secret versions are created by updating the content of a secret"
        )

    def extra_change_needed(self, resource):
        """Report whether a scheduled deletion must be cancelled.

        Cancellation is not an update-field difference, so the shared update
        planner cannot see it.

        Args:
            resource: The current version.

        Returns:
            ``True`` when the version is scheduled for deletion.
        """
        return resource.time_of_deletion is not None

    def apply_extra_change(self, resource):
        """Cancel the scheduled deletion of ``resource``.

        Args:
            resource: The version that is scheduled for deletion.

        Returns:
            The version after the cancellation.
        """
        self.call_with_retry(
            self.client.cancel_secret_version_deletion,
            secret_id=resource.secret_id,
            secret_version_number=resource.version_number,
        )
        return self.wait_for_deletion_schedule(resource.version_number, scheduled=False)

    def delete_resource(self, resource):
        """Schedule ``resource`` for deletion and wait until it is scheduled.

        Args:
            resource: The deprecated version to delete.

        Returns:
            The version with its deletion scheduled, or its state right after the
            request when not waiting.
        """
        self.call_delete_fn(
            resource,
            self.client.schedule_secret_version_deletion,
            action_verb="schedule deletion of",
            secret_id=resource.secret_id,
            secret_version_number=resource.version_number,
            schedule_secret_version_deletion_details=(
                oci.vault.models.ScheduleSecretVersionDeletionDetails(
                    **build_deletion_schedule(self.module.params.get("deletion_days"))
                )
            ),
        )
        return self.wait_for_deletion_schedule(resource.version_number, scheduled=True)

    def validate_delete_request(self):
        """Validate the target and ``deletion_days`` before scheduling deletion.

        The inherited check knows nothing about ``deletion_days``, whose range
        OCI enforces only after the request is sent.
        """
        super(OciVaultSecretVersionModule, self).validate_delete_request()
        validate_deletion_days(
            self.module, SECRET_MIN_DELETION_DAYS, MAX_DELETION_DAYS
        )

    def wait_for_deletion_schedule(self, version_number, scheduled):
        """Wait until a version's deletion is scheduled or cancelled.

        A secret version has no lifecycle state to wait on, so the waiter
        watches ``time_of_deletion`` instead. OCI also keeps the owning
        secret ``UPDATING`` for a while after the version changes and rejects
        further changes to the secret until then, so the wait ends only once
        the secret is ``ACTIVE`` again.

        Args:
            version_number: The number of the version.
            scheduled: Whether to wait for ``time_of_deletion`` to be set
                (True) or cleared (False).

        Returns:
            The refreshed version. When not waiting, the version as OCI
            reports it right after the request.
        """
        initial_response = self.get_resource_response(version_number)
        if not self.module.params.get("wait", True):
            return initial_response.data
        waiter_result = self.wait_until(
            initial_response,
            lambda response: (response.data.time_of_deletion is not None) == scheduled,
            lambda: self.get_resource_response(version_number),
        )
        self.wait_until(
            self.get_secret_response(),
            lambda response: response.data.lifecycle_state == SECRET_STATE_ACTIVE,
            self.get_secret_response,
        )
        return waiter_result.data

    def get_secret_response(self):
        """Return the raw ``get_secret`` response for the owning secret.

        Returns:
            The OCI SDK response wrapper.
        """
        return self.call_with_retry(
            self.client.get_secret, secret_id=self.module.params["secret_id"]
        )

    def wait_until(self, initial_response, evaluate_response, fetch):
        """Poll ``fetch`` until ``evaluate_response`` accepts its response.

        Args:
            initial_response: The first response to evaluate.
            evaluate_response: A callable that returns True when done.
            fetch: A callable that returns a fresh response.

        Returns:
            The accepted response.
        """
        return oci.wait_until(
            self.client,
            initial_response,
            max_interval_seconds=self.module.params.get("wait_interval", 30),
            max_wait_seconds=self.module.params.get("wait_timeout", 1200),
            evaluate_response=evaluate_response,
            fetch_func=lambda response=None: _fetch_during_wait(fetch, response),
        )


def main():
    """Run the ``oci_vault_secret_version`` module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_WAIT_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        secret_id=dict(type="str", required=True),
        version_number=dict(type="int"),
        version_name=dict(type="str"),
        deletion_days=dict(type="int"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=[["version_number", "version_name"]],
        mutually_exclusive=[["version_number", "version_name"]],
        supports_check_mode=True,
    )

    OciVaultSecretVersionModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
