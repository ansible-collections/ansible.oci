# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_alarm
short_description: Manage an alarm in Oracle Cloud Infrastructure Monitoring
description:
  - Create, update, and delete OCI Monitoring alarms.
version_added: "1.2.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_name_lookup_options
  - ansible.oci.oci_wait_options
  - ansible.oci.oci_tags_options
options:
  state:
    description:
      - The desired state of the alarm.
      - C(absent) deletes the alarm.
    type: str
    choices: [present, absent]
    default: present
  alarm_id:
    description:
      - The OCID of the alarm.
      - When provided, the module manages this exact alarm.
      - Required to distinguish between multiple alarms that share the same
        C(name).
    type: str
  name:
    description:
      - The human-readable name of the alarm, sent to OCI as the display name.
      - Required when creating an alarm.
      - When C(alarm_id) is omitted, the module uses C(compartment_id + name)
        to find an existing alarm.
      - If more than one alarm matches, the task fails and the caller must
        supply C(alarm_id).
    type: str
  compartment_id:
    description:
      - The OCID of the compartment that contains the alarm.
      - Required when creating an alarm.
      - Also scopes name-based lookups when C(alarm_id) is omitted.
      - The module does not move an existing alarm to another compartment.
    type: str
  metric_compartment_id:
    description:
      - The OCID of the compartment that contains the metric being evaluated.
      - Required when creating an alarm.
    type: str
  metric_compartment_id_in_subtree:
    description:
      - Whether metrics in sub-compartments of C(metric_compartment_id) are
        also evaluated.
      - Requires C(metric_compartment_id) to be a tenancy OCID.
    type: bool
  namespace:
    description:
      - The metric namespace to evaluate, for example C(oci_computeagent).
      - Required when creating an alarm.
    type: str
  resource_group:
    description:
      - The metric resource group to evaluate.
    type: str
  query:
    description:
      - The Monitoring Query Language (MQL) expression that defines the alarm
        trigger condition.
      - Required when creating an alarm.
    type: str
  resolution:
    description:
      - The time between calculated aggregation windows, for example C(1m).
    type: str
  pending_duration:
    description:
      - The period of time, as an ISO 8601 duration such as C(PT5M), that the
        condition must hold before the alarm fires.
    type: str
  severity:
    description:
      - The perceived severity of the alarm.
      - Required when creating an alarm.
    type: str
    choices: [critical, error, warning, info]
  body:
    description:
      - The human-readable content of the notification delivered for the alarm.
    type: str
  is_notifications_per_metric_dimension_enabled:
    description:
      - Whether the alarm sends a separate notification for each metric stream.
    type: bool
  message_format:
    description:
      - The format of the notification message.
    type: str
    choices: [raw, pretty_json, ons_optimized]
  destinations:
    description:
      - The OCIDs of the notification topics or streams that receive alarm
        notifications.
      - Required when creating an alarm.
      - The order of the list is not significant.
    type: list
    elements: str
  repeat_notification_duration:
    description:
      - The ISO 8601 duration between repeated notifications while the alarm
        is firing, for example C(PT2H).
    type: str
  is_enabled:
    description:
      - Whether the alarm is enabled.
      - Defaults to C(true), so omitting this option re-enables an alarm that
        was disabled outside of this module. Set it to C(false) to keep an
        alarm disabled.
    type: bool
    default: true
  overrides:
    description:
      - Rule overrides applied to the alarm.
      - The order of the list is significant because overrides are evaluated in
        order, so reordering or resizing the list updates the alarm.
    type: list
    elements: dict
    suboptions:
      pending_duration:
        description:
          - The ISO 8601 pending duration for this override.
        type: str
      severity:
        description:
          - The severity for this override.
        type: str
        choices: [critical, error, warning, info]
      body:
        description:
          - The notification body for this override.
        type: str
      rule_name:
        description:
          - The name that identifies this override rule.
        type: str
        required: true
      query:
        description:
          - The MQL expression for this override.
        type: str
  rule_name:
    description:
      - The name of the base alarm rule, used to identify it in notifications.
    type: str
  notification_version:
    description:
      - The version of the alarm notification to be delivered, for example C(1.X).
    type: str
  notification_title:
    description:
      - The title of the alarm notification, used as the notification subject.
    type: str
  evaluation_slack_duration:
    description:
      - The ISO 8601 duration to wait for late-arriving metric data before
        evaluating the alarm.
    type: str
  alarm_summary:
    description:
      - The summary text of the alarm, available in notification templates.
    type: str
"""

EXAMPLES = r"""
- name: Create an alarm
  ansible.oci.oci_alarm:
    compartment_id: ocid1.compartment.oc1..example
    name: high-cpu
    metric_compartment_id: ocid1.compartment.oc1..example
    namespace: oci_computeagent
    query: CpuUtilization[1m].mean() > 80
    severity: critical
    destinations:
      - ocid1.onstopic.oc1..example
    pending_duration: PT5M
  register: created_alarm

- name: Create an alarm with an override
  ansible.oci.oci_alarm:
    compartment_id: ocid1.compartment.oc1..example
    name: high-memory
    metric_compartment_id: ocid1.compartment.oc1..example
    namespace: oci_computeagent
    query: MemoryUtilization[1m].mean() > 80
    severity: warning
    destinations:
      - ocid1.onstopic.oc1..example
    overrides:
      - rule_name: very-high-memory
        query: MemoryUtilization[1m].mean() > 95
        severity: critical

- name: Disable an alarm by name
  ansible.oci.oci_alarm:
    compartment_id: ocid1.compartment.oc1..example
    name: high-cpu
    is_enabled: false

- name: Delete an alarm
  ansible.oci.oci_alarm:
    state: absent
    alarm_id: "{{ created_alarm.resource.id }}"
"""

RETURN = r"""
resource:
  description:
    - The alarm resource.
    - The alarm display name is returned as C(name) and enumerated values such
      as C(severity) are returned as OCI uppercase values.
  returned: when state != absent
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_ACTIVE,
    OCI_COMMON_ARGS,
    build_model,
    filter_none_values,
    import_oci_sdk,
    normalize_choice_parameters,
    values_differ_as_subset,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

oci = import_oci_sdk()[0]


SEVERITY_VALUES = {
    "critical": "CRITICAL",
    "error": "ERROR",
    "warning": "WARNING",
    "info": "INFO",
}
CHOICE_VALUE_MAPS = {
    ("severity",): SEVERITY_VALUES,
    ("message_format",): {
        "raw": "RAW",
        "pretty_json": "PRETTY_JSON",
        "ons_optimized": "ONS_OPTIMIZED",
    },
    ("overrides", "severity"): SEVERITY_VALUES,
}

CREATE_REQUIRED_FIELDS = [
    "compartment_id",
    "name",
    "metric_compartment_id",
    "namespace",
    "query",
    "severity",
    "destinations",
]
WAIT_FOR_ALARM_STATES = [LIFECYCLE_ACTIVE]

# Module parameters sent to OCI under the same name on create and update.
ALARM_FIELDS = (
    "metric_compartment_id",
    "metric_compartment_id_in_subtree",
    "namespace",
    "resource_group",
    "query",
    "resolution",
    "pending_duration",
    "severity",
    "body",
    "is_notifications_per_metric_dimension_enabled",
    "message_format",
    "destinations",
    "repeat_notification_duration",
    "is_enabled",
    "rule_name",
    "notification_version",
    "notification_title",
    "evaluation_slack_duration",
    "alarm_summary",
    "freeform_tags",
    "defined_tags",
)
OVERRIDE_FIELDS = ("pending_duration", "severity", "body", "rule_name", "query")


def build_override_models(overrides):
    """Build AlarmOverride models from module override dictionaries.

    Args:
        overrides: The list of override dictionaries, or None.

    Returns:
        A list of AlarmOverride models, or None when overrides is None.
    """
    if overrides is None:
        return None
    return [
        build_model(override, oci.monitoring.models.AlarmOverride, keys=OVERRIDE_FIELDS)
        for override in overrides
    ]


def build_create_alarm_details(params):
    """Build the CreateAlarmDetails payload from module parameters.

    Args:
        params: The module parameter dictionary.

    Returns:
        A CreateAlarmDetails model containing only the options that were set.
    """
    details = filter_none_values(
        {
            "display_name": params.get("name"),
            "compartment_id": params.get("compartment_id"),
            "overrides": build_override_models(params.get("overrides")),
            **{field: params.get(field) for field in ALARM_FIELDS},
        }
    )
    return oci.monitoring.models.CreateAlarmDetails(**details)


class OciAlarmModule(OciResourceBase):
    """Concrete resource adapter for OCI Monitoring alarms."""

    @property
    def client_class(self):
        return oci.monitoring.MonitoringClient

    resource_id_param = "alarm_id"
    list_resource_method = "list_alarms"
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "alarm"
    update_method_name = "update_alarm"
    update_details_name = "update_alarm_details"
    update_wait_states = WAIT_FOR_ALARM_STATES
    update_field_specs = (
        UpdateFieldSpec(
            param_name="name",
            resource_field="display_name",
            is_mutable=True,
        ),
        *(
            UpdateFieldSpec(
                param_name=field,
                is_mutable=True,
                compare="sorted_list" if field == "destinations" else None,
            )
            for field in ALARM_FIELDS
            if field not in ("freeform_tags", "defined_tags")
        ),
        UpdateFieldSpec(
            param_name="overrides",
            is_mutable=True,
            compare="ordered_subset_list",
        ),
        UpdateFieldSpec(
            param_name="compartment_id",
            is_mutable=False,
        ),
    )

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_alarm,
            alarm_id=resource_id,
        )

    def hydrate_named_resource(self, resource):
        """Re-fetch a name-lookup match with get_alarm.

        Overridden because list_alarms returns an AlarmSummary that omits
        fields the update planner compares (such as resolution, pending_duration,
        body, and message_format), which would make an unchanged alarm look
        like it needs an update.

        Args:
            resource: The AlarmSummary matched by name.

        Returns:
            The full alarm model, or the summary if the alarm cannot be fetched.
        """
        full_resource = self.get_resource_by_id(resource.id)
        return full_resource if full_resource is not None else resource

    def compare_update_field_values(self, current_value, desired_value, compare=None):
        """Return True when a planned field value differs from the alarm.

        Overridden to add the ``ordered_subset_list`` strategy. Alarm overrides
        are evaluated in list order, so the lists must have equal length and
        each desired override is compared with the current override at the same
        index. Each pair is compared as a subset because OCI echoes defaults
        inside every override that the caller did not set. All other strategies
        are delegated to the base class.

        Args:
            current_value: The value on the current resource.
            desired_value: The value requested by the caller.
            compare: The comparison strategy named by the field spec.

        Returns:
            True when the desired value differs from the current value.
        """
        if compare != "ordered_subset_list":
            return super().compare_update_field_values(
                current_value, desired_value, compare=compare
            )
        current_value = current_value or []
        if len(current_value) != len(desired_value):
            return True
        return any(
            values_differ_as_subset(current_item, desired_item)
            for current_item, desired_item in zip(current_value, desired_value)
        )

    def create_resource(self):
        create_alarm_details = build_create_alarm_details(self.module.params)
        response = self.call_with_retry(
            self.client.create_alarm,
            create_alarm_details=create_alarm_details,
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_ALARM_STATES,
        )

    def build_update_details(self, update_model_fields):
        """Build UpdateAlarmDetails, converting override dictionaries to models.

        Overridden because the planner stores overrides as plain dictionaries
        while the SDK expects AlarmOverride models.

        Args:
            update_model_fields: The changed fields chosen by the update planner.

        Returns:
            An UpdateAlarmDetails model.
        """
        fields = dict(update_model_fields)
        if "overrides" in fields:
            fields["overrides"] = build_override_models(fields["overrides"])
        return oci.monitoring.models.UpdateAlarmDetails(**fields)

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_alarm,
            alarm_id=resource.id,
        )


def main():
    """Run the oci_alarm module."""
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        alarm_id=dict(type="str"),
        metric_compartment_id=dict(type="str"),
        metric_compartment_id_in_subtree=dict(type="bool"),
        namespace=dict(type="str"),
        resource_group=dict(type="str"),
        query=dict(type="str"),
        resolution=dict(type="str"),
        pending_duration=dict(type="str"),
        severity=dict(type="str", choices=list(SEVERITY_VALUES)),
        body=dict(type="str"),
        is_notifications_per_metric_dimension_enabled=dict(type="bool"),
        message_format=dict(
            type="str", choices=list(CHOICE_VALUE_MAPS[("message_format",)])
        ),
        destinations=dict(type="list", elements="str"),
        repeat_notification_duration=dict(type="str"),
        is_enabled=dict(type="bool", default=True),
        overrides=dict(
            type="list",
            elements="dict",
            options=dict(
                pending_duration=dict(type="str"),
                severity=dict(type="str", choices=list(SEVERITY_VALUES)),
                body=dict(type="str"),
                rule_name=dict(type="str", required=True),
                query=dict(type="str"),
            ),
        ),
        rule_name=dict(type="str"),
        notification_version=dict(type="str"),
        notification_title=dict(type="str"),
        evaluation_slack_duration=dict(type="str"),
        alarm_summary=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    normalize_choice_parameters(module, CHOICE_VALUE_MAPS)

    OciAlarmModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
