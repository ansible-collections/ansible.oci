# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_blockstorage_volume
short_description: Manage a block volume resource in Oracle Cloud Infrastructure
description:
  - Create, update, and delete OCI block volumes via the Block Storage service.
  - A block volume is a detachable, availability-domain-scoped storage device.
    Use C(oci_volume_attachment) to attach it to a compute instance.
  - Uses the shared OCI helper layer for authentication, waiting, retry
    behavior, and result shaping.
  - When C(wait) is true, create and update wait until the volume is
    C(AVAILABLE) and hydration has finished. OCI rejects VPUs and autotune
    changes while a volume is hydrating, including after an online size
    increase.
  - Create requests must omit C(volume_id). After create, capture the returned
    volume ID and use it for later C(state=present) and C(state=absent) tasks.
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
      - The desired lifecycle state of the block volume.
    type: str
    choices: [present, absent]
    default: present
  volume_id:
    description:
      - The OCID of the block volume.
      - When provided, the module manages this exact volume.
      - Required to distinguish between multiple volumes that share the same
        scoped C(name).
    type: str
  name:
    description:
      - Human-readable name for the block volume.
      - Required when creating a volume.
      - When C(volume_id) is omitted, the module uses C(compartment_id + name)
        to find an existing volume.
      - If exactly one volume matches, C(state=present) manages it as the
        update target and C(state=absent) deletes it.
      - If more than one volume matches, the task fails and the caller must
        supply C(volume_id).
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the block volume.
      - Required when creating a volume.
      - The module does not move an existing volume to another compartment.
      - Also scopes name-based volume lookups when C(volume_id) is omitted.
    type: str
  availability_domain:
    description:
      - The availability domain in which to create the block volume.
      - Required when creating a volume.
      - The module does not move an existing volume to another availability
        domain.
    type: str
  size_in_gbs:
    description:
      - The size of the block volume in GBs.
      - Omit C(size_in_gbs) and C(vpus_per_gb) to use OCI's service defaults,
        which matches the Console "Default" size and performance option. The
        CLI documents those defaults as 1 TB at Balanced (10 VPUs/GB).
      - Set this to choose a custom size (the Console "Custom" option).
      - OCI only supports increasing the size of an existing volume; requesting
        a smaller size fails at the service.
    type: int
  vpus_per_gb:
    description:
      - The number of volume performance units (VPUs) per GB.
      - When performance-based autotune is off, selectable values are C(0),
        C(10), C(20), C(30), C(40), and so on up to C(120).
      - When C(performance_based_auto_tune) is true, this becomes the default
        (minimum) VPUs/GB the volume returns to when idle. In that case
        selectable values are C(10), C(20), C(30), and so on up to C(120).
      - The Console uses a selectable control that moves in steps of 10.
    type: int
  performance_based_auto_tune:
    description:
      - Whether to enable performance-based autotuning, which raises
        performance up to C(max_vpus_per_gb) based on workload and returns to
        C(vpus_per_gb) when idle.
      - The Console default is false. This parameter is unset by default so
        omitted values do not disable autotune on update.
      - When true, also set C(vpus_per_gb) and C(max_vpus_per_gb).
    type: bool
  max_vpus_per_gb:
    description:
      - The maximum VPUs/GB that performance-based autotuning may raise the
        volume to.
      - Selectable values are 10, 20, 30, and so on up to 120.
      - Required when C(performance_based_auto_tune) is true.
      - Must be greater than or equal to C(vpus_per_gb) when both are set.
      - On an existing volume that already has performance-based autotune, this
        can be updated on its own; the module keeps the current autotune flags.
    type: int
  detached_volume_auto_tune:
    description:
      - Whether to lower volume performance while the volume is detached.
      - Shown in the Console only when size and performance are Custom.
      - Independent of C(performance_based_auto_tune); both can be enabled.
      - Unset by default so omitted values do not disable autotune on update.
    type: bool
  kms_key_id:
    description:
      - The OCID of the Vault master encryption key to assign as the
        customer-managed key for the volume's at-rest encryption.
      - Omit this to encrypt with Oracle-managed keys.
      - Set this to encrypt with a customer-managed key. In the Console, the
        vault compartment, vault, and key compartment pickers are only used
        to select this OCID.
      - This is applied only at create time. Changing the encryption key of an
        existing volume is not supported by this module (OCI exposes a separate
        operation for that), so a change is rejected.
    type: str
  backup_policy_id:
    description:
      - The OCID of the volume backup policy to assign to the volume.
      - Applied only at create time. The volume resource does not return the
        assigned policy, and this module does not call the separate backup
        policy assignment API, so C(backup_policy_id) cannot be compared after
        create. A later C(state=present) that includes this value leaves the
        existing assignment unchanged and does not fail.
    type: str
  cluster_placement_group_id:
    description:
      - The OCID of the cluster placement group to place the volume in.
      - Set only at create time; moving an existing volume between cluster
        placement groups is not supported, so a change is rejected.
    type: str
  reservations_enabled:
    description:
      - Whether SCSI Persistent Reservation (SCSI PR) is enabled for the
        volume.
      - Returned by OCI as C(is_reservations_enabled).
    type: bool
notes:
  - Cross-availability-domain and cross-region replication are not supported.
    Replication can be added later.
  - Cloning a volume or restoring from a backup or replica is not supported.
    Created volumes are empty.
  - Omit C(kms_key_id) to encrypt with Oracle-managed keys. Set C(kms_key_id)
    to the OCID of a Vault master encryption key for customer-managed keys.
  - Changing the encryption key of an existing volume is not supported.
  - The module does not move an existing volume to another compartment or
    availability domain.
  - C(backup_policy_id) is applied only at create time. It cannot be
    compared or changed on an existing volume because OCI does not return
    the assignment on the volume resource. Passing it on a later
    C(state=present) task is ignored.
"""

EXAMPLES = r"""
- name: Create a volume with OCI default size and performance
  oracle.oci.oci_blockstorage_volume:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    name: default-volume
  register: created_volume

- name: Create a custom 50 GB Balanced block volume
  oracle.oci.oci_blockstorage_volume:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    name: example-volume
    size_in_gbs: 50
    vpus_per_gb: 10
  register: created_volume

- name: Create a custom Ultra High Performance volume without autotune
  oracle.oci.oci_blockstorage_volume:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    name: uhp-volume
    size_in_gbs: 100
    vpus_per_gb: 30

- name: Create a volume with performance-based autotuning
  oracle.oci.oci_blockstorage_volume:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    name: autotuned-volume
    size_in_gbs: 100
    vpus_per_gb: 10
    performance_based_auto_tune: true
    max_vpus_per_gb: 120

- name: Create a volume with detached-volume autotuning
  oracle.oci.oci_blockstorage_volume:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    name: detached-autotune-volume
    size_in_gbs: 50
    vpus_per_gb: 10
    detached_volume_auto_tune: true

- name: Create a volume with a customer-managed encryption key
  oracle.oci.oci_blockstorage_volume:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    name: encrypted-volume
    size_in_gbs: 100
    kms_key_id: ocid1.key.oc1..example
    backup_policy_id: ocid1.volumebackuppolicy.oc1..example

- name: Grow the volume and change its performance level
  oracle.oci.oci_blockstorage_volume:
    state: present
    volume_id: "{{ created_volume.resource.id }}"
    size_in_gbs: 100
    vpus_per_gb: 20

- name: Delete the created volume
  oracle.oci.oci_blockstorage_volume:
    state: absent
    volume_id: "{{ created_volume.resource.id }}"

- name: Delete a uniquely named volume without providing volume_id
  oracle.oci.oci_blockstorage_volume:
    state: absent
    compartment_id: ocid1.compartment.oc1..example
    name: example-volume
"""

RETURN = r"""
resource:
  description: The block volume resource.
  returned: when state != absent
  type: dict
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
      description:
        - The number of VPUs per GB configured for the volume.
        - C(0) is Lower Cost, C(10) is Balanced, C(20) is Higher Performance,
          and C(30) to C(120) is Ultra High Performance.
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
    is_hydrated:
      description:
        - Whether the volume has finished hydrating.
        - This is false while data is still copying after clone, restore, or
          an online size increase. OCI rejects VPUs and autotune updates
          until hydration completes.
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
    system_tags:
      description: System tags applied to the block volume by OCI.
      type: dict
      returned: always
      sample: {}
    time_created:
      description: The date and time the block volume was created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
  sample:
    id: ocid1.volume.oc1..example
    name: example-volume
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    lifecycle_state: AVAILABLE
    size_in_gbs: 50
    size_in_mbs: 51200
    vpus_per_gb: 10
    auto_tuned_vpus_per_gb: 10
    is_auto_tune_enabled: false
    is_reservations_enabled: false
    autotune_policies:
      - autotune_type: PERFORMANCE_BASED
        max_vpus_per_gb: 120
    block_volume_replicas: []
    kms_key_id: null
    is_hydrated: true
    freeform_tags: {"environment": "production"}
    defined_tags: {"Operations": {"CostCenter": "42"}}
    time_created: "2026-01-01T00:00:00.000Z"
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.oracle.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_AVAILABLE,
    LIFECYCLE_FAILED,
    OCI_COMMON_ARGS,
    filter_none_values,
    import_oci_sdk,
)
from ansible_collections.oracle.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]

CREATE_REQUIRED_FIELDS = [
    "compartment_id",
    "availability_domain",
    "name",
]
WAIT_FOR_VOLUME_STATES = [LIFECYCLE_AVAILABLE]

# Module inputs use lowercase snake_case choices (Ansible convention), while
# OCI's wire format and returned resources use upper-case constants (for
# example "performance_based" -> "PERFORMANCE_BASED"). This set is assigned to
# OciBlockstorageVolumeModule.enum_keys so the shared "subset_dict" comparator
# (see oci_resource.py) normalizes autotune_policies the same way the create
# builder does.
ENUM_KEYS = frozenset({"autotune_type"})


def _policy_value(policy, field_name):
    if isinstance(policy, dict):
        return policy.get(field_name)
    return getattr(policy, field_name, None)


def parse_autotune_policies(policies):
    has_performance = False
    has_detached = False
    max_vpus_per_gb = None
    for policy in policies or []:
        autotune_type = _policy_value(policy, "autotune_type")
        if isinstance(autotune_type, str):
            autotune_type = autotune_type.lower()
        if autotune_type == "performance_based":
            has_performance = True
            max_vpus_per_gb = _policy_value(policy, "max_vpus_per_gb")
        elif autotune_type == "detached_volume":
            has_detached = True
    return {
        "performance_based": has_performance,
        "detached_volume": has_detached,
        "max_vpus_per_gb": max_vpus_per_gb,
    }


def desired_autotune_policy_dicts(params, current_policies=None):
    performance_based = params.get("performance_based_auto_tune")
    detached_volume = params.get("detached_volume_auto_tune")
    max_vpus_per_gb = params.get("max_vpus_per_gb")
    if (
        performance_based is None
        and detached_volume is None
        and max_vpus_per_gb is None
    ):
        return None

    current = parse_autotune_policies(current_policies)
    desired_values = {
        "performance_based": performance_based,
        "detached_volume": detached_volume,
        "max_vpus_per_gb": max_vpus_per_gb,
    }
    for field_name in desired_values:
        if desired_values[field_name] is None:
            desired_values[field_name] = current[field_name]
    performance_based = desired_values["performance_based"]
    detached_volume = desired_values["detached_volume"]
    max_vpus_per_gb = desired_values["max_vpus_per_gb"]

    policies = []
    if performance_based:
        policy = {"autotune_type": "performance_based"}
        if max_vpus_per_gb is not None:
            policy["max_vpus_per_gb"] = max_vpus_per_gb
        policies.append(policy)
    if detached_volume:
        policies.append({"autotune_type": "detached_volume"})
    return policies


def autotune_policies_as_dicts(policies):
    dicts = []
    for policy in policies or []:
        item = {"autotune_type": _policy_value(policy, "autotune_type")}
        max_vpus_per_gb = _policy_value(policy, "max_vpus_per_gb")
        if max_vpus_per_gb is not None:
            item["max_vpus_per_gb"] = max_vpus_per_gb
        dicts.append(item)
    return dicts


def _sorted_autotune_dicts(policies):
    return sorted(
        policies or [],
        key=lambda item: (item.get("autotune_type") or "").upper(),
    )


SELECTABLE_VPUS_CHOICES = tuple(range(0, 121, 10))
AUTOTUNE_VPUS_CHOICES = tuple(range(10, 121, 10))


def validate_volume_performance(params, fail_json, current_policies=None):
    vpus_per_gb = params.get("vpus_per_gb")
    performance_based = params.get("performance_based_auto_tune")
    max_vpus_per_gb = params.get("max_vpus_per_gb")

    if vpus_per_gb is not None and vpus_per_gb not in SELECTABLE_VPUS_CHOICES:
        fail_json(
            msg=(
                "vpus_per_gb must be a selectable value "
                "(0, 10, 20, 30, ... 120)"
            )
        )
    if (
        performance_based is True
        and vpus_per_gb is not None
        and vpus_per_gb not in AUTOTUNE_VPUS_CHOICES
    ):
        fail_json(
            msg=(
                "vpus_per_gb must be a selectable autotune default value "
                "(10, 20, 30, ... 120)"
            )
        )

    if max_vpus_per_gb is not None:
        if max_vpus_per_gb not in AUTOTUNE_VPUS_CHOICES:
            fail_json(
                msg=(
                    "max_vpus_per_gb must be a selectable autotune value "
                    "(10, 20, 30, ... 120)"
                )
            )
        if performance_based is not True and (
            performance_based is False
            or not parse_autotune_policies(current_policies)["performance_based"]
        ):
            fail_json(
                msg=(
                    "max_vpus_per_gb can only be set when "
                    "performance_based_auto_tune is true"
                )
            )

    if (
        performance_based is True
        and vpus_per_gb is not None
        and max_vpus_per_gb is not None
        and max_vpus_per_gb < vpus_per_gb
    ):
        fail_json(
            msg=(
                "max_vpus_per_gb must be greater than or equal to vpus_per_gb"
            )
        )


def build_autotune_policies(autotune_policies):
    if autotune_policies is None:
        return None
    models = []
    for policy in autotune_policies:
        if policy.get("autotune_type") == "performance_based":
            models.append(
                oci.core.models.PerformanceBasedAutotunePolicy(
                    **filter_none_values(
                        {"max_vpus_per_gb": policy.get("max_vpus_per_gb")}
                    )
                )
            )
        elif policy.get("autotune_type") == "detached_volume":
            models.append(oci.core.models.DetachedVolumeAutotunePolicy())
        else:
            raise ValueError(
                "autotune_type must be performance_based or detached_volume, "
                f"got: {policy.get('autotune_type')!r}"
            )
    return models


# For updates, the shared planner records the raw parameter values in the update
# model; these builders convert them into the SDK model objects the update call
# expects, mirroring the create path (see oci_instance.py for the same idiom).
NESTED_UPDATE_BUILDERS = {
    "autotune_policies": build_autotune_policies,
}


def build_create_volume_details(params):
    policy_dicts = desired_autotune_policy_dicts(params)
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "availability_domain": params.get("availability_domain"),
            "display_name": params.get("name"),
            "size_in_gbs": params.get("size_in_gbs"),
            "vpus_per_gb": params.get("vpus_per_gb"),
            "kms_key_id": params.get("kms_key_id"),
            "backup_policy_id": params.get("backup_policy_id"),
            "cluster_placement_group_id": params.get("cluster_placement_group_id"),
            "is_reservations_enabled": params.get("reservations_enabled"),
            "autotune_policies": (
                build_autotune_policies(policy_dicts) if policy_dicts else None
            ),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.core.models.CreateVolumeDetails(**details)


class OciBlockstorageVolumeModule(OciResourceBase):
    """Concrete resource adapter for OCI block volumes."""

    @property
    def client_class(self):
        return oci.core.BlockstorageClient

    resource_id_param = "volume_id"
    list_resource_method = "list_volumes"
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "block volume"
    update_method_name = "update_volume"
    update_details_name = "update_volume_details"
    update_wait_states = WAIT_FOR_VOLUME_STATES
    enum_keys = ENUM_KEYS
    update_field_specs = [
        {
            "param_name": "name",
            "resource_field": "display_name",
            "update_field": "display_name",
            "is_mutable": True,
        },
        {
            "param_name": "size_in_gbs",
            "resource_field": "size_in_gbs",
            "update_field": "size_in_gbs",
            "is_mutable": True,
        },
        {
            "param_name": "vpus_per_gb",
            "resource_field": "vpus_per_gb",
            "update_field": "vpus_per_gb",
            "is_mutable": True,
        },
        {
            "param_name": "reservations_enabled",
            "resource_field": "is_reservations_enabled",
            "update_field": "is_reservations_enabled",
            "is_mutable": True,
        },
        {
            "param_name": "availability_domain",
            "resource_field": "availability_domain",
            "is_mutable": False,
        },
        {
            "param_name": "compartment_id",
            "resource_field": "compartment_id",
            "is_mutable": False,
        },
        {
            "param_name": "kms_key_id",
            "resource_field": "kms_key_id",
            "is_mutable": False,
            "immutable_reason": (
                "OCI changes a volume's encryption key through a separate "
                "operation this module does not manage"
            ),
        },
        {
            "param_name": "cluster_placement_group_id",
            "resource_field": "cluster_placement_group_id",
            "is_mutable": False,
        },
    ]

    def validate_create_request(self):
        super().validate_create_request()
        validate_volume_performance(self.module.params, self.module.fail_json)

    def build_update_plan(self, resource):
        validate_volume_performance(
            self.module.params,
            self.module.fail_json,
            current_policies=getattr(resource, "autotune_policies", None),
        )
        update_plan = super().build_update_plan(resource)
        desired_dicts = desired_autotune_policy_dicts(
            self.module.params,
            current_policies=getattr(resource, "autotune_policies", None),
        )
        if desired_dicts is None:
            return update_plan
        current_dicts = autotune_policies_as_dicts(
            getattr(resource, "autotune_policies", None)
        )
        # An empty list means "disable all autotune". The shared subset_dict
        # comparator treats a falsy desired value as {}, so handle that case
        # before comparing policy contents.
        if desired_dicts == []:
            if not current_dicts:
                return update_plan
        elif not self.compare_update_field_values(
            _sorted_autotune_dicts(current_dicts),
            _sorted_autotune_dicts(desired_dicts),
            compare="subset_dict",
        ):
            return update_plan
        update_plan["update_needed"] = True
        update_plan["update_model_fields"]["autotune_policies"] = desired_dicts
        return update_plan

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_volume,
            volume_id=resource_id,
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
                state in WAIT_FOR_VOLUME_STATES
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
        create_volume_details = build_create_volume_details(self.module.params)
        response = self.call_with_retry(
            self.client.create_volume,
            create_volume_details=create_volume_details,
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_VOLUME_STATES,
        )

    def build_update_details(self, update_model_fields):
        update_model_fields = dict(update_model_fields)
        for field_name, builder in NESTED_UPDATE_BUILDERS.items():
            if field_name in update_model_fields:
                update_model_fields[field_name] = builder(update_model_fields[field_name])
        return oci.core.models.UpdateVolumeDetails(**update_model_fields)

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_volume,
            volume_id=resource.id,
        )


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        volume_id=dict(type="str"),
        availability_domain=dict(type="str"),
        size_in_gbs=dict(type="int"),
        vpus_per_gb=dict(type="int"),
        performance_based_auto_tune=dict(type="bool"),
        max_vpus_per_gb=dict(type="int"),
        detached_volume_auto_tune=dict(type="bool"),
        kms_key_id=dict(type="str"),
        backup_policy_id=dict(type="str"),
        cluster_placement_group_id=dict(type="str"),
        reservations_enabled=dict(type="bool"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ["performance_based_auto_tune", True, ["vpus_per_gb", "max_vpus_per_gb"]],
        ],
    )

    OciBlockstorageVolumeModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
