# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_volume_group
short_description: Manage a volume group resource in Oracle Cloud Infrastructure
description:
  - Create, update, and delete OCI Block Volume groups.
  - A volume group is a collection of block and boot volumes that can be managed
    and backed up together, providing crash-consistent, point-in-time snapshots
    across all member volumes.
  - Use M(ansible.oci.oci_volume_group_info) to list or fetch volume groups.
  - Uses the shared OCI helper layer for authentication, waiting, retry
    behavior, and result shaping.
  - Create requests must omit C(volume_group_id). After create, capture the
    returned volume group ID and use it for later C(state=present) and
    C(state=absent) tasks.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_name_lookup_options
  - ansible.oci.oci_wait_options
  - ansible.oci.oci_tags_options
options:
  state:
    description:
      - The desired lifecycle state of the volume group.
    type: str
    choices: [present, absent]
    default: present
  volume_group_id:
    description:
      - The OCID of the volume group.
      - When provided, the module manages this exact volume group.
      - Required to distinguish between multiple volume groups that share the
        same scoped C(name).
    type: str
  name:
    description:
      - Human-readable name for the volume group.
      - Required when creating a volume group.
      - When C(volume_group_id) is omitted, the module uses
        C(compartment_id + name) to find an existing volume group.
      - If exactly one volume group matches, C(state=present) manages it as the
        update target and C(state=absent) deletes it.
      - If more than one volume group matches, the task fails and the caller
        must supply C(volume_group_id).
    type: str
  compartment_id:
    description:
      - The OCID of the compartment to create the volume group in.
      - Required when creating a volume group.
      - The module does not move an existing volume group to another
        compartment.
      - Also scopes name-based volume group lookups when C(volume_group_id) is
        omitted.
    type: str
  availability_domain:
    description:
      - The availability domain to create the volume group in.
      - Required when creating a volume group.
      - The module does not update this field after create.
      - Availability domain names are tenancy-specific; use
        M(ansible.oci.oci_availability_domain_info) to discover the valid names
        for your tenancy and region.
    type: str
  volume_ids:
    description:
      - The OCIDs of the block and boot volumes that make up the volume group.
      - Required when creating a volume group.
      - Supports updates; setting a different list adds or removes member
        volumes. The comparison is order-insensitive.
    type: list
    elements: str
  backup_policy_id:
    description:
      - The OCID of a volume backup policy to assign to the volume group at
        creation time.
      - The module does not update this field after create.
    type: str
"""

EXAMPLES = r"""
- name: Create a volume group from existing volumes
  ansible.oci.oci_volume_group:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    name: app-volume-group
    volume_ids:
      - ocid1.volume.oc1..example1
      - ocid1.volume.oc1..example2
  register: created_volume_group

- name: Add a volume to the group by updating the member list
  ansible.oci.oci_volume_group:
    state: present
    volume_group_id: "{{ created_volume_group.resource.id }}"
    volume_ids:
      - ocid1.volume.oc1..example1
      - ocid1.volume.oc1..example2
      - ocid1.volume.oc1..example3

- name: Reconcile a uniquely named volume group by name (update tags)
  ansible.oci.oci_volume_group:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    name: app-volume-group
    volume_ids:
      - ocid1.volume.oc1..example1
      - ocid1.volume.oc1..example2
    freeform_tags:
      env: prod

- name: Delete the volume group
  ansible.oci.oci_volume_group:
    state: absent
    volume_group_id: "{{ created_volume_group.resource.id }}"

- name: Delete a uniquely named volume group without providing volume_group_id
  ansible.oci.oci_volume_group:
    state: absent
    compartment_id: ocid1.compartment.oc1..example
    name: app-volume-group
"""

RETURN = r"""
resource:
  description: The volume group resource.
  returned: when state != absent
  type: dict
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
    id: ocid1.volumegroup.oc1..example
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

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_AVAILABLE,
    OCI_COMMON_ARGS,
    filter_none_values,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]

CREATE_REQUIRED_FIELDS = [
    "compartment_id",
    "availability_domain",
    "name",
    "volume_ids",
]
WAIT_FOR_VOLUME_GROUP_STATES = [LIFECYCLE_AVAILABLE]


def build_create_volume_group_details(params):
    # On create, member volumes are supplied through a source-details model
    # (VolumeGroupSourceFromVolumesDetails); on update they go directly into
    # UpdateVolumeGroupDetails.volume_ids instead.
    source_details = oci.core.models.VolumeGroupSourceFromVolumesDetails(
        volume_ids=params.get("volume_ids"),
    )
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "availability_domain": params.get("availability_domain"),
            "display_name": params.get("name"),
            "source_details": source_details,
            "backup_policy_id": params.get("backup_policy_id"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.core.models.CreateVolumeGroupDetails(**details)


class OciVolumeGroupModule(OciResourceBase):
    """Concrete resource adapter for OCI volume groups."""

    @property
    def client_class(self):
        return oci.core.BlockstorageClient

    resource_id_param = "volume_group_id"
    list_resource_method = "list_volume_groups"
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "volume group"
    update_method_name = "update_volume_group"
    update_details_name = "update_volume_group_details"
    update_wait_states = WAIT_FOR_VOLUME_GROUP_STATES
    update_field_specs = (
        UpdateFieldSpec(
            param_name="name",
            resource_field="display_name",
            is_mutable=True,
        ),
        UpdateFieldSpec(
            param_name="volume_ids",
            is_mutable=True,
            compare="sorted_list",
        ),
        UpdateFieldSpec(
            param_name="availability_domain",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="compartment_id",
            is_mutable=False,
        ),
    )

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_volume_group,
            volume_group_id=resource_id,
        )

    def create_resource(self):
        create_volume_group_details = build_create_volume_group_details(
            self.module.params
        )
        response = self.call_with_retry(
            self.client.create_volume_group,
            create_volume_group_details=create_volume_group_details,
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_VOLUME_GROUP_STATES,
        )

    def build_update_details(self, update_model_fields):
        return oci.core.models.UpdateVolumeGroupDetails(**update_model_fields)

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_volume_group,
            volume_group_id=resource.id,
        )


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        volume_group_id=dict(type="str"),
        availability_domain=dict(type="str"),
        volume_ids=dict(type="list", elements="str"),
        backup_policy_id=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciVolumeGroupModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
