# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_drg
short_description: Manage a Dynamic Routing Gateway (DRG) resource in Oracle Cloud Infrastructure
description:
  - Create, update, and delete OCI Dynamic Routing Gateways (DRGs).
  - A DRG is a standalone regional resource. It is not scoped to a single VCN,
    so this module has no C(vcn_id) parameter. Use C(oci_drg_attachment) to
    attach a DRG to a VCN.
  - Uses the shared OCI helper layer for authentication, waiting, retry
    behavior, and result shaping.
  - Create requests must omit C(drg_id). After create, capture the returned
    DRG ID and use it for later C(state=present) and C(state=absent) tasks.
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
      - The desired lifecycle state of the DRG.
    type: str
    choices: [present, absent]
    default: present
  drg_id:
    description:
      - The OCID of the DRG.
      - When provided, the module manages this exact DRG.
      - Required to distinguish between multiple DRGs that share the same
        scoped C(name).
    type: str
  name:
    description:
      - Human-readable name for the DRG.
      - Required when creating a DRG.
      - When C(drg_id) is omitted, the module uses C(compartment_id + name)
        to find an existing DRG.
      - If exactly one DRG matches, C(state=present) manages it as the update
        target and C(state=absent) deletes it.
      - If more than one DRG matches, the task fails and the caller must
        supply C(drg_id).
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the DRG.
      - Required when creating a DRG.
      - The module does not move an existing DRG to another compartment.
      - Also scopes name-based DRG lookups when C(drg_id) is omitted.
    type: str
"""

EXAMPLES = r"""
- name: Create a DRG
  oracle.oci.oci_drg:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: example-drg
  register: created_drg

- name: Reconcile a uniquely named DRG by name
  oracle.oci.oci_drg:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: example-drg
    freeform_tags:
      env: prod

- name: Delete the created DRG
  oracle.oci.oci_drg:
    state: absent
    drg_id: "{{ created_drg.resource.id }}"

- name: Delete a uniquely named DRG without providing drg_id
  oracle.oci.oci_drg:
    state: absent
    compartment_id: ocid1.compartment.oc1..example
    name: example-drg
"""

RETURN = r"""
resource:
  description: The DRG resource.
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
    "name",
]
WAIT_FOR_DRG_STATES = [LIFECYCLE_AVAILABLE]


def build_create_drg_details(params):
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "display_name": params.get("name"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.core.models.CreateDrgDetails(**details)


class OciDrgModule(OciResourceBase):
    """Concrete resource adapter for OCI DRGs."""

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    resource_id_param = "drg_id"
    list_resource_method = "list_drgs"
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "DRG"
    update_method_name = "update_drg"
    update_details_name = "update_drg_details"
    update_wait_states = WAIT_FOR_DRG_STATES
    update_field_specs = [
        {
            "param_name": "name",
            "resource_field": "display_name",
            "update_field": "display_name",
            "is_mutable": True,
        },
    ]

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_drg,
            drg_id=resource_id,
        )

    def create_resource(self):
        create_drg_details = build_create_drg_details(self.module.params)
        response = self.call_with_retry(
            self.client.create_drg,
            create_drg_details=create_drg_details,
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_DRG_STATES,
        )

    def build_update_details(self, update_model_fields):
        return oci.core.models.UpdateDrgDetails(**update_model_fields)

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_drg,
            drg_id=resource.id,
        )


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        drg_id=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciDrgModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
