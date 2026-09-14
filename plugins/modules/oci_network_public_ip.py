# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_network_public_ip
short_description: Manage a Public IP resource in Oracle Cloud Infrastructure
description:
  - Create, update, and delete OCI public IP resources.
  - Use C(lifetime=ephemeral) for an address tied to a primary private IP, or
    C(lifetime=reserved) for an address controlled independently by the caller.
  - Uses the shared OCI helper layer for authentication, waiting, retries,
    name lookup, and result shaping.
version_added: "1.1.0"
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
      - The desired lifecycle state of the public IP.
    type: str
    choices: [present, absent]
    default: present
  public_ip_id:
    description:
      - The OCID of the public IP.
      - When provided, the module manages this exact public IP.
    type: str
  name:
    description:
      - Human-readable name for the public IP.
      - Required when creating a public IP.
      - Reserved public IP name lookup is scoped by C(compartment_id) and
        C(lifetime). Ephemeral public IP lookup uses C(private_ip_id).
      - Supply C(public_ip_id) when changing the name of an existing public IP.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the public IP.
      - Required when creating a public IP and for reserved name lookup.
      - This module does not move an existing public IP between compartments.
    type: str
  lifetime:
    description:
      - Whether OCI deletes the public IP with its assigned entity or keeps it
        reserved until explicitly deleted.
      - Required when creating a public IP and for name lookup.
      - This value cannot be changed after creation.
    type: str
    choices: [ephemeral, reserved]
  private_ip_id:
    description:
      - The OCID of the private IP to which the public IP is assigned.
      - Required when creating an ephemeral public IP.
      - Reserved public IPs can be created unassigned and later assigned or
        moved by supplying this option with C(public_ip_id).
      - Ephemeral public IPs cannot be moved after creation.
    type: str
  public_ip_pool_id:
    description:
      - The OCID of the public IP pool from which to allocate the address.
      - This value cannot be changed after creation.
    type: str
"""

EXAMPLES = r"""
- name: Create an unassigned reserved public IP
  ansible.oci.oci_network_public_ip:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: application-public-ip
    lifetime: reserved
  register: created_public_ip

- name: Create an ephemeral public IP on a primary private IP
  ansible.oci.oci_network_public_ip:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: ephemeral-application-public-ip
    lifetime: ephemeral
    private_ip_id: ocid1.privateip.oc1..example

- name: Update and assign a reserved public IP
  ansible.oci.oci_network_public_ip:
    state: present
    public_ip_id: "{{ created_public_ip.resource.id }}"
    name: application-public-ip-updated
    private_ip_id: ocid1.privateip.oc1..example
    freeform_tags:
      environment: production

- name: Delete the public IP
  ansible.oci.oci_network_public_ip:
    state: absent
    public_ip_id: "{{ created_public_ip.resource.id }}"
"""

RETURN = r"""
resource:
  description: The public IP resource.
  returned: when state != absent
  type: dict
  contains:
    id:
      description: The OCID of the public IP.
      type: str
      returned: always
    name:
      description: The display name of the public IP.
      type: str
      returned: always
    assigned_entity_id:
      description: The OCID of the entity to which the public IP is assigned.
      type: str
      returned: always
    assigned_entity_type:
      description: The type of entity to which the public IP is assigned.
      type: str
      returned: always
    availability_domain:
      description: The availability domain of an ephemeral public IP.
      type: str
      returned: always
    compartment_id:
      description: The OCID of the containing compartment.
      type: str
      returned: always
    ip_address:
      description: The allocated public IP address.
      type: str
      returned: always
    lifecycle_state:
      description: The current lifecycle state of the public IP.
      type: str
      returned: always
    lifetime:
      description: Whether the public IP is ephemeral or reserved.
      type: str
      returned: always
    private_ip_id:
      description: The deprecated private IP assignment field returned by OCI.
      type: str
      returned: always
    public_ip_pool_id:
      description: The OCID of the source public IP pool, when applicable.
      type: str
      returned: always
    scope:
      description: Whether the public IP is regional or availability-domain scoped.
      type: str
      returned: always
    freeform_tags:
      description: Free-form tags applied to the public IP.
      type: dict
      returned: always
    defined_tags:
      description: Defined tags applied to the public IP.
      type: dict
      returned: always
    time_created:
      description: The date and time the public IP was created.
      type: str
      returned: always
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    DEAD_STATES,
    OCI_COMMON_ARGS,
    filter_none_values,
    import_oci_sdk,
    normalize_enum_values,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

oci = import_oci_sdk()[0]

create_required_fields = ("compartment_id", "lifetime", "name")
lifetime_enum_keys = frozenset({"lifetime"})
public_ip_ready_states = ("AVAILABLE", "ASSIGNED")


def build_create_public_ip_details(params):
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "defined_tags": params.get("defined_tags"),
            "display_name": params.get("name"),
            "freeform_tags": params.get("freeform_tags"),
            "lifetime": params.get("lifetime"),
            "private_ip_id": params.get("private_ip_id"),
            "public_ip_pool_id": params.get("public_ip_pool_id"),
        }
    )
    return oci.core.models.CreatePublicIpDetails(
        **normalize_enum_values(details, lifetime_enum_keys)
    )


class OciNetworkPublicIpModule(OciResourceBase):
    """Concrete resource adapter for OCI public IPs."""

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    resource_id_param = "public_ip_id"
    list_resource_method = "list_public_ips"
    create_required_fields = create_required_fields
    create_resource_name = "public IP"
    update_method_name = "update_public_ip"
    update_details_name = "update_public_ip_details"
    update_wait_states = public_ip_ready_states
    update_field_specs = (
        UpdateFieldSpec(
            param_name="name",
            resource_field="display_name",
            is_mutable=True,
        ),
        UpdateFieldSpec(
            param_name="private_ip_id",
            resource_field="assigned_entity_id",
            update_field="private_ip_id",
            is_mutable=True,
        ),
        UpdateFieldSpec(
            param_name="public_ip_pool_id",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="lifetime",
            is_mutable=False,
            compare="case_insensitive",
        ),
        UpdateFieldSpec(
            param_name="compartment_id",
            is_mutable=False,
        ),
    )

    @property
    def normalized_lifetime(self):
        lifetime = self.module.params.get("lifetime")
        return lifetime.upper() if isinstance(lifetime, str) else lifetime

    def validate_create_request(self):
        super().validate_create_request()
        if (
            self.normalized_lifetime == "EPHEMERAL"
            and not self.module.params.get("private_ip_id")
        ):
            self.module.fail_json(
                msg="Creating an ephemeral public IP requires private_ip_id."
            )
        if (
            self.normalized_lifetime == "EPHEMERAL"
            and self.module.params.get("allow_duplicate_name", False)
        ):
            self.module.fail_json(
                msg=(
                    "allow_duplicate_name is not supported for ephemeral public "
                    "IPs because a private IP can have only one public IP."
                )
            )

    def validate_name_lookup_scope(self):
        if self.normalized_lifetime is None:
            self.module.fail_json(
                msg="Using name lookup for a public IP requires lifetime."
            )
        if self.normalized_lifetime == "EPHEMERAL":
            if not self.module.params.get("private_ip_id"):
                self.module.fail_json(
                    msg=(
                        "Using name lookup for an ephemeral public IP requires "
                        "private_ip_id."
                    )
                )
            return
        if not self.module.params.get("compartment_id"):
            self.module.fail_json(
                msg=(
                    "Using name lookup for a reserved public IP requires "
                    "compartment_id."
                )
            )

    def find_resources_by_name(self):
        if not self.has_name_lookup_request:
            return []

        self.validate_name_lookup_scope()
        if self.normalized_lifetime == "EPHEMERAL":
            details = oci.core.models.GetPublicIpByPrivateIpIdDetails(
                private_ip_id=self.module.params.get("private_ip_id")
            )
            try:
                response = self.call_with_retry(
                    self.client.get_public_ip_by_private_ip_id,
                    get_public_ip_by_private_ip_id_details=details,
                )
            except Exception as exc:
                if getattr(exc, "status", None) == 404:
                    return []
                raise
            resources = [response.data]
        else:
            list_params = {
                "scope": "REGION",
                "compartment_id": self.module.params.get("compartment_id"),
                "lifetime": "RESERVED",
            }
            public_ip_pool_id = self.module.params.get("public_ip_pool_id")
            if public_ip_pool_id is not None:
                list_params["public_ip_pool_id"] = public_ip_pool_id
            resources = self.list_all_resources(
                self.client.list_public_ips,
                **list_params,
            )

        matches = self.filter_resources_by_display_name(
            resources,
            self.name_lookup_value,
        )
        return [
            resource
            for resource in matches
            if getattr(resource, "lifecycle_state", None) not in DEAD_STATES
        ]

    def compare_update_field_values(self, current_value, desired_value, compare=None):
        if compare == "case_insensitive":
            current_value = (
                current_value.upper()
                if isinstance(current_value, str)
                else current_value
            )
            desired_value = (
                desired_value.upper()
                if isinstance(desired_value, str)
                else desired_value
            )
            return current_value != desired_value
        return super().compare_update_field_values(
            current_value,
            desired_value,
            compare=compare,
        )

    def build_update_plan(self, resource):
        desired_private_ip_id = self.module.params.get("private_ip_id")
        assigned_entity_id = getattr(resource, "assigned_entity_id", None)
        if (
            desired_private_ip_id is not None
            and desired_private_ip_id != assigned_entity_id
            and getattr(resource, "lifetime", None) == "EPHEMERAL"
        ):
            self.module.fail_json(
                msg="Moving an ephemeral public IP to another private IP is not supported."
            )
        return super().build_update_plan(resource)

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_public_ip,
            public_ip_id=resource_id,
        )

    def create_resource(self):
        create_public_ip_details = build_create_public_ip_details(self.module.params)
        response = self.call_with_retry(
            self.client.create_public_ip,
            create_public_ip_details=create_public_ip_details,
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            public_ip_ready_states,
        )

    def build_update_details(self, update_model_fields):
        return oci.core.models.UpdatePublicIpDetails(**update_model_fields)

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_public_ip,
            public_ip_id=resource.id,
        )


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        public_ip_id=dict(type="str"),
        lifetime=dict(type="str", choices=["ephemeral", "reserved"]),
        private_ip_id=dict(type="str"),
        public_ip_pool_id=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciNetworkPublicIpModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
