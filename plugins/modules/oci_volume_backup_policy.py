# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_volume_backup_policy
short_description: Manage a volume backup policy in Oracle Cloud Infrastructure
description:
  - Create, update, and delete user-defined OCI Block Volume backup policies.
  - A backup policy can contain schedules that define backup frequency, type,
    and retention settings.
  - The OCI policy APIs are synchronous, so this module does not expose waiter
    options.
  - Create requests must omit C(volume_backup_policy_id). The returned policy
    ID can be used for later C(state=present) and C(state=absent) tasks.
version_added: "1.1.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_name_lookup_options
  - ansible.oci.oci_tags_options
options:
  state:
    description:
      - The desired state of the volume backup policy.
    type: str
    choices: [present, absent]
    default: present
  volume_backup_policy_id:
    description:
      - The OCID of the volume backup policy.
      - When provided, the module manages this exact policy.
    type: str
  name:
    description:
      - Human-readable name for the volume backup policy.
      - Required when creating a policy.
      - When C(volume_backup_policy_id) is omitted, the module uses
        C(compartment_id + name) to find an existing policy.
      - A unique match is used for C(state=present) or C(state=absent).
      - If more than one policy matches, the task fails and the caller must
        supply C(volume_backup_policy_id).
    type: str
  compartment_id:
    description:
      - The OCID of the compartment that contains the volume backup policy.
      - Required when creating a policy and for name-based lookup.
      - Existing policies cannot be moved to another compartment.
    type: str
  destination_region:
    description:
      - The paired destination region to which scheduled backups are copied.
      - Set this to C(none) to disable cross-region copying on an existing
        policy.
      - Supports updates.
    type: str
  schedules:
    description:
      - The schedules applied by the volume backup policy.
      - Supports updates. Set to an empty list to remove all schedules.
      - Schedule ordering is ignored when checking idempotency.
    type: list
    elements: dict
    suboptions:
      backup_type:
        description:
          - The type of volume backup to create.
        type: str
        choices: [full, incremental]
        required: true
      offset_seconds:
        description:
          - Number of seconds by which to shift the backup start time from the
            default interval boundary.
          - Used when C(offset_type=numeric_seconds).
        type: int
      period:
        description:
          - The volume backup frequency.
        type: str
        choices: [one_hour, one_day, one_week, one_month, one_year]
        required: true
      offset_type:
        description:
          - How the schedule offset is defined.
          - C(structured) uses the structured date and time fields.
          - C(numeric_seconds) uses C(offset_seconds).
        type: str
        choices: [structured, numeric_seconds]
      hour_of_day:
        description:
          - Hour of the day at which to create the backup.
        type: int
      day_of_week:
        description:
          - Day of the week on which to create the backup.
        type: str
        choices: [monday, tuesday, wednesday, thursday, friday, saturday, sunday]
      day_of_month:
        description:
          - Day of the month on which to create the backup.
        type: int
      month:
        description:
          - Month of the year in which to create the backup.
        type: str
        choices: [january, february, march, april, may, june, july, august,
          september, october, november, december]
      retention_seconds:
        description:
          - Legacy retention duration, in seconds, for backups created by this
            schedule.
        type: int
        required: true
      time_zone:
        description:
          - Time zone used by the schedule.
        type: str
        choices: [utc, regional_data_center_time]
      retention_period:
        description:
          - Retention duration for backups created by this schedule.
        type: dict
        suboptions:
          retention_time_amount:
            description:
              - Numeric length of the retention period.
            type: int
            required: true
          retention_time_unit:
            description:
              - Unit for C(retention_time_amount).
            type: str
            choices: [days, years]
            required: true
      prevent_deletion_enabled:
        description:
          - Whether backups created by this schedule are protected from
            deletion during the configured retention period.
          - Returned by OCI as C(is_prevent_deletion_enabled).
        type: bool
      retention_lock_enabled:
        description:
          - Whether backups created by this schedule use retention lock.
          - Use together with C(retention_period).
          - Returned by OCI as C(is_retention_lock_enabled).
        type: bool
notes:
  - Oracle-defined backup policies can be read by the OCI API, but only
    user-defined policies can be updated or deleted.
  - OCI validates which structured schedule fields apply to each period.
  - Retention lock constraints are enforced by OCI.
"""

EXAMPLES = r"""
- name: Create a daily volume backup policy
  ansible.oci.oci_volume_backup_policy:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: application-daily-backups
    schedules:
      - backup_type: incremental
        period: one_day
        offset_type: structured
        hour_of_day: 2
        retention_seconds: 604800
        time_zone: utc
  register: created_policy

- name: Create a policy with retention controls
  ansible.oci.oci_volume_backup_policy:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: retained-backups
    schedules:
      - backup_type: full
        period: one_week
        offset_type: structured
        day_of_week: sunday
        hour_of_day: 1
        retention_seconds: 2592000
        retention_period:
          retention_time_amount: 30
          retention_time_unit: days
        prevent_deletion_enabled: true
        retention_lock_enabled: true

- name: Update schedules and enable cross-region copying
  ansible.oci.oci_volume_backup_policy:
    state: present
    volume_backup_policy_id: "{{ created_policy.resource.id }}"
    destination_region: us-ashburn-1
    schedules:
      - backup_type: incremental
        period: one_day
        offset_type: structured
        hour_of_day: 3
        retention_seconds: 1209600
        time_zone: utc

- name: Disable cross-region copying
  ansible.oci.oci_volume_backup_policy:
    state: present
    volume_backup_policy_id: "{{ created_policy.resource.id }}"
    destination_region: none

- name: Delete a uniquely named policy
  ansible.oci.oci_volume_backup_policy:
    state: absent
    compartment_id: ocid1.compartment.oc1..example
    name: application-daily-backups
"""

RETURN = r"""
resource:
  description: The volume backup policy resource.
  returned: when state != absent
  type: dict
  contains:
    id:
      description: The OCID of the volume backup policy.
      type: str
      returned: always
      sample: ocid1.volumebackuppolicy.oc1..example
    name:
      description: The display name of the volume backup policy.
      type: str
      returned: always
      sample: application-daily-backups
    compartment_id:
      description: The OCID of the compartment containing the policy.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    destination_region:
      description: The paired destination region for scheduled backup copies.
      type: str
      returned: always
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
      returned: always
      sample: {"environment": "production"}
    defined_tags:
      description: Defined tags applied to the policy.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
    time_created:
      description: The policy creation time in RFC3339 format.
      type: str
      returned: always
      sample: "2026-08-27T10:00:00.000Z"
  sample:
    id: ocid1.volumebackuppolicy.oc1..example
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
        retention_period:
          retention_time_amount: 7
          retention_time_unit: DAYS
        is_prevent_deletion_enabled: true
        is_retention_lock_enabled: false
    freeform_tags: {"environment": "production"}
    defined_tags: {"Operations": {"CostCenter": "42"}}
    time_created: "2026-08-27T10:00:00.000Z"
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_backup import (
    build_retention_period,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    OCI_NAME_LOOKUP_ARGS,
    OCI_TAG_ARGS,
    filter_none_values,
    import_oci_sdk,
    normalize_enum_values,
    serialize_oci_model,
    strip_none_values,
    values_differ_as_subset,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]

CREATE_REQUIRED_FIELDS = ["compartment_id", "name"]

ENUM_KEYS = frozenset(
    {
        "backup_type",
        "period",
        "offset_type",
        "day_of_week",
        "month",
        "time_zone",
        "retention_time_unit",
    }
)

SCHEDULE_FIELDS = (
    "backup_type",
    "offset_seconds",
    "period",
    "offset_type",
    "hour_of_day",
    "day_of_week",
    "day_of_month",
    "month",
    "retention_seconds",
    "time_zone",
    "retention_period",
)


def normalize_schedule(schedule):
    schedule = normalize_enum_values(strip_none_values(schedule or {}), ENUM_KEYS)
    normalized = {field: schedule.get(field) for field in SCHEDULE_FIELDS}
    normalized["is_prevent_deletion_enabled"] = schedule.get(
        "is_prevent_deletion_enabled",
        schedule.get("prevent_deletion_enabled"),
    )
    normalized["is_retention_lock_enabled"] = schedule.get(
        "is_retention_lock_enabled",
        schedule.get("retention_lock_enabled"),
    )
    return strip_none_values(normalized)


def build_volume_backup_schedule(schedule):
    normalized = normalize_schedule(schedule)
    if "retention_period" in normalized:
        normalized["retention_period"] = build_retention_period(
            normalized["retention_period"]
        )
    return oci.core.models.VolumeBackupSchedule(**normalized)


def build_schedules(schedules):
    if schedules is None:
        return None
    return [build_volume_backup_schedule(schedule) for schedule in schedules]


def schedules_match(current_schedules, desired_schedules):
    unmatched_current = [
        normalize_schedule(schedule) for schedule in (current_schedules or [])
    ]
    desired = [normalize_schedule(schedule) for schedule in (desired_schedules or [])]
    if len(unmatched_current) != len(desired):
        return False

    for desired_schedule in desired:
        match_index = next(
            (
                index
                for index, current_schedule in enumerate(unmatched_current)
                if not values_differ_as_subset(
                    current_schedule,
                    desired_schedule,
                )
            ),
            None,
        )
        if match_index is None:
            return False
        unmatched_current.pop(match_index)
    return True


def build_create_volume_backup_policy_details(params):
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "display_name": params.get("name"),
            "destination_region": params.get("destination_region"),
            "schedules": build_schedules(params.get("schedules")),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.core.models.CreateVolumeBackupPolicyDetails(**details)


class OciVolumeBackupPolicyModule(OciResourceBase):
    """Concrete resource adapter for OCI volume backup policies."""

    @property
    def client_class(self):
        return oci.core.BlockstorageClient

    resource_id_param = "volume_backup_policy_id"
    list_resource_method = "list_volume_backup_policies"
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "volume backup policy"
    enum_keys = ENUM_KEYS
    update_field_specs = (
        UpdateFieldSpec(
            param_name="name",
            resource_field="display_name",
            is_mutable=True,
        ),
        UpdateFieldSpec(
            param_name="destination_region",
            is_mutable=True,
            compare="destination_region",
        ),
        UpdateFieldSpec(
            param_name="compartment_id",
            is_mutable=False,
        ),
    )

    def compare_update_field_values(self, current_value, desired_value, compare=None):
        if compare == "destination_region":
            if desired_value == "none" and current_value is None:
                return False
            return current_value != desired_value
        return super().compare_update_field_values(
            current_value,
            desired_value,
            compare=compare,
        )

    def build_update_plan(self, resource):
        update_plan = super().build_update_plan(resource)
        desired_schedules = self.module.params.get("schedules")
        if desired_schedules is None:
            return update_plan

        resource_dict = serialize_oci_model(resource)
        if schedules_match(resource_dict.get("schedules"), desired_schedules):
            return update_plan

        update_plan["update_needed"] = True
        update_plan["update_model_fields"]["schedules"] = desired_schedules
        return update_plan

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_volume_backup_policy,
            policy_id=resource_id,
        )

    def create_resource(self):
        create_details = build_create_volume_backup_policy_details(self.module.params)
        response = self.call_with_retry(
            self.client.create_volume_backup_policy,
            create_volume_backup_policy_details=create_details,
        )
        return response.data

    def build_update_details(self, update_model_fields):
        update_model_fields = dict(update_model_fields)
        if "schedules" in update_model_fields:
            update_model_fields["schedules"] = build_schedules(
                update_model_fields["schedules"]
            )
        return oci.core.models.UpdateVolumeBackupPolicyDetails(**update_model_fields)

    def update_resource(self, resource):
        update_details = self.build_update_details(
            self.get_update_plan(resource)["update_model_fields"]
        )
        response = self.call_with_retry(
            self.client.update_volume_backup_policy,
            policy_id=resource.id,
            update_volume_backup_policy_details=update_details,
        )
        return response.data

    def delete_resource(self, resource):
        return self.call_with_retry(
            self.client.delete_volume_backup_policy,
            policy_id=resource.id,
        ).data


def main():
    argument_spec = dict(OCI_AUTH_ARGS, **OCI_TAG_ARGS, **OCI_NAME_LOOKUP_ARGS)
    argument_spec.update(
        state=dict(type="str", choices=["present", "absent"], default="present"),
        volume_backup_policy_id=dict(type="str"),
        destination_region=dict(type="str"),
        schedules=dict(
            type="list",
            elements="dict",
            options=dict(
                backup_type=dict(
                    type="str",
                    choices=["full", "incremental"],
                    required=True,
                ),
                offset_seconds=dict(type="int"),
                period=dict(
                    type="str",
                    choices=[
                        "one_hour",
                        "one_day",
                        "one_week",
                        "one_month",
                        "one_year",
                    ],
                    required=True,
                ),
                offset_type=dict(
                    type="str",
                    choices=["structured", "numeric_seconds"],
                ),
                hour_of_day=dict(type="int"),
                day_of_week=dict(
                    type="str",
                    choices=[
                        "monday",
                        "tuesday",
                        "wednesday",
                        "thursday",
                        "friday",
                        "saturday",
                        "sunday",
                    ],
                ),
                day_of_month=dict(type="int"),
                month=dict(
                    type="str",
                    choices=[
                        "january",
                        "february",
                        "march",
                        "april",
                        "may",
                        "june",
                        "july",
                        "august",
                        "september",
                        "october",
                        "november",
                        "december",
                    ],
                ),
                retention_seconds=dict(type="int", required=True),
                time_zone=dict(
                    type="str",
                    choices=["utc", "regional_data_center_time"],
                ),
                retention_period=dict(
                    type="dict",
                    options=dict(
                        retention_time_amount=dict(type="int", required=True),
                        retention_time_unit=dict(
                            type="str",
                            choices=["days", "years"],
                            required=True,
                        ),
                    ),
                ),
                prevent_deletion_enabled=dict(type="bool"),
                retention_lock_enabled=dict(type="bool"),
            ),
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciVolumeBackupPolicyModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
