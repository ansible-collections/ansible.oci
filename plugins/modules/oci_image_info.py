# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_image_info
short_description: Retrieve Compute image information from Oracle Cloud Infrastructure
description:
  - Retrieve details about one or more OCI Compute images.
  - Use C(image_id) to fetch a specific image, or C(compartment_id) to list
    images available in a compartment.
  - This is a read-only module and does not modify resources.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_info_filter_options
options:
  compartment_id:
    description:
      - The OCID of the compartment to list images from.
      - Required when listing resources.
    type: str
  image_id:
    description:
      - The OCID of a specific image to retrieve.
      - When specified, narrows C(images) to at most one matching element
        instead of listing every image in a compartment. Returns an empty
        C(images) list if no image exists for this OCID.
    type: str
  operating_system:
    description:
      - Filter listed images by operating system.
      - This expects the exact OCI operating system value returned by
        C(oci_image_info), for example C(Oracle Linux), C(Ubuntu), or
        C(Windows Server) for example but more values are possible.
    type: str
  operating_system_version:
    description:
      - Filter listed images by operating system version.
      - This expects the exact OCI operating system version returned by
        C(oci_image_info), for example C(9), C(22.04), C(24.04), or
        C(2022).
      - Exact values vary by operating system and OCI's current image catalog.
      - Only used when C(compartment_id) is provided.
    type: str
  shape:
    description:
      - Filter listed images by compatibility with a compute shape.
      - Only used when C(compartment_id) is provided.
    type: str
notes:
  - OCI returns both platform images and custom images from C(list_images).
  - Oracle-provided platform images return C(compartment_id) as C(null) since
    they are not owned by any compartment in your tenancy. Custom images
    return the compartment that owns them.
  - The local C(name) filter matches the image display name exactly.
  - Common OCI public image families documented by OCI include
    C(Oracle Linux), C(Ubuntu), and C(Windows Server). Other values can appear
    and custom images too.
  - Use an unfiltered C(oci_image_info) query first if you need to discover the
    current C(operating_system) and C(operating_system_version) values available
    in your region and compartment.
"""

EXAMPLES = r"""
- name: List all images in a compartment
  ansible.oci.oci_image_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List Oracle Linux images compatible with a shape
  ansible.oci.oci_image_info:
    compartment_id: ocid1.compartment.oc1..example
    operating_system: Oracle Linux
    operating_system_version: "9"
    shape: VM.Standard.E4.Flex

- name: List Ubuntu 22.04 images
  ansible.oci.oci_image_info:
    compartment_id: ocid1.compartment.oc1..example
    operating_system: Ubuntu
    operating_system_version: "22.04"

- name: Get a specific image by OCID
  ansible.oci.oci_image_info:
    image_id: ocid1.image.oc1..example
"""

RETURN = r"""
images:
  description: List of images that matched the query.
  returned: always
  type: list
  elements: dict
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
      sample: Oracle-Linux-9
    compartment_id:
      description:
        - The OCID of the compartment containing the image.
        - Returned as C(null) for Oracle-provided platform images, since those
          are not owned by any compartment in your tenancy. Populated for
          custom images.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    operating_system:
      description: The operating system for the image.
      type: str
      returned: always
      sample: Oracle Linux
    operating_system_version:
      description: The operating system version for the image.
      type: str
      returned: always
      sample: "9"
    lifecycle_state:
      description: The current lifecycle state of the image.
      type: str
      returned: always
      sample: AVAILABLE
    create_image_allowed:
      description: Whether instances launched with this image can be used to create new images.
      type: bool
      returned: always
      sample: true
    launch_mode:
      description: The launch mode supported by the image.
      type: str
      returned: when supported
      sample: NATIVE
    launch_options:
      description: Tuning options for VM shape compatibility and performance.
      type: dict
      returned: when supported
      contains:
        boot_volume_type:
          description: Emulation type for the boot volume.
          type: str
          returned: when supported
          sample: PARAVIRTUALIZED
        firmware:
          description: Firmware used to boot the VM.
          type: str
          returned: when supported
          sample: UEFI_64
        network_type:
          description: Emulation type for the physical network interface card.
          type: str
          returned: when supported
          sample: PARAVIRTUALIZED
        remote_data_volume_type:
          description: Emulation type for remote block storage volumes.
          type: str
          returned: when supported
          sample: PARAVIRTUALIZED
        is_pv_encryption_in_transit_enabled:
          description: Whether in-transit encryption for paravirtualized volumes is enabled.
          type: bool
          returned: when supported
          sample: true
        is_consistent_volume_naming_enabled:
          description: Whether the consistent volume naming feature is enabled.
          type: bool
          returned: when supported
          sample: true
      sample:
        boot_volume_type: PARAVIRTUALIZED
        firmware: UEFI_64
        network_type: PARAVIRTUALIZED
        remote_data_volume_type: PARAVIRTUALIZED
        is_pv_encryption_in_transit_enabled: true
        is_consistent_volume_naming_enabled: true
    agent_features:
      description: Oracle Cloud Agent features supported on the image.
      type: dict
      returned: when supported
      contains:
        is_monitoring_supported:
          description: Whether monitoring is supported on the image. Not currently used by OCI.
          type: bool
          returned: when supported
        is_management_supported:
          description: Whether management is supported on the image. Not currently used by OCI.
          type: bool
          returned: when supported
    listing_type:
      description: The Marketplace listing type of the image, when applicable.
      type: str
      returned: when supported
      sample: NONE
    size_in_mbs:
      description: The boot volume size for an instance launched from this image, in MBs.
      type: int
      returned: when supported
      sample: 47694
    billable_size_in_gbs:
      description: The size of the internal storage for this image that is subject to billing, in GBs.
      type: int
      returned: when supported
      sample: 6
    base_image_id:
      description: The OCID of the base image when the image is a custom image.
      type: str
      returned: when supported
      sample: ocid1.image.oc1..baseexample
    defined_tags:
      description: Defined tags for the image, keyed by namespace.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
    freeform_tags:
      description: Free-form tags for the image.
      type: dict
      returned: always
      sample: {"Department": "Finance"}
    time_created:
      description: The date and time the image was created, in RFC3339 format.
      type: str
      returned: when supported
      sample: "2026-01-01T00:00:00.000Z"
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import (
    OciInfoBase,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]


class OciImageInfoModule(OciInfoBase):
    """Concrete info adapter for OCI Compute images."""

    @property
    def client_class(self):
        return oci.core.ComputeClient

    results_key = "images"
    resource_id_param = "image_id"
    resource_get_method = "get_image"
    list_resource_method = "list_images"
    list_filter_params = [
        "compartment_id",
        "operating_system",
        "operating_system_version",
        "shape",
        "lifecycle_state",
    ]


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        image_id=dict(type="str"),
        name=dict(type="str"),
        operating_system=dict(type="str"),
        operating_system_version=dict(type="str"),
        shape=dict(type="str"),
        lifecycle_state=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "image_id"]],
    )

    OciImageInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
