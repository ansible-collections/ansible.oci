# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_volume_group_info
short_description: Retrieve volume group information from Oracle Cloud Infrastructure
description:
  - Retrieve details about one or more OCI Block Volume groups.
  - Use C(volume_group_id) to fetch a single volume group, or C(compartment_id)
    to list volume groups in a compartment.
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
      - The OCID of the compartment to list volume groups from.
      - Required when listing resources.
    type: str
  volume_group_id:
    description:
      - The OCID of a specific volume group to retrieve.
      - When specified, returns a single resource instead of a list.
    type: str
  availability_domain:
    description:
      - Filter listed volume groups by availability domain.
      - Only used when C(compartment_id) is provided.
    type: str
"""

EXAMPLES = r"""
- name: List all volume groups in a compartment
  oracle.oci.oci_volume_group_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List volume groups in an availability domain
  oracle.oci.oci_volume_group_info:
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1

- name: List volume groups in a compartment by name
  oracle.oci.oci_volume_group_info:
    compartment_id: ocid1.compartment.oc1..example
    name: app-volume-group

- name: Get a specific volume group
  oracle.oci.oci_volume_group_info:
    volume_group_id: ocid1.volumegroup.oc1..example
"""

RETURN = r"""
volume_groups:
  description: List of volume groups that matched the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the volume group.
      type: str
      returned: always
      sample: ocid1.volumegroup.oc1..example
    name:
      description: The display name of the volume group.
      type: str
      returned: always
      sample: app-volume-group
    compartment_id:
      description: The OCID of the compartment containing the volume group.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    availability_domain:
      description: The availability domain the volume group is in.
      type: str
      returned: always
      sample: Uocm:PHX-AD-1
    lifecycle_state:
      description: The current lifecycle state of the volume group.
      type: str
      returned: always
      sample: AVAILABLE
    volume_ids:
      description: The OCIDs of the volumes that are members of the volume group.
      type: list
      elements: str
      returned: always
      sample:
        - ocid1.volume.oc1..example1
        - ocid1.volume.oc1..example2
    size_in_gbs:
      description: The aggregate size of the volume group, in GBs.
      type: int
      returned: always
      sample: 100
    size_in_mbs:
      description: The aggregate size of the volume group, in MBs.
      type: int
      returned: always
      sample: 102400
    source_details:
      description: The source the volume group was provisioned from.
      type: dict
      returned: always
      contains:
        type:
          description:
            - The source type.
            - C(volumeIds) when created from member volumes, C(volumeGroupId)
              when cloned from another volume group, C(volumeGroupBackupId)
              when restored from a backup, or C(volumeGroupReplicaId) when
              created from a replica.
          type: str
          returned: always
          sample: volumeIds
        volume_ids:
          description: The OCIDs of the source volumes, when C(type) is C(volumeIds).
          type: list
          elements: str
          returned: when type is volumeIds
          sample:
            - ocid1.volume.oc1..example1
            - ocid1.volume.oc1..example2
        volume_group_id:
          description: The OCID of the source volume group, when C(type) is C(volumeGroupId).
          type: str
          returned: when type is volumeGroupId
          sample: ocid1.volumegroup.oc1..example
        volume_group_backup_id:
          description: The OCID of the source volume group backup, when C(type) is C(volumeGroupBackupId).
          type: str
          returned: when type is volumeGroupBackupId
          sample: ocid1.volumegroupbackup.oc1..example
        volume_group_replica_id:
          description: The OCID of the source volume group replica, when C(type) is C(volumeGroupReplicaId).
          type: str
          returned: when type is volumeGroupReplicaId
          sample: ocid1.volumegroupreplica.oc1..example
    volume_group_replicas:
      description: The volume group replicas maintained for this volume group.
      type: list
      elements: dict
      returned: always
      contains:
        volume_group_replica_id:
          description: The OCID of the volume group replica.
          type: str
          returned: always
          sample: ocid1.volumegroupreplica.oc1..example
        availability_domain:
          description: The availability domain of the replica.
          type: str
          returned: always
          sample: Uocm:PHX-AD-2
        display_name:
          description: The name of the replica.
          type: str
          returned: always
          sample: app-volume-group-replica
        kms_key_id:
          description: The OCID of the encryption key used by the replica, if any.
          type: str
          returned: always
          sample: null
    is_hydrated:
      description: Whether the volume group's contents have finished copying from its source.
      type: bool
      returned: always
      sample: true
    freeform_tags:
      description: Free-form tags applied to the volume group.
      type: dict
      returned: always
      sample: {"environment": "production"}
    defined_tags:
      description: Defined tags applied to the volume group.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
    time_created:
      description: The date and time the volume group was created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
  sample:
    - id: ocid1.volumegroup.oc1..example
      name: app-volume-group
      compartment_id: ocid1.compartment.oc1..example
      availability_domain: Uocm:PHX-AD-1
      lifecycle_state: AVAILABLE
      volume_ids:
        - ocid1.volume.oc1..example1
        - ocid1.volume.oc1..example2
      size_in_gbs: 100
      size_in_mbs: 102400
      source_details:
        type: volumeIds
        volume_ids:
          - ocid1.volume.oc1..example1
          - ocid1.volume.oc1..example2
      volume_group_replicas: []
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


class OciVolumeGroupInfoModule(OciInfoBase):
    """Concrete info adapter for OCI volume groups."""

    @property
    def client_class(self):
        return oci.core.BlockstorageClient

    results_key = "volume_groups"
    resource_id_param = "volume_group_id"
    resource_get_method = "get_volume_group"
    list_resource_method = "list_volume_groups"
    list_filter_params = [
        "compartment_id",
        "availability_domain",
        "lifecycle_state",
    ]


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        volume_group_id=dict(type="str"),
        availability_domain=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "volume_group_id"]],
    )

    OciVolumeGroupInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
