# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_alarm_info
short_description: Retrieve alarm information from Oracle Cloud Infrastructure
description:
  - Retrieve details about one or more OCI Monitoring alarms.
  - Use C(alarm_id) to fetch a single alarm, or C(compartment_id) to list
    alarms in a compartment.
  - This is a read-only module and does not modify resources.
version_added: "1.2.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  compartment_id:
    description:
      - The OCID of the compartment to list alarms from.
      - Required when listing resources.
    type: str
  alarm_id:
    description:
      - The OCID of a specific alarm to retrieve.
      - When specified, returns a single resource instead of a list.
    type: str
  name:
    description:
      - Filter listed alarms by name.
      - Only used when C(compartment_id) is provided.
    type: str
  lifecycle_state:
    description:
      - Filter listed alarms by lifecycle state.
      - When unset, OCI lists only alarms in the C(active) state.
      - Only used when C(compartment_id) is provided.
    type: str
    choices: [active, deleting, deleted]
  compartment_id_in_subtree:
    description:
      - When true, also list alarms in all compartments under C(compartment_id).
      - OCI only allows this when C(compartment_id) is the tenancy OCID.
      - Only used when C(compartment_id) is provided.
    type: bool
"""

EXAMPLES = r"""
- name: List alarms in a compartment
  ansible.oci.oci_alarm_info:
    compartment_id: ocid1.compartment.oc1..example

- name: Find an alarm by name
  ansible.oci.oci_alarm_info:
    compartment_id: ocid1.compartment.oc1..example
    name: example-alarm

- name: List alarms across the whole tenancy
  ansible.oci.oci_alarm_info:
    compartment_id: ocid1.tenancy.oc1..example
    compartment_id_in_subtree: true

- name: Get a specific alarm
  ansible.oci.oci_alarm_info:
    alarm_id: ocid1.alarm.oc1..example
"""

RETURN = r"""
alarms:
  description:
    - List of alarms that matched the query.
    - Listing returns alarm summaries. Some fields, such as C(body), C(resolution),
      C(pending_duration), C(message_format), C(repeat_notification_duration),
      C(metric_compartment_id_in_subtree), C(time_created) and C(time_updated),
      are only returned when C(alarm_id) is used.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the alarm.
      type: str
      sample: ocid1.alarm.oc1..example
    name:
      description: The display name of the alarm.
      type: str
      sample: example-alarm
    compartment_id:
      description: The OCID of the compartment containing the alarm.
      type: str
      sample: ocid1.compartment.oc1..example
    metric_compartment_id:
      description: The OCID of the compartment containing the metric being evaluated.
      type: str
      sample: ocid1.compartment.oc1..example
    metric_compartment_id_in_subtree:
      description: Whether metrics in sub-compartments of C(metric_compartment_id) are evaluated.
      type: bool
      sample: false
    namespace:
      description: The source service or application emitting the metric.
      type: str
      sample: oci_computeagent
    resource_group:
      description: The resource group the metric belongs to.
      type: str
      sample: null
    query:
      description: The Monitoring Query Language expression evaluated by the alarm.
      type: str
      sample: CpuUtilization[1m].mean() > 90
    severity:
      description: The perceived severity of the alarm.
      type: str
      sample: CRITICAL
    body:
      description: The human-readable content of the notification delivered.
      type: str
      sample: CPU is high
    pending_duration:
      description: The period of time the condition must hold before the alarm fires, in ISO 8601 format.
      type: str
      sample: PT5M
    resolution:
      description: The time between calculated aggregation windows.
      type: str
      sample: 1m
    message_format:
      description: The format of the notification message.
      type: str
      sample: ONS_OPTIMIZED
    destinations:
      description: The OCIDs of the notification destinations.
      type: list
      elements: str
      sample: ["ocid1.onstopic.oc1..example"]
    repeat_notification_duration:
      description: The period of time between repeated notifications, in ISO 8601 format.
      type: str
      sample: null
    is_enabled:
      description: Whether the alarm is enabled.
      type: bool
      sample: true
    is_notifications_per_metric_dimension_enabled:
      description: Whether a separate notification is sent for each metric stream.
      type: bool
      sample: true
    overrides:
      description: Rule overrides that apply to the alarm.
      type: list
      elements: dict
      sample: []
    lifecycle_state:
      description: The current lifecycle state of the alarm.
      type: str
      sample: ACTIVE
    freeform_tags:
      description: Free-form tags applied to the alarm.
      type: dict
      sample: {"environment": "production"}
    defined_tags:
      description: Defined tags applied to the alarm.
      type: dict
      sample: {"Operations": {"CostCenter": "42"}}
    time_created:
      description: The date and time the alarm was created, in RFC3339 format.
      type: str
      sample: "2026-01-01T00:00:00.000Z"
    time_updated:
      description: The date and time the alarm was last updated, in RFC3339 format.
      type: str
      sample: "2026-01-01T00:00:00.000Z"
  sample:
    - id: ocid1.alarm.oc1..example
      name: example-alarm
      compartment_id: ocid1.compartment.oc1..example
      metric_compartment_id: ocid1.compartment.oc1..example
      namespace: oci_computeagent
      query: CpuUtilization[1m].mean() > 90
      severity: CRITICAL
      destinations: ["ocid1.onstopic.oc1..example"]
      is_enabled: true
      lifecycle_state: ACTIVE
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import (
    OciInfoBase,
)

oci = import_oci_sdk()[0]


class OciAlarmInfoModule(OciInfoBase):
    """Concrete info adapter for OCI Monitoring alarms."""

    @property
    def client_class(self):
        return oci.monitoring.MonitoringClient

    results_key = "alarms"
    resource_id_param = "alarm_id"
    resource_get_method = "get_alarm"
    list_resource_method = "list_alarms"
    list_filter_params = (
        "compartment_id",
        "lifecycle_state",
        "compartment_id_in_subtree",
    )

    def collect_list_filters(self, *param_groups):
        """Convert the lifecycle filter to the SDK enum spelling.

        Args:
            *param_groups: Parameter groups to collect.

        Returns:
            SDK list filters with an uppercase lifecycle state.
        """
        filters = super(OciAlarmInfoModule, self).collect_list_filters(*param_groups)
        if "lifecycle_state" in filters:
            filters["lifecycle_state"] = filters["lifecycle_state"].upper()
        return filters


def main():
    """Build the argument spec and run the info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        alarm_id=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(type="str", choices=["active", "deleting", "deleted"]),
        compartment_id_in_subtree=dict(type="bool"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "alarm_id"]],
    )

    OciAlarmInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
