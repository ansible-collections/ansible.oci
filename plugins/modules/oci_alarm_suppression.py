# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_alarm_suppression
short_description: Manage an alarm suppression in Oracle Cloud Infrastructure Monitoring
description:
  - Create and delete OCI Monitoring alarm suppressions.
  - A suppression stops notifications for one alarm, or for every alarm in a
    compartment, during a time window.
version_added: "1.2.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_name_lookup_options
  - ansible.oci.oci_wait_options
  - ansible.oci.oci_tags_options
notes:
  - OCI does not support updating an alarm suppression. When an existing
    suppression differs from any supplied option, including tags, the task
    fails. Delete the suppression and create it again to change it.
  - Time values accept fractional seconds of up to six digits (microseconds),
    and the C(T) and C(Z) characters must be uppercase.
options:
  state:
    description:
      - The desired state of the alarm suppression.
      - C(absent) deletes the alarm suppression.
    type: str
    choices: [present, absent]
    default: present
  alarm_suppression_id:
    description:
      - The OCID of the alarm suppression.
      - When provided, the module manages this exact alarm suppression.
      - Required to distinguish between multiple alarm suppressions that share
        the same C(name).
    type: str
  name:
    description:
      - The human-readable name of the alarm suppression, sent to OCI as the
        display name.
      - Required when creating an alarm suppression.
      - When C(alarm_suppression_id) is omitted, the module finds an existing
        suppression by C(name) among the suppressions that target C(alarm_id)
        or C(compartment_id).
      - If more than one suppression matches, the task fails and the caller
        must supply C(alarm_suppression_id).
    type: str
  alarm_id:
    description:
      - The OCID of the alarm to suppress.
      - Mutually exclusive with C(compartment_id).
      - One of C(alarm_id) or C(compartment_id) is required when creating an
        alarm suppression or looking it up by C(name).
    type: str
  compartment_id:
    description:
      - The OCID of the compartment whose alarms are suppressed.
      - Mutually exclusive with C(alarm_id).
      - One of C(alarm_id) or C(compartment_id) is required when creating an
        alarm suppression or looking it up by C(name).
    type: str
  compartment_id_in_subtree:
    description:
      - Whether alarms in sub-compartments of C(compartment_id) are also
        suppressed.
      - Requires C(compartment_id) to be a tenancy OCID.
      - Mutually exclusive with C(alarm_id).
    type: bool
  description:
    description:
      - A description of the alarm suppression, such as the reason for it.
    type: str
  level:
    description:
      - The level of the alarm suppression.
      - C(alarm) suppresses the entire alarm, regardless of dimension.
      - C(dimension) suppresses only alarm state entries that match
        C(dimensions).
      - OCI uses C(dimension) when this option is not set.
    type: str
    choices: [alarm, dimension]
  dimensions:
    description:
      - The dimension key-value pairs that alarm state entries must include to
        be suppressed, for example C(resourceId=ocid1.instance.oc1..example).
      - Required when C(level=dimension).
    type: dict
  time_suppress_from:
    description:
      - The start date and time of the suppression, inclusive, in RFC3339
        format such as C(2026-11-03T01:00:00Z).
      - The value must include a time zone offset or C(Z).
      - Required when creating an alarm suppression.
    type: str
  time_suppress_until:
    description:
      - The end date and time of the suppression, inclusive, in RFC3339 format
        such as C(2026-11-03T05:00:00Z).
      - The value must include a time zone offset or C(Z).
      - Required when creating an alarm suppression.
    type: str
  suppression_conditions:
    description:
      - Conditions that limit when the suppression applies within the
        C(time_suppress_from) to C(time_suppress_until) window.
      - The order of the list is significant.
    type: list
    elements: dict
    suboptions:
      condition_type:
        description:
          - The type of suppression condition.
        type: str
        choices: [recurrence]
        default: recurrence
      suppression_recurrence:
        description:
          - The frequency and start time of the recurring suppression, as an
            RFC 5545 recurrence rule such as C(FREQ=DAILY;BYHOUR=10).
          - Only C(FREQ) values C(DAILY) and C(WEEKLY) are supported. Start
            times are in UTC.
        type: str
        required: true
      suppression_duration:
        description:
          - The ISO 8601 duration of each recurring suppression, between
            C(PT1M) and C(PT24H).
        type: str
        required: true
"""

EXAMPLES = r"""
- name: Suppress an alarm during a maintenance window
  ansible.oci.oci_alarm_suppression:
    alarm_id: ocid1.alarm.oc1..example
    name: maintenance-window
    description: Planned database maintenance
    level: alarm
    time_suppress_from: "2026-11-03T01:00:00Z"
    time_suppress_until: "2026-11-03T05:00:00Z"
  register: suppression

- name: Suppress an alarm for one instance only
  ansible.oci.oci_alarm_suppression:
    alarm_id: ocid1.alarm.oc1..example
    name: instance-rebuild
    level: dimension
    dimensions:
      resourceId: ocid1.instance.oc1..example
    time_suppress_from: "2026-11-03T01:00:00Z"
    time_suppress_until: "2026-11-04T01:00:00Z"

- name: Suppress every alarm in a compartment for two hours each night
  ansible.oci.oci_alarm_suppression:
    compartment_id: ocid1.compartment.oc1..example
    name: nightly-batch
    level: alarm
    time_suppress_from: "2026-11-01T00:00:00Z"
    time_suppress_until: "2026-12-01T00:00:00Z"
    suppression_conditions:
      - suppression_recurrence: FREQ=DAILY;BYHOUR=2
        suppression_duration: PT2H

- name: Delete an alarm suppression
  ansible.oci.oci_alarm_suppression:
    state: absent
    alarm_suppression_id: "{{ suppression.resource.id }}"

- name: Change a suppression by deleting it and creating it again
  block:
    - name: Delete the existing suppression
      ansible.oci.oci_alarm_suppression:
        state: absent
        alarm_id: ocid1.alarm.oc1..example
        name: maintenance-window

    - name: Create the suppression with the new window
      ansible.oci.oci_alarm_suppression:
        alarm_id: ocid1.alarm.oc1..example
        name: maintenance-window
        level: alarm
        time_suppress_from: "2026-11-03T02:00:00Z"
        time_suppress_until: "2026-11-03T06:00:00Z"
"""

RETURN = r"""
resource:
  description:
    - The alarm suppression resource.
    - The display name is returned as C(name) and enumerated values such as
      C(level) are returned as OCI uppercase values.
  returned: when state != absent
  type: dict
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
      sample: [{"condition_type": "RECURRENCE", "suppression_recurrence": "FREQ=DAILY;BYHOUR=2", "suppression_duration": "PT2H"}]
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
"""

from datetime import datetime

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_ACTIVE,
    OCI_COMMON_ARGS,
    build_model,
    filter_none_values,
    import_oci_sdk,
    normalize_choice_parameters,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

oci = import_oci_sdk()[0]


CHOICE_VALUE_MAPS = {
    ("level",): {"alarm": "ALARM", "dimension": "DIMENSION"},
    ("suppression_conditions", "condition_type"): {"recurrence": "RECURRENCE"},
}

CREATE_REQUIRED_FIELDS = ["name", "time_suppress_from", "time_suppress_until"]
WAIT_FOR_SUPPRESSION_STATES = [LIFECYCLE_ACTIVE]
TIME_PARAMS = ("time_suppress_from", "time_suppress_until")
# strptime accepts "Z" for %z, which RFC3339 timestamps commonly use.
RFC3339_FORMATS = ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z")
IMMUTABLE_REASON = "OCI does not support updating alarm suppressions"

# Module parameters sent to OCI under the same name on create.
SUPPRESSION_FIELDS = (
    "description",
    "level",
    "dimensions",
    "time_suppress_from",
    "time_suppress_until",
)
# Module parameters stored on the suppression's alarm_suppression_target.
TARGET_FIELDS = ("alarm_id", "compartment_id", "compartment_id_in_subtree")
RECURRENCE_FIELDS = ("suppression_recurrence", "suppression_duration")


def parse_rfc3339(value):
    """Parse an RFC3339 timestamp into a timezone-aware datetime.

    Args:
        value: The timestamp string.

    Returns:
        A timezone-aware datetime.

    Raises:
        ValueError: If the value is not an RFC3339 timestamp with a time zone.
    """
    for time_format in RFC3339_FORMATS:
        try:
            return datetime.strptime(value, time_format)
        except ValueError:
            continue
    raise ValueError(f"{value} is not an RFC3339 timestamp with a time zone")


def normalize_time_parameters(module):
    """Replace RFC3339 time parameters with datetimes.

    OCI returns suppression times as datetimes, so converting the inputs lets
    the update planner compare them directly and lets the SDK serialize them.

    Args:
        module: The active AnsibleModule.
    """
    for param_name in TIME_PARAMS:
        value = module.params.get(param_name)
        if value is None:
            continue
        try:
            module.params[param_name] = parse_rfc3339(value)
        except ValueError as exc:
            module.fail_json(msg=f"Invalid {param_name}: {exc}")


def build_suppression_target(params):
    """Build the alarm or compartment suppression target from module parameters.

    Args:
        params: The module parameter dictionary.

    Returns:
        An AlarmSuppressionAlarmTarget when alarm_id is set, otherwise an
        AlarmSuppressionCompartmentTarget.
    """
    if params.get("alarm_id"):
        return oci.monitoring.models.AlarmSuppressionAlarmTarget(
            alarm_id=params["alarm_id"]
        )
    return build_model(
        params,
        oci.monitoring.models.AlarmSuppressionCompartmentTarget,
        keys=("compartment_id", "compartment_id_in_subtree"),
    )


def build_create_alarm_suppression_details(params):
    """Build the CreateAlarmSuppressionDetails payload from module parameters.

    Args:
        params: The module parameter dictionary.

    Returns:
        A CreateAlarmSuppressionDetails model containing only the options that
        were set.
    """
    conditions = params.get("suppression_conditions")
    if conditions is not None:
        conditions = [
            build_model(condition, oci.monitoring.models.Recurrence, keys=RECURRENCE_FIELDS)
            for condition in conditions
        ]
    details = filter_none_values(
        {
            "display_name": params.get("name"),
            "alarm_suppression_target": build_suppression_target(params),
            "suppression_conditions": conditions,
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
            **{field: params.get(field) for field in SUPPRESSION_FIELDS},
        }
    )
    return oci.monitoring.models.CreateAlarmSuppressionDetails(**details)


class OciAlarmSuppressionModule(OciResourceBase):
    """Concrete resource adapter for OCI Monitoring alarm suppressions."""

    @property
    def client_class(self):
        return oci.monitoring.MonitoringClient

    resource_id_param = "alarm_suppression_id"
    list_resource_method = "list_alarm_suppressions"
    # Name lookups are scoped by the suppression target instead.
    common_list_filter_params = ()
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "alarm suppression"
    common_update_field_specs = (
        UpdateFieldSpec(
            param_name="freeform_tags",
            is_mutable=False,
            immutable_reason=IMMUTABLE_REASON,
        ),
        UpdateFieldSpec(
            param_name="defined_tags",
            is_mutable=False,
            immutable_reason=IMMUTABLE_REASON,
        ),
    )
    update_field_specs = (
        UpdateFieldSpec(
            param_name="name",
            resource_field="display_name",
            is_mutable=False,
            immutable_reason=IMMUTABLE_REASON,
        ),
        *(
            UpdateFieldSpec(
                param_name=field,
                is_mutable=False,
                immutable_reason=IMMUTABLE_REASON,
            )
            for field in SUPPRESSION_FIELDS + ("suppression_conditions",)
        ),
        *(
            UpdateFieldSpec(
                param_name=field,
                is_mutable=False,
                strategy="check_target_field",
            )
            for field in TARGET_FIELDS
        ),
    )

    @property
    def target_type(self):
        """Return the OCI target type implied by the module parameters.

        Returns:
            C(ALARM) when alarm_id is set, otherwise C(COMPARTMENT).
        """
        return "ALARM" if self.module.params.get("alarm_id") else "COMPARTMENT"

    @property
    def list_filter_params(self):
        """Return the parameter that scopes name lookups to the target.

        Returns:
            A one-item tuple naming alarm_id or compartment_id.
        """
        return ("alarm_id",) if self.target_type == "ALARM" else ("compartment_id",)

    def collect_list_filters(self, *param_groups):
        """Collect list filters and restrict them to the suppression target type.

        Overridden because listing by compartment_id alone also returns
        suppressions that target individual alarms in that compartment, which
        must not match a compartment-wide suppression of the same name.

        Args:
            *param_groups: Groups of module parameter names to collect.

        Returns:
            The list filters, including target_type.
        """
        list_filters = super().collect_list_filters(*param_groups)
        list_filters["target_type"] = self.target_type
        return list_filters

    def validate_create_request(self) -> None:
        """Fail when a create request omits the suppression target.

        The target is a single alarm or a whole compartment, so exactly one of
        C(alarm_id) or C(compartment_id) must be set. The module-level
        mutually_exclusive declaration already rejects setting both.
        """
        super().validate_create_request()
        if not (
            self.module.params.get("alarm_id")
            or self.module.params.get("compartment_id")
        ):
            self.module.fail_json(
                msg=(
                    "Creating an alarm suppression requires one of the "
                    "following parameters: alarm_id, compartment_id"
                )
            )

    def validate_name_lookup_scope(self) -> None:
        """Fail when a name lookup omits the suppression target.

        Overridden because the base message names only the parameter that the
        C(list_filter_params) property happens to select, which is confusing
        when the caller intended to scope the lookup by the other target
        parameter.
        """
        if not (
            self.module.params.get("alarm_id")
            or self.module.params.get("compartment_id")
        ):
            self.module.fail_json(
                msg=(
                    "Using name lookup for alarm suppression requires one of "
                    "the following parameters: alarm_id, compartment_id"
                )
            )
        super().validate_name_lookup_scope()

    def check_target_field(self, resource, resource_dict, spec, desired_value):
        """Fail when a target option differs from the existing suppression.

        The target options are nested under alarm_suppression_target, so the
        update planner cannot compare them as top-level resource fields.

        Args:
            resource: The current alarm suppression model.
            resource_dict: The serialized alarm suppression.
            spec: The field spec for the target option.
            desired_value: The value requested by the caller.

        Returns:
            An empty list, because no update operation is ever planned.
        """
        target = resource_dict.get("alarm_suppression_target") or {}
        if target.get(spec.param_name) != desired_value:
            self.fail_immutable_field_change(spec.param_name, reason=IMMUTABLE_REASON)
        return []

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_alarm_suppression,
            alarm_suppression_id=resource_id,
        )

    def create_resource(self):
        details = build_create_alarm_suppression_details(self.module.params)
        response = self.call_with_retry(
            self.client.create_alarm_suppression,
            create_alarm_suppression_details=details,
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_SUPPRESSION_STATES,
        )

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_alarm_suppression,
            alarm_suppression_id=resource.id,
        )


def main():
    """Run the oci_alarm_suppression module."""
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        alarm_suppression_id=dict(type="str"),
        alarm_id=dict(type="str"),
        compartment_id_in_subtree=dict(type="bool"),
        description=dict(type="str"),
        level=dict(type="str", choices=list(CHOICE_VALUE_MAPS[("level",)])),
        dimensions=dict(type="dict"),
        time_suppress_from=dict(type="str"),
        time_suppress_until=dict(type="str"),
        suppression_conditions=dict(
            type="list",
            elements="dict",
            options=dict(
                condition_type=dict(
                    type="str",
                    choices=["recurrence"],
                    default="recurrence",
                ),
                suppression_recurrence=dict(type="str", required=True),
                suppression_duration=dict(type="str", required=True),
            ),
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[
            ["alarm_id", "compartment_id"],
            ["alarm_id", "compartment_id_in_subtree"],
        ],
        required_by={"compartment_id_in_subtree": ["compartment_id"]},
    )

    normalize_choice_parameters(module, CHOICE_VALUE_MAPS)
    normalize_time_parameters(module)

    OciAlarmSuppressionModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
