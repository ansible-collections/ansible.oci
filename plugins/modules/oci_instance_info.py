# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_instance_info
short_description: Retrieve Compute instance information from Oracle Cloud Infrastructure
description:
  - Retrieve details about one or more OCI Compute instances.
  - Use C(instance_id) to fetch a single instance, or C(compartment_id) to
    list instances in a compartment.
  - This is a read-only module and does not modify resources.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - oracle.oci.oci_auth_options
  - oracle.oci.oci_info_filter_options
options:
  compartment_id:
    description:
      - The OCID of the compartment to list instances from.
      - Required when listing resources.
    type: str
  instance_id:
    description:
      - The OCID of a specific instance to retrieve.
      - When specified, returns a single resource instead of a list.
    type: str
  availability_domain:
    description:
      - Filter listed instances by availability domain.
      - Only used when C(compartment_id) is provided.
    type: str
"""

EXAMPLES = r"""
- name: List all instances in a compartment
  oracle.oci.oci_instance_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List running instances in a compartment filtered by name
  oracle.oci.oci_instance_info:
    compartment_id: ocid1.compartment.oc1..example
    name: example-instance
    lifecycle_state: RUNNING

- name: List instances in a specific availability domain
  oracle.oci.oci_instance_info:
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1

- name: Get a specific instance
  oracle.oci.oci_instance_info:
    instance_id: ocid1.instance.oc1..example
"""

RETURN = r"""
instances:
  description: List of instances that matched the query.
  returned: always
  type: list
  elements: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.oracle.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.oracle.oci.plugins.module_utils.oci_info import (
    OciInfoBase,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]


class OciInstanceInfoModule(OciInfoBase):
    """Concrete info adapter for OCI Compute instances."""

    @property
    def client_class(self):
        return oci.core.ComputeClient

    results_key = "instances"
    resource_id_param = "instance_id"
    resource_get_method = "get_instance"
    list_resource_method = "list_instances"
    list_filter_params = [
        "compartment_id",
        "availability_domain",
        "lifecycle_state",
    ]


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        instance_id=dict(type="str"),
        availability_domain=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "instance_id"]],
    )

    OciInstanceInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
