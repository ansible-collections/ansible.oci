# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_network_security_group
short_description: Manage a Network Security Group resource in Oracle Cloud Infrastructure
description:
  - Create, update, and delete OCI Network Security Groups.
  - Network Security Group rules are managed separately and are not part of this module.
  - Uses the shared OCI helper layer for authentication, waiting, retry behavior,
    name lookup, and result shaping.
version_added: "1.0.0"
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
      - The desired lifecycle state of the Network Security Group.
    type: str
    choices: [present, absent]
    default: present
  network_security_group_id:
    description:
      - The OCID of the Network Security Group.
      - When provided, the module manages this exact resource.
    type: str
  name:
    description:
      - Human-readable name for the Network Security Group.
      - Required when creating a Network Security Group.
      - When C(network_security_group_id) is omitted, the module uses
        C(compartment_id + vcn_id + name) to find an existing resource.
      - If multiple resources match, supply C(network_security_group_id) to
        disambiguate them.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the Network Security Group.
      - Required for creation and name-based lookup.
      - This value cannot be changed after creation.
    type: str
  vcn_id:
    description:
      - The OCID of the VCN containing the Network Security Group.
      - Required for creation and name-based lookup.
      - This value cannot be changed after creation.
    type: str
"""

EXAMPLES = r"""
- name: Create a Network Security Group
  ansible.oci.oci_network_security_group:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-network-security-group
    freeform_tags:
      environment: production
  register: created_network_security_group

- name: Pass the Network Security Group to a compute instance
  ansible.oci.oci_instance:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: example-availability-domain
    name: example-instance
    shape: VM.Standard.E4.Flex
    source_details:
      source_type: image
      image_id: ocid1.image.oc1..example
    subnet_id: ocid1.subnet.oc1..example
    nsg_ids:
      - "{{ created_network_security_group.resource.id }}"

- name: Update a Network Security Group
  ansible.oci.oci_network_security_group:
    state: present
    network_security_group_id: ocid1.networksecuritygroup.oc1..example
    name: renamed-network-security-group
    freeform_tags:
      environment: development

- name: Delete a Network Security Group
  ansible.oci.oci_network_security_group:
    state: absent
    network_security_group_id: ocid1.networksecuritygroup.oc1..example
"""

RETURN = r"""
resource:
  description: The Network Security Group resource.
  returned: when state != absent
  type: dict
  contains:
    id:
      description: The OCID of the Network Security Group.
      type: str
      returned: always
    name:
      description: The display name of the Network Security Group.
      type: str
      returned: always
    compartment_id:
      description: The OCID of the containing compartment.
      type: str
      returned: always
    vcn_id:
      description: The OCID of the containing VCN.
      type: str
      returned: always
    lifecycle_state:
      description: The current lifecycle state.
      type: str
      returned: always
    freeform_tags:
      description: Free-form tags applied to the resource.
      type: dict
      returned: always
    defined_tags:
      description: Defined tags applied to the resource.
      type: dict
      returned: always
    time_created:
      description: The date and time the resource was created.
      type: str
      returned: always
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_AVAILABLE,
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

CREATE_REQUIRED_FIELDS = ["compartment_id", "vcn_id", "name"]
WAIT_FOR_NETWORK_SECURITY_GROUP_STATES = [LIFECYCLE_AVAILABLE]


def build_create_network_security_group_details(params):
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "vcn_id": params.get("vcn_id"),
            "display_name": params.get("name"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.core.models.CreateNetworkSecurityGroupDetails(**details)


class OciNetworkSecurityGroupModule(OciResourceBase):
    """Concrete resource adapter for OCI Network Security Groups."""

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    resource_id_param = "network_security_group_id"
    list_resource_method = "list_network_security_groups"
    list_filter_params = ("vcn_id",)
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "Network Security Group"
    update_method_name = "update_network_security_group"
    update_details_name = "update_network_security_group_details"
    update_wait_states = WAIT_FOR_NETWORK_SECURITY_GROUP_STATES
    update_field_specs = (
        UpdateFieldSpec(
            param_name="name",
            resource_field="display_name",
            is_mutable=True,
        ),
        UpdateFieldSpec(
            param_name="vcn_id",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="compartment_id",
            is_mutable=False,
        ),
    )

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_network_security_group,
            network_security_group_id=resource_id,
        )

    def create_resource(self):
        create_details = build_create_network_security_group_details(
            self.module.params
        )
        response = self.call_with_retry(
            self.client.create_network_security_group,
            create_network_security_group_details=create_details,
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_NETWORK_SECURITY_GROUP_STATES,
        )

    def build_update_details(self, update_model_fields):
        return oci.core.models.UpdateNetworkSecurityGroupDetails(
            **update_model_fields
        )

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_network_security_group,
            network_security_group_id=resource.id,
        )


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        network_security_group_id=dict(type="str"),
        vcn_id=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciNetworkSecurityGroupModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
