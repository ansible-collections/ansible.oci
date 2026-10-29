"""Shared Autonomous Database helpers for OCI modules."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
)

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    import_oci_sdk,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]


class OciADBBase(OciResourceBase):

    @property
    def client_class(self):
        return oci.database.DatabaseClient

    resource_id_param = "autonomous_database_id"
    list_resource_method = "list_autonomous_databases"
    update_method_name = "update_autonomous_database"
    update_details_name = "update_autonomous_database_details"

    def get_resource_response(self, resource_id):
        """Return the raw OCI get-response wrapper for one ADB.

        Args:
            resource_id: The OCID of the DB.

        Returns:
            The OCI SDK response whose ``data`` is the ``AutonomousDatabase``.
        """
        return self.call_with_retry(
            self.client.get_autonomous_database,
            autonomous_database_id=resource_id,
        )

    def build_update_details(self, update_model_fields):
        """Build the OCI update-details model from planned field changes.

        Args:
            update_model_fields: The fields the shared planner marked as changed.

        Returns:
            A populated ``UpdateAutonomousDatabaseDetails`` model.
        """
        return oci.database.models.UpdateAutonomousDatabaseDetails(
            **update_model_fields
        )

    def delete_resource(self, resource):
        """Terminate the Autonomous Database and wait for a terminal state.

        Args:
            resource: The current ``AutonomousDatabase`` model to terminate.

        Returns:
            The terminated resource model, or the raw response when waiting is
            disabled.
        """
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_autonomous_database,
            autonomous_database_id=self.get_resource_ocid(resource),
        )
