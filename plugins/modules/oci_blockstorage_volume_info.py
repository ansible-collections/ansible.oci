# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_blockstorage_volume_info
short_description: Retrieve block volume information from Oracle Cloud Infrastructure
description:
  - Retrieve details about one or more OCI block volumes.
  - Use C(volume_id) to fetch a single volume, or C(compartment_id) to list
    volumes in a compartment.
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
      - The OCID of the compartment to list block volumes from.
      - Required when listing resources.
    type: str
  volume_id:
    description:
      - The OCID of a specific block volume to retrieve.
      - When specified, returns a single resource instead of a list.
    type: str
  availability_domain:
    description:
      - Filter listed volumes by availability domain.
      - Only used when C(compartment_id) is provided.
    type: str
"""

EXAMPLES = r"""
- name: List all block volumes in a compartment
  oracle.oci.oci_blockstorage_volume_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List block volumes in a compartment by name
  oracle.oci.oci_blockstorage_volume_info:
    compartment_id: ocid1.compartment.oc1..example
    name: example-volume

- name: Get a specific block volume
  oracle.oci.oci_blockstorage_volume_info:
    volume_id: ocid1.volume.oc1..example
"""

RETURN = r"""
volumes:
  description: List of block volumes that matched the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the block volume.
      type: str
      returned: always
      sample: ocid1.volume.oc1..example
    name:
      description: The display name of the block volume.
      type: str
      returned: always
      sample: example-volume
    compartment_id:
      description: The OCID of the compartment containing the block volume.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    availability_domain:
      description: The availability domain of the block volume.
      type: str
      returned: always
      sample: Uocm:PHX-AD-1
    lifecycle_state:
      description: The current lifecycle state of the block volume.
      type: str
      returned: always
      sample: AVAILABLE
    size_in_gbs:
      description: The size of the block volume in GBs.
      type: int
      returned: always
      sample: 50
    size_in_mbs:
      description: The size of the block volume in MBs.
      type: int
      returned: always
      sample: 51200
    vpus_per_gb:
      description: The number of VPUs per GB configured for the volume.
      type: int
      returned: always
      sample: 10
    auto_tuned_vpus_per_gb:
      description: The number of VPUs per GB autotuning has currently applied.
      type: int
      returned: always
      sample: 20
    is_auto_tune_enabled:
      description: Whether legacy detached-volume autotuning is enabled.
      type: bool
      returned: always
      sample: false
    is_reservations_enabled:
      description: Whether SCSI Persistent Reservation is enabled for the volume.
      type: bool
      returned: always
      sample: false
    autotune_policies:
      description: The autotune policies applied to the volume.
      type: list
      elements: dict
      returned: always
      contains:
        autotune_type:
          description: The autotune policy type (C(DETACHED_VOLUME) or C(PERFORMANCE_BASED)).
          type: str
          returned: always
          sample: PERFORMANCE_BASED
        max_vpus_per_gb:
          description: The maximum VPUs/GB for a performance-based policy.
          type: int
          returned: when autotune_type is PERFORMANCE_BASED
          sample: 120
    block_volume_replicas:
      description: The block volume replicas maintained for this volume.
      type: list
      elements: dict
      returned: always
      contains:
        block_volume_replica_id:
          description: The OCID of the block volume replica.
          type: str
          returned: always
          sample: ocid1.blockvolumereplica.oc1..example
        availability_domain:
          description: The availability domain of the replica.
          type: str
          returned: always
          sample: Uocm:PHX-AD-2
        display_name:
          description: The name of the replica.
          type: str
          returned: always
          sample: example-volume-replica
        kms_key_id:
          description: The OCID of the encryption key used by the replica, if any.
          type: str
          returned: always
          sample: null
    kms_key_id:
      description: The OCID of the customer-managed encryption key, if any.
      type: str
      returned: always
      sample: null
    cluster_placement_group_id:
      description: The OCID of the cluster placement group the volume is in, if any.
      type: str
      returned: always
      sample: null
    volume_group_id:
      description: The OCID of the source volume group, if the volume belongs to one.
      type: str
      returned: always
      sample: null
    source_details:
      description: The source the volume was provisioned from, if any.
      type: dict
      returned: always
      contains:
        type:
          description: The source type (for example C(volume), C(volumeBackup)).
          type: str
          returned: always
          sample: volumeBackup
        id:
          description: The OCID of the source volume, backup, or replica.
          type: str
          returned: when the source type carries a single id
          sample: ocid1.volumebackup.oc1..example
    system_tags:
      description: System tags applied to the block volume by OCI.
      type: dict
      returned: always
      sample: {}
    is_hydrated:
      description: Whether the volume's data has finished copying from its source.
      type: bool
      returned: always
      sample: true
    freeform_tags:
      description: Free-form tags applied to the block volume.
      type: dict
      returned: always
      sample: {"environment": "production"}
    defined_tags:
      description: Defined tags applied to the block volume.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
    time_created:
      description: The date and time the block volume was created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
  sample:
    - id: ocid1.volume.oc1..example
      name: example-volume
      compartment_id: ocid1.compartment.oc1..example
      availability_domain: Uocm:PHX-AD-1
      lifecycle_state: AVAILABLE
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


class OciBlockstorageVolumeInfoModule(OciInfoBase):
    """Concrete info adapter for OCI block volumes."""

    @property
    def client_class(self):
        return oci.core.BlockstorageClient

    results_key = "volumes"
    resource_id_param = "volume_id"
    resource_get_method = "get_volume"
    list_resource_method = "list_volumes"
    list_filter_params = [
        "compartment_id",
        "availability_domain",
        "lifecycle_state",
    ]


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        volume_id=dict(type="str"),
        availability_domain=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "volume_id"]],
    )

    OciBlockstorageVolumeInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
