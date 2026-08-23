# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_boot_volume_info
short_description: Retrieve boot volume information from Oracle Cloud Infrastructure
description:
  - Retrieve details about one or more OCI boot volumes.
  - Use C(boot_volume_id) to fetch a single boot volume, or C(compartment_id)
    to list boot volumes in a compartment.
  - Listing boot volumes typically also requires C(availability_domain).
  - This is a read-only module and does not modify resources.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - oracle.oci.oci_auth_options
  - oracle.oci.oci_info_filter_options
options:
  compartment_id:
    description:
      - The OCID of the compartment to list boot volumes from.
      - Required when listing resources.
    type: str
  boot_volume_id:
    description:
      - The OCID of a specific boot volume to retrieve.
      - When specified, returns a single resource instead of a list.
    type: str
  availability_domain:
    description:
      - Filter listed boot volumes by availability domain.
      - OCI requires this value when listing boot volumes by compartment.
      - Only used when C(compartment_id) is provided.
    type: str
"""

EXAMPLES = r"""
- name: List boot volumes in a compartment and availability domain
  oracle.oci.oci_boot_volume_info:
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1

- name: List boot volumes in a compartment by name
  oracle.oci.oci_boot_volume_info:
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    name: example-instance (Boot Volume)

- name: Get a specific boot volume
  oracle.oci.oci_boot_volume_info:
    boot_volume_id: ocid1.bootvolume.oc1..example
"""

RETURN = r"""
boot_volumes:
  description: List of boot volumes that matched the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the boot volume.
      type: str
      returned: always
      sample: ocid1.bootvolume.oc1..example
    name:
      description: The display name of the boot volume.
      type: str
      returned: always
      sample: example-instance (Boot Volume)
    compartment_id:
      description: The OCID of the compartment containing the boot volume.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    availability_domain:
      description: The availability domain of the boot volume.
      type: str
      returned: always
      sample: Uocm:PHX-AD-1
    lifecycle_state:
      description: The current lifecycle state of the boot volume.
      type: str
      returned: always
      sample: AVAILABLE
    image_id:
      description: The OCID of the image used to create this boot volume, if any.
      type: str
      returned: always
      sample: ocid1.image.oc1..example
    size_in_gbs:
      description: The size of the boot volume in GBs.
      type: int
      returned: always
      sample: 50
    size_in_mbs:
      description: The size of the boot volume in MBs.
      type: int
      returned: always
      sample: 51200
    vpus_per_gb:
      description: The number of VPUs per GB configured for the boot volume.
      type: int
      returned: always
      sample: 10
    auto_tuned_vpus_per_gb:
      description: The number of VPUs per GB autotuning has currently applied.
      type: int
      returned: always
      sample: 20
    is_auto_tune_enabled:
      description: Whether performance autotuning is enabled.
      type: bool
      returned: always
      sample: false
    is_hydrated:
      description: Whether the boot volume's data has finished copying from its source.
      type: bool
      returned: always
      sample: true
    kms_key_id:
      description: The OCID of the customer-managed encryption key, if any.
      type: str
      returned: always
      sample: null
    volume_group_id:
      description: The OCID of the volume group this boot volume belongs to, if any.
      type: str
      returned: always
      sample: null
    cluster_placement_group_id:
      description: The OCID of the cluster placement group the boot volume is in, if any.
      type: str
      returned: always
      sample: null
    source_details:
      description: The source the boot volume was provisioned from, if any.
      type: dict
      returned: always
      sample: {"type": "bootVolumeBackup", "id": "ocid1.bootvolumebackup.oc1..example"}
    autotune_policies:
      description: The autotune policies applied to the boot volume.
      type: list
      elements: dict
      returned: always
      sample: []
    boot_volume_replicas:
      description: The boot volume replicas maintained for this boot volume.
      type: list
      elements: dict
      returned: always
      sample: []
    freeform_tags:
      description: Free-form tags applied to the boot volume.
      type: dict
      returned: always
      sample: {"environment": "production"}
    defined_tags:
      description: Defined tags applied to the boot volume.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
    system_tags:
      description: System tags applied to the boot volume by OCI.
      type: dict
      returned: always
      sample: {}
    time_created:
      description: The date and time the boot volume was created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
  sample:
    - id: ocid1.bootvolume.oc1..example
      name: example-instance (Boot Volume)
      compartment_id: ocid1.compartment.oc1..example
      availability_domain: Uocm:PHX-AD-1
      lifecycle_state: AVAILABLE
      image_id: ocid1.image.oc1..example
      size_in_gbs: 50
      size_in_mbs: 51200
      vpus_per_gb: 10
      is_hydrated: true
      freeform_tags: {"environment": "production"}
      defined_tags: {"Operations": {"CostCenter": "42"}}
      time_created: "2026-01-01T00:00:00.000Z"
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.oracle.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.oracle.oci.plugins.module_utils.oci_info import (
    OciInfoBase,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]


class OciBootVolumeInfoModule(OciInfoBase):
    """Concrete info adapter for OCI boot volumes."""

    @property
    def client_class(self):
        return oci.core.BlockstorageClient

    results_key = "boot_volumes"
    resource_id_param = "boot_volume_id"
    resource_get_method = "get_boot_volume"
    list_resource_method = "list_boot_volumes"
    list_filter_params = [
        "compartment_id",
        "availability_domain",
    ]


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        boot_volume_id=dict(type="str"),
        availability_domain=dict(type="str"),
        name=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "boot_volume_id"]],
    )

    OciBootVolumeInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
