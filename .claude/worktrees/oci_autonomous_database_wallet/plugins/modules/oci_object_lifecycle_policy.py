# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_object_lifecycle_policy
short_description: Manage an Object Storage bucket lifecycle policy
description:
  - Create, replace, and delete the lifecycle policy for an Object Storage bucket.
version_added: "1.1.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  state:
    description:
      - The desired state of the bucket lifecycle policy.
    type: str
    choices: [present, absent]
    default: present
  bucket_name:
    description:
      - Name of the Object Storage bucket whose lifecycle policy is managed.
      - Required for both C(state=present) and C(state=absent).
    type: str
    required: true
  namespace_name:
    description:
      - Object Storage namespace containing the bucket.
      - When omitted, the module resolves the namespace for the configured tenancy.
    type: str
  items:
    description:
      - Complete desired set of lifecycle rules for the bucket.
      - Required when C(state=present), including when updating an existing policy.
      - The list is authoritative; an empty list removes all rules.
      - Rule ordering does not affect idempotency.
    type: list
    elements: dict
    suboptions:
      name:
        description:
          - Unique name for the lifecycle rule within the policy.
        type: str
        required: true
      action:
        description:
          - Action to perform when the rule's age threshold is reached.
        type: str
        choices: [archive, infrequent_access, delete, abort]
        required: true
      target:
        description:
          - Objects or uploads to which the lifecycle rule applies.
        type: str
        choices: [objects, multipart-uploads, previous-object-versions]
        default: objects
      time_amount:
        description:
          - Age threshold for applying the lifecycle rule, in C(time_unit).
        type: int
        required: true
      time_unit:
        description:
          - Unit used by C(time_amount).
        type: str
        choices: [days, years]
        required: true
      is_enabled:
        description:
          - Whether the lifecycle rule is active.
        type: bool
        required: true
      object_name_filter:
        description:
          - Optional filters limiting the objects affected by the rule.
        type: dict
        suboptions:
          inclusion_patterns:
            description:
              - Glob patterns matching object names to include.
            type: list
            elements: str
          exclusion_patterns:
            description:
              - Glob patterns matching object names to exclude.
            type: list
            elements: str
          inclusion_prefixes:
            description:
              - Object name prefixes to include.
            type: list
            elements: str
"""

EXAMPLES = r"""
- name: Set lifecycle rules for an Object Storage bucket
  ansible.oci.oci_object_lifecycle_policy:
    state: present
    bucket_name: application-logs
    items:
      - name: archive-old-logs
        action: archive
        target: objects
        time_amount: 90
        time_unit: days
        is_enabled: true
        object_name_filter:
          inclusion_prefixes:
            - archived/
          exclusion_patterns:
            - keep-*.log
  register: lifecycle_policy

- name: Replace the bucket lifecycle rules
  ansible.oci.oci_object_lifecycle_policy:
    state: present
    bucket_name: application-logs
    namespace_name: mytenancy
    items:
      - name: abort-old-uploads
        action: abort
        target: multipart-uploads
        time_amount: 7
        time_unit: days
        is_enabled: true

- name: Delete the bucket lifecycle policy
  ansible.oci.oci_object_lifecycle_policy:
    state: absent
    bucket_name: application-logs
    namespace_name: mytenancy
"""

RETURN = r"""
resource:
  description:
    - The Object Storage lifecycle policy returned by OCI.
    - The C(items) field contains the configured lifecycle rules.
    - C(items) is empty when the policy has no rules.
    - Rule actions and time units use the uppercase OCI enum values.
    - C(object_name_filter) and its unspecified fields are null when not configured.
  returned: when state=present, except when check mode predicts a change
  type: dict
  sample:
    items:
      - name: archive-old-logs
        action: ARCHIVE
        target: objects
        time_amount: 90
        time_unit: DAYS
        is_enabled: true
        object_name_filter:
          inclusion_prefixes: ["archived/"]
          exclusion_patterns: ["keep-*.log"]
          inclusion_patterns: null
    time_created: "2026-09-28T10:00:00.000000+00:00"
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    filter_none_values,
    import_oci_sdk,
    normalize_enum_values,
    serialize_oci_model,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_object_storage import (
    OciObjectStorageNamespaceMixin,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
)

oci = import_oci_sdk()[0]


def build_policy_details(items):
    """Convert module lifecycle rules into the OCI put-policy model."""
    model_items = []
    for item in items or []:
        rule_fields = dict(item)
        object_name_filter = rule_fields.pop("object_name_filter", None)
        if "target" not in rule_fields or rule_fields["target"] is None:
            rule_fields["target"] = "objects"
        if object_name_filter:
            object_name_filter = filter_none_values(object_name_filter)
        if object_name_filter:
            rule_fields["object_name_filter"] = oci.object_storage.models.ObjectNameFilter(
                **object_name_filter
            )
        rule_fields = normalize_enum_values(rule_fields, ("action", "time_unit"))
        model_items.append(
            oci.object_storage.models.ObjectLifecycleRule(**rule_fields)
        )
    return oci.object_storage.models.PutObjectLifecyclePolicyDetails(items=model_items)


def _normalized_filter(value):
    """Return a canonical filter while treating unset and empty fields alike."""
    if not value:
        return ()
    value = serialize_oci_model(value)
    normalized = {}
    for field in ("inclusion_patterns", "exclusion_patterns", "inclusion_prefixes"):
        values = value.get(field) or []
        if values:
            normalized[field] = tuple(sorted(values))
    return tuple(sorted(normalized.items()))


def _normalized_rule(rule):
    """Return the effective fields of one rule for stable comparison."""
    rule = serialize_oci_model(rule)
    target = rule.get("target") or "objects"
    return (
        rule.get("name"),
        (rule.get("action") or "").upper(),
        target.lower(),
        rule.get("time_amount"),
        (rule.get("time_unit") or "").upper(),
        rule.get("is_enabled"),
        _normalized_filter(rule.get("object_name_filter")),
    )


def normalized_policy_items(items):
    """Return a rule-order-independent representation of a policy."""
    return tuple(sorted(_normalized_rule(item) for item in items or []))


class OciObjectLifecyclePolicyModule(OciObjectStorageNamespaceMixin, OciResourceBase):
    """Manage the single Object Storage lifecycle policy scoped to a bucket."""

    @property
    def client_class(self):
        return oci.object_storage.ObjectStorageClient

    resource_id_param = None
    list_resource_method = None
    name_lookup_param = None
    create_resource_name = "Object Storage lifecycle policy"
    create_required_fields = ("items",)
    common_update_field_specs = ()
    update_field_specs = ()

    def validate_delete_request(self):
        if not self.module.params.get("bucket_name"):
            self.module.fail_json(
                msg="Deleting an Object Storage lifecycle policy requires bucket_name"
            )

    def resolve_target_resource(self):
        return self.get_resource_by_id(self.module.params.get("bucket_name"))

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_object_lifecycle_policy,
            namespace_name=self.namespace_name,
            bucket_name=resource_id,
        )

    def needs_update(self, resource):
        """Override the shared comparison to ignore rule/filter order and normalize OCI enums and defaults."""
        current_items = getattr(resource, "items", None)
        desired_items = self.module.params.get("items")
        return normalized_policy_items(current_items) != normalized_policy_items(
            desired_items
        )

    def create_resource(self):
        response = self.call_with_retry(
            self.client.put_object_lifecycle_policy,
            namespace_name=self.namespace_name,
            bucket_name=self.module.params["bucket_name"],
            put_object_lifecycle_policy_details=build_policy_details(
                self.module.params.get("items")
            ),
        )
        return response.data

    def update_resource(self, resource):
        return self.create_resource()

    def delete_resource(self, resource):
        return self.call_with_retry(
            self.client.delete_object_lifecycle_policy,
            namespace_name=self.namespace_name,
            bucket_name=self.module.params["bucket_name"],
        ).data


def main():
    argument_spec = dict(OCI_AUTH_ARGS)
    argument_spec.update(
        state=dict(type="str", choices=["present", "absent"], default="present"),
        bucket_name=dict(type="str", required=True),
        namespace_name=dict(type="str"),
        items=dict(
            type="list",
            elements="dict",
            options=dict(
                name=dict(type="str", required=True),
                action=dict(
                    type="str",
                    choices=["archive", "infrequent_access", "delete", "abort"],
                    required=True,
                ),
                target=dict(
                    type="str",
                    choices=["objects", "multipart-uploads", "previous-object-versions"],
                    default="objects",
                ),
                time_amount=dict(type="int", required=True),
                time_unit=dict(type="str", choices=["days", "years"], required=True),
                is_enabled=dict(type="bool", required=True),
                object_name_filter=dict(
                    type="dict",
                    options=dict(
                        inclusion_patterns=dict(type="list", elements="str"),
                        exclusion_patterns=dict(type="list", elements="str"),
                        inclusion_prefixes=dict(type="list", elements="str"),
                    ),
                ),
            ),
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[("state", "present", ["items"])],
        supports_check_mode=True,
    )

    OciObjectLifecyclePolicyModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
