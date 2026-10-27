"""Helpers shared by OCI Vault and key management resource and info modules."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from datetime import datetime, timedelta, timezone
from functools import partial

from ansible.module_utils.basic import missing_required_lib

from ansible_collections.ansible.oci.plugins.module_utils.oci_auth import (
    create_service_client,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    import_oci_sdk,
)

oci, HAS_OCI_SDK = import_oci_sdk()

OCI_VAULT_ENDPOINT_ARGS = {
    "vault_id": dict(type="str"),
    "management_endpoint": dict(type="str"),
}
OCI_VAULT_ENDPOINT_REQUIRED_ONE_OF = [["vault_id", "management_endpoint"]]
OCI_VAULT_ENDPOINT_MUTUALLY_EXCLUSIVE = [["vault_id", "management_endpoint"]]

STATE_PENDING_DELETION = "PENDING_DELETION"
STATE_SCHEDULING_DELETION = "SCHEDULING_DELETION"
STATE_DELETING = "DELETING"
STATE_DELETED = "DELETED"
MIN_DELETION_DAYS = 7
MAX_DELETION_DAYS = 30


def resolve_management_endpoint(module):
    """Return the vault management endpoint used by key management calls.

    Args:
        module: The active Ansible module with ``vault_id`` or
            ``management_endpoint`` parameters.

    Returns:
        The explicit ``management_endpoint`` or the endpoint of ``vault_id``,
        without a trailing slash.
    """
    management_endpoint = module.params.get("management_endpoint")
    if management_endpoint:
        return management_endpoint.rstrip("/")

    vault_id = module.params.get("vault_id")
    vault_client = create_service_client(module, oci.key_management.KmsVaultClient)
    response = oci.retry.DEFAULT_RETRY_STRATEGY.make_retrying_call(
        vault_client.get_vault,
        vault_id=vault_id,
    )
    management_endpoint = getattr(response.data, "management_endpoint", None)
    if not management_endpoint:
        module.fail_json(
            msg=f"Vault {vault_id} does not expose a management endpoint"
        )
    return management_endpoint.rstrip("/")


class OciVaultManagementMixin:
    """Create a ``KmsManagementClient`` bound to one vault's endpoint.

    Key management operations are served by a per-vault endpoint rather than
    the regional endpoint the SDK derives from configuration, so the endpoint
    must be resolved before the base class creates its client.
    """

    def __init__(self, module):
        """Resolve the vault endpoint and create the shared OCI client.

        Args:
            module: The active Ansible module.
        """
        if not HAS_OCI_SDK:
            module.fail_json(msg=missing_required_lib("oci"))
        self.management_endpoint = resolve_management_endpoint(module)
        super(OciVaultManagementMixin, self).__init__(module)

    @property
    def client_class(self):
        """Return a key management client factory bound to the vault endpoint.

        Returns:
            A callable that accepts the OCI SDK client arguments.
        """
        return partial(
            oci.key_management.KmsManagementClient,
            service_endpoint=self.management_endpoint,
        )


class OciScheduledDeletionMixin:
    """Share the scheduled-deletion lifecycle of vaults and keys.

    OCI never deletes a vault or key immediately. ``state=absent`` schedules
    deletion 7 to 30 days out, and a resource pending deletion can be restored
    by cancelling the schedule. Concrete adapters implement
    :meth:`cancel_deletion` with their resource's cancel operation.
    """

    @property
    def dead_states(self):
        """Return the lifecycle states that count as "no such resource".

        A resource scheduled for deletion is not really gone: it can be
        restored until OCI deletes it. The inherited fixed set therefore cannot
        serve both states. For ``state=absent`` a resource that is pending
        deletion is already as deleted as OCI allows, which keeps the task
        idempotent and makes ``delete_resource_and_wait`` wait for
        ``PENDING_DELETION``. For ``state=present`` a pending resource must
        still be found so its deletion can be cancelled instead of a duplicate
        being created.

        Returns:
            A frozenset of lifecycle state names.
        """
        dead_states = {STATE_DELETED, STATE_DELETING}
        if self.module.params.get("state", "present") == "absent":
            dead_states |= {STATE_PENDING_DELETION, STATE_SCHEDULING_DELETION}
        return frozenset(dead_states)

    @staticmethod
    def is_pending_deletion(resource):
        """Return ``True`` when ``resource`` is scheduled for deletion.

        Args:
            resource: The current resource.

        Returns:
            Whether the resource is in ``PENDING_DELETION``.
        """
        return getattr(resource, "lifecycle_state", None) == STATE_PENDING_DELETION

    def cancel_deletion(self, resource):
        """Cancel the scheduled deletion of ``resource``.

        Args:
            resource: The resource that is pending deletion.

        Returns:
            The restored resource.

        Raises:
            NotImplementedError: When the concrete adapter does not implement it.
        """
        raise NotImplementedError(
            f"{type(self).__name__} must define cancel_deletion()"
        )

    def update_resource(self, resource):
        """Restore a resource pending deletion, then apply the shared update plan.

        The inherited implementation calls the update operation, which OCI
        rejects for a resource that is pending deletion, so the deletion is
        cancelled first.

        Args:
            resource: The current resource.

        Returns:
            The updated resource.
        """
        if self.is_pending_deletion(resource):
            resource = self.cancel_deletion(resource)
        return super(OciScheduledDeletionMixin, self).update_resource(resource)

    def extra_change_needed(self, resource):
        """Report whether a scheduled deletion must be cancelled.

        Cancellation is not an update-field difference, so the shared update
        planner cannot see it.

        Args:
            resource: The current resource.

        Returns:
            ``True`` when the resource is pending deletion.
        """
        return self.is_pending_deletion(resource)

    def apply_extra_change(self, resource):
        """Cancel a scheduled deletion that is still outstanding.

        The base flow calls this after ``update_resource``, which has already
        restored a pending resource when an update was needed, so cancellation
        only happens here when no update ran.

        Args:
            resource: The current resource.

        Returns:
            The resource, restored when it was pending deletion.
        """
        if self.is_pending_deletion(resource):
            resource = self.cancel_deletion(resource)
        return resource

    def validate_delete_request(self):
        """Validate the target and ``deletion_days`` before scheduling deletion.

        The inherited check knows nothing about ``deletion_days``, whose range
        OCI enforces only after the request is sent.
        """
        super(OciScheduledDeletionMixin, self).validate_delete_request()
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

    def build_deletion_schedule(self):
        """Return the fields of a schedule-deletion details model.

        Returns:
            ``{"time_of_deletion": ...}`` set ``deletion_days`` from now, or an
            empty dict so OCI applies its default window when
            ``deletion_days`` is omitted.
        """
        deletion_days = self.module.params.get("deletion_days")
        if deletion_days is None:
            return {}
        return {
            "time_of_deletion": datetime.now(timezone.utc) + timedelta(days=deletion_days)
        }
