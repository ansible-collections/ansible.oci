# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_subnet
short_description: Manage a Subnet resource in Oracle Cloud Infrastructure
description:
  - Create, update, and delete OCI subnets.
  - Uses the shared OCI helper layer for authentication, waiting, retry
    behavior, and result shaping.
  - Create requests must omit C(subnet_id). After create, capture the returned
    subnet ID and use it for later C(state=present) and C(state=absent) tasks.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - oracle.oci.oci_auth_options
  - oracle.oci.oci_name_lookup_options
  - oracle.oci.oci_wait_options
  - oracle.oci.oci_tags_options
options:
  state:
    description:
      - The desired lifecycle state of the subnet.
    type: str
    choices: [present, absent]
    default: present
  subnet_id:
    description:
      - The OCID of the subnet.
      - When provided, the module manages this exact subnet.
      - Required to distinguish between multiple subnets that share the same
        scoped C(name).
    type: str
  name:
    description:
      - Human-readable name for the subnet.
      - Required when creating a subnet.
      - When C(subnet_id) is omitted, the module uses
        C(compartment_id + vcn_id + name) to find an existing subnet.
      - If exactly one subnet matches, C(state=present) manages it as the
        update target and C(state=absent) deletes it.
      - If more than one subnet matches, the task fails and the caller must
        supply C(subnet_id).
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the subnet.
      - Required when creating a subnet.
      - The module does not move an existing subnet to another compartment.
      - Also scopes name-based subnet lookups when C(subnet_id) is omitted.
    type: str
  vcn_id:
    description:
      - The OCID of the VCN containing the subnet.
      - Required when creating a subnet.
      - The module does not support moving an existing subnet to another VCN.
      - Also scopes name-based subnet lookups when C(subnet_id) is omitted.
    type: str
  cidr_block:
    description:
      - The IPv4 CIDR block for the subnet.
      - Required when creating a subnet.
      - Supports valid OCI subnet CIDR block updates after create.
      - OCI enforces additional constraints on subnet CIDR changes.
    type: str
  dns_label:
    description:
      - The DNS label for the subnet.
      - The OCI API treats this as create-time only.
    type: str
  availability_domain:
    description:
      - The availability domain for an AD-specific subnet.
      - Omit this value to create a regional subnet.
      - The module does not update this field after create.
    type: str
  route_table_id:
    description:
      - The OCID of the route table the subnet should use.
    type: str
  security_list_ids:
    description:
      - The OCIDs of the security lists associated with the subnet.
      - When updated, this replaces the subnet's current security list set.
    type: list
    elements: str
  prohibit_public_ip_on_vnic:
    description:
      - Whether VNICs created in this subnet must not have public IP addresses.
      - The module does not update this field after create.
    type: bool
"""

EXAMPLES = r"""
- name: Create a subnet
  oracle.oci.oci_subnet:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    cidr_block: 10.0.1.0/24
    name: example-subnet
    dns_label: examplesubnet
    route_table_id: ocid1.routetable.oc1..example
    security_list_ids:
      - ocid1.securitylist.oc1..example
  register: created_subnet

- name: Reconcile a uniquely named subnet by name
  oracle.oci.oci_subnet:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    cidr_block: 10.0.1.0/24
    name: example-subnet
    route_table_id: ocid1.routetable.oc1..updated

- name: Intentionally create a second subnet with the same display name
  oracle.oci.oci_subnet:
    state: present
    allow_duplicate_name: true
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    cidr_block: 10.0.2.0/24
    name: example-subnet
    dns_label: examplesubnetcopy

- name: Delete the created subnet
  oracle.oci.oci_subnet:
    state: absent
    subnet_id: "{{ created_subnet.resource.id }}"

- name: Delete a uniquely named subnet without providing subnet_id
  oracle.oci.oci_subnet:
    state: absent
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-subnet
"""

RETURN = r"""
resource:
  description: The subnet resource.
  returned: when state != absent
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.oracle.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_AVAILABLE,
    OCI_COMMON_ARGS,
    filter_none_values,
    import_oci_sdk,
)
from ansible_collections.oracle.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]

CREATE_REQUIRED_FIELDS = [
    "compartment_id",
    "vcn_id",
    "cidr_block",
    "name",
]
WAIT_FOR_SUBNET_STATES = [LIFECYCLE_AVAILABLE]


def build_create_subnet_details(params):
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "vcn_id": params.get("vcn_id"),
            "cidr_block": params.get("cidr_block"),
            "display_name": params.get("name"),
            "dns_label": params.get("dns_label"),
            "availability_domain": params.get("availability_domain"),
            "route_table_id": params.get("route_table_id"),
            "security_list_ids": params.get("security_list_ids"),
            "prohibit_public_ip_on_vnic": params.get("prohibit_public_ip_on_vnic"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.core.models.CreateSubnetDetails(**details)


class OciSubnetModule(OciResourceBase):
    """Concrete resource adapter for OCI subnets."""

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    resource_id_param = "subnet_id"
    list_resource_method = "list_subnets"
    list_filter_params = ("vcn_id",)
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "subnet"
    update_method_name = "update_subnet"
    update_details_name = "update_subnet_details"
    update_wait_states = WAIT_FOR_SUBNET_STATES
    update_field_specs = [
        {
            "param_name": "cidr_block",
            "resource_field": "cidr_block",
            "update_field": "cidr_block",
            "is_mutable": True,
        },
        {
            "param_name": "name",
            "resource_field": "display_name",
            "update_field": "display_name",
            "is_mutable": True,
        },
        {
            "param_name": "route_table_id",
            "resource_field": "route_table_id",
            "update_field": "route_table_id",
            "is_mutable": True,
        },
        {
            "param_name": "security_list_ids",
            "resource_field": "security_list_ids",
            "update_field": "security_list_ids",
            "is_mutable": True,
            "compare": "sorted_list",
        },
        {
            "param_name": "dns_label",
            "resource_field": "dns_label",
            "is_mutable": False,
            "immutable_reason": "OCI treats dns_label as immutable after create",
        },
        {
            "param_name": "availability_domain",
            "resource_field": "availability_domain",
            "is_mutable": False,
        },
        {
            "param_name": "vcn_id",
            "resource_field": "vcn_id",
            "is_mutable": False,
        },
        {
            "param_name": "compartment_id",
            "resource_field": "compartment_id",
            "is_mutable": False,
        },
        {
            "param_name": "prohibit_public_ip_on_vnic",
            "resource_field": "prohibit_public_ip_on_vnic",
            "is_mutable": False,
        },
    ]

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_subnet,
            subnet_id=resource_id,
        )

    def create_resource(self):
        create_subnet_details = build_create_subnet_details(self.module.params)
        response = self.call_with_retry(
            self.client.create_subnet,
            create_subnet_details=create_subnet_details,
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_SUBNET_STATES,
        )

    def build_update_details(self, update_model_fields):
        return oci.core.models.UpdateSubnetDetails(**update_model_fields)

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_subnet,
            subnet_id=resource.id,
        )


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        subnet_id=dict(type="str"),
        vcn_id=dict(type="str"),
        cidr_block=dict(type="str"),
        dns_label=dict(type="str"),
        availability_domain=dict(type="str"),
        route_table_id=dict(type="str"),
        security_list_ids=dict(type="list", elements="str"),
        prohibit_public_ip_on_vnic=dict(type="bool"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    # check_mode is honored by execute_resource_module via the shared helper layer
    OciSubnetModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
