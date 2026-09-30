# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_object_storage_object_info
short_description: Retrieve Object Storage object information
description:
  - Retrieve one object or list objects in an Object Storage bucket.
version_added: "1.1.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  namespace_name:
    description: Object Storage namespace; resolved automatically when omitted.
    type: str
  bucket_name:
    description: Bucket containing the objects.
    type: str
    required: true
  object_name:
    description: Exact object name to retrieve as an SDK object summary with HEAD metadata.
    type: str
  prefix:
    description:
      - Prefix used to list matching objects.
      - Used only when C(object_name) is omitted.
    type: str
"""

EXAMPLES = r"""
- name: Get one object
  ansible.oci.oci_object_storage_object_info:
    bucket_name: application-data
    object_name: reports/today.csv

- name: List report objects
  ansible.oci.oci_object_storage_object_info:
    bucket_name: application-data
    prefix: reports/
"""

RETURN = r"""
objects:
  description:
    - SDK object summaries containing C(name), C(size), C(etag), C(md5), storage tier, and timestamps.
    - Exact lookups also include a C(headers) dictionary with lowercase names such as C(content-length) and C(content-type).
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


class OciObjectStorageObjectInfoModule(OciInfoBase):
    results_key = "objects"

    @property
    def client_class(self):
        return oci.object_storage.ObjectStorageClient

    def serialize_result_resource(self, resource):
        return oci.util.to_dict(resource)

    @property
    def namespace_name(self):
        namespace = getattr(self, "_namespace_name", None)
        if namespace is None:
            namespace = self.module.params.get("namespace_name")
            if not namespace:
                namespace = self.client.get_namespace().data
            self._namespace_name = namespace
        return namespace

    def fetch_resources(self):
        common = {
            "namespace_name": self.namespace_name,
            "bucket_name": self.module.params["bucket_name"],
        }
        object_name = self.module.params.get("object_name")
        response = self.list_all_resources(
            self.client.list_objects,
            **common,
            prefix=object_name or self.module.params.get("prefix"),
            fields=",".join(oci.object_storage.models.ObjectSummary().attribute_map.values()),
        )
        if not object_name:
            return response.objects

        summary = next((obj for obj in response.objects if obj.name == object_name), None)
        if summary is None:
            return []

        try:
            head = self.client.head_object(object_name=object_name, **common)
        except oci.exceptions.ServiceError as exc:
            if exc.status == 404:
                return []
            raise

        resource = self.serialize_result_resource(summary)
        resource["headers"] = {name.lower(): value for name, value in (head.headers or {}).items()}
        return [resource]


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        namespace_name=dict(type="str"),
        bucket_name=dict(type="str", required=True),
        object_name=dict(type="str"),
        prefix=dict(type="str"),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    OciObjectStorageObjectInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
