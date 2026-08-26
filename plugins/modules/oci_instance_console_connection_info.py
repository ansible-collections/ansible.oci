# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_instance_console_connection_info
short_description: Retrieve Compute instance console connection information from Oracle Cloud Infrastructure
description:
  - Retrieve details about one or more OCI Compute instance console connections.
  - Use C(instance_console_connection_id) to fetch a single console connection, or
    C(compartment_id) to list console connections in a compartment.
  - Console connections have no display name in the OCI API, so C(instance_id) is
    the supported list filter instead of a name-based lookup.
  - This is a read-only module and does not modify resources.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  compartment_id:
    description:
      - The OCID of the compartment to list console connections from.
      - Required when listing resources.
    type: str
  instance_console_connection_id:
    description:
      - The OCID of a specific console connection to retrieve.
      - When specified, returns a single resource instead of a list.
    type: str
  instance_id:
    description:
      - Filter listed console connections by instance.
      - Only used when C(compartment_id) is provided.
    type: str
  lifecycle_state:
    description:
      - Filter returned console connections by lifecycle state.
      - Applied locally after retrieval, because the OCI list API for this
        resource does not support a server-side lifecycle state filter.
      - Use C(ACTIVE) to discover the currently open/usable console
        connections for an instance or compartment.
    type: str
"""

EXAMPLES = r"""
- name: List all console connections in a compartment
  ansible.oci.oci_instance_console_connection_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List the active console connections for an instance
  ansible.oci.oci_instance_console_connection_info:
    compartment_id: ocid1.compartment.oc1..example
    instance_id: ocid1.instance.oc1..example
    lifecycle_state: ACTIVE

- name: Get a specific console connection
  ansible.oci.oci_instance_console_connection_info:
    instance_console_connection_id: ocid1.instanceconsoleconnection.oc1..example
"""

RETURN = r"""
instance_console_connections:
  description: List of console connections that matched the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the console connection.
      type: str
      returned: always
      sample: ocid1.instanceconsoleconnection.oc1..example
    compartment_id:
      description: The OCID of the compartment containing the console connection.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    instance_id:
      description: The OCID of the instance the console connection belongs to.
      type: str
      returned: always
      sample: ocid1.instance.oc1..example
    lifecycle_state:
      description: The current lifecycle state of the console connection.
      type: str
      returned: always
      sample: ACTIVE
    connection_string:
      description: The SSH connection string for the console connection.
      type: str
      returned: always
      sample: "ssh -o ProxyCommand='ssh -W %h:%p -p 443 ocid1...@instance-console.us-phoenix-1.oci.oraclecloud.com' -p 22 ocid1.instance.oc1..example"
    vnc_connection_string:
      description: The VNC connection string for the console connection.
      type: str
      returned: always
      sample: null
    fingerprint:
      description: The SSH public key fingerprint recorded for the console connection.
      type: str
      returned: always
      sample: "12:34:56:78:9a:bc:de:f0:12:34:56:78:9a:bc:de:f0"
    service_host_key_fingerprint:
      description: The SSH host key fingerprint of the console service, once assigned.
      type: str
      returned: always
      sample: null
    freeform_tags:
      description: Free-form tags applied to the console connection.
      type: dict
      returned: always
      sample: {"environment": "production"}
    defined_tags:
      description: Defined tags applied to the console connection.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
  sample:
    - id: ocid1.instanceconsoleconnection.oc1..example
      compartment_id: ocid1.compartment.oc1..example
      instance_id: ocid1.instance.oc1..example
      lifecycle_state: ACTIVE
      connection_string: "ssh -o ProxyCommand='ssh -W %h:%p -p 443 ocid1...@instance-console.example.com' -p 22 ocid1.instance.oc1..example"
      vnc_connection_string: null
      fingerprint: "12:34:56:78:9a:bc:de:f0:12:34:56:78:9a:bc:de:f0"
      service_host_key_fingerprint: null
      freeform_tags: {"environment": "production"}
      defined_tags: {"Operations": {"CostCenter": "42"}}
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import (
    OciInfoBase,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]


class OciInstanceConsoleConnectionInfoModule(OciInfoBase):
    """Concrete info adapter for OCI Compute instance console connections.

    Console connections have no display name in the OCI API, so this module
    does not use the shared name-lookup filter. ``lifecycle_state`` is
    instead applied locally after retrieval for both the get and list paths,
    mirroring the resource module's own active-connection lookup, because the
    OCI list API for this resource has no server-side lifecycle state filter.
    """

    @property
    def client_class(self):
        return oci.core.ComputeClient

    results_key = "instance_console_connections"
    resource_id_param = "instance_console_connection_id"
    resource_get_method = "get_instance_console_connection"
    list_resource_method = "list_instance_console_connections"
    list_filter_params = [
        "compartment_id",
        "instance_id",
    ]
    name_filter_param = None

    def fetch_resources(self):
        resources = super().fetch_resources()
        lifecycle_state = self.module.params.get("lifecycle_state")
        if lifecycle_state is None:
            return resources
        return [
            resource
            for resource in resources
            if getattr(resource, "lifecycle_state", None) == lifecycle_state
        ]


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        instance_console_connection_id=dict(type="str"),
        instance_id=dict(type="str"),
        lifecycle_state=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "instance_console_connection_id"]],
    )

    OciInstanceConsoleConnectionInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
