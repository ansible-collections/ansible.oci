# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_notification_topic_info
short_description: Retrieve OCI Notifications topic information
description:
  - Retrieve one or more OCI Notifications topics.
version_added: "1.2.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_info_filter_options
options:
  topic_id:
    description:
      - The OCID of the topic to retrieve.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment from which to list topics.
      - Required when C(topic_id) is not set.
    type: str
  name:
    description:
      - Filter returned topics by exact topic name.
    type: str
  lifecycle_state:
    description:
      - Filter topics by lifecycle state.
    type: str
    choices: [active, deleting, creating]
"""

EXAMPLES = r"""
- name: List active topics in a compartment
  ansible.oci.oci_notification_topic_info:
    compartment_id: ocid1.compartment.oc1..example
    lifecycle_state: active

- name: Find a topic by exact name
  ansible.oci.oci_notification_topic_info:
    compartment_id: ocid1.compartment.oc1..example
    name: example-topic

- name: Get a topic by OCID
  ansible.oci.oci_notification_topic_info:
    topic_id: ocid1.onstopic.oc1..example
"""

RETURN = r"""
topics:
  description: Topics that matched the query.
  returned: always
  type: list
  elements: dict
  contains:
    topic_id:
      description: The topic OCID.
      type: str
      returned: always
    short_topic_id:
      description: The short, unique identifier of the topic.
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
    description:
      description: The topic description.
      type: str
      returned: when available
    lifecycle_state:
      description: The topic lifecycle state.
      type: str
      returned: always
    time_created:
      description: The date and time when the topic was created.
      type: str
      returned: always
    etag:
      description: The entity tag of the topic, used for optimistic concurrency control.
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
    import_oci_sdk,
    normalize_choice_parameters,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

oci = import_oci_sdk()[0]


CHOICE_VALUE_MAPS = {
    ("lifecycle_state",): {
        "active": "ACTIVE",
        "deleting": "DELETING",
        "creating": "CREATING",
    },
}


class OciNotificationTopicInfoModule(OciInfoBase):
    """Retrieve OCI Notifications topics with shared get and list helpers."""

    @property
    def client_class(self):
        """Return the OCI Notifications control plane client class.

        Returns:
            The OCI NotificationControlPlaneClient class.
        """
        return oci.ons.NotificationControlPlaneClient

    results_key = "topics"
    resource_id_param = "topic_id"
    resource_get_method = "get_topic"
    list_resource_method = "list_topics"
    name_response_field = "name"
    list_filter_params = ["compartment_id", "lifecycle_state"]


def main():
    """Build the Ansible argument spec and run the topic info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        topic_id=dict(type="str"),
        compartment_id=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(
            type="str",
            choices=list(CHOICE_VALUE_MAPS[("lifecycle_state",)]),
        ),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "topic_id"]],
    )
    normalize_choice_parameters(module, CHOICE_VALUE_MAPS)
    OciNotificationTopicInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
