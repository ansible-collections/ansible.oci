# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_object_lifecycle_policy_info
short_description: Get an Object Storage bucket lifecycle policy from Oracle Cloud Infrastructure
description:
  - Get the lifecycle policy configured for one Object Storage bucket.
  - This is a read-only module and does not modify resources.
version_added: "1.1.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  bucket_name:
    description:
      - Name of the bucket whose lifecycle policy should be retrieved.
    type: str
    required: true
  namespace_name:
    description:
      - Object Storage namespace containing the bucket.
      - When omitted, the namespace is resolved from OCI.
    type: str
"""

EXAMPLES = r"""
- name: Get a bucket's lifecycle policy
  ansible.oci.oci_object_lifecycle_policy_info:
    bucket_name: application-logs

- name: Get a lifecycle policy using an explicit namespace
  ansible.oci.oci_object_lifecycle_policy_info:
    namespace_name: my-namespace
    bucket_name: application-logs
"""

RETURN = r"""
object_lifecycle_policies:
  description:
    - The lifecycle policy for the requested bucket.
    - The list contains one item when a policy is found and is empty when none is found.
    - Each policy's C(items) field contains its lifecycle rules.
  returned: always
  type: list
  elements: dict
  sample:
    - time_created: "2026-09-20T12:00:00.000Z"
      items:
        - name: expire-logs
          target: objects
          action: DELETE
          time_amount: 30
          time_unit: DAYS
          is_enabled: true
          object_name_filter:
            inclusion_patterns:
              - logs/*
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase
from ansible_collections.ansible.oci.plugins.module_utils.oci_object_storage import (
    OciObjectStorageNamespaceMixin,
)

oci = import_oci_sdk()[0]


class OciObjectLifecyclePolicyInfoModule(OciObjectStorageNamespaceMixin, OciInfoBase):
    """Info adapter for the lifecycle policy of one Object Storage bucket."""

    @property
    def client_class(self):
        return oci.object_storage.ObjectStorageClient

    results_key = "object_lifecycle_policies"

    def fetch_resources(self):
        bucket_name = self.module.params["bucket_name"]
        return self.get_resource_by_id(
            bucket_name,
            self.client.get_object_lifecycle_policy,
            namespace_name=self.namespace_name,
            bucket_name=bucket_name,
        )


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        namespace_name=dict(type="str"),
        bucket_name=dict(type="str", required=True),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciObjectLifecyclePolicyInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
