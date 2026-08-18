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
  - A custom image is captured from an existing Compute instance and can then be
    used to launch new instances with M(oracle.oci.oci_instance).
  - Use M(oracle.oci.oci_image_info) to list platform and custom images.
  - Uses the shared OCI helper layer for authentication, waiting, retry
    behavior, and result shaping.
  - Create requests must omit C(image_id). After create, capture the returned
    image ID and use it for later C(state=present) and C(state=absent) tasks.
  - This module only creates custom images from an existing instance. Importing
    an image from Object Storage and exporting an image to Object Storage are
    not supported.
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
      - Required when creating an image.
      - The instance should be stopped before capturing an image to guarantee a
        consistent image.
      - The module does not update this field after create.
    type: str
  launch_mode:
    description:
      - The launch mode to configure the custom image with, determining how the
        instances launched from it boot.
      - When omitted, OCI derives the launch mode from the source instance.
      - The module does not update this field after create.
    type: str
    choices: [native, emulated, paravirtualized, custom]
"""

EXAMPLES = r"""
- name: Capture a custom image from a stopped instance
  oracle.oci.oci_image:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: hardened-oracle-linux
    instance_id: ocid1.instance.oc1..example
  register: created_image

- name: Reconcile a uniquely named image by name (update tags)
  oracle.oci.oci_image:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: hardened-oracle-linux
    freeform_tags:
      env: prod

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
    "instance_id",
    "name",
]
WAIT_FOR_IMAGE_STATES = [LIFECYCLE_AVAILABLE]

# Module inputs use lowercase snake_case choices (Ansible convention), while
# OCI's wire format uses upper-case constants (for example "paravirtualized" ->
# "PARAVIRTUALIZED").
ENUM_KEYS = {"launch_mode"}


def build_create_image_details(params):
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "instance_id": params.get("instance_id"),
            "display_name": params.get("name"),
            "launch_mode": normalize_enum_values(
                {"launch_mode": params.get("launch_mode")}, ENUM_KEYS
            )["launch_mode"],
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
    # instance_id is intentionally not an update field spec. It is a create-only
    # source parameter with no counterpart on the Image resource, so it must not
    # participate in drift detection: rerunning the create task (which supplies
    # instance_id) against an existing image must stay idempotent.
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
        launch_mode=dict(
            type="str",
            choices=["native", "emulated", "paravirtualized", "custom"],
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciImageModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
