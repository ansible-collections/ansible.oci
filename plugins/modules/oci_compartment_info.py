# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_compartment_info
short_description: Retrieve OCI compartment information
description:
  - Retrieve details about one or more OCI compartments.
  - Use C(compartment_id) to retrieve one compartment, or
    C(parent_compartment_id) to list direct child compartments.
  - This is a read-only module and does not modify resources.
version_added: "1.1.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  compartment_id:
    description:
      - The OCID of a specific compartment to retrieve.
      - When specified, returns a single resource instead of a list.
    type: str
  parent_compartment_id:
    description:
      - The OCID of the parent compartment whose direct children are listed.
      - Required when listing resources.
    type: str
  name:
    description:
      - Filter listed compartments by name.
      - Only used when C(parent_compartment_id) is provided.
    type: str
  lifecycle_state:
    description:
      - Filter listed compartments by lifecycle state.
      - Only used when C(parent_compartment_id) is provided.
    type: str
"""

EXAMPLES = r"""
- name: List direct child compartments
  ansible.oci.oci_compartment_info:
    parent_compartment_id: ocid1.compartment.oc1..example

- name: List active child compartments by name
  ansible.oci.oci_compartment_info:
    parent_compartment_id: ocid1.compartment.oc1..example
    name: project-development
    lifecycle_state: ACTIVE

- name: Get a specific compartment
  ansible.oci.oci_compartment_info:
    compartment_id: ocid1.compartment.oc1..example
"""

RETURN = r"""
compartments:
  description: List of compartments that matched the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the compartment.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    compartment_id:
      description: The OCID of the parent compartment.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..parent-example
    name:
      description: The name of the compartment.
      type: str
      returned: always
      sample: project-development
    description:
      description: The compartment description.
      type: str
      returned: always
      sample: Development resources for the project
    lifecycle_state:
      description: The current lifecycle state of the compartment.
      type: str
      returned: always
      sample: ACTIVE
    time_created:
      description: The creation time in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
    freeform_tags:
      description: Free-form tags applied to the compartment.
      type: dict
      returned: always
      sample: {"environment": "development"}
    defined_tags:
      description: Defined tags applied to the compartment.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import (
    OciInfoBase,
)

oci, HAS_OCI_SDK = import_oci_sdk()


class OciCompartmentInfoModule(OciInfoBase):
    """Concrete info adapter for OCI compartments."""

    @property
    def client_class(self):
        return oci.identity.IdentityClient

    results_key = "compartments"
    resource_id_param = "compartment_id"
    resource_get_method = "get_compartment"
    list_resource_method = "list_compartments"
    name_response_field = "name"

    def fetch_resources(self):
        compartment_id = self.module.params.get(self.resource_id_param)
        if compartment_id:
            return self.get_resource_by_id(
                compartment_id,
                self.client.get_compartment,
                compartment_id=compartment_id,
            )

        resources = self.list_all_resources(
            self.client.list_compartments,
            compartment_id=self.module.params["parent_compartment_id"],
            **self.collect_list_filters(("lifecycle_state",)),
        )
        return self.filter_resources_by_display_name(
            resources,
            self.module.params.get(self.name_filter_param),
        )


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        parent_compartment_id=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "parent_compartment_id"]],
    )

    OciCompartmentInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
