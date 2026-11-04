# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_alarm_suppression_info
short_description: Retrieve alarm suppression information from Oracle Cloud Infrastructure
description:
  - Retrieve details about one or more OCI Monitoring alarm suppressions.
  - Use C(alarm_suppression_id) to fetch a single suppression, or C(alarm_id)
    or C(compartment_id) to list suppressions.
  - This is a read-only module and does not modify resources.
version_added: "1.2.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  alarm_suppression_id:
    description:
      - The OCID of a specific alarm suppression to retrieve.
      - When specified, returns a single resource instead of a list.
    type: str
  alarm_id:
    description:
      - List suppressions that target this alarm.
    type: str
  compartment_id:
    description:
      - List suppressions in this compartment.
      - When C(target_type) is not set, this lists every suppression defined
        in the compartment, including suppressions that target individual
        alarms.
    type: str
  compartment_id_in_subtree:
    description:
      - When true, also list suppressions in all compartments under
        C(compartment_id).
      - OCI only allows this when C(compartment_id) is the tenancy OCID.
    type: bool
  target_type:
    description:
      - List only suppressions with this target type.
      - C(alarm) requires C(alarm_id) and C(compartment) requires
        C(compartment_id).
    type: str
    choices: [alarm, compartment]
  is_all_suppressions:
    description:
      - When true, list every suppression that affects C(alarm_id), including
        suppressions that target its compartment or tenancy.
      - Requires C(alarm_id).
    type: bool
  name:
    description:
      - Filter listed suppressions by name.
    type: str
  level:
    description:
      - Filter listed suppressions by level.
    type: str
    choices: [alarm, dimension]
  lifecycle_state:
    description:
      - Filter listed suppressions by lifecycle state.
      - When unset, OCI lists only suppressions in the C(active) state.
    type: str
    choices: [active, deleted]
"""

EXAMPLES = r"""
- name: List suppressions for an alarm
  ansible.oci.oci_alarm_suppression_info:
    alarm_id: ocid1.alarm.oc1..example

- name: List every suppression that affects an alarm
  ansible.oci.oci_alarm_suppression_info:
    alarm_id: ocid1.alarm.oc1..example
    is_all_suppressions: true

- name: List compartment-wide suppressions
  ansible.oci.oci_alarm_suppression_info:
    compartment_id: ocid1.compartment.oc1..example
    target_type: compartment

- name: Find a suppression by name
  ansible.oci.oci_alarm_suppression_info:
    alarm_id: ocid1.alarm.oc1..example
    name: maintenance-window

- name: Get a specific suppression
  ansible.oci.oci_alarm_suppression_info:
    alarm_suppression_id: ocid1.alarmsuppression.oc1..example
"""

RETURN = r"""
alarm_suppressions:
  description: List of alarm suppressions that matched the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the alarm suppression.
      type: str
      sample: ocid1.alarmsuppression.oc1..example
    name:
      description: The display name of the alarm suppression.
      type: str
      sample: maintenance-window
    compartment_id:
      description: The OCID of the compartment containing the alarm suppression.
      type: str
      sample: ocid1.compartment.oc1..example
    alarm_suppression_target:
      description: The alarm or compartment that the suppression applies to.
      type: dict
      sample: {"target_type": "ALARM", "alarm_id": "ocid1.alarm.oc1..example"}
    level:
      description: The level of the alarm suppression.
      type: str
      sample: ALARM
    description:
      description: The description of the alarm suppression.
      type: str
      sample: Planned database maintenance
    dimensions:
      description: The dimension filter of the alarm suppression.
      type: dict
      sample: {}
    time_suppress_from:
      description: The start date and time of the suppression, in RFC3339 format.
      type: str
      sample: "2026-11-03T01:00:00+00:00"
    time_suppress_until:
      description: The end date and time of the suppression, in RFC3339 format.
      type: str
      sample: "2026-11-03T05:00:00+00:00"
    suppression_conditions:
      description: Conditions that limit when the suppression applies.
      type: list
      elements: dict
      sample: []
    lifecycle_state:
      description: The current lifecycle state of the alarm suppression.
      type: str
      sample: ACTIVE
    freeform_tags:
      description: Free-form tags applied to the alarm suppression.
      type: dict
      sample: {"environment": "production"}
    defined_tags:
      description: Defined tags applied to the alarm suppression.
      type: dict
      sample: {"Operations": {"CostCenter": "42"}}
    time_created:
      description: The date and time the alarm suppression was created, in RFC3339 format.
      type: str
      sample: "2026-11-02T00:00:00+00:00"
    time_updated:
      description: The date and time the alarm suppression was last updated, in RFC3339 format.
      type: str
      sample: "2026-11-02T00:00:00+00:00"
  sample:
    - id: ocid1.alarmsuppression.oc1..example
      name: maintenance-window
      compartment_id: ocid1.compartment.oc1..example
      alarm_suppression_target:
        target_type: ALARM
        alarm_id: ocid1.alarm.oc1..example
      level: ALARM
      time_suppress_from: "2026-11-03T01:00:00+00:00"
      time_suppress_until: "2026-11-03T05:00:00+00:00"
      lifecycle_state: ACTIVE
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
    normalize_choice_parameters,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import (
    OciInfoBase,
)

oci = import_oci_sdk()[0]


CHOICE_VALUE_MAPS = {
    ("target_type",): {"alarm": "ALARM", "compartment": "COMPARTMENT"},
    ("level",): {"alarm": "ALARM", "dimension": "DIMENSION"},
    ("lifecycle_state",): {"active": "ACTIVE", "deleted": "DELETED"},
}


class OciAlarmSuppressionInfoModule(OciInfoBase):
    """Concrete info adapter for OCI Monitoring alarm suppressions."""

    @property
    def client_class(self):
        return oci.monitoring.MonitoringClient

    results_key = "alarm_suppressions"
    resource_id_param = "alarm_suppression_id"
    resource_get_method = "get_alarm_suppression"
    list_resource_method = "list_alarm_suppressions"
    list_filter_params = (
        "alarm_id",
        "compartment_id",
        "compartment_id_in_subtree",
        "target_type",
        "is_all_suppressions",
        "level",
        "lifecycle_state",
    )


def main():
    """Build the argument spec and run the info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        alarm_suppression_id=dict(type="str"),
        alarm_id=dict(type="str"),
        compartment_id=dict(type="str"),
        compartment_id_in_subtree=dict(type="bool"),
        target_type=dict(
            type="str", choices=list(CHOICE_VALUE_MAPS[("target_type",)])
        ),
        is_all_suppressions=dict(type="bool"),
        name=dict(type="str"),
        level=dict(type="str", choices=list(CHOICE_VALUE_MAPS[("level",)])),
        lifecycle_state=dict(
            type="str", choices=list(CHOICE_VALUE_MAPS[("lifecycle_state",)])
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["alarm_suppression_id", "alarm_id", "compartment_id"]],
        required_if=[
            ["target_type", "alarm", ["alarm_id"]],
            ["target_type", "compartment", ["compartment_id"]],
        ],
        required_by={
            "compartment_id_in_subtree": ["compartment_id"],
            "is_all_suppressions": ["alarm_id"],
        },
        mutually_exclusive=[["alarm_id", "compartment_id_in_subtree"]],
    )

    normalize_choice_parameters(module, CHOICE_VALUE_MAPS)
    OciAlarmSuppressionInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
