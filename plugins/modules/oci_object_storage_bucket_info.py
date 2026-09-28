# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_object_storage_bucket_info
short_description: Retrieve Object Storage bucket information from Oracle Cloud Infrastructure
description:
  - Get one bucket by name or list buckets in a compartment.
  - A single-bucket lookup returns full bucket details; a compartment list
    returns bucket summaries.
version_added: "1.1.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  namespace_name:
    description:
      - Object Storage namespace containing the buckets.
      - When omitted, the namespace is resolved from OCI.
    type: str
  bucket_name:
    description:
      - Name of one bucket to retrieve.
      - When provided, this takes precedence over C(compartment_id).
    type: str
  compartment_id:
    description:
      - OCID of the compartment whose buckets should be listed.
      - Required when C(bucket_name) is omitted.
    type: str
  name:
    description:
      - Filter a compartment list by exact bucket name.
      - Only used when C(bucket_name) is omitted.
    type: str
"""

EXAMPLES = r"""
- name: Get full details for one bucket
  ansible.oci.oci_object_storage_bucket_info:
    bucket_name: application-logs

- name: List buckets in a compartment
  ansible.oci.oci_object_storage_bucket_info:
    compartment_id: ocid1.compartment.oc1..example

- name: Find a bucket in a compartment
  ansible.oci.oci_object_storage_bucket_info:
    compartment_id: ocid1.compartment.oc1..example
    name: application-logs
"""

RETURN = r"""
buckets:
  description: Buckets matching the request.
  returned: always
  type: list
  elements: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

oci = import_oci_sdk()[0]


class OciObjectStorageBucketInfoModule(OciInfoBase):
    @property
    def client_class(self):
        return oci.object_storage.ObjectStorageClient

    results_key = "buckets"
    name_response_field = "name"

    @property
    def namespace_name(self):
        namespace = getattr(self, "_namespace_name", None)
        if namespace is None:
            namespace = self.module.params.get("namespace_name")
            if not namespace:
                compartment_id = self.module.params.get("compartment_id")
                kwargs = {"compartment_id": compartment_id} if compartment_id else {}
                namespace = self.call_with_retry(
                    self.client.get_namespace, **kwargs
                ).data
            self._namespace_name = namespace
        return namespace

    def fetch_resources(self):
        bucket_name = self.module.params.get("bucket_name")
        if bucket_name:
            return self.get_resource_by_id(
                bucket_name,
                self.client.get_bucket,
                namespace_name=self.namespace_name,
                bucket_name=bucket_name,
                fields=["autoTiering"],
            )

        resources = self.list_all_resources(
            self.client.list_buckets,
            namespace_name=self.namespace_name,
            compartment_id=self.module.params["compartment_id"],
        )
        return self.filter_resources_by_display_name(
            resources, self.module.params.get("name")
        )


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        namespace_name=dict(type="str"),
        bucket_name=dict(type="str"),
        compartment_id=dict(type="str"),
        name=dict(type="str"),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["bucket_name", "compartment_id"]],
    )
    OciObjectStorageBucketInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
