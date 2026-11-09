# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_instance_capacity_reservation
short_description: Manage an OCI compute capacity reservation
description:
  - Create, update, and delete an OCI compute capacity reservation.
version_added: "1.3.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_name_lookup_options
  - ansible.oci.oci_wait_options
  - ansible.oci.oci_tags_options
options:
  state:
    description:
      - The desired state of the capacity reservation.
    type: str
    choices: [present, absent]
    default: present
  capacity_reservation_id:
    description:
      - The OCID of the capacity reservation.
    type: str
  name:
    description:
      - The display name of the capacity reservation.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment for the reservation.
      - Required when the module creates a reservation.
      - The module does not support compartment moves.
    type: str
  availability_domain:
    description:
      - The availability domain for the reservation.
      - Required when the module creates a reservation.
    type: str
  is_default_reservation:
    description:
      - Whether this reservation is the default reservation.
      - OCI allows one default reservation in each root compartment and availability domain.
    type: bool
  instance_reservation_configs:
    description:
      - Instance shape configurations and reserved counts for the reservation.
      - This list replaces all existing configurations when set.
      - Set this value to an empty list to clear all configurations.
      - Omit this value to keep existing configurations during an update.
      - At least one configuration is required when the module creates a reservation.
      - OCI can reserve less capacity than requested when capacity is unavailable.
    type: list
    elements: dict
    suboptions:
      instance_shape:
        description:
          - The instance shape name.
        type: str
        required: true
      reserved_count:
        description:
          - The number of instances to reserve.
        type: int
        required: true
      instance_shape_config:
        description:
          - The flexible shape configuration.
        type: dict
        suboptions:
          ocpus:
            description:
              - The number of OCPUs.
            type: float
          memory_in_gbs:
            description:
              - The memory amount in GB.
            type: float
      fault_domain:
        description:
          - The fault domain for the reserved instances.
          - Omit this value to reserve capacity without a specified fault domain.
          - To change the fault domain, delete the reservation and create a new reservation.
        type: str
      cluster_placement_group_id:
        description:
          - The OCID of the cluster placement group.
        type: str
      cluster_config:
        description:
          - The HPC cluster configuration.
        type: dict
        suboptions:
          hpc_island_id:
            description:
              - The HPC island identifier.
            type: str
            required: true
          network_block_ids:
            description:
              - The network block identifiers.
            type: list
            elements: str
"""

EXAMPLES = r"""
- name: Create a capacity reservation
  ansible.oci.oci_instance_capacity_reservation:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    name: reserved-compute
    instance_reservation_configs:
      - instance_shape: VM.Standard.E5.Flex
        reserved_count: 2
        instance_shape_config:
          ocpus: 2
          memory_in_gbs: 16

- name: Update a capacity reservation
  ansible.oci.oci_instance_capacity_reservation:
    capacity_reservation_id: ocid1.computecapacityreservation.oc1..example
    is_default_reservation: true
    wait: true

- name: Delete a capacity reservation
  ansible.oci.oci_instance_capacity_reservation:
    capacity_reservation_id: ocid1.computecapacityreservation.oc1..example
    state: absent
"""

RETURN = r"""
resource:
  description: The capacity reservation resource.
  returned: when state is present
  type: dict
  contains:
    id:
      description: The capacity reservation OCID.
      type: str
    name:
      description: The reservation display name.
      type: str
    compartment_id:
      description: The reservation compartment OCID.
      type: str
    availability_domain:
      description: The reservation availability domain.
      type: str
    lifecycle_state:
      description: The reservation lifecycle state.
      type: str
    is_default_reservation:
      description: Whether this is the default reservation.
      type: bool
    instance_reservation_configs:
      description: Shape configurations and reserved and used counts.
      type: list
      elements: dict
      contains:
        instance_shape:
          description: The instance shape name.
          type: str
        instance_shape_config:
          description: The flexible shape configuration.
          type: dict
          contains:
            ocpus:
              description: The number of OCPUs.
              type: float
            memory_in_gbs:
              description: The memory amount in GB.
              type: float
        fault_domain:
          description: The fault domain for the reserved instances.
          type: str
        cluster_placement_group_id:
          description: The cluster placement group OCID.
          type: str
        cluster_config:
          description: The HPC cluster configuration.
          type: dict
          contains:
            hpc_island_id:
              description: The HPC island identifier.
              type: str
            network_block_ids:
              description: The network block identifiers.
              type: list
              elements: str
        reserved_count:
          description: The requested instance count.
          type: int
        used_count:
          description: The number of instances in use.
          type: int
    reserved_instance_count:
      description: The total number of reserved instances.
      type: int
    used_instance_count:
      description: The total number of used reserved instances.
      type: int
    freeform_tags:
      description: Free-form tags assigned to the reservation.
      type: dict
    defined_tags:
      description: Defined tags assigned to the reservation.
      type: dict
    time_created:
      description: The time when OCI created the reservation.
      type: str
    time_updated:
      description: The time when OCI last updated the reservation.
      type: str
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_auth import create_service_client
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_ACTIVE,
    LIFECYCLE_DELETED,
    OCI_COMMON_ARGS,
    build_model,
    import_oci_sdk,
    match_unordered_subset_list,
    serialize_oci_model,
    values_differ_as_subset,
    values_differ_as_unordered_subset_list,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

oci = import_oci_sdk()[0]

WAIT_FOR_CAPACITY_RESERVATION_STATES = (LIFECYCLE_ACTIVE,)


def reservation_config_differs(current, desired):
    """Compare fault domains exactly and other requested fields as subsets."""
    return (
        current.get("fault_domain") != desired.get("fault_domain")
        or values_differ_as_subset(current, desired)
    )


def build_instance_reservation_config(config):
    """Build one SDK reservation configuration from module input.

    Args:
        config: One reservation configuration supplied by the caller.

    Returns:
        An OCI InstanceReservationConfigDetails model.
    """
    details = dict(config)
    details["instance_shape_config"] = build_model(
        details.get("instance_shape_config"),
        oci.core.models.InstanceReservationShapeConfigDetails,
    )
    details["cluster_config"] = build_model(
        details.get("cluster_config"), oci.core.models.ClusterConfigDetails
    )
    return build_model(details, oci.core.models.InstanceReservationConfigDetails)


def build_capacity_reservation_details(params, model_class):
    """Build create or update details for a capacity reservation.

    Args:
        params: Module parameters or planned update fields.
        model_class: OCI create or update details model class.

    Returns:
        An OCI capacity reservation details model.
    """
    fields = dict(params)
    configs = fields.get("instance_reservation_configs")
    if configs is not None:
        fields["instance_reservation_configs"] = [
            build_instance_reservation_config(item) for item in configs
        ]
    return build_model(fields, model_class)


class OciComputeCapacityReservationModule(OciResourceBase):
    """Manage one OCI compute capacity reservation."""

    @property
    def client_class(self):
        """Return the OCI compute client class."""
        return oci.core.ComputeClient

    resource_id_param = "capacity_reservation_id"
    list_resource_method = "list_compute_capacity_reservations"
    create_resource_name = "compute capacity reservation"
    create_required_fields = (
        "compartment_id",
        "availability_domain",
        "instance_reservation_configs",
    )
    update_method_name = "update_compute_capacity_reservation"
    update_details_name = "update_compute_capacity_reservation_details"
    update_wait_states = WAIT_FOR_CAPACITY_RESERVATION_STATES
    update_field_specs = (
        UpdateFieldSpec(param_name="name", resource_field="display_name", is_mutable=True),
        UpdateFieldSpec(param_name="is_default_reservation", is_mutable=True),
        UpdateFieldSpec(param_name="instance_reservation_configs", is_mutable=True, compare="reservation_configs"),
        UpdateFieldSpec(param_name="compartment_id", is_mutable=False, immutable_reason="this module does not support compartment moves"),
        UpdateFieldSpec(param_name="availability_domain", is_mutable=False, immutable_reason="OCI does not support changing the availability domain"),
    )

    def __init__(self, module):
        """Set up the compute and work request clients for this run.

        Args:
            module: The active Ansible module instance.
        """
        super().__init__(module)
        self.work_request_client = create_service_client(
            module, oci.work_requests.WorkRequestClient
        )

    def compare_update_field_values(self, current_value, desired_value, compare=None):
        """Apply reservation placement rules through the shared list matcher."""
        if compare == "reservation_configs":
            return values_differ_as_unordered_subset_list(
                current_value, desired_value, reservation_config_differs
            )
        return super().compare_update_field_values(current_value, desired_value, compare)

    def build_update_plan(self, resource):
        """Reject fault-domain replacements before any update operation."""
        plan = super().build_update_plan(resource)
        if "instance_reservation_configs" not in plan["update_model_fields"]:
            return plan
        current = serialize_oci_model(resource).get("instance_reservation_configs") or []
        desired = self.module.params["instance_reservation_configs"]
        current_identity = [{key: value for key, value in item.items() if key != "reserved_count"} for item in current]
        desired_identity = [{key: value for key, value in item.items() if key != "reserved_count"} for item in desired]
        retained = match_unordered_subset_list(current_identity, desired_identity, reservation_config_differs)
        unmatched_current = [item for index, item in enumerate(current_identity) if index not in retained.values()]
        unmatched_desired = [item for index, item in enumerate(desired_identity) if index not in retained]
        for wanted in unmatched_desired:
            without_domain = {key: value for key, value in wanted.items() if key != "fault_domain"}
            if any(
                item.get("fault_domain") != wanted.get("fault_domain")
                and not values_differ_as_subset(item, without_domain)
                for item in unmatched_current
            ):
                self.module.fail_json(
                    msg="Changing instance_reservation_configs.fault_domain requires deleting the reservation "
                    "and creating a new reservation. This includes removing a specified fault domain."
                )
        return plan

    def get_resource_response(self, resource_id):
        """Fetch one capacity reservation by OCID.

        Args:
            resource_id: The capacity reservation OCID.

        Returns:
            The OCI SDK response.
        """
        return self.call_with_retry(
            self.client.get_compute_capacity_reservation,
            capacity_reservation_id=resource_id,
        )

    def validate_create_request(self):
        """Require a non-empty configuration list for reservation creation.

        The OCI API rejects create requests with an empty configuration list.
        The shared validator checks for an unset value but permits an empty list.
        """
        super().validate_create_request()
        if not self.module.params.get("instance_reservation_configs"):
            self.module.fail_json(
                msg="Creating a compute capacity reservation requires at least one instance_reservation_configs item."
            )

    def hydrate_named_resource(self, resource):
        """Fetch full reservation data because the list API returns summaries.

        Args:
            resource: The summary model returned by the list operation.

        Returns:
            The full resource model when the get call succeeds.
        """
        return self.get_resource_by_id(resource.id) or resource

    def wait_for_reservation_work_request(self, response, resource_id, target_states):
        """Wait for the mutation work request and resource lifecycle.

        Args:
            response: The OCI mutation response.
            resource_id: The capacity reservation OCID.
            target_states: The resource lifecycle states that complete the wait.

        Returns:
            The refreshed reservation when waiting is enabled.
        """
        if not self.module.params.get("wait", True):
            return self.get_resource_by_id(resource_id) or response.data
        work_request_id = response.headers.get("opc-work-request-id")
        if work_request_id:
            self.wait_for_work_request(self.work_request_client, work_request_id)
        return self.wait_for_resource_id(resource_id, target_states)

    def create_resource(self):
        """Create a capacity reservation and wait for its work request.

        Returns:
            The created reservation model.
        """
        details = build_capacity_reservation_details(
            {
                "compartment_id": self.module.params.get("compartment_id"),
                "availability_domain": self.module.params.get("availability_domain"),
                "display_name": self.module.params.get("name"),
                "is_default_reservation": self.module.params.get("is_default_reservation"),
                "instance_reservation_configs": self.module.params.get("instance_reservation_configs"),
                "freeform_tags": self.module.params.get("freeform_tags"),
                "defined_tags": self.module.params.get("defined_tags"),
            },
            oci.core.models.CreateComputeCapacityReservationDetails,
        )
        response = self.call_with_retry(
            self.client.create_compute_capacity_reservation,
            create_compute_capacity_reservation_details=details,
        )
        return self.wait_for_reservation_work_request(
            response, response.data.id, WAIT_FOR_CAPACITY_RESERVATION_STATES
        )

    def build_update_details(self, update_model_fields):
        """Build the SDK update details model.

        Args:
            update_model_fields: Fields selected by the shared update planner.

        Returns:
            An OCI update details model.
        """
        return build_capacity_reservation_details(
            update_model_fields,
            oci.core.models.UpdateComputeCapacityReservationDetails,
        )

    def get_update_result(self, response, resource_id):
        """Wait for asynchronous update work and return the refreshed resource.

        The shared update result handler only waits on resource lifecycle state.
        This API also returns a work request ID, so this override waits for it first.

        Args:
            response: The OCI response from the update operation.
            resource_id: The capacity reservation OCID.

        Returns:
            The updated reservation model.
        """
        return self.wait_for_reservation_work_request(
            response, resource_id, WAIT_FOR_CAPACITY_RESERVATION_STATES
        )

    def delete_resource(self, resource):
        """Delete a capacity reservation and wait for its work request.

        Args:
            resource: The capacity reservation model to delete.

        Returns:
            The final reservation model or None after deletion.
        """
        response = self.call_delete_fn(
            resource,
            self.client.delete_compute_capacity_reservation,
            capacity_reservation_id=resource.id,
        )
        if not self.module.params.get("wait", True):
            return response.data
        return self.wait_for_reservation_work_request(
            response, resource.id, (LIFECYCLE_DELETED,)
        )


def main():
    """Run the capacity reservation resource module."""
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        capacity_reservation_id=dict(type="str"),
        availability_domain=dict(type="str"),
        is_default_reservation=dict(type="bool"),
        instance_reservation_configs=dict(
            type="list", elements="dict", options=dict(
                instance_shape=dict(type="str", required=True),
                reserved_count=dict(type="int", required=True),
                instance_shape_config=dict(type="dict", options=dict(
                    ocpus=dict(type="float"), memory_in_gbs=dict(type="float")
                )),
                fault_domain=dict(type="str"),
                cluster_placement_group_id=dict(type="str"),
                cluster_config=dict(type="dict", options=dict(
                    hpc_island_id=dict(type="str", required=True),
                    network_block_ids=dict(type="list", elements="str"),
                )),
            ),
        ),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    OciComputeCapacityReservationModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
