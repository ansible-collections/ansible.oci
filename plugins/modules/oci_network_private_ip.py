# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_network_private_ip
short_description: Manage a Private IP resource in Oracle Cloud Infrastructure
description:
  - Create, update, and delete secondary OCI private IP resources.
  - A private IP can be assigned to a VNIC, allocated from an Oracle Cloud
    VMware Solution VLAN, or reserved in a subnet.
  - The OCI private IP APIs are synchronous, so this module does not expose
    waiter options.
  - Primary private IPs are managed through instance and VNIC operations and
    cannot be changed or deleted with this module.
version_added: "1.1.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_name_lookup_options
  - ansible.oci.oci_tags_options
options:
  state:
    description:
      - The desired state of the private IP.
    type: str
    choices: [present, absent]
    default: present
  private_ip_id:
    description:
      - The OCID of the private IP.
      - When provided, the module manages this exact private IP.
    type: str
  name:
    description:
      - Human-readable name for the private IP.
      - Required when creating a private IP.
      - When C(private_ip_id) is omitted, exactly one of C(vnic_id),
        C(vlan_id), or C(subnet_id) scopes the name lookup.
    type: str
  ip_address:
    description:
      - A private IPv4 address within the selected subnet or VLAN.
      - When omitted, OCI selects an available address.
      - This value cannot be changed after creation.
    type: str
  cidr_prefix_length:
    description:
      - Prefix length used with C(ip_address) to allocate a secondary IPv4
        CIDR.
      - This value cannot be changed after creation.
    type: int
  vnic_id:
    description:
      - The OCID of the VNIC to which the private IP is assigned.
      - Mutually exclusive with C(vlan_id) and C(subnet_id).
      - An existing secondary private IP can be reassigned to another VNIC in
        the same subnet when C(private_ip_id) is supplied.
    type: str
  vlan_id:
    description:
      - The OCID of the Oracle Cloud VMware Solution VLAN from which the
        private IP is allocated.
      - Mutually exclusive with C(vnic_id) and C(subnet_id).
      - This value cannot be changed after creation.
    type: str
  subnet_id:
    description:
      - The OCID of the subnet from which an unassigned private IP is
        allocated.
      - Mutually exclusive with C(vnic_id) and C(vlan_id).
      - This value cannot be changed after creation.
    type: str
  ipv4_subnet_cidr_at_creation:
    description:
      - One of the IPv4 CIDRs allocated to the subnet, used to select the
        allocation CIDR at creation time.
      - This value cannot be changed after creation.
    type: str
  hostname_label:
    description:
      - The hostname used for the private IP's DNS record.
      - This value can be updated after creation.
    type: str
  lifetime:
    description:
      - Whether the private IP is ephemeral or reserved.
    type: str
    choices: [ephemeral, reserved]
  route_table_id:
    description:
      - The OCID of the route table used by the private IP or its VNIC.
    type: str
"""

EXAMPLES = r"""
- name: Create a secondary private IP on a VNIC
  ansible.oci.oci_network_private_ip:
    state: present
    name: application-private-ip
    vnic_id: ocid1.vnic.oc1..example
    ip_address: 10.0.1.20
    hostname_label: application
    freeform_tags:
      environment: production
  register: created_private_ip

- name: Reassign and update a secondary private IP
  ansible.oci.oci_network_private_ip:
    state: present
    private_ip_id: "{{ created_private_ip.resource.id }}"
    name: application-private-ip-updated
    vnic_id: ocid1.vnic.oc1..standby
    lifetime: reserved
    route_table_id: ocid1.routetable.oc1..example

- name: Reserve a private IP in a subnet
  ansible.oci.oci_network_private_ip:
    state: present
    name: reserved-private-ip
    subnet_id: ocid1.subnet.oc1..example
    lifetime: reserved

- name: Allocate a secondary IPv4 CIDR on a VNIC
  ansible.oci.oci_network_private_ip:
    state: present
    name: application-private-cidr
    vnic_id: ocid1.vnic.oc1..example
    ip_address: 10.0.2.0
    cidr_prefix_length: 28
    ipv4_subnet_cidr_at_creation: 10.0.0.0/16

- name: Delete a secondary private IP
  ansible.oci.oci_network_private_ip:
    state: absent
    private_ip_id: "{{ created_private_ip.resource.id }}"
"""

RETURN = r"""
resource:
  description: The private IP resource.
  returned: when state != absent
  type: dict
  contains:
    id:
      description: The OCID of the private IP.
      type: str
      returned: always
    name:
      description: The display name of the private IP.
      type: str
      returned: always
    availability_domain:
      description: The private IP availability domain, when applicable.
      type: str
      returned: always
    compartment_id:
      description: The OCID of the containing compartment.
      type: str
      returned: always
    ip_address:
      description: The allocated IPv4 address.
      type: str
      returned: always
    cidr_prefix_length:
      description: The secondary IPv4 CIDR prefix length, when applicable.
      type: int
      returned: always
    hostname_label:
      description: The private IP DNS hostname label.
      type: str
      returned: always
    is_primary:
      description: Whether this is the VNIC's primary private IP.
      type: bool
      returned: always
    ip_state:
      description: Whether the private IP is assigned or available.
      type: str
      returned: always
    lifetime:
      description: Whether the private IP is ephemeral or reserved.
      type: str
      returned: always
    route_table_id:
      description: The OCID of the associated route table.
      type: str
      returned: always
    subnet_id:
      description: The OCID of the containing subnet, when applicable.
      type: str
      returned: always
    vlan_id:
      description: The OCID of the containing VLAN, when applicable.
      type: str
      returned: always
    vnic_id:
      description: The OCID of the assigned VNIC, when applicable.
      type: str
      returned: always
    ipv4_subnet_cidr_at_creation:
      description: The subnet IPv4 CIDR selected during allocation.
      type: str
      returned: always
    freeform_tags:
      description: Free-form tags applied to the private IP.
      type: dict
      returned: always
    defined_tags:
      description: Defined tags applied to the private IP.
      type: dict
      returned: always
    time_created:
      description: The date and time the private IP was created.
      type: str
      returned: always
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    OCI_TAG_ARGS,
    filter_none_values,
    import_oci_sdk,
    normalize_enum_values,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

oci = import_oci_sdk()[0]

PRIVATE_IP_SCOPE_FIELDS = ("vnic_id", "vlan_id", "subnet_id")
LIFETIME_ENUM_KEYS = frozenset({"lifetime"})
CREATE_REQUIRED_FIELDS = ("name",)


def build_create_private_ip_details(params):
    details = filter_none_values(
        {
            "display_name": params.get("name"),
            "ip_address": params.get("ip_address"),
            "cidr_prefix_length": params.get("cidr_prefix_length"),
            "vnic_id": params.get("vnic_id"),
            "vlan_id": params.get("vlan_id"),
            "subnet_id": params.get("subnet_id"),
            "ipv4_subnet_cidr_at_creation": params.get(
                "ipv4_subnet_cidr_at_creation"
            ),
            "hostname_label": params.get("hostname_label"),
            "lifetime": params.get("lifetime"),
            "route_table_id": params.get("route_table_id"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.core.models.CreatePrivateIpDetails(
        **normalize_enum_values(details, LIFETIME_ENUM_KEYS)
    )


class OciNetworkPrivateIpModule(OciResourceBase):
    """Concrete resource adapter for OCI secondary private IPs."""

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    resource_id_param = "private_ip_id"
    list_resource_method = "list_private_ips"
    common_list_filter_params = ()
    list_filter_params = PRIVATE_IP_SCOPE_FIELDS
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "secondary private IP"
    update_field_specs = (
        UpdateFieldSpec(
            param_name="name",
            resource_field="display_name",
            is_mutable=True,
        ),
        UpdateFieldSpec(param_name="hostname_label", is_mutable=True),
        UpdateFieldSpec(param_name="vnic_id", is_mutable=True),
        UpdateFieldSpec(
            param_name="lifetime",
            is_mutable=True,
            compare="case_insensitive",
        ),
        UpdateFieldSpec(param_name="route_table_id", is_mutable=True),
        UpdateFieldSpec(param_name="ip_address", is_mutable=False),
        UpdateFieldSpec(param_name="cidr_prefix_length", is_mutable=False),
        UpdateFieldSpec(param_name="vlan_id", is_mutable=False),
        UpdateFieldSpec(param_name="subnet_id", is_mutable=False),
        UpdateFieldSpec(
            param_name="ipv4_subnet_cidr_at_creation",
            is_mutable=False,
        ),
    )

    def validate_scope(self):
        supplied_scopes = [
            field
            for field in PRIVATE_IP_SCOPE_FIELDS
            if self.module.params.get(field) is not None
        ]
        if len(supplied_scopes) != 1:
            self.module.fail_json(
                msg=(
                    "Managing a secondary private IP without private_ip_id requires "
                    "exactly one of vnic_id, vlan_id, or subnet_id."
                )
            )

    def validate_create_request(self):
        super().validate_create_request()
        self.validate_scope()

    def validate_name_lookup_scope(self):
        self.validate_scope()

    def find_resources_by_name(self):
        resources = super().find_resources_by_name()
        return [
            resource
            for resource in resources
            if not getattr(resource, "is_primary", False)
        ]

    def resolve_target_resource(self):
        resource = super().resolve_target_resource()
        if resource is not None and getattr(resource, "is_primary", False):
            self.module.fail_json(
                msg=(
                    "oci_network_private_ip manages only secondary private IPs; "
                    "primary private IPs must be managed through instance or VNIC operations."
                )
            )
        return resource

    def compare_update_field_values(self, current_value, desired_value, compare=None):
        if compare == "case_insensitive":
            current_normalized = (
                current_value.upper() if isinstance(current_value, str) else current_value
            )
            desired_normalized = (
                desired_value.upper() if isinstance(desired_value, str) else desired_value
            )
            return current_normalized != desired_normalized
        return super().compare_update_field_values(
            current_value,
            desired_value,
            compare=compare,
        )

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_private_ip,
            private_ip_id=resource_id,
        )

    def create_resource(self):
        create_details = build_create_private_ip_details(self.module.params)
        response = self.call_with_retry(
            self.client.create_private_ip,
            create_private_ip_details=create_details,
        )
        return response.data

    def build_update_details(self, update_model_fields):
        normalized_fields = normalize_enum_values(
            dict(update_model_fields),
            LIFETIME_ENUM_KEYS,
        )
        return oci.core.models.UpdatePrivateIpDetails(**normalized_fields)

    def update_resource(self, resource):
        update_details = self.build_update_details(
            self.get_update_plan(resource)["update_model_fields"]
        )
        response = self.call_with_retry(
            self.client.update_private_ip,
            private_ip_id=resource.id,
            update_private_ip_details=update_details,
        )
        return response.data

    def delete_resource(self, resource):
        return self.call_with_retry(
            self.client.delete_private_ip,
            private_ip_id=resource.id,
        ).data


def main():
    argument_spec = dict(OCI_AUTH_ARGS, **OCI_TAG_ARGS)
    argument_spec.update(
        state=dict(type="str", choices=["present", "absent"], default="present"),
        private_ip_id=dict(type="str"),
        name=dict(type="str"),
        ip_address=dict(type="str"),
        cidr_prefix_length=dict(type="int"),
        vnic_id=dict(type="str"),
        vlan_id=dict(type="str"),
        subnet_id=dict(type="str"),
        ipv4_subnet_cidr_at_creation=dict(type="str"),
        hostname_label=dict(type="str"),
        lifetime=dict(type="str", choices=["ephemeral", "reserved"]),
        route_table_id=dict(type="str"),
        allow_duplicate_name=dict(type="bool", default=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[PRIVATE_IP_SCOPE_FIELDS],
    )

    OciNetworkPrivateIpModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
