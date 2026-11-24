"""Helpers shared by OCI Vault, key, and secret resource and info modules."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import base64
from datetime import datetime, timedelta, timezone
from functools import partial

from ansible.module_utils.basic import missing_required_lib

from ansible_collections.ansible.oci.plugins.module_utils.oci_auth import (
    create_service_client,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    import_oci_sdk,
    threaded_map,
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
STATE_CANCELLING_DELETION = "CANCELLING_DELETION"
STATE_DELETING = "DELETING"
STATE_DELETED = "DELETED"
RESTORED_STATES = ("ACTIVE", "ENABLED", "DISABLED")
MIN_DELETION_DAYS = 7
MAX_DELETION_DAYS = 30
SECRET_MIN_DELETION_DAYS = 1
DELETION_SCHEDULE_MARGIN = timedelta(minutes=10)
SECRET_CONTENT_ENCODINGS = ("text", "base64")


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

    min_deletion_days = MIN_DELETION_DAYS
    max_deletion_days = MAX_DELETION_DAYS

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

    def delete_resource_and_wait(
        self, resource, delete_fn, action_verb="delete", **delete_kwargs
    ):
        """Schedule deletion of ``resource`` and wait until it is pending.

        ``SCHEDULING_DELETION`` is a dead state so a rerun during the
        transition stays idempotent, but it is only transient. Waiting on the
        inherited dead states would return as soon as OCI accepts the request,
        before the resource reaches ``PENDING_DELETION``.

        Args:
            resource: The resource to schedule for deletion.
            delete_fn: The OCI schedule-deletion operation.
            action_verb: The verb describing the operation in errors.
            **delete_kwargs: Arguments passed to ``delete_fn``.

        Returns:
            The resource in ``PENDING_DELETION``, or the raw response data when
            not waiting.
        """
        response = self.call_delete_fn(
            resource, delete_fn, action_verb, **delete_kwargs
        )
        return self.get_mutation_result(
            response.data,
            self.get_resource_ocid(resource),
            tuple(self.dead_states - {STATE_SCHEDULING_DELETION}),
        )

    def resolve_target_resource(self):
        """Return the target resource, waiting out a deletion transition.

        A ``state=present`` task can find a resource that is still in the
        transient ``SCHEDULING_DELETION`` state, for example after a
        ``state=absent`` task with ``wait: false``. The restoration checks
        only recognize ``PENDING_DELETION``, so the transition is waited out
        here before the base flow evaluates restoration, honoring the task's
        ``wait`` settings.

        Returns:
            The current resource, refreshed when it was scheduling deletion.
        """
        resource = super(OciScheduledDeletionMixin, self).resolve_target_resource()
        if (
            self.module.params.get("state", "present") == "present"
            and getattr(resource, "lifecycle_state", None)
            == STATE_SCHEDULING_DELETION
        ):
            resource = self.wait_for_deletion_transition(resource)
        return resource

    def wait_for_deletion_transition(self, resource):
        """Wait for a scheduling resource to settle into a stable state.

        ``SCHEDULING_DELETION`` only lasts until OCI accepts the schedule, so
        the wait ends at ``PENDING_DELETION`` or at a state another actor
        restored the resource to. ``DELETING`` and ``DELETED`` fail the wait
        rather than letting the task silently report no change.

        Args:
            resource: The resource that is scheduling deletion.

        Returns:
            The refreshed resource.
        """
        return self.wait_for_resource_id(
            self.get_resource_ocid(resource),
            (STATE_PENDING_DELETION, "ACTIVE", "ENABLED", "DISABLED"),
            failure_states=(STATE_DELETING, STATE_DELETED),
        )

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

    def restore_resource(self, resource):
        """Cancel a pending deletion and wait for the restoration to finish.

        ``cancel_deletion`` honors the task's ``wait`` setting, so with
        ``wait: false`` it returns while the resource is still in the
        transient ``CANCELLING_DELETION`` state. OCI rejects updates and key
        rotation in that state, and the update or rotation this task was
        asked to perform follows immediately, so the transition is waited
        out here regardless of ``wait``.

        Args:
            resource: The resource that is pending deletion.

        Returns:
            The restored resource.
        """
        resource = self.cancel_deletion(resource)
        if getattr(resource, "lifecycle_state", None) == STATE_CANCELLING_DELETION:
            resource = self.wait_for_restoration(resource)
        return resource

    def wait_for_restoration(self, resource):
        """Wait for a resource that is cancelling deletion to become usable.

        Unlike the shared wait helpers this wait ignores ``wait: false``,
        because the operations that follow a restoration cannot succeed
        while the resource is still in ``CANCELLING_DELETION``. The
        ``wait_timeout`` and ``wait_interval`` settings still bound it.

        Args:
            resource: The resource in ``CANCELLING_DELETION``.

        Returns:
            The refreshed resource in a stable state.
        """
        resource_id = self.get_resource_ocid(resource)

        def fetch(response=None):
            return self.call_with_retry(self.get_resource_response, resource_id)

        waiter_result = oci.wait_until(
            self.client,
            fetch(),
            max_wait_seconds=self.module.params.get("wait_timeout", 1200),
            max_interval_seconds=self.module.params.get("wait_interval", 30),
            evaluate_response=partial(
                self._restoration_wait_complete, resource_id
            ),
            fetch_func=fetch,
        )
        return getattr(waiter_result, "data", None)

    def _restoration_wait_complete(self, resource_id, response):
        """Evaluate one restoration poll, failing on a lost resource.

        Args:
            resource_id: The OCID of the resource being restored.
            response: The current ``get`` response.

        Returns:
            Whether the resource reached a stable restored state.
        """
        state = getattr(response.data, "lifecycle_state", None)
        if state in (STATE_DELETING, STATE_DELETED):
            self.module.fail_json(
                msg=f"Resource {resource_id} entered failure state: {state}"
            )
        return state in RESTORED_STATES

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
            resource = self.restore_resource(resource)
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
            resource = self.restore_resource(resource)
        return resource

    def validate_delete_request(self):
        """Validate the target and ``deletion_days`` before scheduling deletion.

        The inherited check knows nothing about ``deletion_days``, whose range
        OCI enforces only after the request is sent.
        """
        super(OciScheduledDeletionMixin, self).validate_delete_request()
        validate_deletion_days(
            self.module, self.min_deletion_days, self.max_deletion_days
        )

    def build_deletion_schedule(self):
        """Return the fields of a schedule-deletion details model.

        Returns:
            ``{"time_of_deletion": ...}`` set ``deletion_days`` from now, or an
            empty dict so OCI applies its default window when
            ``deletion_days`` is omitted.
        """
        return build_deletion_schedule(
            self.module.params.get("deletion_days"), self.max_deletion_days
        )


def validate_deletion_days(module, min_days, max_days):
    """Fail when ``deletion_days`` falls outside the window OCI accepts.

    OCI enforces the window only after the request is sent, so checking it
    first gives a clear error before any change is made.

    Args:
        module: The active Ansible module.
        min_days: The smallest accepted number of days.
        max_days: The largest accepted number of days.
    """
    deletion_days = module.params.get("deletion_days")
    if deletion_days is not None and not min_days <= deletion_days <= max_days:
        module.fail_json(
            msg=(
                f"deletion_days must be between {min_days} and "
                f"{max_days}, got {deletion_days}"
            )
        )


def build_deletion_schedule(deletion_days, max_days=MAX_DELETION_DAYS):
    """Return the fields of a schedule-deletion details model.

    OCI checks the deletion window when it receives the request, so a time
    exactly at the minimum would already be too early. A short margin is
    added, capped so the time never passes the maximum.

    Args:
        deletion_days: The number of days from now until deletion, or None.
        max_days: The largest number of days OCI accepts.

    Returns:
        ``{"time_of_deletion": ...}`` set about ``deletion_days`` from now, or
        an empty dict so OCI applies its default window when
        ``deletion_days`` is None.
    """
    if deletion_days is None:
        return {}
    now = datetime.now(timezone.utc)
    return {
        "time_of_deletion": min(
            now + timedelta(days=deletion_days) + DELETION_SCHEDULE_MARGIN,
            now + timedelta(days=max_days),
        )
    }


def secret_content_to_bytes(content, encoding):
    """Return the raw bytes of secret content supplied in ``encoding``.

    Args:
        content: The secret content as text or as a base64 string.
        encoding: ``text`` or ``base64``.

    Returns:
        The decoded content bytes.
    """
    if encoding == "base64":
        return base64.b64decode(content)
    return content.encode("utf-8")


def encode_secret_content(content, encoding):
    """Return secret content as the base64 string OCI stores.

    Args:
        content: The secret content as text or as a base64 string.
        encoding: ``text`` or ``base64``.

    Returns:
        The base64-encoded content.
    """
    return base64.b64encode(secret_content_to_bytes(content, encoding)).decode("ascii")


def decode_secret_content(module, content, encoding):
    """Return base64 content from a secret bundle in ``encoding``.

    Args:
        module: The active Ansible module, used to report undecodable text.
        content: The base64 content of a secret bundle.
        encoding: ``text`` or ``base64``.

    Returns:
        The content as UTF-8 text, or unchanged when ``encoding`` is
        ``base64``.
    """
    if encoding == "base64":
        return content
    try:
        return base64.b64decode(content).decode("utf-8")
    except UnicodeDecodeError:
        module.fail_json(
            msg="Secret content is not valid UTF-8 text; use content_encoding=base64"
        )


class OciSecretBundleMixin:
    """Read secret content, which the Vault management API never returns.

    Secret content is only served by ``SecretsClient.get_secret_bundle``,
    which needs the ``read secret-bundles`` permission, so the client is
    created only when content is actually read.
    """

    _secrets_client = None

    @property
    def secrets_client(self):
        """Return the lazily created secret retrieval client.

        Returns:
            An ``oci.secrets.SecretsClient``.
        """
        if self._secrets_client is None:
            self._secrets_client = create_service_client(
                self.module, oci.secrets.SecretsClient
            )
        return self._secrets_client

    def get_secret_bundle_content(self, secret_id, **selector):
        """Return the base64 content of one secret version.

        Args:
            secret_id: The OCID of the secret.
            **selector: ``stage`` or ``version_number`` passed to
                ``get_secret_bundle``; the ``CURRENT`` version when empty.

        Returns:
            The base64 content, or None when no version matches the selector.
        """
        try:
            response = self.call_with_retry(
                self.secrets_client.get_secret_bundle,
                secret_id=secret_id,
                **selector,
            )
        except Exception as exc:
            if getattr(exc, "status", None) == 404:
                return None
            raise
        return response.data.secret_bundle_content.content


class OciSecretContentInfoMixin(OciSecretBundleMixin):
    """Attach secret content to info module results when requested.

    Concrete adapters implement :meth:`content_request` to say which secret
    version, if any, can be read for each listed resource.
    """

    def content_request(self, resource):
        """Return the bundle lookup for ``resource``, or None when unreadable.

        Args:
            resource: One resource returned by ``fetch_resources``.

        Returns:
            A ``(secret_id, selector)`` tuple for ``get_secret_bundle_content``,
            or None to report no content for the resource.

        Raises:
            NotImplementedError: When the concrete adapter does not implement it.
        """
        raise NotImplementedError(
            f"{type(self).__name__} must define content_request()"
        )

    def fetch_contents(self, resources):
        """Read the content of every readable resource in parallel.

        Args:
            resources: The resources returned by ``fetch_resources``.

        Returns:
            The content of each resource in ``content_encoding``, in input
            order, with None for resources that are unreadable or have no
            matching version.
        """
        requests = [self.content_request(resource) for resource in resources]
        readable = [request for request in requests if request is not None]
        if readable:
            # Create the lazy client once so the workers share it.
            self.secrets_client
        encoded_contents = iter(
            threaded_map(
                lambda request: self.get_secret_bundle_content(
                    request[0], **request[1]
                ),
                readable,
            )
        )
        encoding = self.module.params["content_encoding"]
        contents = []
        for request in requests:
            content = None if request is None else next(encoded_contents)
            contents.append(
                None
                if content is None
                else decode_secret_content(self.module, content, encoding)
            )
        return contents

    def execute_info_module(self):
        """Exit with the serialized resources, adding content when requested.

        The inherited implementation serializes each resource on its own, but
        secret content is not part of the resource model and is fetched for
        all resources in parallel, so it is attached after serialization.
        """
        resources = self.fetch_resources()
        results = [self.serialize_result_resource(resource) for resource in resources]
        if self.module.params["include_content"]:
            for result, content in zip(results, self.fetch_contents(resources)):
                result["content"] = content
        self.module.exit_json(changed=False, **{self.results_key: results})
