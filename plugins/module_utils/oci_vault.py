"""Helpers shared by OCI Vault key management resource and info modules."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

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
