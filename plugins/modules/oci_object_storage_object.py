# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_object_storage_object
short_description: Upload, download, or delete an Object Storage object
description:
  - Transfers one object between the Ansible host and an OCI Object Storage bucket.
  - Can remove an object from the bucket's current view or delete a specific object version.
version_added: "1.1.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  state:
    description:
      - Desired state of the object.
      - With versioning enabled, C(absent) without O(version_id) creates a delete marker and retains prior object versions.
      - With O(version_id), C(absent) permanently deletes that specific version.
    type: str
    choices: [present, absent]
    default: present
  bucket_name:
    description: Bucket containing the object.
    type: str
    required: true
  object_name:
    description: Object name within the bucket.
    type: str
    required: true
  namespace_name:
    description: Object Storage namespace; resolved automatically when omitted.
    type: str
  src:
    description:
      - Local file on the Ansible host to upload.
      - Required for an upload operation. The OCI SDK selects single-part or multipart upload based on the file size.
      - Exactly one of C(src) and C(dest) is required when C(state=present), and neither is used when C(state=absent).
      - Upload headers and metadata require this option; metadata-only updates are not supported.
    type: path
  dest:
    description:
      - File on the Ansible host to receive a downloaded object.
      - Required for a download operation.
      - Exactly one of C(src) and C(dest) is required when C(state=present), and neither is used when C(state=absent).
      - Missing parent directories are created automatically.
    type: path
  content_type:
    description: Content type sent with an upload. Defaults to C(application/octet-stream) on upload.
    type: str
  content_md5:
    description:
      - Base64-encoded MD5 digest of the uploaded body, checked by Object Storage for single-part uploads.
      - The SDK ignores this value for multipart uploads and calculates checksums for individual parts.
    type: str
  content_language:
    description: Content-Language header for the uploaded object.
    type: str
  content_encoding:
    description: Content-Encoding header for the uploaded object.
    type: str
  content_disposition:
    description: Content-Disposition header for the uploaded object.
    type: str
  cache_control:
    description: Cache-Control header for the uploaded object.
    type: str
  storage_tier:
    description: Storage tier for the uploaded object; defaults to the bucket's tier when omitted.
    type: str
    choices: [standard, infrequent_access, archive]
  opc_meta:
    description: User-defined metadata key and value pairs for the uploaded object.
    type: dict
  opc_sse_kms_key_id:
    description: OCID of the KMS key used to encrypt the uploaded object.
    type: str
  opc_sse_customer_algorithm:
    description:
      - Customer-provided server-side encryption algorithm for upload or download.
      - Must be supplied with O(opc_sse_customer_key) and O(opc_sse_customer_key_sha256).
    type: str
    choices: [aes256]
  opc_sse_customer_key:
    description: Base64-encoded customer-provided encryption key for upload or download.
    type: str
  opc_sse_customer_key_sha256:
    description: Base64-encoded SHA256 digest of the customer-provided encryption key.
    type: str
  version_id:
    description:
      - Exact object version to download or permanently delete.
      - Cannot be used with O(src).
    type: str
  force:
    description:
      - Whether to overwrite an existing object or destination file.
      - When false, an existing target is left unchanged regardless of content.
      - When true, an existing target is overwritten unless its MD5 checksum matches the local file.
    type: bool
    default: false
"""

EXAMPLES = r"""
- name: Upload an object
  ansible.oci.oci_object_storage_object:
    bucket_name: application-data
    object_name: reports/today.csv
    src: /tmp/today.csv

- name: Download an object
  ansible.oci.oci_object_storage_object:
    bucket_name: application-data
    object_name: reports/today.csv
    dest: /tmp/today.csv

- name: Upload an object with metadata and an explicit storage tier
  ansible.oci.oci_object_storage_object:
    bucket_name: application-data
    object_name: reports/today.csv
    src: /tmp/today.csv
    opc_meta:
      owner: analytics
    storage_tier: infrequent_access

- name: Download a specific object version
  ansible.oci.oci_object_storage_object:
    bucket_name: application-data
    object_name: reports/today.csv
    version_id: version-id-example
    dest: /tmp/today-old.csv

- name: Delete an object
  ansible.oci.oci_object_storage_object:
    bucket_name: application-data
    object_name: reports/today.csv
    state: absent

- name: Permanently delete a specific object version
  ansible.oci.oci_object_storage_object:
    bucket_name: application-data
    object_name: reports/today.csv
    version_id: version-id-example
    state: absent
"""

RETURN = r"""
resource:
  description:
    - Metadata available for the operation. Its contents depend on whether a transfer is performed, skipped, or checked.
    - Completed uploads and downloads return OCI HTTP response headers directly in this dictionary.
  returned: when C(state=present), including check mode
  type: dict
  sample:
    Content-Length: "26"
    Content-Type: application/octet-stream
    content-md5: rKDERctQsdklz4hxIIJCqg==
    etag: f86a64ce-48b1-4794-a3b4-392aab8f4360
"""

import os
import stat
import tempfile

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_base import OciModuleBase
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)

oci = import_oci_sdk()[0]

UPLOAD_OPTION_NAMES = (
    "content_type",
    "content_md5",
    "content_language",
    "content_encoding",
    "content_disposition",
    "cache_control",
    "storage_tier",
    "opc_meta",
    "opc_sse_kms_key_id",
)

CUSTOMER_ENCRYPTION_OPTION_NAMES = (
    "opc_sse_customer_algorithm",
    "opc_sse_customer_key",
    "opc_sse_customer_key_sha256",
)

STORAGE_TIER_TO_OCI = {
    "standard": "Standard",
    "infrequent_access": "InfrequentAccess",
    "archive": "Archive",
}


class OciObjectStorageObjectModule(OciModuleBase):
    @property
    def client_class(self):
        return oci.object_storage.ObjectStorageClient

    @property
    def namespace_name(self):
        namespace = getattr(self, "_namespace_name", None)
        if namespace is None:
            namespace = self.module.params.get("namespace_name")
            if not namespace:
                namespace = self.client.get_namespace().data
            self._namespace_name = namespace
        return namespace

    def validate_arguments(self):
        params = self.module.params
        source = params.get("src")
        destination = params.get("dest")

        if params.get("version_id") is not None and not params["version_id"]:
            self.module.fail_json(msg="version_id must not be empty")

        if params.get("state", "present") == "present":
            if bool(source) == bool(destination):
                self.module.fail_json(
                    msg="state=present requires exactly one of src or dest"
                )
            if source and params.get("version_id") is not None:
                self.module.fail_json(
                    msg="version_id is only supported for download and delete"
                )

            if destination:
                upload_options = [
                    name for name in UPLOAD_OPTION_NAMES if params.get(name) is not None
                ]
                if upload_options:
                    self.module.fail_json(
                        msg="Upload options require src: " + ", ".join(upload_options)
                    )

            customer_options = [
                name
                for name in CUSTOMER_ENCRYPTION_OPTION_NAMES
                if params.get(name) is not None
            ]
            if customer_options and len(customer_options) != len(CUSTOMER_ENCRYPTION_OPTION_NAMES):
                self.module.fail_json(msg="All three SSE-C options must be supplied together")
            if customer_options and params["opc_sse_customer_algorithm"] != "aes256":
                self.module.fail_json(msg="opc_sse_customer_algorithm must be aes256")

            if source and not os.path.isfile(source):
                self.module.fail_json(msg="src must refer to an existing regular file")
            if destination and os.path.isdir(destination):
                self.module.fail_json(msg="dest must be a file path, not a directory")
        else:
            if source or destination:
                self.module.fail_json(msg="src and dest cannot be used when state=absent")
            upload_options = [
                name for name in UPLOAD_OPTION_NAMES if params.get(name) is not None
            ]
            if upload_options:
                self.module.fail_json(
                    msg="Upload options require src: " + ", ".join(upload_options)
                )

    def _request_kwargs(self):
        return {
            "namespace_name": self.namespace_name,
            "bucket_name": self.module.params["bucket_name"],
            "object_name": self.module.params["object_name"],
        }

    def _customer_encryption_kwargs(self):
        kwargs = {
            name: self.module.params[name]
            for name in CUSTOMER_ENCRYPTION_OPTION_NAMES
            if self.module.params.get(name) is not None
        }
        if "opc_sse_customer_algorithm" in kwargs:
            kwargs["opc_sse_customer_algorithm"] = "AES256"
        return kwargs

    def _read_kwargs(self):
        kwargs = self._request_kwargs()
        kwargs.update(self._customer_encryption_kwargs())
        if self.module.params.get("version_id") is not None:
            kwargs["version_id"] = self.module.params["version_id"]
        return kwargs

    def _head(self):
        try:
            return self.client.head_object(**self._read_kwargs())
        except oci.exceptions.ServiceError as exc:
            if exc.status == 404:
                return None
            raise

    def _current_object(self):
        result = self.list_all_resources(
            self.client.list_objects,
            namespace_name=self.namespace_name,
            bucket_name=self.module.params["bucket_name"],
            prefix=self.module.params["object_name"],
            fields="name,etag,md5",
        )
        return next(
            (item for item in result.objects if item.name == self.module.params["object_name"]),
            None,
        )

    def _object_version(self):
        result = self.list_all_resources(
            self.client.list_object_versions,
            namespace_name=self.namespace_name,
            bucket_name=self.module.params["bucket_name"],
            prefix=self.module.params["object_name"],
        )
        return next(
            (
                item
                for item in result
                if item.name == self.module.params["object_name"]
                and item.version_id == self.module.params["version_id"]
            ),
            None,
        )

    def _resource(self, response):
        if response is None:
            return {}
        if hasattr(response, "headers"):
            return dict(response.headers or {})
        return oci.util.to_dict(response)

    def _same_content(self, path, expected_md5):
        if not expected_md5 or not os.path.isfile(path):
            return False
        return oci.object_storage.MultipartObjectAssembler.calculate_md5(
            path, 0, os.path.getsize(path)
        ) == expected_md5

    def _upload(self, source):
        """Upload a local file through the SDK's single or multipart transfer."""
        # Collect the object identity, encryption options, and upload headers.
        request_kwargs = self._request_kwargs()
        request_kwargs.update(self._customer_encryption_kwargs())
        for name in UPLOAD_OPTION_NAMES:
            value = self.module.params.get(name)
            if value is not None:
                request_kwargs[name] = value

        # Translate module parameters to the names and values expected by the SDK.
        if "opc_meta" in request_kwargs:
            request_kwargs["metadata"] = request_kwargs.pop("opc_meta")
        if self.module.params.get("storage_tier"):
            request_kwargs["storage_tier"] = STORAGE_TIER_TO_OCI[
                self.module.params["storage_tier"]
            ]
        request_kwargs["content_type"] = (
            self.module.params.get("content_type") or "application/octet-stream"
        )

        # Enforce force=false even if another client creates the object after our lookup.
        if not self.module.params.get("force", False):
            request_kwargs["if_none_match"] = "*"

        # The SDK reads the file and selects single or multipart upload.
        upload_manager = oci.object_storage.UploadManager(self.client)
        return upload_manager.upload_file(file_path=source, **request_kwargs)

    def _download(self, destination):
        """Download through the SDK, then publish the completed destination file."""
        from oci.object_storage.transfer.internal.download.DownloadConfiguration import (
            DownloadConfiguration,
        )

        download_manager = oci.object_storage.DownloadManager.DownloadManager(
            DownloadConfiguration(), self.client
        )
        temporary = None
        try:
            # Stage beside the destination to keep it intact on failure and allow atomic replacement.
            parent = os.path.dirname(os.path.abspath(destination))
            os.makedirs(parent, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=".ansible-oci-", dir=parent, delete=False
            ) as output:
                temporary = output.name

            # The SDK handles transfer and response cleanup. Identity encoding preserves stored bytes.
            _bytes_downloaded, response = download_manager.get_object_to_path(
                destination_path=temporary,
                http_response_content_encoding="identity",
                **self._read_kwargs(),
            )
            if self.module.params.get("force", False):
                # Preserve an existing file's mode and replace it only after a successful download.
                if os.path.isfile(destination):
                    os.chmod(temporary, stat.S_IMODE(os.stat(destination).st_mode))
                os.replace(temporary, destination)
            else:
                # Linking refuses to overwrite a destination created during the download.
                try:
                    os.link(temporary, destination)
                except FileExistsError:
                    return response, False
            return response, True
        except OSError as exc:
            self.module.fail_json(msg=f"Cannot download object to {destination}: {exc}")
        finally:
            # Remove the staging file after publication or a failed transfer.
            if temporary is not None:
                try:
                    os.unlink(temporary)
                except FileNotFoundError:
                    pass

    def execute_resource_module(self):
        self.validate_arguments()
        params = self.module.params
        state = params.get("state", "present")

        if state == "absent":
            existing = (
                self._object_version()
                if params.get("version_id")
                else self._current_object()
            )
            if existing is None:
                self.module.exit_json(changed=False)
            if self.module.check_mode:
                self.module.exit_json(changed=True)

            request_kwargs = self._request_kwargs()
            if params.get("version_id"):
                request_kwargs["version_id"] = params["version_id"]
            self.client.delete_object(**request_kwargs)
            self.module.exit_json(changed=True)

        is_upload = bool(params.get("src"))
        if (
            not is_upload
            and not params.get("force", False)
            and os.path.lexists(params["dest"])
        ):
            self.module.exit_json(changed=False, resource={})

        existing = self._current_object() if is_upload else self._head()
        target_exists = existing is not None if is_upload else os.path.lexists(params["dest"])
        if target_exists and not params.get("force", False):
            self.module.exit_json(changed=False, resource=self._resource(existing))
        if not is_upload and existing is None:
            self.module.fail_json(msg="Cannot download object because it does not exist")

        if target_exists:
            path = params["src"] if is_upload else params["dest"]
            expected_md5 = (
                getattr(existing, "md5", None)
                if is_upload
                else existing.headers.get("content-md5")
            )
            if self._same_content(path, expected_md5):
                self.module.exit_json(changed=False, resource=self._resource(existing))

        if self.module.check_mode:
            self.module.exit_json(changed=True, resource=self._resource(existing))

        if is_upload:
            try:
                response = self._upload(params["src"])
            except oci.exceptions.ServiceError as exc:
                if not params.get("force", False) and exc.status == 412:
                    existing = self._current_object()
                    if existing is not None:
                        self.module.exit_json(changed=False, resource=self._resource(existing))
                raise
            changed = True
        else:
            response, changed = self._download(params["dest"])
        self.module.exit_json(changed=changed, resource=self._resource(response))


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        bucket_name=dict(type="str", required=True),
        object_name=dict(type="str", required=True),
        namespace_name=dict(type="str"),
        src=dict(type="path"),
        dest=dict(type="path"),
        content_type=dict(type="str"),
        content_md5=dict(type="str"),
        content_language=dict(type="str"),
        content_encoding=dict(type="str"),
        content_disposition=dict(type="str"),
        cache_control=dict(type="str"),
        storage_tier=dict(
            type="str", choices=["standard", "infrequent_access", "archive"]
        ),
        opc_meta=dict(type="dict"),
        opc_sse_kms_key_id=dict(type="str"),
        opc_sse_customer_algorithm=dict(type="str", choices=["aes256"]),
        opc_sse_customer_key=dict(type="str", no_log=True),
        opc_sse_customer_key_sha256=dict(type="str", no_log=True),
        version_id=dict(type="str"),
        force=dict(type="bool", default=False),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    OciObjectStorageObjectModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
