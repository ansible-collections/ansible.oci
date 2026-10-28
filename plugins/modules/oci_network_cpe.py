# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: oci_network_cpe
short_description: Manage an OCI customer-premises equipment object
description:
- Create, update, and delete an OCI customer-premises equipment (CPE) object.
version_added: 1.2.0
author:
- Ron Gershburg (@ronger4)
extends_documentation_fragment:
- ansible.oci.oci_auth_options
- ansible.oci.oci_name_lookup_options
- ansible.oci.oci_tags_options
options:
  state:
    description: The desired state of the CPE.
    type: str
    choices:
    - present
    - absent
    default: present
  cpe_id:
    description: The OCID of the CPE.
    type: str
  name:
    description:
    - The display name of the CPE.
    - Required when creating a CPE and used with C(compartment_id) for name lookup.
    - The display name is mutable.
    type: str
  compartment_id:
    description:
    - The OCID of the CPE compartment.
    - Required when creating a CPE and when using name lookup.
    - The compartment is immutable after creation.
    type: str
  ip_address:
    description:
    - The public IP address of the on-premises router.
    - Required for creation. This value cannot change after creation.
    type: str
  cpe_device_shape_id:
    description:
    - The OCID of the CPE device shape.
    - This value can be updated.
    type: str
"""

EXAMPLES = r"""
- name: Create a CPE
  ansible.oci.oci_network_cpe:
    compartment_id: ocid1.compartment.oc1..example
    name: example-cpe
    ip_address: 203.0.113.2
  register: created_cpe

- name: Update a CPE device shape
  ansible.oci.oci_network_cpe:
    cpe_id: "{{ created_cpe.resource.id }}"
    cpe_device_shape_id: ocid1.cpedeviceshape.oc1..example

- name: Delete a CPE
  ansible.oci.oci_network_cpe:
    state: absent
    cpe_id: "{{ created_cpe.resource.id }}"
"""

RETURN = r"""
resource:
  description: The CPE resource.
  returned: when state=present, except when check mode predicts a change
  type: dict
  contains:
    id:
      description: The OCID of the CPE.
      type: str
    name:
      description: The display name of the CPE.
      type: str
    compartment_id:
      description: The CPE compartment OCID.
      type: str
    ip_address:
      description: The on-premises router IP address.
      type: str
    cpe_device_shape_id:
      description: The CPE device shape OCID.
      type: str
    freeform_tags:
      description: Free-form tags applied to the CPE.
      type: dict
    defined_tags:
      description: Defined tags applied to the CPE.
      type: dict
    time_created:
      description: The creation time in RFC3339 format.
      type: str
    is_private:
      description: Whether the CPE represents a private endpoint.
      type: bool
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    OCI_NAME_LOOKUP_ARGS,
    OCI_TAG_ARGS,
    build_model,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

oci = import_oci_sdk()[0]


class OciNetworkCpeModule(OciResourceBase):
    """Manage one OCI CPE resource."""

    @property
    def client_class(self):
        """Return the OCI virtual network client class.

        Returns:
            The SDK client class.
        """
        return oci.core.VirtualNetworkClient

    resource_id_param = "cpe_id"
    list_resource_method = "list_cpes"
    create_required_fields = ("compartment_id", "name", "ip_address")
    create_resource_name = "CPE"
    update_field_specs = (
        UpdateFieldSpec(
            param_name="name", resource_field="display_name", is_mutable=True
        ),
        UpdateFieldSpec(param_name="cpe_device_shape_id", is_mutable=True),
        UpdateFieldSpec(
            param_name="ip_address",
            is_mutable=False,
            immutable_reason="the OCI CPE IP address cannot change",
        ),
        UpdateFieldSpec(
            param_name="compartment_id",
            is_mutable=False,
            immutable_reason="the OCI CPE compartment cannot change",
        ),
    )

    def get_resource_response(self, resource_id):
        """Fetch a CPE by OCID.

        Args:
            resource_id: The CPE OCID.

        Returns:
            The OCI response wrapper.
        """
        return self.call_with_retry(self.client.get_cpe, cpe_id=resource_id)

    def create_resource(self):
        """Create a CPE and return its SDK model.

        Returns:
            The created CPE model.
        """
        params = self.module.params
        details = build_model(
            {
                "compartment_id": params.get("compartment_id"),
                "display_name": params.get("name"),
                "ip_address": params.get("ip_address"),
                "cpe_device_shape_id": params.get("cpe_device_shape_id"),
                "freeform_tags": params.get("freeform_tags"),
                "defined_tags": params.get("defined_tags"),
            },
            oci.core.models.CreateCpeDetails,
        )
        response = self.call_with_retry(
            self.client.create_cpe,
            create_cpe_details=details,
        )
        return response.data

    def update_resource(self, resource):
        """Update a CPE without lifecycle polling because CPE has no lifecycle state.

        Args:
            resource: The current CPE model.

        Returns:
            The updated CPE model.
        """
        details = build_model(
            self.get_update_plan(resource)["update_model_fields"],
            oci.core.models.UpdateCpeDetails,
        )
        return self.call_with_retry(
            self.client.update_cpe,
            cpe_id=resource.id,
            update_cpe_details=details,
        ).data

    def delete_resource(self, resource):
        """Delete a CPE and return the SDK response data.

        Args:
            resource: The CPE model to delete.

        Returns:
            The OCI delete response data.
        """
        return self.call_delete_fn(
            resource, self.client.delete_cpe, cpe_id=resource.id
        ).data


def main():
    """Initialize and run the CPE module."""
    module = AnsibleModule(
        argument_spec=dict(
            OCI_AUTH_ARGS,
            **OCI_TAG_ARGS,
            **OCI_NAME_LOOKUP_ARGS,
            state=dict(type="str", choices=["present", "absent"], default="present"),
            cpe_id=dict(type="str"),
            ip_address=dict(type="str"),
            cpe_device_shape_id=dict(type="str"),
        ),
        supports_check_mode=True,
    )
    OciNetworkCpeModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
