"""Shared helpers for Network Firewall resource operations."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
)


class OciNetworkFirewallResourceBase(OciResourceBase):
    """Handle work requests for Network Firewalls and their policies."""

    def get_update_result(self, response, resource_id):
        """Return the resource after the update and configured wait.

        Args:
            response: The complete OCI response from the update operation.
            resource_id: The OCID of the resource.

        Returns:
            The refreshed resource, immediate response data, or resource ID.
        """
        return self._wait_for_mutation(response, resource_id)

    def _wait_for_mutation(self, response, resource_id, deleting=False):
        """Wait for an operation and return its resource.

        Args:
            response: The complete OCI response from the operation.
            resource_id: The OCID of the resource.
            deleting: Whether the operation deletes the resource.

        Returns:
            The refreshed resource, immediate response data, or resource ID.
        """
        if not self.module.params.get("wait", True):
            return response.data or {"id": resource_id}
        work_request_id = getattr(response, "headers", {}).get("opc-work-request-id")
        if work_request_id:
            self.wait_for_work_request(self.client, work_request_id)
            if deleting:
                return response.data or {"id": resource_id}
            return self.get_resource_by_id(resource_id)
        return self.get_mutation_result(
            response.data,
            resource_id,
            tuple(self.dead_states) if deleting else self.update_wait_states,
        )
