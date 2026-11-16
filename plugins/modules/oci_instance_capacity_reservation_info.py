# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_instance_capacity_reservation_info
short_description: Get OCI compute capacity reservation information
description:
  - Get one or more OCI compute capacity reservations.
version_added: "1.3.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_info_filter_options
options:
  capacity_reservation_id:
    description:
      - The OCID of one capacity reservation to get.
      - A get by OCID returns full details, including instance reservation configurations.
      - A list query returns capacity reservation summaries.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment to list.
      - This value is required when C(capacity_reservation_id) is not set.
    type: str
  availability_domain:
    description:
      - Filter results by availability domain.
    type: str
  name:
    description:
      - Filter results by display name.
    type: str
  lifecycle_state:
    description:
      - Filter results by lifecycle state.
    type: str
    choices: [active, creating, updating, moving, deleted, deleting]
"""

EXAMPLES = r"""
- name: List capacity reservations in a compartment
  ansible.oci.oci_instance_capacity_reservation_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List active reservations by name and availability domain
  ansible.oci.oci_instance_capacity_reservation_info:
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    name: reserved-compute
    lifecycle_state: active

- name: Get one capacity reservation
  ansible.oci.oci_instance_capacity_reservation_info:
    capacity_reservation_id: ocid1.computecapacityreservation.oc1..example
"""

RETURN = r"""
capacity_reservations:
  description: Capacity reservations that match the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The reservation OCID.
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
      description: Whether the reservation is the default reservation.
      type: bool
    reserved_instance_count:
      description: The total number of reserved instances.
      type: int
    used_instance_count:
      description: The total number of used reserved instances.
      type: int
    instance_reservation_configs:
      description: Full instance reservation configurations returned by a get by OCID.
      returned: when capacity_reservation_id is supplied
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
          description: The actual number of instances reserved for this configuration.
          type: int
        used_count:
          description: The number of instances in use.
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

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
    normalize_choice_parameters,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

oci = import_oci_sdk()[0]


class OciComputeCapacityReservationInfoModule(OciInfoBase):
    """Get one or more OCI compute capacity reservations."""

    @property
    def client_class(self):
        """Return the OCI compute client class."""
        return oci.core.ComputeClient

    results_key = "capacity_reservations"
    resource_id_param = "capacity_reservation_id"
    resource_get_method = "get_compute_capacity_reservation"
    list_resource_method = "list_compute_capacity_reservations"
    list_filter_params = ("compartment_id", "availability_domain", "lifecycle_state")


def main():
    """Run the capacity reservation info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        capacity_reservation_id=dict(type="str"),
        compartment_id=dict(type="str"),
        availability_domain=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(
            type="str",
            choices=["active", "creating", "updating", "moving", "deleted", "deleting"],
        ),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "capacity_reservation_id"]],
    )
    normalize_choice_parameters(
        module,
        {
            ("lifecycle_state",): {
                "active": "ACTIVE",
                "creating": "CREATING",
                "updating": "UPDATING",
                "moving": "MOVING",
                "deleted": "DELETED",
                "deleting": "DELETING",
            }
        },
    )
    OciComputeCapacityReservationInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
