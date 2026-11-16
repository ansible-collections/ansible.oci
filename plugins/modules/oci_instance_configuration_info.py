# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_instance_configuration_info
short_description: Get OCI Compute instance configuration information
description:
- Get one instance configuration by OCID or list configurations in a compartment.
version_added: 1.3.0
author:
- Ron Gershburg (@ronger4)
extends_documentation_fragment:
- ansible.oci.oci_auth_options
options:
  name:
    description:
    - Filter listed configurations by name.
    - This option applies only to list operations.
    type: str
  compartment_id:
    description:
    - The OCID of the compartment to query.
    - List operations require this option.
    type: str
  instance_configuration_id:
    description:
    - The OCID of the configuration to retrieve.
    - A missing configuration returns an empty list.
    type: str
"""

EXAMPLES = r"""
- name: List configurations in a compartment
  ansible.oci.oci_instance_configuration_info:
    compartment_id: ocid1.compartment.oc1..example

- name: Get one configuration
  ansible.oci.oci_instance_configuration_info:
    instance_configuration_id: ocid1.instanceconfiguration.oc1..example
"""

RETURN = r"""
instance_configurations:
  description: The configurations that matched the query. List operations return summary fields only.
    Unset fields can be null.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the resource.
      type: str
      returned: always
    name:
      description: The name of the configuration.
      type: str
      returned: always
    compartment_id:
      description: The OCID of the compartment that contains this resource.
      type: str
      returned: always
    instance_details:
      description: The Compute template stored in the configuration.
      type: dict
      returned: when a complete configuration is returned
    deferred_fields:
      description: The omitted settings that OCI requires when launching an instance.
      type: list
      returned: when a complete configuration is returned
      elements: str
    freeform_tags:
      description: The free-form tags assigned to this resource.
      type: dict
      returned: always
    defined_tags:
      description: The defined tags, grouped by tag namespace.
      type: dict
      returned: always
    time_created:
      description: The creation time in RFC 3339 format.
      type: str
      returned: always
  sample:
  - id: ocid1.instanceconfiguration.oc1..example
    name: application-template
    compartment_id: ocid1.compartment.oc1..example
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

oci = import_oci_sdk()[0]


class OciInstanceConfigurationInfoModule(OciInfoBase):
    """Info adapter for OCI Compute instance configurations."""

    @property
    def client_class(self):
        """Return the Compute Management client class.

        Returns:
            The OCI SDK client class.
        """
        return oci.core.ComputeManagementClient

    results_key = "instance_configurations"
    resource_id_param = "instance_configuration_id"
    resource_get_method = "get_instance_configuration"
    list_resource_method = "list_instance_configurations"
    list_filter_params = ("compartment_id",)


def main():
    """Run the instance configuration info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        instance_configuration_id=dict(type="str"),
        name=dict(type="str"),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "instance_configuration_id"]],
    )
    OciInstanceConfigurationInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
