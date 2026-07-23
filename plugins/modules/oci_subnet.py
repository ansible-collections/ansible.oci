"""Manage OCI Subnets."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.oracle.oci.plugins.module_utils.oci_common import (
    DEAD_STATES,
    LIFECYCLE_AVAILABLE,
    OCI_COMMON_ARGS,
    filter_none_values,
    to_dict as serialize_resource_dict,
)
from ansible_collections.oracle.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
)
from ansible_collections.oracle.oci.plugins.module_utils.oci_wait import (
    call_with_retry,
    wait_for_resource,
)

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
      - Required for update and delete operations.
      - Must be omitted for create operations.
    type: str
  display_name:
    description:
      - Human-readable name for the subnet.
      - Required when creating a subnet.
      - Not used to identify existing subnets for update or delete operations.
      - Re-running create without C(subnet_id) can create additional subnets
        because OCI display names are not unique.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the subnet.
      - Required when creating a subnet.
      - The module does not move an existing subnet to another compartment.
    type: str
  vcn_id:
    description:
      - The OCID of the VCN containing the subnet.
      - Required when creating a subnet.
      - The module does not support moving an existing subnet to another VCN.
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
    display_name: example-subnet
    dns_label: examplesubnet
    route_table_id: ocid1.routetable.oc1..example
    security_list_ids:
      - ocid1.securitylist.oc1..example
  register: created_subnet

- name: Update the created subnet display name and route table
  oracle.oci.oci_subnet:
    state: present
    subnet_id: "{{ created_subnet.resource.id }}"
    display_name: example-subnet-updated
    route_table_id: ocid1.routetable.oc1..updated

- name: Delete the created subnet
  oracle.oci.oci_subnet:
    state: absent
    subnet_id: "{{ created_subnet.resource.id }}"
"""

RETURN = r"""
resource:
  description: The subnet resource.
  returned: when state != absent
  type: dict
"""

try:
    import oci
    from oci.exceptions import ServiceError

    HAS_OCI_SDK = True
except ImportError:
    HAS_OCI_SDK = False
    ServiceError = None
    oci = None

CREATE_REQUIRED_FIELDS = (
    "compartment_id",
    "vcn_id",
    "cidr_block",
    "display_name",
)
WAIT_FOR_SUBNET_STATES = (LIFECYCLE_AVAILABLE,)


def build_create_subnet_details(params):
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "vcn_id": params.get("vcn_id"),
            "cidr_block": params.get("cidr_block"),
            "display_name": params.get("display_name"),
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


def build_update_subnet_details(params):
    details = filter_none_values(
        {
            "display_name": params.get("display_name"),
            "cidr_block": params.get("cidr_block"),
            "route_table_id": params.get("route_table_id"),
            "security_list_ids": params.get("security_list_ids"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.core.models.UpdateSubnetDetails(**details)


class OciSubnetModule(OciResourceBase):
    """Concrete resource adapter for OCI subnets."""

    client_class = oci.core.VirtualNetworkClient if HAS_OCI_SDK else object()
    resource_id_param = "subnet_id"
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "subnet"

    def _get_subnet_response(self, subnet_id):
        return call_with_retry(
            self.client.get_subnet,
            subnet_id=subnet_id,
        )

    def _get_subnet_by_id(self, subnet_id):
        try:
            return self._get_subnet_response(subnet_id).data
        except ServiceError as exc:
            if exc.status == 404:
                return None
            raise

    def get_resource(self):
        subnet_id = self.module.params.get("subnet_id")
        if not subnet_id:
            return None
        return self._get_subnet_by_id(subnet_id)

    def create_resource(self):
        create_subnet_details = build_create_subnet_details(self.module.params)
        response = call_with_retry(
            self.client.create_subnet,
            create_subnet_details=create_subnet_details,
        )
        if not self.module.params.get("wait", True):
            return response.data

        subnet_id = getattr(response.data, "id", None)
        if not subnet_id:
            return response.data
        return wait_for_resource(
            self.module,
            self.client,
            self._get_subnet_response,
            subnet_id,
            WAIT_FOR_SUBNET_STATES,
        )

    def update_resource(self, resource):
        update_subnet_details = build_update_subnet_details(self.module.params)
        response = call_with_retry(
            self.client.update_subnet,
            subnet_id=resource.id,
            update_subnet_details=update_subnet_details,
        )
        if not self.module.params.get("wait", True):
            return response.data
        return wait_for_resource(
            self.module,
            self.client,
            self._get_subnet_response,
            resource.id,
            WAIT_FOR_SUBNET_STATES,
        )

    def delete_resource(self, resource):
        try:
            response = call_with_retry(
                self.client.delete_subnet,
                subnet_id=resource.id,
            )
        except ServiceError as exc:
            if exc.status == 409:
                self.module.fail_json(
                    msg=(
                        f"Cannot delete subnet {resource.id} while dependent resources "
                        f"exist: {exc}"
                    )
                )
            raise

        if not self.module.params.get("wait", True):
            return response.data
        return wait_for_resource(
            self.module,
            self.client,
            self._get_subnet_response,
            resource.id,
            tuple(DEAD_STATES),
        )

    def _fail_immutable_field_change(self, field_name, reason=None):
        message = f"Updating {field_name} for an existing subnet is not supported"
        if reason:
            message += f" because {reason}"
        message += " by oci_subnet."
        self.module.fail_json(msg=message)

    def needs_update(self, resource) -> bool:
        resource_dict = serialize_resource_dict(resource)

        desired_cidr_block = self.module.params.get("cidr_block")
        cidr_block_needs_update = (
            desired_cidr_block is not None
            and resource_dict.get("cidr_block") != desired_cidr_block
        )

        desired_dns_label = self.module.params.get("dns_label")
        if desired_dns_label is not None and resource_dict.get("dns_label") != desired_dns_label:
            self._fail_immutable_field_change(
                "dns_label",
                "OCI treats dns_label as immutable after create",
            )

        desired_availability_domain = self.module.params.get("availability_domain")
        if (
            desired_availability_domain is not None
            and resource_dict.get("availability_domain") != desired_availability_domain
        ):
            self._fail_immutable_field_change("availability_domain")

        desired_vcn_id = self.module.params.get("vcn_id")
        if desired_vcn_id is not None and resource_dict.get("vcn_id") != desired_vcn_id:
            self._fail_immutable_field_change("vcn_id")

        desired_compartment_id = self.module.params.get("compartment_id")
        if (
            desired_compartment_id is not None
            and resource_dict.get("compartment_id") != desired_compartment_id
        ):
            self._fail_immutable_field_change("compartment_id")

        desired_prohibit_public_ip = self.module.params.get("prohibit_public_ip_on_vnic")
        if (
            desired_prohibit_public_ip is not None
            and resource_dict.get("prohibit_public_ip_on_vnic")
            != desired_prohibit_public_ip
        ):
            self._fail_immutable_field_change("prohibit_public_ip_on_vnic")

        if cidr_block_needs_update:
            return True

        desired_display_name = self.module.params.get("display_name")
        if desired_display_name is not None and resource_dict.get("display_name") != desired_display_name:
            return True

        desired_route_table_id = self.module.params.get("route_table_id")
        if desired_route_table_id is not None and resource_dict.get("route_table_id") != desired_route_table_id:
            return True

        desired_security_list_ids = self.module.params.get("security_list_ids")
        if desired_security_list_ids is not None:
            current_security_list_ids = resource_dict.get("security_list_ids") or []
            if sorted(current_security_list_ids) != sorted(desired_security_list_ids):
                return True

        return False

    def user_known_fields(self):
        return ("display_name",)


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        subnet_id=dict(type="str"),
        display_name=dict(type="str"),
        compartment_id=dict(type="str"),
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

    OciSubnetModule(module).run()


if __name__ == "__main__":
    main()
