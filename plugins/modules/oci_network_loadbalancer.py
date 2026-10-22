# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
---
module: oci_network_loadbalancer
short_description: Manage an OCI network load balancer
description: >-
  Create, update, and delete OCI network load balancers.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_name_lookup_options
  - ansible.oci.oci_tags_options
options:
  wait:
    description:
      - Whether to wait for lifecycle operations to finish.
      - When false, return an immediate resource snapshot or its identifier.
      - A parent update followed by a security group update waits for the first operation.
    type: bool
    default: true
  wait_timeout:
    description: Maximum seconds to wait for each lifecycle operation.
    type: int
    default: 1200
  wait_interval:
    description: Maximum seconds between status checks.
    type: int
    default: 30
  state:
    description: Desired state of the network load balancer.
    type: str
    choices: [present, absent]
    default: present
  network_load_balancer_id:
    description: OCID of the network load balancer to manage.
    type: str
  name:
    description: Display name. Required on create and used for scoped lookup without an OCID.
    type: str
  compartment_id:
    description: Compartment OCID. Required on create and for name lookup.
    type: str
  subnet_id:
    description: Subnet OCID. Required on create and immutable afterwards.
    type: str
  is_private:
    description: Whether the network load balancer uses a private IP. This is immutable.
    type: bool
  ip_mode:
    description: >-
      IP mode. C(ipv4) selects IPv4. C(ipv6) enables dual-stack IPv4 and IPv6.
      OCI requires an IPv6-enabled subnet for C(ipv6).
    type: str
    choices: [ipv4, ipv6]
  assigned_private_ipv4:
    description: Private IPv4 address to assign during creation. This address cannot change afterwards.
    type: str
  assigned_ipv6:
    description: IPv6 address to assign during create or IPv6 enablement.
    type: str
  subnet_ipv6_cidr:
    description: IPv6 subnet prefix used during create or IPv6 enablement.
    type: str
  reserved_ips:
    description:
      - Reserved public, private, or IPv6 addresses to attach during creation.
      - During an IPv4-to-dual-stack update, one new reserved IPv6 address can be attached.
      - Existing addresses omitted from this option are preserved.
      - An empty list does not detach addresses.
    type: list
    elements: dict
    suboptions:
      id:
        description: OCID of a reserved IP address.
        type: str
        required: true
  network_security_group_ids:
    description: Network security group OCIDs. An empty list removes all associations.
    type: list
    elements: str
  is_preserve_source_destination:
    description: Whether to preserve source and destination addresses.
    type: bool
  is_symmetric_hash_enabled:
    description: Whether symmetric hashing is enabled.
    type: bool
  freeform_tags:
    description: Free-form tags to apply.
    type: dict
  defined_tags:
    description: Defined tags to apply.
    type: dict
  security_attributes:
    description: Security attributes to apply.
    type: dict
"""

EXAMPLES = r"""
- name: Create a private network load balancer
  ansible.oci.oci_network_loadbalancer:
    compartment_id: ocid1.compartment.oc1..example
    name: example-nlb
    subnet_id: ocid1.subnet.oc1..example
    is_private: true
    ip_mode: ipv4

- name: Enable IPv4 and IPv6 on an existing network load balancer
  ansible.oci.oci_network_loadbalancer:
    network_load_balancer_id: ocid1.networkloadbalancer.oc1..example
    ip_mode: ipv6

- name: Delete a network load balancer
  ansible.oci.oci_network_loadbalancer:
    network_load_balancer_id: ocid1.networkloadbalancer.oc1..example
    state: absent
"""

RETURN = r"""
resource:
  description: Network load balancer with OCI display name returned as C(name) and IP version as C(ip_mode).
  returned: when state is present and the resource exists after the operation
  type: dict
"""

import ipaddress

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_COMMON_ARGS,
    build_model,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_network_loadbalancer import (
    build_network_load_balancer_model,
    call_network_load_balancer_mutation,
)

oci = import_oci_sdk()[0]

IP_MODE_TO_OCI = {"ipv4": "IPV4", "ipv6": "IPV4_AND_IPV6"}
CREATE_REQUIRED_FIELDS = ("compartment_id", "name", "subnet_id")


def build_create_network_load_balancer_details(params):
    """Build the SDK create model from module parameters.

    Args:
        params: Module parameter mapping.

    Returns:
        The OCI create details model.
    """
    fields = {
        "compartment_id": params.get("compartment_id"),
        "display_name": params.get("name"),
        "subnet_id": params.get("subnet_id"),
        "is_private": params.get("is_private"),
        "is_preserve_source_destination": params.get("is_preserve_source_destination"),
        "is_symmetric_hash_enabled": params.get("is_symmetric_hash_enabled"),
        "freeform_tags": params.get("freeform_tags"),
        "defined_tags": params.get("defined_tags"),
        "security_attributes": params.get("security_attributes"),
        "network_security_group_ids": params.get("network_security_group_ids"),
        "assigned_private_ipv4": params.get("assigned_private_ipv4"),
        "assigned_ipv6": params.get("assigned_ipv6"),
        "subnet_ipv6_cidr": params.get("subnet_ipv6_cidr"),
    }
    ip_mode = params.get("ip_mode")
    if ip_mode is not None:
        fields["nlb_ip_version"] = IP_MODE_TO_OCI[ip_mode]
    reserved_ips = params.get("reserved_ips")
    if reserved_ips:
        fields["reserved_ips"] = reserved_ips
    return build_network_load_balancer_model("CreateNetworkLoadBalancerDetails", fields)


class OciNetworkLoadBalancerModule(OciResourceBase):
    """Manage OCI network load balancer lifecycle operations."""

    @property
    def client_class(self):
        """Return the OCI network load balancer client class.

        Returns:
            The NetworkLoadBalancerClient class.
        """
        return oci.network_load_balancer.NetworkLoadBalancerClient

    resource_id_param = "network_load_balancer_id"
    list_resource_method = "list_network_load_balancers"
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "network load balancer"
    update_method_name = "update_network_load_balancer"
    field_param_aliases = {"nlb_ip_version": "ip_mode"}
    update_field_specs = (
        UpdateFieldSpec("name", True, resource_field="display_name"),
        UpdateFieldSpec(
            "compartment_id",
            False,
            immutable_reason="OCI does not move network load balancers through update",
        ),
        UpdateFieldSpec("subnet_id", False),
        UpdateFieldSpec("is_private", False),
        UpdateFieldSpec("ip_mode", True, strategy="plan_ip_mode_update"),
        UpdateFieldSpec(
            "assigned_private_ipv4", True, strategy="plan_private_ipv4_update"
        ),
        UpdateFieldSpec("assigned_ipv6", True, strategy="plan_address_update"),
        UpdateFieldSpec("subnet_ipv6_cidr", True, strategy="plan_address_update"),
        UpdateFieldSpec("reserved_ips", True, strategy="plan_reserved_ip_update"),
        UpdateFieldSpec("is_preserve_source_destination", True),
        UpdateFieldSpec("is_symmetric_hash_enabled", True),
        UpdateFieldSpec("security_attributes", True),
    )

    def get_resource_response(self, resource_id):
        """Fetch one network load balancer.

        Args:
            resource_id: Network load balancer OCID.

        Returns:
            The SDK response from the get operation.
        """
        return self.call_with_retry(self.client.get_network_load_balancer, resource_id)

    def _address_matches(self, resource_dict, desired_value, field_name):
        """Compare an address option with assigned addresses.

        Args:
            resource_dict: Serialized current resource.
            desired_value: Requested IP address or network prefix.
            field_name: Address option being compared.

        Returns:
            True when an assigned address satisfies the option.
        """
        is_prefix = field_name == "subnet_ipv6_cidr"
        version = 4 if field_name == "assigned_private_ipv4" else 6
        try:
            desired = (
                ipaddress.ip_network(desired_value, strict=False)
                if is_prefix
                else ipaddress.ip_address(desired_value)
            )
            if desired.version != version:
                raise ValueError("expected IPv{0}".format(version))
        except ValueError as exc:
            self.module.fail_json(msg="Invalid {0}: {1}".format(field_name, exc))
        for entry in resource_dict.get("ip_addresses") or []:
            if field_name == "assigned_private_ipv4" and entry.get("is_public"):
                continue
            address = ipaddress.ip_address(entry["ip_address"])
            if address.version != version:
                continue
            matches = address in desired if is_prefix else address == desired
            if matches:
                return True
        return False

    @staticmethod
    def plan_ip_mode_update(resource, resource_dict, spec, desired_ip_mode):
        """Plan a mapped IP mode update.

        Args:
            resource: Current SDK resource.
            resource_dict: Serialized current resource.
            spec: Field specification.
            desired_ip_mode: Public ipv4 or ipv6 value.

        Returns:
            Update operations for the mapped OCI value.
        """
        desired = IP_MODE_TO_OCI[desired_ip_mode]
        current = resource_dict.get("nlb_ip_version")
        if current == desired:
            return []
        return [{"nlb_ip_version": desired}]

    def plan_address_update(self, resource, resource_dict, spec, desired_value):
        """Plan address settings only when the assigned IP list differs.

        Args:
            resource: Current SDK resource.
            resource_dict: Serialized current resource.
            spec: Field specification.
            desired_value: Requested address value.

        Returns:
            One update operation or an empty list.
        """
        if self._address_matches(
            resource_dict,
            desired_value,
            field_name=spec.param_name,
        ):
            return []
        requested_mode = self.module.params.get("ip_mode")
        if requested_mode != "ipv6" or resource_dict.get("nlb_ip_version") != "IPV4":
            self.module.fail_json(
                msg="IPv6 address selection requires an IPv4-to-dual-stack update."
            )
        return [{spec.param_name: desired_value}]

    def plan_private_ipv4_update(self, resource, resource_dict, spec, desired_value):
        """Reject a private IPv4 address change after create.

        Args:
            resource: Current SDK resource.
            resource_dict: Serialized current resource.
            spec: Field specification.
            desired_value: Requested IPv4 address.

        Returns:
            An empty operation list when the address already matches.
        """
        if self._address_matches(resource_dict, desired_value, "assigned_private_ipv4"):
            return []
        self.module.fail_json(
            msg="Changing assigned_private_ipv4 on an existing network load balancer is not supported."
        )

    def plan_reserved_ip_update(
        self, resource, resource_dict, spec, desired_reserved_ips
    ):
        """Plan one supported reserved IPv6 association during IPv6 enablement.

        Args:
            resource: Current SDK resource.
            resource_dict: Serialized current resource.
            spec: Field specification.
            desired_reserved_ips: Requested reserved IP entries.

        Returns:
            A supported reserved IPv6 update operation, or an empty list.
        """
        desired_ids = {entry["id"] for entry in desired_reserved_ips}
        if not desired_ids:
            return []
        current_ids = {
            entry["reserved_ip"]["id"]
            for entry in resource_dict.get("ip_addresses") or []
            if entry.get("reserved_ip")
        }
        additions = desired_ids - current_ids
        if not additions:
            return []
        if (
            len(additions) != 1
            or self.module.params.get("ip_mode") != "ipv6"
            or resource_dict.get("nlb_ip_version") != "IPV4"
        ):
            self.module.fail_json(
                msg="OCI supports adding one reserved IPv6 address during an IPV4-to-dual-stack update."
            )
        return [
            {
                "reserved_ipv6_id": next(iter(additions)),
                "nlb_ip_version": IP_MODE_TO_OCI["ipv6"],
            }
        ]

    def build_update_plan(self, resource):
        """Build updates and map public IP mode to the SDK value.

        Args:
            resource: Current SDK resource.

        Returns:
            Complete update plan.
        """
        plan = super(OciNetworkLoadBalancerModule, self).build_update_plan(resource)
        for strategy in plan["strategy_operations"]:
            for operation in strategy["operations"]:
                plan["update_model_fields"].update(operation)
        nsgs = self.module.params.get("network_security_group_ids")
        if nsgs is not None and sorted(nsgs) != sorted(
            resource.network_security_group_ids or []
        ):
            plan["update_needed"] = True
        return plan

    @staticmethod
    def build_update_details(update_model_fields):
        """Build an OCI network load balancer update model.

        Args:
            update_model_fields: Planned SDK fields.

        Returns:
            OCI update details model.
        """
        return build_network_load_balancer_model(
            "UpdateNetworkLoadBalancerDetails", update_model_fields
        )

    def _read_mutation_result(self, resource_id):
        """Read the resource after a mutation.

        Args:
            resource_id: Network load balancer OCID.

        Returns:
            The resource, or its identifier when waiting is disabled.
        """
        resource = self.get_resource_by_id(resource_id)
        if resource is None and self.module.params.get("wait", True):
            self.module.fail_json(
                msg="The completed operation did not expose network load balancer {0}.".format(
                    resource_id
                )
            )
        return resource if resource is not None else {"id": resource_id}

    def create_resource(self):
        """Create the resource and read its completed state when waiting.

        Returns:
            The immediate or completed network load balancer model.
        """
        response = call_network_load_balancer_mutation(
            self,
            "create_network_load_balancer",
            create_network_load_balancer_details=build_create_network_load_balancer_details(
                self.module.params
            ),
        )
        resource = response.data
        if not self.module.params.get("wait", True):
            return resource
        return self._read_mutation_result(resource.id)

    def update_resource(self, resource):
        """Apply settings and security groups through separate SDK operations.

        The inherited update method cannot apply both operations.

        Args:
            resource: Current network load balancer model.

        Returns:
            The refreshed resource or its identifier when waiting is disabled.
        """
        fields = self.get_update_plan(resource)["update_model_fields"]
        nsgs = self.module.params.get("network_security_group_ids")
        current_nsgs = resource.network_security_group_ids or []
        nsg_changed = nsgs is not None and sorted(nsgs) != sorted(current_nsgs)
        wait = self.module.params.get("wait", True)
        if fields:
            call_network_load_balancer_mutation(
                self,
                self.update_method_name,
                wait=wait or nsg_changed,
                network_load_balancer_id=resource.id,
                update_network_load_balancer_details=self.build_update_details(fields),
            )
        if nsg_changed:
            call_network_load_balancer_mutation(
                self,
                "update_network_security_groups",
                wait=wait,
                network_load_balancer_id=resource.id,
                update_network_security_groups_details=build_model(
                    {"network_security_group_ids": nsgs},
                    oci.network_load_balancer.models.UpdateNetworkSecurityGroupsDetails,
                ),
            )
        if fields or nsg_changed:
            return self._read_mutation_result(resource.id)
        return resource

    def delete_resource(self, resource):
        """Delete the network load balancer and wait for its work request.

        Args:
            resource: Resource to delete.

        Returns:
            The SDK delete response.
        """
        return call_network_load_balancer_mutation(
            self,
            "delete_network_load_balancer",
            network_load_balancer_id=resource.id,
        )


def main():
    """Build the argument spec and run the module."""
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        network_load_balancer_id=dict(type="str"),
        name=dict(type="str"),
        compartment_id=dict(type="str"),
        subnet_id=dict(type="str"),
        is_private=dict(type="bool"),
        ip_mode=dict(type="str", choices=["ipv4", "ipv6"]),
        assigned_private_ipv4=dict(type="str"),
        assigned_ipv6=dict(type="str"),
        subnet_ipv6_cidr=dict(type="str"),
        reserved_ips=dict(
            type="list",
            elements="dict",
            options=dict(id=dict(type="str", required=True)),
        ),
        network_security_group_ids=dict(type="list", elements="str"),
        is_preserve_source_destination=dict(type="bool"),
        is_symmetric_hash_enabled=dict(type="bool"),
        security_attributes=dict(type="dict"),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    OciNetworkLoadBalancerModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
