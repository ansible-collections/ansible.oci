# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_notification_subscription
short_description: Manage an OCI Notifications subscription
description:
  - Create, update, and delete OCI Notifications subscriptions.
version_added: "1.2.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_wait_options
  - ansible.oci.oci_tags_options
notes:
  - A new subscription stays in the C(PENDING) state until its endpoint confirms it.
    With C(wait=true), the module returns once the subscription is C(PENDING) or C(ACTIVE),
    so it does not wait for the endpoint to confirm.
  - When C(subscription_id) is omitted, the subscription is found by C(compartment_id),
    C(topic_id), C(protocol), and C(endpoint).
  - Module results only include the scheme, hostname, and port of the subscription endpoint because
    some protocols, such as C(slack) and C(pagerduty), embed credentials in it.
options:
  state:
    description:
      - The desired lifecycle state of the subscription.
    type: str
    choices: [present, absent]
    default: present
  subscription_id:
    description:
      - The OCID of the subscription to manage.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment that contains the subscription.
      - Required when creating a subscription or when finding a subscription by endpoint.
      - This value cannot change after subscription creation.
    type: str
  topic_id:
    description:
      - The OCID of the topic that the subscription belongs to.
      - Required when creating a subscription or when finding a subscription by endpoint.
      - This value cannot change after subscription creation.
    type: str
  protocol:
    description:
      - The delivery protocol of the subscription.
      - Required when creating a subscription or when finding a subscription by endpoint.
      - Must be set together with C(endpoint).
      - This value cannot change after subscription creation.
      - The C(https) protocol is deprecated by OCI. Use C(pagerduty) instead.
    type: str
    choices: [custom_https, email, https, oracle_functions, pagerduty, slack, sms]
  endpoint:
    description:
      - The destination of the notifications.
      - The format depends on C(protocol), such as an email address, an HTTPS URL, or a function OCID.
      - Required when creating a subscription or when finding a subscription by endpoint.
      - Must be set together with C(protocol).
      - This value cannot change after subscription creation.
      - OCI advises against putting confidential information in the endpoint.
      - This value is masked in logs. Module results only include its scheme, hostname, and port.
    type: str
  metadata:
    description:
      - Metadata for the subscription.
      - Only used when creating a subscription. OCI does not return the metadata of an existing
        subscription, so changes to it are not detected.
    type: str
  max_retry_duration:
    description:
      - The maximum time, in milliseconds, that OCI retries a failed delivery using exponential backoff.
      - Omit this option to keep the current delivery policy.
    type: int
"""

EXAMPLES = r"""
- name: Create an email subscription
  ansible.oci.oci_notification_subscription:
    compartment_id: ocid1.compartment.oc1..example
    topic_id: ocid1.onstopic.oc1..example
    protocol: email
    endpoint: ops@example.com

- name: Create a custom HTTPS subscription with a retry limit
  ansible.oci.oci_notification_subscription:
    compartment_id: ocid1.compartment.oc1..example
    topic_id: ocid1.onstopic.oc1..example
    protocol: custom_https
    endpoint: https://hooks.example.com/oci
    max_retry_duration: 3600000

- name: Update the retry limit and tags of a subscription
  ansible.oci.oci_notification_subscription:
    subscription_id: ocid1.onssubscription.oc1..example
    max_retry_duration: 7200000
    freeform_tags:
      team: platform

- name: Delete a subscription by compartment, topic, protocol, and endpoint
  ansible.oci.oci_notification_subscription:
    compartment_id: ocid1.compartment.oc1..example
    topic_id: ocid1.onstopic.oc1..example
    protocol: email
    endpoint: ops@example.com
    state: absent
"""

RETURN = r"""
resource:
  description: The notification subscription resource.
  returned: when state is present, except in check mode when a change is predicted
  type: dict
  contains:
    id:
      description: The subscription OCID.
      type: str
      returned: always
    topic_id:
      description: The OCID of the topic that the subscription belongs to.
      type: str
      returned: always
    protocol:
      description: The delivery protocol of the subscription.
      type: str
      returned: always
    endpoint:
      description:
        - The scheme, hostname, and port of the subscription endpoint. The port is only included
          when the endpoint sets one.
        - Null when the endpoint is not a URL, such as an email address or phone number.
      type: str
      returned: always
      sample: https://hooks.slack.com
    lifecycle_state:
      description: The subscription lifecycle state.
      type: str
      returned: always
      sample: PENDING
    compartment_id:
      description: The OCID of the compartment that contains the subscription.
      type: str
      returned: always
    created_time:
      description: The time when the subscription was created, in milliseconds since the Unix epoch.
      type: int
      returned: always
    delivery_policy:
      description:
        - The delivery policy of the subscription.
        - Null when the subscription has no delivery policy.
      type: dict
      returned: always
      contains:
        backoff_retry_policy:
          description: The exponential backoff retry policy.
          type: dict
          returned: when available
          contains:
            max_retry_duration:
              description: The maximum retry duration in milliseconds.
              type: int
              returned: always
            policy_type:
              description: The retry policy type.
              type: str
              returned: always
              sample: EXPONENTIAL
    etag:
      description: The entity tag of the subscription.
      type: str
      returned: always
    freeform_tags:
      description: Free-form tags applied to the subscription.
      type: dict
      returned: always
    defined_tags:
      description: Defined tags applied to the subscription.
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
    normalize_choice_parameters,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_notification import (
    normalize_subscription_result,
    parse_deliver_policy,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

oci = import_oci_sdk()[0]

CHOICE_VALUE_MAPS = {
    ("protocol",): {
        "custom_https": "CUSTOM_HTTPS",
        "email": "EMAIL",
        "https": "HTTPS",
        "oracle_functions": "ORACLE_FUNCTIONS",
        "pagerduty": "PAGERDUTY",
        "slack": "SLACK",
        "sms": "SMS",
    },
}
CREATE_REQUIRED_FIELDS = ("compartment_id", "topic_id", "protocol", "endpoint")
CREATE_DETAIL_FIELDS = (
    "topic_id",
    "compartment_id",
    "protocol",
    "endpoint",
    "metadata",
    "freeform_tags",
    "defined_tags",
)
WAIT_FOR_SUBSCRIPTION_STATES = ("PENDING", "ACTIVE")


class OciNotificationSubscriptionModule(OciResourceBase):
    """Manage OCI Notifications subscriptions with shared resource lifecycle helpers."""

    @property
    def client_class(self):
        """Return the OCI Notifications data plane client class.

        Returns:
            The OCI NotificationDataPlaneClient class.
        """
        return oci.ons.NotificationDataPlaneClient

    resource_id_param = "subscription_id"
    list_resource_method = "list_subscriptions"
    list_filter_params = ("topic_id",)
    name_lookup_param = "endpoint"
    name_response_field = "endpoint"
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "notification subscription"
    update_method_name = "update_subscription"
    update_details_name = "update_subscription_details"
    update_wait_states = WAIT_FOR_SUBSCRIPTION_STATES
    update_field_specs = (
        UpdateFieldSpec("compartment_id", is_mutable=False),
        UpdateFieldSpec("topic_id", is_mutable=False),
        UpdateFieldSpec("protocol", is_mutable=False),
        UpdateFieldSpec("endpoint", is_mutable=False),
        UpdateFieldSpec(
            "max_retry_duration",
            is_mutable=True,
            resource_field="deliver_policy",
            update_field="max_retry_duration",
            compare="max_retry_duration",
        ),
    )

    def filter_resources_by_display_name(self, resources, name_value):
        """Match subscriptions by endpoint and protocol.

        An endpoint alone is not unique within a topic, because the same
        endpoint can be subscribed through different protocols.

        Args:
            resources: The subscription summaries returned by OCI.
            name_value: The requested endpoint.

        Returns:
            The summaries with the requested endpoint and protocol.
        """
        matches = super(OciNotificationSubscriptionModule, self).filter_resources_by_display_name(
            resources, name_value
        )
        protocol = self.module.params.get("protocol")
        return [resource for resource in matches if getattr(resource, "protocol", None) == protocol]

    def hydrate_named_resource(self, resource):
        """Re-fetch a lookup match by OCID to get the full subscription.

        list_subscriptions returns summaries that carry ``delivery_policy`` as
        a model, while get_subscription returns ``deliver_policy`` as a JSON
        string. Re-fetching keeps the compared and returned shape the same
        whether or not subscription_id was supplied.

        Args:
            resource: The subscription summary matched by lookup.

        Returns:
            The full subscription model, or None when it no longer exists.
        """
        return self.get_resource_by_id(resource.id)

    def compare_update_field_values(self, current_value, desired_value, compare=None):
        """Compare the requested retry duration with the current delivery policy.

        OCI returns the delivery policy as a JSON string, so the retry
        duration must be extracted before it can be compared.

        Args:
            current_value: The ``deliver_policy`` JSON string returned by OCI.
            desired_value: The requested maximum retry duration in milliseconds.
            compare: The declared update comparison mode.

        Returns:
            True when the current and requested values differ.
        """
        if compare == "max_retry_duration":
            policy = parse_deliver_policy(current_value) or {}
            backoff = policy.get("backoff_retry_policy") or {}
            return backoff.get("max_retry_duration") != desired_value
        return super(OciNotificationSubscriptionModule, self).compare_update_field_values(
            current_value, desired_value, compare=compare
        )

    def build_update_details(self, update_model_fields):
        """Build the OCI subscription update model from planned field changes.

        Args:
            update_model_fields: The changed fields selected by the planner.

        Returns:
            The OCI UpdateSubscriptionDetails model.
        """
        fields = dict(update_model_fields)
        if "max_retry_duration" in fields:
            fields["delivery_policy"] = oci.ons.models.DeliveryPolicy(
                backoff_retry_policy=oci.ons.models.BackoffRetryPolicy(
                    max_retry_duration=fields.pop("max_retry_duration"),
                    policy_type="EXPONENTIAL",
                )
            )
        return build_model(fields, oci.ons.models.UpdateSubscriptionDetails)

    def get_update_result(self, response, resource_id):
        """Fetch the subscription after an update.

        update_subscription returns the update details rather than the
        subscription, so the response data cannot be returned as the resource.

        Args:
            response: The OCI update response.
            resource_id: The subscription OCID.

        Returns:
            The current subscription model, after the configured wait.
        """
        return self.wait_for_resource_id(resource_id, self.update_wait_states)

    def get_resource_response(self, resource_id):
        """Fetch a subscription by OCID with the shared retry wrapper.

        Args:
            resource_id: The subscription OCID.

        Returns:
            The OCI response wrapper for the subscription.
        """
        return self.call_with_retry(self.client.get_subscription, subscription_id=resource_id)

    def create_resource(self):
        """Create a subscription and wait until it is pending or active.

        A subscription stays pending until its endpoint confirms it, so a
        pending subscription counts as created.

        Returns:
            The created subscription model after the configured wait.
        """
        details = build_model(
            self.module.params,
            oci.ons.models.CreateSubscriptionDetails,
            keys=CREATE_DETAIL_FIELDS,
        )
        response = self.call_with_retry(
            self.client.create_subscription, create_subscription_details=details
        )
        return self.get_mutation_result(
            response.data,
            response.data.id,
            WAIT_FOR_SUBSCRIPTION_STATES,
        )

    def finalize_created_resource(self, resource):
        """Apply the retry duration to a newly created subscription.

        The create call has no delivery policy, so max_retry_duration can only
        be applied with a follow-up update.

        Args:
            resource: The newly created subscription model.

        Returns:
            The subscription model after any follow-up update.
        """
        if self.needs_update(resource):
            return self.update_resource(resource)
        return resource

    def delete_resource(self, resource):
        """Delete a subscription through the shared delete and wait helper.

        Args:
            resource: The subscription model to delete.

        Returns:
            The final subscription model, or None when the subscription is gone.
        """
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_subscription,
            subscription_id=resource.id,
        )

    def serialize_result_resource(self, resource):
        """Serialize a subscription with the delivery policy as a dict.

        The shared serializer would return the ``deliver_policy`` JSON string
        that get_subscription provides, and the full endpoint, which can
        contain credentials. The endpoint is reduced to its scheme, hostname, and port.

        Args:
            resource: The OCI subscription model.

        Returns:
            The serialized subscription with ``delivery_policy`` as a dict and
            a summarized ``endpoint``.
        """
        return normalize_subscription_result(
            super(OciNotificationSubscriptionModule, self).serialize_result_resource(resource)
        )


def main():
    """Build the Ansible argument spec and run the subscription resource module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_WAIT_ARGS,
        **OCI_TAG_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        subscription_id=dict(type="str"),
        compartment_id=dict(type="str"),
        topic_id=dict(type="str"),
        protocol=dict(type="str", choices=list(CHOICE_VALUE_MAPS[("protocol",)])),
        endpoint=dict(type="str", no_log=True),
        metadata=dict(type="str"),
        max_retry_duration=dict(type="int"),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_together=[["protocol", "endpoint"]],
    )
    normalize_choice_parameters(module, CHOICE_VALUE_MAPS)
    OciNotificationSubscriptionModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
