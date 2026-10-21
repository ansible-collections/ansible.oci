# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_vnic_attachment
short_description: Manage a VNIC attachment resource in Oracle Cloud Infrastructure
description:
  - Create a secondary VNIC and attach it to a compute instance, or detach and
    delete the secondary VNIC.
  - The fields in C(create_vnic_details) are used only when creating the VNIC.
    They are not reconciled after the attachment exists.
  - Attachment identity fields cannot be updated. Detach and create another
    attachment to change C(instance_id), C(name), or C(nic_index).
version_added: "1.1.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_name_lookup_options
  - ansible.oci.oci_wait_options
options:
  state:
    description:
      - The desired lifecycle state of the VNIC attachment.
      - C(present) creates and attaches a secondary VNIC. C(absent) detaches
        and deletes it.
    type: str
    choices: [present, absent]
    default: present
  vnic_attachment_id:
    description:
      - The OCID of the VNIC attachment.
      - Use the ID returned by a create operation for unambiguous subsequent
        operations.
    type: str
  name:
    description:
      - The display name of the VNIC attachment.
      - Required for creation so the attachment can be resolved idempotently.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the compute instance.
      - Required for creation and name-based lookup.
    type: str
  instance_id:
    description:
      - The OCID of the compute instance to attach the secondary VNIC to.
      - Required for creation and name-based lookup.
    type: str
  nic_index:
    description:
      - The physical network interface card index to use.
      - OCI defaults this value to C(0) when it is omitted.
    type: int
  create_vnic_details:
    description:
      - Properties of the secondary VNIC to create.
      - Exactly one of C(subnet_id) and C(vlan_id) is required.
      - These values are create-only and are ignored after the attachment has
        been found by ID or scoped name.
    type: dict
    suboptions:
      assign_ipv6_ip:
        description:
          - Whether OCI should assign an IPv6 address from an IPv6-enabled subnet.
        type: bool
      assign_public_ip:
        description:
          - Whether OCI should assign a public IPv4 address to the VNIC.
          - Cannot be C(true) when C(vlan_id) is used.
        type: bool
      assign_private_dns_record:
        description:
          - Whether OCI should register a private DNS record for the VNIC.
          - Must not be C(false) when C(hostname_label) is provided.
        type: bool
      defined_tags:
        description:
          - Defined tags to assign to the created VNIC.
        type: dict
      display_name:
        description:
          - The display name of the created VNIC.
          - This is distinct from the attachment C(name).
        type: str
      freeform_tags:
        description:
          - Free-form tags to assign to the created VNIC.
        type: dict
      security_attributes:
        description:
          - Zero Trust Packet Routing security attributes for the created VNIC.
        type: dict
      hostname_label:
        description:
          - The hostname label for the VNIC's primary private IP.
          - Cannot be used with C(vlan_id).
        type: str
      ipv6_address_ipv6_subnet_cidr_pair_details:
        description:
          - IPv6 addresses, reserved IPv6 OCIDs, or subnet prefixes to use.
        type: list
        elements: dict
        suboptions:
          ipv6_id:
            description:
              - The OCID of a previously reserved IPv6 address.
            type: str
          ipv6_subnet_cidr:
            description:
              - An IPv6 prefix allocated to the subnet.
            type: str
          ipv6_address:
            description:
              - A specific IPv6 address from the subnet prefix.
            type: str
      subnet_cidr:
        description:
          - The IPv4 subnet CIDR from which OCI should allocate the private IP.
          - Mutually exclusive with C(private_ip) and C(private_ip_id).
        type: str
      nsg_ids:
        description:
          - OCIDs of network security groups to associate with the VNIC.
          - Cannot be used with C(vlan_id).
        type: list
        elements: str
      private_ip:
        description:
          - A private IPv4 address to assign to the VNIC.
          - Mutually exclusive with C(private_ip_id) and C(subnet_cidr).
        type: str
      private_ip_id:
        description:
          - The OCID of a previously reserved private IPv4 address.
          - Mutually exclusive with C(private_ip) and C(subnet_cidr).
        type: str
      skip_source_dest_check:
        description:
          - Whether to disable the source and destination check for the VNIC.
          - Cannot be used with C(vlan_id).
        type: bool
      subnet_id:
        description:
          - The OCID of the subnet in which to create the VNIC.
          - Mutually exclusive with C(vlan_id).
        type: str
      vlan_id:
        description:
          - The OCID of the VLAN in which to create the VNIC.
          - Mutually exclusive with C(subnet_id).
        type: str
"""

EXAMPLES = r"""
- name: Attach a secondary VNIC
  ansible.oci.oci_vnic_attachment:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    instance_id: ocid1.instance.oc1..example
    name: example-vnic-attachment
    create_vnic_details:
      subnet_id: ocid1.subnet.oc1..example
      display_name: example-secondary-vnic
      assign_public_ip: false
      nsg_ids:
        - ocid1.networksecuritygroup.oc1..example
  register: secondary_vnic

- name: Reconcile the attachment by returned ID
  ansible.oci.oci_vnic_attachment:
    state: present
    vnic_attachment_id: "{{ secondary_vnic.resource.id }}"
    instance_id: ocid1.instance.oc1..example
    name: example-vnic-attachment

- name: Detach and delete the secondary VNIC
  ansible.oci.oci_vnic_attachment:
    state: absent
    vnic_attachment_id: "{{ secondary_vnic.resource.id }}"
"""

RETURN = r"""
resource:
  description: The VNIC attachment acted upon by the module.
  returned: when state is present
  type: dict
  contains:
    id:
      description: The OCID of the VNIC attachment.
      type: str
      sample: ocid1.vnicattachment.oc1..example
    name:
      description: The display name of the VNIC attachment.
      type: str
      sample: example-vnic-attachment
    compartment_id:
      description: The OCID of the compartment containing the attachment.
      type: str
      sample: ocid1.compartment.oc1..example
    instance_id:
      description: The OCID of the attached compute instance.
      type: str
      sample: ocid1.instance.oc1..example
    lifecycle_state:
      description: The lifecycle state of the attachment.
      type: str
      sample: ATTACHED
    nic_index:
      description: The physical NIC index used by the VNIC.
      type: int
      sample: 0
    subnet_id:
      description: The OCID of the VNIC subnet, when applicable.
      type: str
      sample: ocid1.subnet.oc1..example
    vlan_id:
      description: The OCID of the VNIC VLAN, when applicable.
      type: str
      sample: ocid1.vlan.oc1..example
    vnic_id:
      description: The OCID of the attached VNIC.
      type: str
      sample: ocid1.vnic.oc1..example
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    OCI_NAME_LOOKUP_ARGS,
    OCI_WAIT_ARGS,
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

ATTACHED_STATE = "ATTACHED"
DETACHED_STATE = "DETACHED"
CREATE_REQUIRED_FIELDS = (
    "compartment_id",
    "instance_id",
    "name",
    "create_vnic_details",
)


def validate_create_vnic_details(details, fail_json):
    details = details or {}
    subnet_id = details.get("subnet_id")
    vlan_id = details.get("vlan_id")
    if bool(subnet_id) == bool(vlan_id):
        fail_json(
            msg="create_vnic_details requires exactly one of subnet_id or vlan_id"
        )

    private_ip_fields = ("private_ip", "private_ip_id", "subnet_cidr")
    provided_private_ip_fields = [
        field for field in private_ip_fields if details.get(field) is not None
    ]
    if len(provided_private_ip_fields) > 1:
        fail_json(
            msg=(
                "create_vnic_details fields private_ip, private_ip_id, and "
                "subnet_cidr are mutually exclusive"
            )
        )

    if details.get("hostname_label") and details.get("assign_private_dns_record") is False:
        fail_json(
            msg=(
                "create_vnic_details.assign_private_dns_record cannot be false "
                "when hostname_label is provided"
            )
        )

    if not vlan_id:
        return

    vlan_incompatible_fields = (
        "hostname_label",
        "nsg_ids",
        "private_ip",
        "private_ip_id",
        "skip_source_dest_check",
        "subnet_cidr",
    )
    incompatible = [
        field
        for field in vlan_incompatible_fields
        if details.get(field) is not None
    ]
    if details.get("assign_public_ip") is True:
        incompatible.append("assign_public_ip=true")
    if incompatible:
        fail_json(
            msg=(
                "create_vnic_details.vlan_id cannot be combined with: "
                + ", ".join(incompatible)
            )
        )


def build_create_vnic_details(params):
    details = dict(params.get("create_vnic_details") or {})
    ipv6_pairs = details.get("ipv6_address_ipv6_subnet_cidr_pair_details")
    if ipv6_pairs is not None:
        details["ipv6_address_ipv6_subnet_cidr_pair_details"] = [
            oci.core.models.Ipv6AddressIpv6SubnetCidrPairDetails(
                **filter_none_values(pair)
            )
            for pair in ipv6_pairs
        ]
    return oci.core.models.CreateVnicDetails(**filter_none_values(details))


def build_attach_vnic_details(params):
    return oci.core.models.AttachVnicDetails(
        **filter_none_values(
            {
                "create_vnic_details": build_create_vnic_details(params),
                "display_name": params.get("name"),
                "instance_id": params.get("instance_id"),
                "nic_index": params.get("nic_index"),
            }
        )
    )


class OciVnicAttachmentModule(OciResourceBase):
    """Concrete resource adapter for OCI secondary VNIC attachments."""

    @property
    def client_class(self):
        return oci.core.ComputeClient

    resource_id_param = "vnic_attachment_id"
    list_resource_method = "list_vnic_attachments"
    list_filter_params = ("instance_id",)
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "VNIC attachment"
    dead_states = frozenset({DETACHED_STATE})
    update_field_specs = (
        UpdateFieldSpec(
            param_name="name",
            resource_field="display_name",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="instance_id",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="nic_index",
            is_mutable=False,
        ),
    )

    def validate_create_request(self):
        super().validate_create_request()
        validate_create_vnic_details(
            self.module.params.get("create_vnic_details"),
            self.module.fail_json,
        )

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_vnic_attachment,
            vnic_attachment_id=resource_id,
        )

    def create_resource(self):
        response = self.call_with_retry(
            self.client.attach_vnic,
            attach_vnic_details=build_attach_vnic_details(self.module.params),
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            (ATTACHED_STATE,),
        )

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.detach_vnic,
            action_verb="detach",
            vnic_attachment_id=resource.id,
        )


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_WAIT_ARGS,
        **OCI_NAME_LOOKUP_ARGS,
    )
    argument_spec.update(
        state=dict(type="str", choices=["present", "absent"], default="present"),
        vnic_attachment_id=dict(type="str"),
        instance_id=dict(type="str"),
        nic_index=dict(type="int"),
        create_vnic_details=dict(
            type="dict",
            options=dict(
                assign_ipv6_ip=dict(type="bool"),
                assign_public_ip=dict(type="bool"),
                assign_private_dns_record=dict(type="bool"),
                defined_tags=dict(type="dict"),
                display_name=dict(type="str"),
                freeform_tags=dict(type="dict"),
                security_attributes=dict(type="dict"),
                hostname_label=dict(type="str"),
                ipv6_address_ipv6_subnet_cidr_pair_details=dict(
                    type="list",
                    elements="dict",
                    options=dict(
                        ipv6_id=dict(type="str"),
                        ipv6_subnet_cidr=dict(type="str"),
                        ipv6_address=dict(type="str"),
                    ),
                ),
                subnet_cidr=dict(type="str"),
                nsg_ids=dict(type="list", elements="str"),
                private_ip=dict(type="str"),
                private_ip_id=dict(type="str"),
                skip_source_dest_check=dict(type="bool"),
                subnet_id=dict(type="str"),
                vlan_id=dict(type="str"),
            ),
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciVnicAttachmentModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
