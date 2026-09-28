# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_volume_backup_policy_info
short_description: Retrieve volume backup policy information from Oracle Cloud Infrastructure
description:
  - Retrieve details about OCI Block Volume backup policies.
  - This is a read-only module and does not modify resources.
version_added: "1.1.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  volume_backup_policy_id:
    description:
      - The OCID of a specific volume backup policy to fetch.
      - Takes precedence over C(compartment_id) when both are supplied.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment whose available policies are listed.
      - When neither C(compartment_id) nor C(volume_backup_policy_id) is
        supplied, Oracle-defined backup policies are listed.
    type: str
  name:
    description:
      - Filter listed policies by exact display name.
      - Applies to lists with or without C(compartment_id), and is ignored
        when C(volume_backup_policy_id) is supplied.
    type: str
"""

EXAMPLES = r"""
- name: List Oracle-defined backup policies
  ansible.oci.oci_volume_backup_policy_info: {}

- name: List backup policies in a compartment
  ansible.oci.oci_volume_backup_policy_info:
    compartment_id: ocid1.compartment.oc1..example

- name: Find policies by name in a compartment
  ansible.oci.oci_volume_backup_policy_info:
    compartment_id: ocid1.compartment.oc1..example
    name: application-daily-backups

- name: Get a specific backup policy
  ansible.oci.oci_volume_backup_policy_info:
    volume_backup_policy_id: ocid1.volumebackuppolicy.oc1..example
"""

RETURN = r"""
volume_backup_policies:
  description:
    - Policies that matched the query.
    - A lookup by ID returns a one-item list when found and an empty list
      when the policy does not exist.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the volume backup policy.
      type: str
      returned: always
      sample: ocid1.volumebackuppolicy.oc1..example
    name:
      description: The display name of the policy.
      type: str
      returned: always
      sample: application-daily-backups
    compartment_id:
      description: The compartment containing a user-defined policy.
      type: str
      returned: when available
      sample: ocid1.compartment.oc1..example
    destination_region:
      description: The paired region for scheduled backup copies.
      type: str
      returned: when configured
      sample: us-ashburn-1
    schedules:
      description: Schedules configured on the policy.
      type: list
      elements: dict
      returned: always
      contains:
        backup_type:
          description: The type of backup created by the schedule.
          type: str
          sample: INCREMENTAL
        period:
          description: The schedule frequency.
          type: str
          sample: ONE_DAY
        offset_seconds:
          description: The numeric schedule offset, in seconds.
          type: int
          sample: 7200
        offset_type:
          description: How the schedule offset is defined.
          type: str
          sample: STRUCTURED
        hour_of_day:
          description: The structured hour of the day.
          type: int
          sample: 2
        day_of_week:
          description: The structured day of the week.
          type: str
          sample: SUNDAY
        day_of_month:
          description: The structured day of the month.
          type: int
          sample: 1
        month:
          description: The structured month of the year.
          type: str
          sample: JANUARY
        retention_seconds:
          description: The legacy retention duration, in seconds.
          type: int
          sample: 604800
        time_zone:
          description: The schedule time zone.
          type: str
          sample: UTC
        retention_period:
          description: The configured retention duration.
          type: dict
          contains:
            retention_time_amount:
              description: Numeric length of the retention period.
              type: int
              sample: 30
            retention_time_unit:
              description: Unit for the retention amount.
              type: str
              sample: DAYS
        is_prevent_deletion_enabled:
          description: Whether deletion prevention is enabled.
          type: bool
          sample: true
        is_retention_lock_enabled:
          description: Whether retention lock is enabled.
          type: bool
          sample: true
    freeform_tags:
      description: Free-form tags applied to the policy.
      type: dict
      returned: when available
      sample: {"environment": "production"}
    defined_tags:
      description: Defined tags applied to the policy.
      type: dict
      returned: when available
      sample: {"Operations": {"CostCenter": "42"}}
    time_created:
      description: The policy creation time in RFC3339 format.
      type: str
      returned: always
      sample: "2026-08-27T10:00:00.000Z"
  sample:
    - id: ocid1.volumebackuppolicy.oc1..example
      name: application-daily-backups
      compartment_id: ocid1.compartment.oc1..example
      destination_region: null
      schedules:
        - backup_type: INCREMENTAL
          period: ONE_DAY
          offset_type: STRUCTURED
          hour_of_day: 2
          retention_seconds: 604800
          time_zone: UTC
      freeform_tags: {"environment": "production"}
      defined_tags: {"Operations": {"CostCenter": "42"}}
      time_created: "2026-08-27T10:00:00.000Z"
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


class OciVolumeBackupPolicyInfoModule(OciInfoBase):
    """Concrete info adapter for OCI volume backup policies."""

    @property
    def client_class(self):
        return oci.core.BlockstorageClient

    results_key = "volume_backup_policies"
    resource_id_param = "volume_backup_policy_id"
    resource_id_kwarg = "policy_id"
    resource_get_method = "get_volume_backup_policy"
    list_resource_method = "list_volume_backup_policies"
    list_filter_params = ["compartment_id"]


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        volume_backup_policy_id=dict(type="str"),
        compartment_id=dict(type="str"),
        name=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciVolumeBackupPolicyInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
