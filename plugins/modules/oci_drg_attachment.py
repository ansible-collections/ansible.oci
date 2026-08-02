# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_drg_attachment
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
  - There is intentionally no paired C(oci_drg_attachment_info) module.
    Read access to attachments is out of scope for this module; verify
    attachment state by rerunning this module and checking C(changed).
  - Uses the shared OCI helper layer for authentication, waiting, retry
    behavior, and result shaping.
  - Create requests must omit C(drg_attachment_id). After create, capture the
    returned attachment ID and use it for later C(state=present) and
    C(state=absent) tasks.
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
  oracle.oci.oci_drg_attachment:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    drg_id: ocid1.drg.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-drg-attachment
  register: created_drg_attachment

- name: Update the route tables used by a DRG attachment
  oracle.oci.oci_drg_attachment:
    state: present
    drg_attachment_id: "{{ created_drg_attachment.resource.id }}"
    route_table_id: ocid1.routetable.oc1..updated
    drg_route_table_id: ocid1.drgroutetable.oc1..updated

- name: Detach the DRG from the VCN
  oracle.oci.oci_drg_attachment:
    state: absent
    drg_attachment_id: "{{ created_drg_attachment.resource.id }}"
"""

RETURN = r"""
resource:
  description: The DRG attachment resource.
  returned: when state != absent
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.oracle.oci.plugins.module_utils.oci_common import (
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
    "drg_id",
    "vcn_id",
    "name",
]
# A DRG attachment uses its own lifecycle vocabulary
# (ATTACHING/ATTACHED/DETACHING/DETACHED). It does not use the
# AVAILABLE/TERMINATED vocabulary that the shared DEAD_STATES constant
# assumes, so the terminal "detached" state is handled explicitly in
# delete_resource() below instead of relying on delete_resource_and_wait().
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


class OciDrgAttachmentModule(OciResourceBase):
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
    update_method_name = "update_drg_attachment"
    update_details_name = "update_drg_attachment_details"
    update_wait_states = WAIT_FOR_DRG_ATTACHMENT_STATES
    update_field_specs = [
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
            "param_name": "drg_route_table_id",
            "resource_field": "drg_route_table_id",
            "update_field": "drg_route_table_id",
            "is_mutable": True,
        },
        {
            "param_name": "drg_id",
            "resource_field": "drg_id",
            "is_mutable": False,
        },
        {
            "param_name": "vcn_id",
            "resource_field": "vcn_id",
            "is_mutable": False,
        },
    ]

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_drg_attachment,
            drg_attachment_id=resource_id,
        )

    def resolve_target_resource(self):
        """Treat an already-DETACHED attachment the same as "not found".

        The shared base class only recognizes the collection-wide
        ``DEAD_STATES`` vocabulary (``DELETED``/``TERMINATED``) as terminal.
        A DRG attachment becomes terminal via ``DETACHED`` instead, so this
        normalizes that case here rather than in the shared framework, which
        keeps present/absent idempotency correct without special-casing this
        one resource type in ``oci_resource.py``.
        """
        resource = super().resolve_target_resource()
        if resource is not None and getattr(resource, "lifecycle_state", None) == DETACHED_STATE:
            return None
        return resource

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
        try:
            response = self.call_with_retry(
                self.client.delete_drg_attachment,
                drg_attachment_id=resource.id,
            )
        except Exception as exc:
            if getattr(exc, "status", None) == 409:
                self.module.fail_json(
                    msg=(
                        f"Cannot delete {self.create_resource_name} {resource.id} while "
                        f"dependent resources exist: {exc}"
                    )
                )
            raise

        if not self.module.params.get("wait", True):
            return response.data
        return self._wait_for_drg_attachment_detached(resource.id)

    def _wait_for_drg_attachment_detached(self, drg_attachment_id):
        """Wait for a DRG attachment to reach DETACHED or disappear.

        The shared ``delete_resource_and_wait()`` helper assumes resources
        become terminal via the collection-wide ``DEAD_STATES`` vocabulary
        (``DELETED``/``TERMINATED``). A DRG attachment instead becomes
        terminal via ``DETACHED``, so this mirrors the shared wait helper
        with the correct target state and treats a 404 as already deleted
        at any point in the wait.
        """
        timeout = self.module.params.get("wait_timeout", 1200)
        interval = self.module.params.get("wait_interval", 30)

        try:
            initial_response = self.get_resource_response(drg_attachment_id)
        except Exception as exc:
            if getattr(exc, "status", None) == 404:
                return None
            raise

        waiter_result = oci.wait_until(
            self.client,
            initial_response,
            max_interval_seconds=interval,
            max_wait_seconds=timeout,
            succeed_on_not_found=True,
            evaluate_response=lambda response: (
                getattr(response.data, "lifecycle_state", None) == DETACHED_STATE
            ),
            fetch_func=lambda response=None: self.get_resource_response(
                drg_attachment_id
            ),
        )
        return getattr(waiter_result, "data", None)


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

    OciDrgAttachmentModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
