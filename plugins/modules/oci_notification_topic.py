# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_notification_topic
short_description: Manage an OCI Notifications topic
description:
  - Create, update, and delete OCI Notifications topics.
version_added: "1.2.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_wait_options
  - ansible.oci.oci_tags_options
options:
  state:
    description:
      - The desired lifecycle state of the topic.
    type: str
    choices: [present, absent]
    default: present
  topic_id:
    description:
      - The OCID of the topic to manage.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment that contains the topic.
      - Required when creating a topic or when finding a topic by name.
      - This value cannot change after topic creation.
    type: str
  name:
    description:
      - The name of the topic.
      - Required when creating a topic.
      - The name must be unique across the tenancy.
      - This value cannot change after topic creation.
      - When C(topic_id) is omitted, the topic is found by this name in C(compartment_id).
    type: str
  description:
    description:
      - The topic description. An empty value is allowed.
      - Omit this option to keep the current description.
    type: str
"""

EXAMPLES = r"""
- name: Create a notification topic
  ansible.oci.oci_notification_topic:
    compartment_id: ocid1.compartment.oc1..example
    name: example-topic
    description: Alerts for the operations team

- name: Update the description and tags of a topic
  ansible.oci.oci_notification_topic:
    topic_id: ocid1.onstopic.oc1..example
    description: Alerts for the platform team
    freeform_tags:
      team: platform

- name: Delete a notification topic
  ansible.oci.oci_notification_topic:
    topic_id: ocid1.onstopic.oc1..example
    state: absent
"""

RETURN = r"""
resource:
  description: The notification topic resource.
  returned: when state is present, except in check mode when a change is predicted
  type: dict
  contains:
    topic_id:
      description: The topic OCID.
      type: str
      returned: always
    short_topic_id:
      description: The short form of the topic OCID.
      type: str
      returned: always
    name:
      description: The topic name.
      type: str
      returned: always
    compartment_id:
      description: The OCID of the compartment that contains the topic.
      type: str
      returned: always
    lifecycle_state:
      description: The topic lifecycle state.
      type: str
      returned: always
      sample: ACTIVE
    description:
      description: The topic description.
      type: str
      returned: when available
    time_created:
      description: The date and time when the topic was created.
      type: str
      returned: always
    etag:
      description: The entity tag of the topic.
      type: str
      returned: always
    api_endpoint:
      description: The endpoint used to publish messages to the topic.
      type: str
      returned: always
    freeform_tags:
      description: Free-form tags applied to the topic.
      type: dict
      returned: always
    defined_tags:
      description: Defined tags applied to the topic.
      type: dict
      returned: always
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    OCI_TAG_ARGS,
    OCI_WAIT_ARGS,
    build_model,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

oci = import_oci_sdk()[0]

CREATE_REQUIRED_FIELDS = ("compartment_id", "name")
WAIT_FOR_TOPIC_STATES = ("ACTIVE",)


class OciNotificationTopicModule(OciResourceBase):
    """Manage OCI Notifications topics with shared resource lifecycle helpers."""

    @property
    def client_class(self):
        """Return the OCI Notifications control plane client class.

        Returns:
            The OCI NotificationControlPlaneClient class.
        """
        return oci.ons.NotificationControlPlaneClient

    resource_id_param = "topic_id"
    resource_id_field = "topic_id"
    list_resource_method = "list_topics"
    name_response_field = "name"
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "notification topic"
    update_method_name = "update_topic"
    update_details_name = "topic_attributes_details"
    update_wait_states = WAIT_FOR_TOPIC_STATES
    update_field_specs = (
        UpdateFieldSpec("name", is_mutable=False),
        UpdateFieldSpec("compartment_id", is_mutable=False),
        UpdateFieldSpec("description", is_mutable=True, compare="empty_as_none"),
    )

    def compare_update_field_values(self, current_value, desired_value, compare=None):
        """Treat an unset description and an empty description as equal.

        OCI may return None for an unset description while the user sends an
        empty string, so exact comparison would report a change on every run.

        Args:
            current_value: The value returned by OCI.
            desired_value: The value requested by the user.
            compare: The declared update comparison mode.

        Returns:
            True when the current and requested values differ.
        """
        if compare == "empty_as_none":
            return (current_value or "") != (desired_value or "")
        return super(OciNotificationTopicModule, self).compare_update_field_values(
            current_value, desired_value, compare=compare
        )

    def build_update_plan(self, resource):
        """Always send the description when a topic update is needed.

        OCI requires the description on every topic update, so a tags-only
        update would otherwise fail or clear the current description.

        Args:
            resource: The current OCI topic model.

        Returns:
            The shared update plan with the description included.
        """
        update_plan = super(OciNotificationTopicModule, self).build_update_plan(resource)
        fields = update_plan["update_model_fields"]
        if fields and "description" not in fields:
            fields["description"] = resource.description or ""
        return update_plan

    def build_update_details(self, update_model_fields):
        """Build the OCI topic update model from planned field changes.

        Args:
            update_model_fields: The changed fields selected by the planner.

        Returns:
            The OCI TopicAttributesDetails model.
        """
        return build_model(update_model_fields, oci.ons.models.TopicAttributesDetails)

    def get_resource_response(self, resource_id):
        """Fetch a topic by OCID with the shared retry wrapper.

        Args:
            resource_id: The topic OCID.

        Returns:
            The OCI response wrapper for the topic.
        """
        return self.call_with_retry(self.client.get_topic, topic_id=resource_id)

    def create_resource(self):
        """Create a topic and wait for its active state.

        Returns:
            The created topic model after the configured wait.
        """
        params = self.module.params
        details = build_model(
            {
                "compartment_id": params.get("compartment_id"),
                "name": params.get("name"),
                "description": params.get("description"),
                "freeform_tags": params.get("freeform_tags"),
                "defined_tags": params.get("defined_tags"),
            },
            oci.ons.models.CreateTopicDetails,
        )
        response = self.call_with_retry(
            self.client.create_topic, create_topic_details=details
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "topic_id", None),
            WAIT_FOR_TOPIC_STATES,
        )

    def delete_resource(self, resource):
        """Delete a topic through the shared delete and wait helper.

        Args:
            resource: The topic model to delete.

        Returns:
            The final topic model, or None when the topic is gone.
        """
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_topic,
            topic_id=resource.topic_id,
        )


def main():
    """Build the Ansible argument spec and run the topic resource module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_WAIT_ARGS,
        **OCI_TAG_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        topic_id=dict(type="str"),
        compartment_id=dict(type="str"),
        name=dict(type="str"),
        description=dict(type="str"),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    OciNotificationTopicModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
