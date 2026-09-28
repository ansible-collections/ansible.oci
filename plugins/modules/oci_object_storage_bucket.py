# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_object_storage_bucket
short_description: Manage an Object Storage bucket in Oracle Cloud Infrastructure
description:
  - Create, update, and delete OCI Object Storage buckets.
  - Buckets are identified by their name within an Object Storage namespace.
  - An existing bucket is never moved to another compartment.
version_added: "1.1.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_tags_options
options:
  state:
    description:
      - Desired lifecycle state of the bucket.
    type: str
    choices: [present, absent]
    default: present
  name:
    description:
      - Name of the bucket to manage.
      - Bucket names are unique within an Object Storage namespace.
    type: str
    required: true
  namespace_name:
    description:
      - Object Storage namespace containing the bucket.
      - When omitted, the namespace is resolved from OCI.
    type: str
  compartment_id:
    description:
      - OCID of the compartment in which to create the bucket.
      - Required for creation. An existing bucket cannot be moved by this module.
    type: str
  public_access_type:
    description:
      - Public access level for the bucket.
    type: str
    choices: [NoPublicAccess, ObjectRead, ObjectReadWithoutList]
  storage_tier:
    description:
      - Storage tier of the bucket. It cannot be changed after creation.
    type: str
    choices: [Standard, Archive]
  metadata:
    description:
      - User-defined key-value metadata for the bucket.
      - Pass an empty dictionary to remove existing metadata.
    type: dict
  object_events_enabled:
    description:
      - Whether to emit events when objects in the bucket change.
    type: bool
  auto_tiering:
    description:
      - Whether to automatically move objects between Standard and Infrequent Access tiers.
    type: str
    choices: [Disabled, InfrequentAccess]
  versioning:
    description:
      - Versioning state of the bucket.
      - C(Disabled) is available only before versioning has been enabled.
      - C(Suspended) is available only after versioning has been enabled.
    type: str
    choices: [Disabled, Enabled, Suspended]
  kms_key_id:
    description:
      - OCID of a customer-managed KMS key for bucket encryption.
      - The module can set or change a key but does not remove one.
    type: str
  is_bucket_key_enabled:
    description:
      - Whether to use a cached bucket encryption key with KMS encryption.
    type: bool
  force:
    description:
      - When deleting, remove bucket contents and other deletion blockers first.
      - This permanently deletes object versions and aborts multipart uploads.
      - Locked retention rules can still prevent deletion of protected objects.
    type: bool
    default: false
"""

EXAMPLES = r"""
- name: Create a private, versioned bucket
  ansible.oci.oci_object_storage_bucket:
    name: application-logs
    compartment_id: ocid1.compartment.oc1..example
    storage_tier: Standard
    public_access_type: NoPublicAccess
    versioning: Enabled
    freeform_tags:
      purpose: logs
  register: bucket

- name: Suspend versioning on the bucket
  ansible.oci.oci_object_storage_bucket:
    name: application-logs
    versioning: Suspended

- name: Delete an empty bucket
  ansible.oci.oci_object_storage_bucket:
    name: application-logs
    state: absent

- name: Delete a bucket and its contents
  ansible.oci.oci_object_storage_bucket:
    name: application-logs
    state: absent
    force: true
"""

RETURN = r"""
resource:
  description: The Object Storage bucket.
  returned: when state=present and not in check mode
  type: dict
"""

from datetime import datetime, timezone

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    OCI_TAG_ARGS,
    filter_none_values,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

oci = import_oci_sdk()[0]


class OciObjectStorageBucketModule(OciResourceBase):
    @property
    def client_class(self):
        return oci.object_storage.ObjectStorageClient

    resource_id_param = None
    create_resource_name = "Object Storage bucket"
    create_required_fields = ("name", "compartment_id")
    update_field_specs = (
        UpdateFieldSpec(param_name="compartment_id", is_mutable=False),
        UpdateFieldSpec(param_name="storage_tier", is_mutable=False),
        UpdateFieldSpec(param_name="public_access_type", is_mutable=True),
        UpdateFieldSpec(param_name="metadata", is_mutable=True),
        UpdateFieldSpec(param_name="object_events_enabled", is_mutable=True),
        UpdateFieldSpec(param_name="auto_tiering", is_mutable=True),
        UpdateFieldSpec(param_name="versioning", is_mutable=True),
        UpdateFieldSpec(param_name="kms_key_id", is_mutable=True),
        UpdateFieldSpec(param_name="is_bucket_key_enabled", is_mutable=True),
    )

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

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_bucket,
            namespace_name=self.namespace_name,
            bucket_name=resource_id,
            fields=["autoTiering"],
        )

    def resolve_target_resource(self):
        return self.get_resource_by_id(self.module.params["name"])

    def validate_kms_key_id(self):
        if self.module.params.get("kms_key_id") == "":
            self.module.fail_json(
                msg="kms_key_id must be a nonempty key OCID; removing a key is not supported"
            )

    def validate_create_request(self):
        super().validate_create_request()
        self.validate_kms_key_id()
        if self.module.params.get("versioning") == "Suspended":
            self.module.fail_json(
                msg="versioning=Suspended is unavailable when creating a bucket"
            )

    def build_update_plan(self, resource):
        self.validate_kms_key_id()
        desired_versioning = self.module.params.get("versioning")
        current_versioning = getattr(resource, "versioning", None)
        if desired_versioning == "Disabled" and current_versioning != "Disabled":
            self.module.fail_json(
                msg="versioning cannot be Disabled after it has been enabled"
            )
        if desired_versioning == "Suspended" and current_versioning == "Disabled":
            self.module.fail_json(
                msg="versioning cannot be Suspended before it has been enabled"
            )
        return super().build_update_plan(resource)

    def create_resource(self):
        params = self.module.params
        details = oci.object_storage.models.CreateBucketDetails(
            **filter_none_values(
                {
                    "name": params.get("name"),
                    "compartment_id": params.get("compartment_id"),
                    "public_access_type": params.get("public_access_type"),
                    "storage_tier": params.get("storage_tier"),
                    "metadata": params.get("metadata"),
                    "object_events_enabled": params.get("object_events_enabled"),
                    "auto_tiering": params.get("auto_tiering"),
                    "versioning": params.get("versioning"),
                    "kms_key_id": params.get("kms_key_id"),
                    "is_bucket_key_enabled": params.get("is_bucket_key_enabled"),
                    "freeform_tags": params.get("freeform_tags"),
                    "defined_tags": params.get("defined_tags"),
                }
            )
        )
        return self.call_with_retry(
            self.client.create_bucket,
            namespace_name=self.namespace_name,
            create_bucket_details=details,
        ).data

    def update_resource(self, resource):
        details = oci.object_storage.models.UpdateBucketDetails(
            **self.get_update_plan(resource)["update_model_fields"]
        )
        return self.call_with_retry(
            self.client.update_bucket,
            namespace_name=self.namespace_name,
            bucket_name=resource.name,
            update_bucket_details=details,
        ).data

    def _bucket_request(self, method, mutation=False, **kwargs):
        try:
            response = self.call_with_retry(
                method,
                namespace_name=self.namespace_name,
                bucket_name=self.module.params["name"],
                **kwargs,
            )
        except oci.exceptions.ServiceError as exc:
            self.module.fail_json(
                changed=self._force_delete_changed,
                msg=(
                    f"Cannot delete Object Storage bucket {self.module.params['name']} "
                    f"during {method.__name__}: {exc}"
                ),
            )
        if mutation:
            self._force_delete_changed = True
        return response

    def _list_bucket_records(self, method):
        records = []
        page = None
        while True:
            kwargs = {"page": page} if page else {}
            response = self._bucket_request(method, **kwargs)
            data = response.data
            records.extend(data.items if hasattr(data, "items") else data)
            page = response.headers.get("opc-next-page")
            if not page:
                return records

    def _delete_bucket_contents(self, resource):
        if getattr(resource, "is_read_only", False):
            self._bucket_request(self.client.make_bucket_writable, mutation=True)

        for policy in self._list_bucket_records(self.client.list_replication_policies):
            self._bucket_request(
                self.client.delete_replication_policy,
                mutation=True,
                replication_id=policy.id,
            )

        for rule in self._list_bucket_records(self.client.list_retention_rules):
            locked_at = rule.time_rule_locked
            if locked_at is not None:
                if locked_at.tzinfo is None:
                    locked_at = locked_at.replace(tzinfo=timezone.utc)
                if locked_at <= datetime.now(timezone.utc):
                    continue
            self._bucket_request(
                self.client.delete_retention_rule,
                mutation=True,
                retention_rule_id=rule.id,
            )

        for request in self._list_bucket_records(
            self.client.list_preauthenticated_requests
        ):
            self._bucket_request(
                self.client.delete_preauthenticated_request,
                mutation=True,
                par_id=request.id,
            )

        while True:
            uploads = self._bucket_request(self.client.list_multipart_uploads).data
            if not uploads:
                break
            for upload in uploads:
                self._bucket_request(
                    self.client.abort_multipart_upload,
                    mutation=True,
                    object_name=upload.object,
                    upload_id=upload.upload_id,
                )

        if getattr(resource, "versioning", None) in ("Enabled", "Suspended"):
            while True:
                versions = self._bucket_request(
                    self.client.list_object_versions
                ).data.items
                if not versions:
                    break
                for version in versions:
                    if not version.version_id and resource.versioning == "Enabled":
                        self.module.fail_json(
                            changed=self._force_delete_changed,
                            msg=(
                                f"Cannot delete Object Storage bucket {resource.name}: "
                                f"object {version.name} has no version ID while "
                                "versioning is enabled"
                            ),
                        )
                    kwargs = (
                        {"version_id": version.version_id} if version.version_id else {}
                    )
                    self._bucket_request(
                        self.client.delete_object,
                        mutation=True,
                        object_name=version.name,
                        **kwargs,
                    )

        if getattr(resource, "versioning", None) != "Enabled":
            while True:
                objects = self._bucket_request(self.client.list_objects).data.objects
                if not objects:
                    break
                for obj in objects:
                    self._bucket_request(
                        self.client.delete_object,
                        mutation=True,
                        object_name=obj.name,
                    )

    def delete_resource(self, resource):
        self._force_delete_changed = False
        if self.module.params.get("force"):
            self._delete_bucket_contents(resource)
        return self._bucket_request(self.client.delete_bucket, mutation=True).data


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_TAG_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        name=dict(type="str", required=True),
        namespace_name=dict(type="str"),
        compartment_id=dict(type="str"),
        public_access_type=dict(
            type="str",
            choices=["NoPublicAccess", "ObjectRead", "ObjectReadWithoutList"],
        ),
        storage_tier=dict(type="str", choices=["Standard", "Archive"]),
        metadata=dict(type="dict"),
        object_events_enabled=dict(type="bool"),
        auto_tiering=dict(type="str", choices=["Disabled", "InfrequentAccess"]),
        versioning=dict(type="str", choices=["Disabled", "Enabled", "Suspended"]),
        kms_key_id=dict(type="str"),
        is_bucket_key_enabled=dict(type="bool"),
        force=dict(type="bool", default=False),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    OciObjectStorageBucketModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
