# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_image
short_description: Manage a custom Compute image resource in Oracle Cloud Infrastructure
description:
  - Create, update, and delete OCI custom Compute images.
  - Create by capturing a Compute instance, or by importing an image file from
    Object Storage. Use the resulting image to launch instances with
    M(oracle.oci.oci_instance).
  - Exactly one create source is required. Use C(instance_id),
    C(object_storage), or C(source_uri).
  - Use M(oracle.oci.oci_image_info) to list platform and custom images.
  - Uses the shared OCI helper layer for authentication, waiting, retry
    behavior, and result shaping.
  - Create requests must omit C(image_id). After create, capture the returned
    image ID and use it for later C(state=present) and C(state=absent) tasks.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - oracle.oci.oci_auth_options
  - oracle.oci.oci_name_lookup_options
  - oracle.oci.oci_wait_options
  - oracle.oci.oci_tags_options
options:
  state:
    description:
      - The desired lifecycle state of the image.
    type: str
    choices: [present, absent]
    default: present
  image_id:
    description:
      - The OCID of the image.
      - When provided, the module manages this exact image.
      - Required to distinguish between multiple images that share the same
        scoped C(name).
    type: str
  name:
    description:
      - Human-readable name for the image.
      - Required when creating an image.
      - When C(image_id) is omitted, the module uses C(compartment_id + name)
        to find an existing image.
      - If exactly one image matches, C(state=present) manages it as the update
        target and C(state=absent) deletes it.
      - If more than one image matches, the task fails and the caller must
        supply C(image_id).
    type: str
  compartment_id:
    description:
      - The OCID of the compartment the custom image is created in.
      - Required when creating an image.
      - The module does not move an existing image to another compartment.
      - Also scopes name-based image lookups when C(image_id) is omitted.
    type: str
  instance_id:
    description:
      - The OCID of the instance to capture the custom image from.
      - Exactly one of C(instance_id), C(object_storage), or C(source_uri) is
        required when creating an image.
      - The instance should be stopped before capturing an image to guarantee a
        consistent image.
      - The module does not update this field after create.
    type: str
  object_storage:
    description:
      - Object Storage bucket location of an image file to import.
      - Exactly one of C(instance_id), C(object_storage), or C(source_uri) is
        required when creating an image.
      - C(namespace_name) is the Object Storage namespace for the tenancy; use
        C(oci os ns get) to look it up.
      - The module does not update this field after create.
    type: dict
    suboptions:
      namespace_name:
        description:
          - The Object Storage namespace that contains the bucket.
        type: str
        required: true
      bucket_name:
        description:
          - The Object Storage bucket that contains the image file.
        type: str
        required: true
      object_name:
        description:
          - The name of the image object in the bucket.
        type: str
        required: true
  source_uri:
    description:
      - The Object Storage URL of an image file to import.
      - Exactly one of C(instance_id), C(object_storage), or C(source_uri) is
        required when creating an image.
      - Cross-tenancy imports must use a pre-authenticated request URL.
      - The module does not update this field after create.
    type: str
  operating_system:
    description:
      - Operating system of the image being imported.
      - Required when importing with C(object_storage) or C(source_uri).
      - Not used when capturing from C(instance_id).
      - Choices use lowercase snake_case. The module maps each choice to the
        matching OCI Console Import image label before sending it to the API,
        for example C(oracle_linux) becomes C(Oracle Linux) and C(rhel)
        becomes C(Red Hat Enterprise Linux).
      - The module does not update this field after create.
    type: str
    choices:
      - almalinux
      - centos
      - debian
      - generic_linux
      - oracle_linux
      - rhel
      - rocky_linux
      - suse
      - ubuntu
      - windows
  operating_system_version:
    description:
      - Operating system version of the image being imported.
      - Required when C(operating_system=windows).
      - Optional for Linux imports.
      - Not used when capturing from C(instance_id).
      - The module does not update this field after create.
    type: str
  source_image_type:
    description:
      - Format of the image file being imported.
      - Required when importing with C(object_storage) or C(source_uri).
      - Not used when capturing from C(instance_id).
      - C(vmdk) and C(qcow2) are sent to OCI as the import format.
      - C(oci) is the Oracle Cloud Infrastructure export format. The API does
        not accept a source image type for this format, so the module omits
        it. C(launch_mode) cannot be set when C(source_image_type=oci)
        because OCI derives launch mode from the exported image metadata.
      - The module does not update this field after create.
    type: str
    choices: [vmdk, qcow2, oci]
  launch_mode:
    description:
      - The launch mode to configure the custom image with, determining how the
        instances launched from it boot.
      - When capturing from C(instance_id) and this is omitted, OCI derives the
        launch mode from the source instance.
      - Cannot be set when C(source_image_type=oci).
      - C(custom) and C(acceleratedpv) are omitted because they require launch
        options this module does not expose.
      - The module does not update this field after create.
    type: str
    choices: [native, emulated, paravirtualized]
notes:
  - Create using exactly one source. C(instance_id) captures a Compute
    instance. C(object_storage) imports from a bucket. C(source_uri) imports
    from an Object Storage URL.
  - Windows image imports must comply with Microsoft licensing.
  - Exporting an image to Object Storage is not supported.
"""

EXAMPLES = r"""
- name: Capture a custom image from a stopped instance
  oracle.oci.oci_image:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: hardened-oracle-linux
    instance_id: ocid1.instance.oc1..example
  register: created_image

- name: Import a QCOW2 image from an Object Storage bucket
  oracle.oci.oci_image:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: imported-oracle-linux
    object_storage:
      namespace_name: mytenancy
      bucket_name: custom-images
      object_name: golden-ol9.qcow2
    operating_system: oracle_linux
    source_image_type: qcow2
    launch_mode: paravirtualized
  register: imported_image

- name: Import an image from an Object Storage URL
  oracle.oci.oci_image:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: imported-from-url
    source_uri: https://objectstorage.us-phoenix-1.oraclecloud.com/n/mytenancy/b/custom-images/o/golden-ol9.qcow2
    operating_system: oracle_linux
    source_image_type: qcow2

- name: Import a Windows VMDK image
  oracle.oci.oci_image:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: imported-windows
    object_storage:
      namespace_name: mytenancy
      bucket_name: custom-images
      object_name: windows-server.vmdk
    operating_system: windows
    operating_system_version: Server 2025 Standard
    source_image_type: vmdk
    launch_mode: paravirtualized

- name: Import an OCI-format image exported from another region
  oracle.oci.oci_image:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: imported-oci-export
    source_uri: https://objectstorage.us-phoenix-1.oraclecloud.com/n/mytenancy/b/custom-images/o/export.oci
    operating_system: oracle_linux
    source_image_type: oci

- name: Reconcile a uniquely named image by name (update tags)
  oracle.oci.oci_image:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: hardened-oracle-linux
    freeform_tags:
      env: prod

- name: Intentionally create a second image with the same display name
  oracle.oci.oci_image:
    state: present
    allow_duplicate_name: true
    compartment_id: ocid1.compartment.oc1..example
    name: hardened-oracle-linux
    instance_id: ocid1.instance.oc1..example

- name: Launch an instance from the custom image
  oracle.oci.oci_instance:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    name: fleet-node
    shape: VM.Standard.E4.Flex
    image_id: "{{ created_image.resource.id }}"
    subnet_id: ocid1.subnet.oc1..example

- name: Delete the custom image
  oracle.oci.oci_image:
    state: absent
    image_id: "{{ created_image.resource.id }}"

- name: Delete a uniquely named image without providing image_id
  oracle.oci.oci_image:
    state: absent
    compartment_id: ocid1.compartment.oc1..example
    name: hardened-oracle-linux
"""

RETURN = r"""
resource:
  description: The image resource.
  returned: when state != absent
  type: dict
  contains:
    id:
      description: The OCID of the image.
      type: str
      returned: always
      sample: ocid1.image.oc1..example
    name:
      description: The display name of the image.
      type: str
      returned: always
      sample: hardened-oracle-linux
    compartment_id:
      description: The OCID of the compartment containing the image.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    lifecycle_state:
      description: The current lifecycle state of the image.
      type: str
      returned: always
      sample: AVAILABLE
    operating_system:
      description: The operating system of the image.
      type: str
      returned: always
      sample: Oracle Linux
    operating_system_version:
      description: The operating system version of the image.
      type: str
      returned: always
      sample: "9"
    base_image_id:
      description: The OCID of the image the custom image was derived from.
      type: str
      returned: always
      sample: ocid1.image.oc1..baseexample
    create_image_allowed:
      description: Whether instances launched with this image can be used to create new images.
      type: bool
      returned: always
      sample: true
    launch_mode:
      description: The launch mode configured for the image.
      type: str
      returned: always
      sample: PARAVIRTUALIZED
    size_in_mbs:
      description: The boot volume size for an instance launched from this image, in MBs.
      type: int
      returned: always
      sample: 47694
    billable_size_in_gbs:
      description: The size of the internal storage for this image that is subject to billing, in GBs.
      type: int
      returned: always
      sample: 6
    freeform_tags:
      description: Free-form tags applied to the image.
      type: dict
      returned: always
      sample: {"environment": "production"}
    defined_tags:
      description: Defined tags applied to the image.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
    time_created:
      description: The date and time the image was created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
  sample:
    id: ocid1.image.oc1..example
    name: hardened-oracle-linux
    compartment_id: ocid1.compartment.oc1..example
    lifecycle_state: AVAILABLE
    operating_system: Oracle Linux
    operating_system_version: "9"
    base_image_id: ocid1.image.oc1..baseexample
    create_image_allowed: true
    launch_mode: PARAVIRTUALIZED
    freeform_tags: {"environment": "production"}
    defined_tags: {"Operations": {"CostCenter": "42"}}
    time_created: "2026-01-01T00:00:00.000Z"
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.oracle.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_AVAILABLE,
    OCI_COMMON_ARGS,
    filter_none_values,
    import_oci_sdk,
    normalize_enum_values,
)
from ansible_collections.oracle.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]

CREATE_REQUIRED_FIELDS = [
    "compartment_id",
    "name",
]
WAIT_FOR_IMAGE_STATES = [LIFECYCLE_AVAILABLE]
IMPORT_ONLY_FIELDS = (
    "operating_system",
    "operating_system_version",
    "source_image_type",
)
OCI_SOURCE_IMAGE_TYPE = "oci"
# Ansible choices are lowercase snake_case. OCI stores the Console Import
# image labels as operating_system metadata.
OPERATING_SYSTEM_API_VALUES = {
    "almalinux": "AlmaLinux",
    "centos": "CentOS",
    "debian": "Debian",
    "generic_linux": "Generic Linux",
    "oracle_linux": "Oracle Linux",
    "rhel": "Red Hat Enterprise Linux",
    "rocky_linux": "Rocky Linux",
    "suse": "SUSE",
    "ubuntu": "Ubuntu",
    "windows": "Windows",
}
OPERATING_SYSTEM_CHOICES = list(OPERATING_SYSTEM_API_VALUES)

# Module inputs use lowercase snake_case choices (Ansible convention), while
# OCI's wire format uses upper-case constants (for example "paravirtualized" ->
# "PARAVIRTUALIZED").
ENUM_KEYS = {"launch_mode", "source_image_type"}


def _shared_image_source_fields(params):
    source_image_type = params.get("source_image_type")
    fields = {
        "operating_system": OPERATING_SYSTEM_API_VALUES.get(
            params.get("operating_system")
        ),
        "operating_system_version": params.get("operating_system_version"),
    }
    if source_image_type and source_image_type != OCI_SOURCE_IMAGE_TYPE:
        fields["source_image_type"] = normalize_enum_values(
            {"source_image_type": source_image_type}, ENUM_KEYS
        )["source_image_type"]
    return fields


def build_image_source_details(params):
    object_storage = params.get("object_storage")
    source_uri = params.get("source_uri")
    shared_fields = _shared_image_source_fields(params)
    if object_storage:
        details = filter_none_values(
            {
                "namespace_name": object_storage.get("namespace_name"),
                "bucket_name": object_storage.get("bucket_name"),
                "object_name": object_storage.get("object_name"),
                **shared_fields,
            }
        )
        return oci.core.models.ImageSourceViaObjectStorageTupleDetails(**details)
    if source_uri:
        details = filter_none_values(
            {
                "source_uri": source_uri,
                **shared_fields,
            }
        )
        return oci.core.models.ImageSourceViaObjectStorageUriDetails(**details)
    return None


def build_create_image_details(params):
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "instance_id": params.get("instance_id"),
            "display_name": params.get("name"),
            "launch_mode": normalize_enum_values(
                {"launch_mode": params.get("launch_mode")}, ENUM_KEYS
            )["launch_mode"],
            "image_source_details": build_image_source_details(params),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.core.models.CreateImageDetails(**details)


class OciImageModule(OciResourceBase):
    """Concrete resource adapter for OCI custom Compute images."""

    @property
    def client_class(self):
        return oci.core.ComputeClient

    resource_id_param = "image_id"
    list_resource_method = "list_images"
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "image"
    update_method_name = "update_image"
    update_details_name = "update_image_details"
    update_wait_states = WAIT_FOR_IMAGE_STATES
    # instance_id, object_storage, source_uri, and the import-only fields are
    # create-only source parameters with no counterpart on the Image resource,
    # so they must not participate in drift detection: rerunning the create
    # task against an existing image must stay idempotent.
    update_field_specs = [
        {
            "param_name": "name",
            "resource_field": "display_name",
            "update_field": "display_name",
            "is_mutable": True,
        },
    ]

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_image,
            image_id=resource_id,
        )

    def validate_create_request(self):
        super().validate_create_request()
        params = self.module.params
        instance_id = params.get("instance_id")
        object_storage = params.get("object_storage")
        source_uri = params.get("source_uri")
        if not instance_id and not object_storage and not source_uri:
            self.module.fail_json(
                msg=(
                    "Creating an image requires instance_id, object_storage, "
                    "or source_uri"
                )
            )
        if instance_id:
            if any(params.get(field) for field in IMPORT_ONLY_FIELDS):
                self.module.fail_json(
                    msg=(
                        "operating_system, operating_system_version, and "
                        "source_image_type are only valid when importing an image"
                    )
                )
            return
        if not params.get("operating_system"):
            self.module.fail_json(
                msg="operating_system is required when importing an image"
            )
        if not params.get("source_image_type"):
            self.module.fail_json(
                msg="source_image_type is required when importing an image"
            )
        if params.get("operating_system") == "windows" and not params.get(
            "operating_system_version"
        ):
            self.module.fail_json(
                msg=(
                    "operating_system_version is required when operating_system "
                    "is windows"
                )
            )
        if (
            params.get("source_image_type") == OCI_SOURCE_IMAGE_TYPE
            and params.get("launch_mode")
        ):
            self.module.fail_json(
                msg="launch_mode cannot be set when source_image_type is oci"
            )

    def create_resource(self):
        create_image_details = build_create_image_details(self.module.params)
        response = self.call_with_retry(
            self.client.create_image,
            create_image_details=create_image_details,
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_IMAGE_STATES,
        )

    def build_update_details(self, update_model_fields):
        return oci.core.models.UpdateImageDetails(**update_model_fields)

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_image,
            image_id=resource.id,
        )


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        image_id=dict(type="str"),
        instance_id=dict(type="str"),
        object_storage=dict(
            type="dict",
            options=dict(
                namespace_name=dict(type="str", required=True),
                bucket_name=dict(type="str", required=True),
                object_name=dict(type="str", required=True),
            ),
        ),
        source_uri=dict(type="str"),
        operating_system=dict(
            type="str",
            choices=OPERATING_SYSTEM_CHOICES,
        ),
        operating_system_version=dict(type="str"),
        source_image_type=dict(
            type="str",
            choices=["vmdk", "qcow2", "oci"],
        ),
        launch_mode=dict(
            type="str",
            choices=["native", "emulated", "paravirtualized"],
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[
            ("instance_id", "object_storage", "source_uri"),
        ],
    )

    OciImageModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
