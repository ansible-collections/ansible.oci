# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_notification_subscription_info
short_description: Retrieve OCI Notifications subscription information
description:
  - Retrieve one or more OCI Notifications subscriptions.
version_added: "1.2.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
notes:
  - Module results only include the scheme, hostname, and port of the subscription endpoint because
    some protocols, such as C(slack) and C(pagerduty), embed credentials in it.
options:
  subscription_id:
    description:
      - The OCID of the subscription to retrieve.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment from which to list subscriptions.
      - Required when C(subscription_id) is not set.
      - Ignored when C(subscription_id) is set.
    type: str
  topic_id:
    description:
      - The OCID of a topic. Only subscriptions to this topic are listed.
      - Ignored when C(subscription_id) is set.
    type: str
"""

EXAMPLES = r"""
- name: List subscriptions in a compartment
  ansible.oci.oci_notification_subscription_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List the subscriptions of a topic
  ansible.oci.oci_notification_subscription_info:
    compartment_id: ocid1.compartment.oc1..example
    topic_id: ocid1.onstopic.oc1..example

- name: Get a subscription by OCID
  ansible.oci.oci_notification_subscription_info:
    subscription_id: ocid1.onssubscription.oc1..example
"""

RETURN = r"""
subscriptions:
  description: Subscriptions that matched the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The subscription OCID.
      type: str
      returned: always
    topic_id:
      description: The OCID of the topic the subscription belongs to.
      type: str
      returned: always
    protocol:
      description: The subscription protocol, such as C(EMAIL) or C(CUSTOM_HTTPS).
      type: str
      returned: always
    lifecycle_state:
      description: The subscription lifecycle state.
      type: str
      returned: always
      sample: ACTIVE
    endpoint:
      description:
        - The scheme, hostname, and port of the subscription endpoint. The port is only included
          when the endpoint sets one.
        - Null when the endpoint is not a URL, such as an email address or phone number.
      type: str
      returned: always
      sample: https://hooks.slack.com
    compartment_id:
      description: The OCID of the compartment that contains the subscription.
      type: str
      returned: always
    created_time:
      description: The creation time of the subscription, in milliseconds since the epoch.
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
          description: The retry policy used when delivery to the endpoint fails.
          type: dict
          returned: when available
          contains:
            max_retry_duration:
              description: The maximum retry duration, in milliseconds.
              type: int
              returned: always
            policy_type:
              description: The type of retry policy.
              type: str
              returned: always
              sample: EXPONENTIAL
    etag:
      description: The entity tag of the subscription, used for optimistic concurrency control.
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
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase
from ansible_collections.ansible.oci.plugins.module_utils.oci_notification import (
    normalize_subscription_result,
)

oci = import_oci_sdk()[0]


class OciNotificationSubscriptionInfoModule(OciInfoBase):
    """Retrieve OCI Notifications subscriptions with shared get and list helpers."""

    @property
    def client_class(self):
        """Return the OCI Notifications data plane client class.

        Returns:
            The OCI NotificationDataPlaneClient class.
        """
        return oci.ons.NotificationDataPlaneClient

    results_key = "subscriptions"
    resource_id_param = "subscription_id"
    resource_get_method = "get_subscription"
    list_resource_method = "list_subscriptions"
    list_filter_params = ["compartment_id", "topic_id"]

    def serialize_result_resource(self, resource):
        """Serialize a subscription so get and list results share one shape.

        get_subscription returns the delivery policy as a JSON string while
        list_subscriptions returns it as a model, so the serialized result is
        normalized to always expose a ``delivery_policy`` dict. The endpoint
        is reduced to its scheme, hostname, and port so credentials are not returned.

        Args:
            resource: A Subscription or SubscriptionSummary model.

        Returns:
            The serialized subscription dict.
        """
        return normalize_subscription_result(
            super(OciNotificationSubscriptionInfoModule, self).serialize_result_resource(resource)
        )


def main():
    """Build the Ansible argument spec and run the subscription info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        subscription_id=dict(type="str"),
        compartment_id=dict(type="str"),
        topic_id=dict(type="str"),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "subscription_id"]],
    )
    OciNotificationSubscriptionInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
