# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_autonomous_database_clone_info
short_description: List the clones of an Autonomous Database in Oracle Cloud Infrastructure
description:
  - List the clones of an OCI Autonomous Database in a compartment.
version_added: "1.2.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
notes:
  - Use M(ansible.oci.oci_autonomous_database_info) to retrieve a single clone
    by its OCID.
options:
  compartment_id:
    description:
      - The OCID of the compartment to list clones from.
    type: str
    required: true
  source_id:
    description:
      - The OCID of the source Autonomous Database whose clones are listed.
    type: str
    required: true
  name:
    description:
      - Return only clones with this exact display name.
    type: str
  lifecycle_state:
    description:
      - Return only clones in this lifecycle state, for example C(AVAILABLE).
    type: str
  refreshable_only:
    description:
      - Whether to return only refreshable clones.
    type: bool
    default: false
"""

EXAMPLES = r"""
- name: List the clones of an Autonomous Database
  ansible.oci.oci_autonomous_database_clone_info:
    compartment_id: ocid1.compartment.oc1..example
    source_id: ocid1.autonomousdatabase.oc1..source

- name: List available refreshable clones of an Autonomous Database
  ansible.oci.oci_autonomous_database_clone_info:
    compartment_id: ocid1.compartment.oc1..example
    source_id: ocid1.autonomousdatabase.oc1..source
    lifecycle_state: AVAILABLE
    refreshable_only: true
"""

RETURN = r"""
autonomous_databases:
  description: The clones that matched the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the clone.
      type: str
      returned: always
      sample: ocid1.autonomousdatabase.oc1..example
    name:
      description: The display name of the clone.
      type: str
      returned: always
      sample: example-adb-clone
    db_name:
      description: The database name of the clone.
      type: str
      returned: always
      sample: exampleclone
    compartment_id:
      description: The OCID of the compartment containing the clone.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    lifecycle_state:
      description: The current lifecycle state of the clone.
      type: str
      returned: always
      sample: AVAILABLE
    source_id:
      description: The OCID of the source database the clone was created from.
      type: str
      returned: always
      sample: ocid1.autonomousdatabase.oc1..source
    clone_type:
      description: The clone type.
      type: str
      returned: always
      sample: METADATA
    is_refreshable_clone:
      description: Whether the clone is a refreshable clone.
      type: bool
      returned: always
      sample: false
    refreshable_mode:
      description: How a refreshable clone is refreshed.
      type: str
      returned: always
      sample: null
    open_mode:
      description: Whether the clone is open read-only or read-write.
      type: str
      returned: always
      sample: READ_WRITE
    freeform_tags:
      description: Free-form tags applied to the clone.
      type: dict
      returned: always
      sample: {"environment": "test"}
    defined_tags:
      description: Defined tags applied to the clone.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
    time_created:
      description: The date and time the clone was created, in RFC 3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
  sample:
    - id: ocid1.autonomousdatabase.oc1..example
      name: example-adb-clone
      db_name: exampleclone
      compartment_id: ocid1.compartment.oc1..example
      lifecycle_state: AVAILABLE
      source_id: ocid1.autonomousdatabase.oc1..source
      clone_type: METADATA
      is_refreshable_clone: false
      open_mode: READ_WRITE
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

REFRESHABLE_CLONE_TYPE = "REFRESHABLE_CLONE"


class OciAutonomousDatabaseCloneInfoModule(OciInfoBase):
    """Concrete info adapter for the clones of one Autonomous Database."""

    @property
    def client_class(self):
        return oci.database.DatabaseClient

    results_key = "autonomous_databases"

    def fetch_resources(self):
        """List the clones of the source database that match the filters.

        The inherited list flow passes module parameters to the SDK under
        their own names. It is overridden because
        ``list_autonomous_database_clones`` takes the source OCID as
        ``autonomous_database_id`` and filters refreshable clones through
        ``clone_type``, neither of which matches a module parameter.

        Returns:
            The matching ``AutonomousDatabaseSummary`` models.
        """
        params = self.module.params
        list_filters = self.collect_list_filters(("compartment_id", "lifecycle_state"))
        list_filters["autonomous_database_id"] = params["source_id"]
        if params.get("refreshable_only"):
            list_filters["clone_type"] = REFRESHABLE_CLONE_TYPE
        resources = self.list_all_resources(
            self.client.list_autonomous_database_clones,
            **list_filters
        )
        return self.filter_resources_by_display_name(
            resources,
            params.get(self.name_filter_param),
        )


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str", required=True),
        source_id=dict(type="str", required=True),
        name=dict(type="str"),
        lifecycle_state=dict(type="str"),
        refreshable_only=dict(type="bool", default=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciAutonomousDatabaseCloneInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
