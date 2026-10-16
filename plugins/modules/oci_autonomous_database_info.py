# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_autonomous_database_info
short_description: Retrieve Autonomous Database information from Oracle Cloud Infrastructure
description:
  - Retrieve details about one or more OCI Autonomous Databases.
  - Use C(autonomous_database_id) to fetch a single database, or
    C(compartment_id) to list databases in a compartment.
  - This is a read-only module and does not modify resources.
version_added: "1.1.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  compartment_id:
    description:
      - The OCID of the compartment to list Autonomous Databases from.
      - Required when listing resources.
    type: str
  autonomous_database_id:
    description:
      - The OCID of a specific Autonomous Database to retrieve.
      - When specified, returns a single resource instead of a list.
    type: str
  name:
    description:
      - Filter listed databases by display name.
      - Only used when C(compartment_id) is provided.
    type: str
  lifecycle_state:
    description:
      - Filter listed databases by lifecycle state.
      - Only used when C(compartment_id) is provided.
    type: str
  db_workload:
    description:
      - Filter listed databases by workload type.
      - Only used when C(compartment_id) is provided.
    type: str
"""

EXAMPLES = r"""
- name: List Autonomous Databases in a compartment
  ansible.oci.oci_autonomous_database_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List available OLTP databases in a compartment by name
  ansible.oci.oci_autonomous_database_info:
    compartment_id: ocid1.compartment.oc1..example
    name: example-adb
    lifecycle_state: AVAILABLE
    db_workload: OLTP

- name: Get a specific Autonomous Database
  ansible.oci.oci_autonomous_database_info:
    autonomous_database_id: ocid1.autonomousdatabase.oc1..example
"""

RETURN = r"""
autonomous_databases:
  description: List of Autonomous Databases that matched the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the Autonomous Database.
      type: str
      returned: always
      sample: ocid1.autonomousdatabase.oc1..example
    name:
      description: The display name of the Autonomous Database.
      type: str
      returned: always
      sample: example-adb
    db_name:
      description: The database name.
      type: str
      returned: always
      sample: exampleadb
    compartment_id:
      description: The OCID of the compartment containing the database.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    lifecycle_state:
      description: The current lifecycle state of the database.
      type: str
      returned: always
      sample: AVAILABLE
    db_workload:
      description: The workload type of the database.
      type: str
      returned: always
      sample: OLTP
    compute_model:
      description: The compute model of the database.
      type: str
      returned: always
      sample: ECPU
    compute_count:
      description: The compute amount (ECPUs) available to the database.
      type: float
      returned: always
      sample: 2.0
    cpu_core_count:
      description: The number of OCPU cores available to the database.
      type: int
      returned: always
      sample: null
    data_storage_size_in_tbs:
      description: The size, in terabytes, of the data volume.
      type: int
      returned: always
      sample: 1
    is_auto_scaling_enabled:
      description: Whether compute auto scaling is enabled.
      type: bool
      returned: always
      sample: true
    is_free_tier:
      description: Whether the database is an Always Free resource.
      type: bool
      returned: always
      sample: false
    is_mtls_connection_required:
      description: Whether mutual TLS is required for connections.
      type: bool
      returned: always
      sample: true
    license_model:
      description: The Oracle license model that applies to the database.
      type: str
      returned: always
      sample: LICENSE_INCLUDED
    db_version:
      description: The Oracle Database version.
      type: str
      returned: always
      sample: "19c"
    subnet_id:
      description: The OCID of the subnet for a private endpoint.
      type: str
      returned: always
      sample: null
    nsg_ids:
      description: The network security groups the private endpoint belongs to.
      type: list
      elements: str
      returned: always
      sample: []
    private_endpoint_ip:
      description: The private endpoint IP address of the database.
      type: str
      returned: always
      sample: null
    whitelisted_ips:
      description: The client IP access control list.
      type: list
      elements: str
      returned: always
      sample: []
    connection_strings:
      description: The connection strings used to connect to the database.
      type: dict
      returned: always
      sample: {}
    freeform_tags:
      description: Free-form tags applied to the database.
      type: dict
      returned: always
      sample: {"environment": "production"}
    defined_tags:
      description: Defined tags applied to the database.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
    time_created:
      description: The date and time the database was created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
  sample:
    - id: ocid1.autonomousdatabase.oc1..example
      name: example-adb
      db_name: exampleadb
      compartment_id: ocid1.compartment.oc1..example
      lifecycle_state: AVAILABLE
      db_workload: OLTP
      compute_model: ECPU
      compute_count: 2.0
      data_storage_size_in_tbs: 1
      is_auto_scaling_enabled: true
      license_model: LICENSE_INCLUDED
      time_created: "2026-01-01T00:00:00.000Z"
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


class OciAutonomousDatabaseInfoModule(OciInfoBase):
    """Concrete info adapter for OCI Autonomous Databases."""

    @property
    def client_class(self):
        return oci.database.DatabaseClient

    results_key = "autonomous_databases"
    resource_id_param = "autonomous_database_id"
    resource_get_method = "get_autonomous_database"
    list_resource_method = "list_autonomous_databases"
    list_filter_params = [
        "compartment_id",
        "lifecycle_state",
        "db_workload",
    ]


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        autonomous_database_id=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(type="str"),
        db_workload=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "autonomous_database_id"]],
    )

    OciAutonomousDatabaseInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
