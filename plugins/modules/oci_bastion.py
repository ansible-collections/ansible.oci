# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_bastion
short_description: Manage a Bastion resource in Oracle Cloud Infrastructure
description:
  - Create, update, and delete OCI bastions.
  - Uses the shared OCI helper layer for authentication, waiting, retry
    behavior, and result shaping.
  - Create requests must omit C(bastion_id). After create, capture the returned
    bastion ID and use it for later C(state=present) and C(state=absent) tasks.
version_added: "1.1.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_name_lookup_options
  - ansible.oci.oci_wait_options
  - ansible.oci.oci_tags_options
options:
  state:
    description:
      - The desired lifecycle state of the bastion.
    type: str
    choices: [present, absent]
    default: present
  bastion_id:
    description:
      - The OCID of the bastion.
      - When provided, the module manages this exact bastion.
      - Required to distinguish between multiple bastions that share the same
        scoped C(name).
    type: str
  name:
    description:
      - Human-readable name for the bastion.
      - Required when creating a bastion.
      - When C(bastion_id) is omitted, the module uses
        C(compartment_id + name) to find an existing bastion.
      - If exactly one bastion matches, C(state=present) manages it as the
        update target and C(state=absent) deletes it.
      - If more than one bastion matches, the task fails and the caller must
        supply C(bastion_id).
      - The OCI API treats this as create-time only; it cannot be changed after
        create.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the bastion.
      - Required when creating a bastion.
      - The module does not move an existing bastion to another compartment.
      - Also scopes name-based bastion lookups when C(bastion_id) is omitted.
    type: str
  bastion_type:
    description:
      - The type of bastion.
      - The module does not update this field after create.
    type: str
    default: standard
  target_subnet_id:
    description:
      - The OCID of the subnet the bastion connects sessions to.
      - Required when creating a bastion.
      - The module does not update this field after create.
    type: str
  client_cidr_block_allow_list:
    description:
      - A list of address ranges in CIDR notation that are allowed to connect
        to sessions hosted by this bastion.
    type: list
    elements: str
  max_session_ttl_in_seconds:
    description:
      - The maximum amount of time, in seconds, that any session on the bastion
        can remain active.
    type: int
  phone_book_entry:
    description:
      - The phonebook entry of the customer's team, which can be used by
        Oracle Support for automation.
      - The module does not update this field after create.
    type: str
  static_jump_host_ip_addresses:
    description:
      - A list of IP addresses of the hosts that the bastion has access to.
      - Not applicable to C(standard) bastions.
    type: list
    elements: str
  dns_proxy_status:
    description:
      - The desired DNS proxy status of the bastion.
      - The module does not update this field after create.
    type: str
    choices: [ENABLED, DISABLED]
  security_attributes:
    description:
      - Zero Trust Packet Routing (ZPR) security attributes applied to the
        bastion, expressed as a nested dictionary keyed by namespace.
    type: dict
"""

EXAMPLES = r"""
- name: Create a bastion
  ansible.oci.oci_bastion:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: example-bastion
    target_subnet_id: ocid1.subnet.oc1..example
    client_cidr_block_allow_list:
      - 0.0.0.0/0
    max_session_ttl_in_seconds: 1800
  register: created_bastion

- name: Reconcile a uniquely named bastion by name
  ansible.oci.oci_bastion:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: example-bastion
    target_subnet_id: ocid1.subnet.oc1..example
    max_session_ttl_in_seconds: 3600

- name: Intentionally create a second bastion with the same display name
  ansible.oci.oci_bastion:
    state: present
    allow_duplicate_name: true
    compartment_id: ocid1.compartment.oc1..example
    name: example-bastion
    target_subnet_id: ocid1.subnet.oc1..example

- name: Delete the created bastion
  ansible.oci.oci_bastion:
    state: absent
    bastion_id: "{{ created_bastion.resource.id }}"

- name: Delete a uniquely named bastion without providing bastion_id
  ansible.oci.oci_bastion:
    state: absent
    compartment_id: ocid1.compartment.oc1..example
    name: example-bastion
"""

RETURN = r"""
resource:
  description: The bastion resource.
  returned: when state != absent
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_ACTIVE,
    OCI_COMMON_ARGS,
    filter_none_values,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]

CREATE_REQUIRED_FIELDS = [
    "compartment_id",
    "name",
    "target_subnet_id",
]
WAIT_FOR_BASTION_STATES = [LIFECYCLE_ACTIVE]


def build_create_bastion_details(params):
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "name": params.get("name"),
            "bastion_type": params.get("bastion_type"),
            "target_subnet_id": params.get("target_subnet_id"),
            "client_cidr_block_allow_list": params.get("client_cidr_block_allow_list"),
            "max_session_ttl_in_seconds": params.get("max_session_ttl_in_seconds"),
            "phone_book_entry": params.get("phone_book_entry"),
            "static_jump_host_ip_addresses": params.get("static_jump_host_ip_addresses"),
            "dns_proxy_status": params.get("dns_proxy_status"),
            "security_attributes": params.get("security_attributes"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.bastion.models.CreateBastionDetails(**details)


class OciBastionModule(OciResourceBase):
    """Concrete resource adapter for OCI bastions."""

    @property
    def client_class(self):
        return oci.bastion.BastionClient

    resource_id_param = "bastion_id"
    list_resource_method = "list_bastions"
    # The Bastion SDK model exposes its display field as ``name`` rather than the
    # ``display_name`` used by most OCI resources, so scoped name lookup and
    # result serialization must resolve against ``name``.
    name_response_field = "name"
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "bastion"
    update_method_name = "update_bastion"
    update_details_name = "update_bastion_details"
    update_wait_states = WAIT_FOR_BASTION_STATES
    update_field_specs = (
        UpdateFieldSpec(
            param_name="max_session_ttl_in_seconds",
            is_mutable=True,
        ),
        UpdateFieldSpec(
            param_name="client_cidr_block_allow_list",
            is_mutable=True,
            compare="sorted_list",
        ),
        UpdateFieldSpec(
            param_name="static_jump_host_ip_addresses",
            is_mutable=True,
            compare="sorted_list",
        ),
        UpdateFieldSpec(
            param_name="security_attributes",
            is_mutable=True,
        ),
        UpdateFieldSpec(
            param_name="name",
            is_mutable=False,
            immutable_reason="OCI does not support renaming a bastion",
        ),
        UpdateFieldSpec(
            param_name="target_subnet_id",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="compartment_id",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="dns_proxy_status",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="phone_book_entry",
            is_mutable=False,
        ),
    )

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_bastion,
            bastion_id=resource_id,
        )

    def create_resource(self):
        create_bastion_details = build_create_bastion_details(self.module.params)
        response = self.call_with_retry(
            self.client.create_bastion,
            create_bastion_details=create_bastion_details,
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_BASTION_STATES,
        )

    def build_update_details(self, update_model_fields):
        return oci.bastion.models.UpdateBastionDetails(**update_model_fields)

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_bastion,
            bastion_id=resource.id,
        )


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        bastion_id=dict(type="str"),
        bastion_type=dict(type="str", default="standard"),
        target_subnet_id=dict(type="str"),
        client_cidr_block_allow_list=dict(type="list", elements="str"),
        max_session_ttl_in_seconds=dict(type="int"),
        phone_book_entry=dict(type="str"),
        static_jump_host_ip_addresses=dict(type="list", elements="str"),
        dns_proxy_status=dict(type="str", choices=["ENABLED", "DISABLED"]),
        security_attributes=dict(type="dict"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciBastionModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
