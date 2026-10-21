# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_network_drg_attachment
short_description: Manage a DRG attachment resource in Oracle Cloud Infrastructure
description:
  - Create, update, and delete OCI DRG (Dynamic Routing Gateway) attachments.
  - This module manages only VCN-type DRG attachments, the common case of
    attaching a DRG to a VCN so the VCN can reach the DRG's other
    attachments. It does not support virtual circuit, IPSec tunnel, or
    remote peering connection attachment types, and it does not expose the
    polymorphic C(network_details) field. Instead it uses the direct
    C(vcn_id) field that OCI also supports on the create and response
    models for VCN attachments.
  - Uses the shared OCI helper layer for authentication, waiting, retry
    behavior, and result shaping.
  - Create requests must omit C(drg_attachment_id). After create, capture the
    returned attachment ID and use it for later C(state=present) and
    C(state=absent) tasks.
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
      - The desired lifecycle state of the DRG attachment.
    type: str
    choices: [present, absent]
    default: present
  drg_attachment_id:
    description:
      - The OCID of the DRG attachment.
      - When provided, the module manages this exact DRG attachment.
      - Required to distinguish between multiple DRG attachments that share
        the same scoped C(name).
    type: str
  name:
    description:
      - Human-readable name for the DRG attachment.
      - When C(drg_attachment_id) is omitted, the module uses
        C(compartment_id + drg_id + vcn_id + name) to find an existing DRG
        attachment.
      - If exactly one DRG attachment matches, C(state=present) manages it as
        the update target and C(state=absent) deletes it.
      - If more than one DRG attachment matches, the task fails and the
        caller must supply C(drg_attachment_id).
    type: str
  compartment_id:
    description:
      - The OCID of the compartment to scope name-based DRG attachment
        lookups when C(drg_attachment_id) is omitted.
      - This is not part of the OCI create payload for a DRG attachment (the
        attachment inherits its compartment from the DRG), but it is
        required to scope the list call used for name-based lookup.
    type: str
  drg_id:
    description:
      - The OCID of the DRG to attach.
      - Required when creating a DRG attachment.
      - The module does not support moving an existing attachment to another
        DRG.
    type: str
  vcn_id:
    description:
      - The OCID of the VCN to attach to the DRG.
      - Required when creating a DRG attachment.
      - The module does not support moving an existing attachment to another
        VCN.
    type: str
  route_table_id:
    description:
      - The OCID of the VCN-side route table associated with this
        attachment.
    type: str
  drg_route_table_id:
    description:
      - The OCID of the DRG-side route table associated with this
        attachment.
    type: str
"""

EXAMPLES = r"""
- name: Attach a DRG to a VCN
  ansible.oci.oci_network_drg_attachment:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    drg_id: ocid1.drg.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-drg-attachment
  register: created_drg_attachment

- name: Update the route tables used by a DRG attachment
  ansible.oci.oci_network_drg_attachment:
    state: present
    drg_attachment_id: "{{ created_drg_attachment.resource.id }}"
    route_table_id: ocid1.routetable.oc1..updated
    drg_route_table_id: ocid1.drgroutetable.oc1..updated

- name: Reconcile a uniquely named DRG attachment by name
  ansible.oci.oci_network_drg_attachment:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    drg_id: ocid1.drg.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-drg-attachment
    route_table_id: ocid1.routetable.oc1..updated

- name: Detach the DRG from the VCN
  ansible.oci.oci_network_drg_attachment:
    state: absent
    drg_attachment_id: "{{ created_drg_attachment.resource.id }}"

- name: Detach a uniquely named DRG attachment without providing drg_attachment_id
  ansible.oci.oci_network_drg_attachment:
    state: absent
    compartment_id: ocid1.compartment.oc1..example
    drg_id: ocid1.drg.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-drg-attachment
"""

RETURN = r"""
resource:
  description: The DRG attachment resource.
  returned: when state != absent
  type: dict
  contains:
    id:
      description: The OCID of the DRG attachment.
      type: str
      returned: always
      sample: ocid1.drgattachment.oc1..example
    name:
      description: The display name of the DRG attachment.
      type: str
      returned: always
      sample: example-drg-attachment
    compartment_id:
      description: The OCID of the compartment containing the DRG attachment.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    drg_id:
      description: The OCID of the attached DRG.
      type: str
      returned: always
      sample: ocid1.drg.oc1..example
    vcn_id:
      description: The OCID of the attached VCN.
      type: str
      returned: always
      sample: ocid1.vcn.oc1..example
    lifecycle_state:
      description: The current lifecycle state of the DRG attachment.
      type: str
      returned: always
      sample: ATTACHED
    route_table_id:
      description: The OCID of the VCN-side route table associated with the attachment, if any.
      type: str
      returned: always
      sample: null
    drg_route_table_id:
      description: The OCID of the DRG-side route table associated with the attachment, if any.
      type: str
      returned: always
      sample: null
    network_details:
      description: The attached network's details, as returned by OCI.
      type: dict
      returned: always
      sample: {"type": "VCN", "id": "ocid1.vcn.oc1..example"}
    export_drg_route_distribution_id:
      description: The OCID of the route distribution assigned to this attachment for exporting routes, if any.
      type: str
      returned: always
      sample: null
    is_cross_tenancy:
      description: Whether the attached network lives in a different tenancy than the DRG.
      type: bool
      returned: always
      sample: false
    freeform_tags:
      description: Free-form tags applied to the DRG attachment.
      type: dict
      returned: always
      sample: {"environment": "production"}
    defined_tags:
      description: Defined tags applied to the DRG attachment.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
    time_created:
      description: The date and time the DRG attachment was created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
  sample:
    id: ocid1.drgattachment.oc1..example
    name: example-drg-attachment
    compartment_id: ocid1.compartment.oc1..example
    drg_id: ocid1.drg.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    lifecycle_state: ATTACHED
    route_table_id: null
    drg_route_table_id: null
    network_details: {"type": "VCN", "id": "ocid1.vcn.oc1..example"}
    export_drg_route_distribution_id: null
    is_cross_tenancy: false
    freeform_tags: {"environment": "production"}
    defined_tags: {"Operations": {"CostCenter": "42"}}
    time_created: "2026-01-01T00:00:00.000Z"
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
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
    "drg_id",
    "vcn_id",
    "name",
]
# A DRG attachment uses DETACHED as its terminal lifecycle state instead of
# the collection default TERMINATED state.
WAIT_FOR_DRG_ATTACHMENT_STATES = ["ATTACHED"]
DETACHED_STATE = "DETACHED"


def build_create_drg_attachment_details(params):
    details = filter_none_values(
        {
            "display_name": params.get("name"),
            "drg_id": params.get("drg_id"),
            "vcn_id": params.get("vcn_id"),
            "route_table_id": params.get("route_table_id"),
            "drg_route_table_id": params.get("drg_route_table_id"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.core.models.CreateDrgAttachmentDetails(**details)


class OciNetworkDrgAttachmentModule(OciResourceBase):
    """Concrete resource adapter for OCI DRG attachments.

    This module manages only VCN-type attachments, using the direct
    ``vcn_id``/``route_table_id`` fields rather than the polymorphic
    ``network_details`` field.
    """

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    resource_id_param = "drg_attachment_id"
    list_resource_method = "list_drg_attachments"
    list_filter_params = ("drg_id", "vcn_id")
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "DRG attachment"
    dead_states = frozenset({DETACHED_STATE})
    update_method_name = "update_drg_attachment"
    update_details_name = "update_drg_attachment_details"
    update_wait_states = WAIT_FOR_DRG_ATTACHMENT_STATES
    update_field_specs = (
        UpdateFieldSpec(
            param_name="name",
            resource_field="display_name",
            is_mutable=True,
        ),
        UpdateFieldSpec(
            param_name="route_table_id",
            is_mutable=True,
        ),
        UpdateFieldSpec(
            param_name="drg_route_table_id",
            is_mutable=True,
        ),
        UpdateFieldSpec(
            param_name="drg_id",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="vcn_id",
            is_mutable=False,
        ),
    )

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_drg_attachment,
            drg_attachment_id=resource_id,
        )

    def create_resource(self):
        create_drg_attachment_details = build_create_drg_attachment_details(
            self.module.params
        )
        response = self.call_with_retry(
            self.client.create_drg_attachment,
            create_drg_attachment_details=create_drg_attachment_details,
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_DRG_ATTACHMENT_STATES,
        )

    def build_update_details(self, update_model_fields):
        return oci.core.models.UpdateDrgAttachmentDetails(**update_model_fields)

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_drg_attachment,
            drg_attachment_id=resource.id,
        )


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        drg_attachment_id=dict(type="str"),
        drg_id=dict(type="str"),
        vcn_id=dict(type="str"),
        route_table_id=dict(type="str"),
        drg_route_table_id=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciNetworkDrgAttachmentModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
