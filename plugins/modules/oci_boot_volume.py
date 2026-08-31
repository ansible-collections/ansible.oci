# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_boot_volume
short_description: Manage a boot volume resource in Oracle Cloud Infrastructure
description:
  - Create, update, and delete OCI boot volumes via the Block Storage service.
  - Restore a boot volume backup by creating a new boot volume with
    C(source_details.type=bootVolumeBackup). This is CreateBootVolume, not a
    backup-module API.
  - Use M(ansible.oci.oci_boot_volume_backup) to create the backup first, and
    M(ansible.oci.oci_boot_volume_info) to list or fetch boot volumes.
  - Uses the shared OCI helper layer for authentication, waiting, retry
    behavior, and result shaping.
  - When C(wait) is true, create and update wait until the boot volume is
    C(AVAILABLE) and hydration has finished.
  - Create requests must omit C(boot_volume_id). After create, capture the
    returned boot volume ID and use it for later C(state=present) and
    C(state=absent) tasks.
version_added: "1.1.0"
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
      - The desired lifecycle state of the boot volume.
    type: str
    choices: [present, absent]
    default: present
  boot_volume_id:
    description:
      - The OCID of the boot volume.
      - When provided, the module manages this exact boot volume.
      - Required to distinguish between multiple boot volumes that share the
        same scoped C(name).
    type: str
  name:
    description:
      - Human-readable name for the boot volume.
      - Required when creating a boot volume.
      - When C(boot_volume_id) is omitted, the module uses
        C(compartment_id + availability_domain + name) to find an existing
        boot volume.
      - If exactly one boot volume matches, C(state=present) manages it as the
        update target and C(state=absent) deletes it.
      - If more than one boot volume matches, the task fails and the caller
        must supply C(boot_volume_id).
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the boot volume.
      - Required when creating a boot volume.
      - The module does not move an existing boot volume to another
        compartment.
      - Also scopes name-based boot volume lookups when C(boot_volume_id) is
        omitted.
    type: str
  availability_domain:
    description:
      - The availability domain in which to create the boot volume.
      - Required when creating a boot volume.
      - The module does not move an existing boot volume to another
        availability domain.
      - Also scopes name-based boot volume lookups when C(boot_volume_id) is
        omitted.
    type: str
  size_in_gbs:
    description:
      - The size of the boot volume in GBs.
      - When restoring from a backup, omit this to inherit the backup's size.
      - OCI only supports increasing the size of an existing boot volume;
        requesting a smaller size fails at the service.
    type: int
  vpus_per_gb:
    description:
      - The number of volume performance units (VPUs) per GB.
    type: int
  source_details:
    description:
      - The source used to provision the boot volume at create time.
      - Set C(type) to C(bootVolumeBackup) and C(id) to a boot volume backup
        OCID to restore from a backup.
      - Applied only at create time. Changing the source of an existing boot
        volume is not supported, so a change is rejected.
      - Cloning from a boot volume or restoring from a replica is not
        supported.
    type: dict
    suboptions:
      type:
        description:
          - The source type.
          - C(bootVolumeBackup) restores from a boot volume backup.
        type: str
        required: true
        choices: [bootVolumeBackup]
      id:
        description:
          - The OCID of the source boot volume backup.
        type: str
        required: true
notes:
  - Restore from a backup by setting C(source_details) at create time.
    Cloning from an existing boot volume is not supported.
  - C(source_details) is applied only at create time. Changing the source
    of an existing boot volume is not supported.
  - The module does not move an existing boot volume to another compartment
    or availability domain.
"""

EXAMPLES = r"""
- name: Restore a boot volume from a backup
  ansible.oci.oci_boot_volume:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    name: restored-boot-volume
    source_details:
      type: bootVolumeBackup
      id: ocid1.bootvolumebackup.oc1..example
  register: restored_boot_volume

- name: Reconcile a uniquely named restored boot volume by name (update tags)
  ansible.oci.oci_boot_volume:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    name: restored-boot-volume
    freeform_tags:
      role: replacement

- name: Update the restored boot volume name
  ansible.oci.oci_boot_volume:
    state: present
    boot_volume_id: "{{ restored_boot_volume.resource.id }}"
    name: restored-boot-volume-updated

- name: Delete the restored boot volume
  ansible.oci.oci_boot_volume:
    state: absent
    boot_volume_id: "{{ restored_boot_volume.resource.id }}"

- name: Delete a uniquely named boot volume without providing boot_volume_id
  ansible.oci.oci_boot_volume:
    state: absent
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    name: restored-boot-volume-updated
"""

RETURN = r"""
resource:
  description: The boot volume resource.
  returned: when state != absent
  type: dict
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
      sample: restored-boot-volume
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
      description:
        - Whether the boot volume has finished hydrating.
        - This is false while data is still copying after restore or an
          online size increase.
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
      contains:
        type:
          description: The source type (for example C(bootVolumeBackup)).
          type: str
          returned: always
          sample: bootVolumeBackup
        id:
          description: The OCID of the source boot volume backup.
          type: str
          returned: when the source type carries a single id
          sample: ocid1.bootvolumebackup.oc1..example
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
    id: ocid1.bootvolume.oc1..example
    name: restored-boot-volume
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    lifecycle_state: AVAILABLE
    size_in_gbs: 50
    vpus_per_gb: 10
    is_hydrated: true
    source_details:
      type: bootVolumeBackup
      id: ocid1.bootvolumebackup.oc1..example
    freeform_tags: {"environment": "production"}
    defined_tags: {"Operations": {"CostCenter": "42"}}
    time_created: "2026-01-01T00:00:00.000Z"
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_AVAILABLE,
    LIFECYCLE_FAILED,
    OCI_COMMON_ARGS,
    filter_none_values,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]

CREATE_REQUIRED_FIELDS = [
    "compartment_id",
    "availability_domain",
    "name",
    "source_details",
]
WAIT_FOR_BOOT_VOLUME_STATES = [LIFECYCLE_AVAILABLE]


def build_source_details(source_details):
    if not source_details:
        return None
    source_type = source_details.get("type")
    source_id = source_details.get("id")
    if source_type == "bootVolumeBackup" and source_id:
        return oci.core.models.BootVolumeSourceFromBootVolumeBackupDetails(
            id=source_id
        )
    raise ValueError(
        "source_details.type must be bootVolumeBackup and source_details.id is required"
    )


def build_create_boot_volume_details(params):
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "availability_domain": params.get("availability_domain"),
            "display_name": params.get("name"),
            "size_in_gbs": params.get("size_in_gbs"),
            "vpus_per_gb": params.get("vpus_per_gb"),
            "source_details": build_source_details(params.get("source_details")),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.core.models.CreateBootVolumeDetails(**details)


class OciBootVolumeModule(OciResourceBase):
    """Concrete resource adapter for OCI boot volumes."""

    @property
    def client_class(self):
        return oci.core.BlockstorageClient

    resource_id_param = "boot_volume_id"
    list_resource_method = "list_boot_volumes"
    list_filter_params = ("availability_domain",)
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "boot volume"
    update_method_name = "update_boot_volume"
    update_details_name = "update_boot_volume_details"
    update_wait_states = WAIT_FOR_BOOT_VOLUME_STATES
    update_field_specs = [
        {
            "param_name": "name",
            "resource_field": "display_name",
            "is_mutable": True,
        },
        {
            "param_name": "size_in_gbs",
            "is_mutable": True,
        },
        {
            "param_name": "vpus_per_gb",
            "is_mutable": True,
        },
        {
            "param_name": "availability_domain",
            "is_mutable": False,
        },
        {
            "param_name": "compartment_id",
            "is_mutable": False,
        },
        {
            "param_name": "source_details",
            "is_mutable": False,
            "compare": "subset_dict",
            "immutable_reason": (
                "source_details is applied only at create time; restoring "
                "into an existing boot volume is not supported"
            ),
        },
    ]

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_boot_volume,
            boot_volume_id=resource_id,
        )

    def wait_for_resource_id(self, resource_id, target_states, failure_states=None):
        resource = super().wait_for_resource_id(
            resource_id,
            target_states,
            failure_states=failure_states,
        )
        if not self.module.params.get("wait", True):
            return resource
        if LIFECYCLE_AVAILABLE not in target_states:
            return resource
        if not self._volume_is_hydrating(resource):
            return resource
        return self._wait_for_volume_hydrated(resource_id)

    def update_resource(self, resource):
        if self.module.params.get("wait", True) and self._volume_is_hydrating(resource):
            resource = self._wait_for_volume_hydrated(resource.id)
        return super().update_resource(resource)

    def _volume_is_hydrating(self, resource):
        return resource is not None and getattr(resource, "is_hydrated", True) is False

    def _wait_for_volume_hydrated(self, resource_id):
        timeout = self.module.params.get("wait_timeout", 1200)
        interval = self.module.params.get("wait_interval", 30)
        initial_response = self.get_resource_response(resource_id)

        def _hydration_complete(response):
            state = getattr(response.data, "lifecycle_state", None)
            if state == LIFECYCLE_FAILED:
                self.module.fail_json(
                    msg=f"Resource {resource_id} entered failure state: {state}",
                )
            return (
                state in WAIT_FOR_BOOT_VOLUME_STATES
                and getattr(response.data, "is_hydrated", True) is not False
            )

        waiter_result = oci.wait_until(
            self.client,
            initial_response,
            max_interval_seconds=interval,
            max_wait_seconds=timeout,
            evaluate_response=_hydration_complete,
            fetch_func=lambda response=None: self.get_resource_response(resource_id),
        )
        return getattr(waiter_result, "data", None)

    def create_resource(self):
        create_boot_volume_details = build_create_boot_volume_details(
            self.module.params
        )
        response = self.call_with_retry(
            self.client.create_boot_volume,
            create_boot_volume_details=create_boot_volume_details,
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_BOOT_VOLUME_STATES,
        )

    def build_update_details(self, update_model_fields):
        return oci.core.models.UpdateBootVolumeDetails(**update_model_fields)

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_boot_volume,
            boot_volume_id=resource.id,
        )


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        boot_volume_id=dict(type="str"),
        availability_domain=dict(type="str"),
        size_in_gbs=dict(type="int"),
        vpus_per_gb=dict(type="int"),
        source_details=dict(
            type="dict",
            options=dict(
                type=dict(
                    type="str",
                    required=True,
                    choices=["bootVolumeBackup"],
                ),
                id=dict(type="str", required=True),
            ),
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciBootVolumeModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
