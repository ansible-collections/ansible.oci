"""Shared SDK models and builders for OCI Compute resources."""

from __future__ import absolute_import, division, print_function

from copy import deepcopy

__metaclass__ = type

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    build_model,
    build_nested_model,
    filter_none_values,
    import_oci_sdk,
    normalize_enum_values,
    rename_aliased_fields,
)

oci = import_oci_sdk()[0]


POLYMORPHIC_MODELS = {
    "ComputeInstanceDetails": (
        "instance_type",
        {"compute": "ComputeInstanceDetails", "instance_options": "ComputeInstanceOptions"},
    ),
    "InstanceConfigurationInstanceSourceDetails": (
        "source_type",
        {
            "image": "InstanceConfigurationInstanceSourceViaImageDetails",
            "bootVolume": "InstanceConfigurationInstanceSourceViaBootVolumeDetails",
        },
    ),
    "InstanceConfigurationVolumeSourceDetails": (
        "type",
        {
            "volume": "InstanceConfigurationVolumeSourceFromVolumeDetails",
            "volumeBackup": "InstanceConfigurationVolumeSourceFromVolumeBackupDetails",
        },
    ),
    "InstanceConfigurationAttachVolumeDetails": (
        "type",
        {
            "iscsi": "InstanceConfigurationIscsiAttachVolumeDetails",
            "paravirtualized": "InstanceConfigurationParavirtualizedAttachVolumeDetails",
        },
    ),
    "InstanceConfigurationAutotunePolicy": (
        "autotune_type",
        {
            "PERFORMANCE_BASED": "InstanceConfigurationPerformanceBasedAutotunePolicy",
            "DETACHED_VOLUME": "InstanceConfigurationDetachedVolumeAutotunePolicy",
        },
    ),
}

MODEL_ENUM_FIELDS = {
    "InstanceConfigurationLaunchInstancePlatformConfig": {"type", "numa_nodes_per_socket"},
    "InstanceConfigurationAutotunePolicy": {"autotune_type"},
    "InstanceConfigurationLaunchOptions": {
        "boot_volume_type",
        "firmware",
        "network_type",
        "remote_data_volume_type",
    },
    "InstanceConfigurationAvailabilityConfig": {"recovery_action"},
    "InstanceAgentPluginConfigDetails": {"desired_state"},
    "InstanceConfigurationLaunchInstanceDetails": {
        "launch_mode",
        "preferred_maintenance_action",
    },
    "InstanceConfigurationLaunchInstanceShapeConfigDetails": {
        "baseline_ocpu_utilization",
    },
}

MODEL_FIELD_ALIASES = {
    "InstanceConfigurationLaunchInstanceAgentConfigDetails": {
        "all_plugins_disabled": "are_all_plugins_disabled",
        "management_disabled": "is_management_disabled",
        "monitoring_disabled": "is_monitoring_disabled",
    },
    "InstanceConfigurationLaunchInstanceDetails": {"name": "display_name"},
    "InstanceConfigurationCreateVnicDetails": {"name": "display_name"},
    "InstanceConfigurationAttachVnicDetails": {"name": "display_name"},
    "InstanceConfigurationAttachVolumeDetails": {"name": "display_name"},
    "InstanceConfigurationIscsiAttachVolumeDetails": {"name": "display_name"},
    "InstanceConfigurationParavirtualizedAttachVolumeDetails": {"name": "display_name"},
    "InstanceConfigurationCreateVolumeDetails": {"name": "display_name"},
    "InstanceConfigurationBlockVolumeReplicaDetails": {"name": "display_name"},
}

MODEL_DISCRIMINATOR_ALIASES = {
    ("InstanceConfigurationInstanceSourceDetails", "source_type"): {
        "boot_volume": "bootVolume",
    },
    ("InstanceConfigurationVolumeSourceDetails", "type"): {
        "volume_backup": "volumeBackup",
    },
}


def _configuration_model_type(model_name, fields):
    """Resolve a concrete model for a configuration discriminator.

    Args:
        model_name: The SDK model name.
        fields: Normalized fields for the model.

    Returns:
        The concrete SDK model name.
    """
    if model_name == "PreemptionAction":
        return "TerminatePreemptionAction"
    if model_name == "InstanceConfigurationLaunchInstancePlatformConfig":
        prefix = "".join(word.capitalize() for word in fields.get("type", "").split("_"))
        return "InstanceConfiguration" + prefix + "LaunchInstancePlatformConfig"
    discriminator = POLYMORPHIC_MODELS.get(model_name)
    if discriminator:
        field, variants = discriminator
        return variants.get(fields.get(field), model_name)
    return model_name


def _configuration_model_fields(model_name, fields):
    """Convert declared model fields without changing user dictionaries.

    Args:
        model_name: The SDK model name.
        fields: User fields for the model.

    Returns:
        A copy with SDK field names and enum values.
    """
    fields = rename_aliased_fields(fields, MODEL_FIELD_ALIASES.get(model_name, {}))
    if model_name == "PreemptionAction":
        fields.pop("type", None)
    enum_fields = MODEL_ENUM_FIELDS.get(model_name, set())
    for field, value in fields.items():
        aliases = MODEL_DISCRIMINATOR_ALIASES.get((model_name, field), {})
        if isinstance(value, str):
            fields[field] = aliases.get(value, value.upper() if field in enum_fields else value)
    return fields


def _build_configuration_model(model_name, fields):
    """Build typed nested configuration models through the shared builder.

    Args:
        model_name: The SDK model name.
        fields: User fields, or None.

    Returns:
        The SDK model, or None when fields are omitted.
    """
    if fields is None:
        return None
    fields = _configuration_model_fields(model_name, fields)
    model_name = _configuration_model_type(model_name, fields)
    model_class = getattr(oci.core.models, model_name)
    nested_models = {}
    list_models = {}
    for field, type_name in model_class().swagger_types.items():
        if type_name.startswith("list[") and hasattr(oci.core.models, type_name[5:-1]):
            list_models[field] = type_name[5:-1]
        elif hasattr(oci.core.models, type_name):
            nested_models[field] = type_name
    return build_nested_model(
        model_class, fields, nested_models, list_models, _build_configuration_model
    )


ENUM_KEYS = {
    "power_state",
    "recovery_action",
    "desired_state",
    "type",
    "boot_volume_type",
    "firmware",
    "network_type",
    "remote_data_volume_type",
    "numa_nodes_per_socket",
}

AGENT_CONFIG_PARAM_TO_OCI = {
    "all_plugins_disabled": "are_all_plugins_disabled",
    "management_disabled": "is_management_disabled",
    "monitoring_disabled": "is_monitoring_disabled",
}

# Nested launch inputs shared by instance and instance-configuration modules.
COMPUTE_SHAPE_CONFIG_OPTIONS = dict(ocpus=dict(type="float"), memory_in_gbs=dict(type="float"))

COMPUTE_LAUNCH_ARGS = dict(
    shape_config=dict(type="dict", options=deepcopy(COMPUTE_SHAPE_CONFIG_OPTIONS)),
    image_id=dict(type="str"),
    boot_volume_id=dict(type="str"),
    boot_volume_size_in_gbs=dict(type="int"),
    boot_volume_vpus_per_gb=dict(type="int"),
    kms_key_id=dict(type="str"),
    subnet_id=dict(type="str"),
    assign_public_ip=dict(type="bool"),
    vnic_name=dict(type="str"),
    private_ip=dict(type="str"),
    private_ip_id=dict(type="str"),
    hostname_label=dict(type="str"),
    nsg_ids=dict(type="list", elements="str"),
    metadata=dict(type="dict"),
    extended_metadata=dict(type="dict"),
    security_attributes=dict(type="dict"),
    launch_options=dict(
        type="dict",
        options=dict(
            boot_volume_type=dict(
                type="str", choices=["ide", "iscsi", "paravirtualized", "scsi", "vfio"]
            ),
            firmware=dict(type="str", choices=["bios", "uefi_64"]),
            network_type=dict(
                type="str", choices=["acceleratedpv", "e1000", "paravirtualized", "vfio"]
            ),
            remote_data_volume_type=dict(
                type="str", choices=["ide", "iscsi", "paravirtualized", "scsi", "vfio"]
            ),
            is_pv_encryption_in_transit_enabled=dict(type="bool"),
            is_consistent_volume_naming_enabled=dict(type="bool"),
        ),
    ),
    instance_options=dict(
        type="dict", options=dict(are_legacy_imds_endpoints_disabled=dict(type="bool"))
    ),
    availability_config=dict(
        type="dict",
        options=dict(
            is_live_migration_preferred=dict(type="bool"),
            recovery_action=dict(type="str", choices=["restore_instance", "stop_instance"]),
        ),
    ),
    preemptible_instance_config=dict(
        type="dict", options=dict(preserve_boot_volume=dict(type="bool"))
    ),
    agent_config=dict(
        type="dict",
        options=dict(
            all_plugins_disabled=dict(type="bool"),
            management_disabled=dict(type="bool"),
            monitoring_disabled=dict(type="bool"),
            plugins_config=dict(
                type="list",
                elements="dict",
                options=dict(
                    name=dict(type="str"),
                    desired_state=dict(type="str", choices=["enabled", "disabled"]),
                ),
            ),
        ),
    ),
    platform_config=dict(
        type="dict",
        options=dict(
            type=dict(type="str"),
            is_secure_boot_enabled=dict(type="bool"),
            is_trusted_platform_module_enabled=dict(type="bool"),
            is_measured_boot_enabled=dict(type="bool"),
            is_memory_encryption_enabled=dict(type="bool"),
            is_symmetric_multi_threading_enabled=dict(type="bool"),
            numa_nodes_per_socket=dict(
                type="str", choices=["nps0", "nps1", "nps2", "nps4", "nps6"]
            ),
            is_access_control_service_enabled=dict(type="bool"),
            are_virtual_instructions_enabled=dict(type="bool"),
            is_input_output_memory_management_unit_enabled=dict(type="bool"),
            percentage_of_cores_enabled=dict(type="int"),
        ),
    ),
    capacity_reservation_id=dict(type="str"),
    dedicated_vm_host_id=dict(type="str"),
    cluster_placement_group_id=dict(type="str"),
    compute_cluster_id=dict(type="str"),
    instance_configuration_id=dict(type="str"),
    ipxe_script=dict(type="str"),
    is_pv_encryption_in_transit_enabled=dict(type="bool"),
    is_ai_enterprise_enabled=dict(type="bool"),
)

INSTANCE_CONFIGURATION_SOURCE_SCALAR_ARGS = {
    field: deepcopy(COMPUTE_LAUNCH_ARGS[field])
    for field in (
        "image_id",
        "boot_volume_id",
        "boot_volume_size_in_gbs",
        "boot_volume_vpus_per_gb",
        "kms_key_id",
    )
}

INSTANCE_CONFIGURATION_VNIC_ARGS = dict(
    **{
        key: deepcopy(COMPUTE_LAUNCH_ARGS[key])
        for key in ("assign_public_ip", "hostname_label", "nsg_ids", "private_ip", "subnet_id")
    },
    assign_private_dns_record=dict(type="bool"),
    defined_tags=dict(type="dict"),
    name=dict(type="str"),
    freeform_tags=dict(type="dict"),
    skip_source_dest_check=dict(type="bool"),
)

INSTANCE_CONFIGURATION_LAUNCH_ARGS = dict(
    availability_domain=dict(type="str"),
    capacity_reservation_id=dict(type="str"),
    compartment_id=dict(type="str"),
    create_vnic_details=dict(type="dict", options=INSTANCE_CONFIGURATION_VNIC_ARGS.copy()),
    defined_tags=dict(type="dict"),
    name=dict(type="str"),
    extended_metadata=dict(type="dict"),
    freeform_tags=dict(type="dict"),
    ipxe_script=dict(type="str"),
    metadata=dict(type="dict"),
    shape=dict(type="str"),
    shape_config=dict(
        type="dict",
        options=dict(
            **deepcopy(COMPUTE_SHAPE_CONFIG_OPTIONS),
            vcpus=dict(type="int"),
            baseline_ocpu_utilization=dict(
                type="str", choices=["baseline_1_8", "baseline_1_2", "baseline_1_1"]
            ),
            nvmes=dict(type="int"),
        ),
    ),
    platform_config=dict(
        type="dict",
        options={
            **deepcopy(COMPUTE_LAUNCH_ARGS["platform_config"]["options"]),
            "numa_nodes_per_socket": dict(type="str", choices=["nps0", "nps1", "nps2", "nps4"]),
            "type": dict(type="str", required=True),
        },
    ),
    source_details=dict(
        type="dict",
        options=dict(
            **deepcopy(INSTANCE_CONFIGURATION_SOURCE_SCALAR_ARGS),
            instance_source_image_filter_details=dict(
                type="dict",
                options=dict(
                    compartment_id=dict(type="str"),
                    defined_tags_filter=dict(type="dict"),
                    operating_system=dict(type="str"),
                    operating_system_version=dict(type="str"),
                ),
            ),
            source_type=dict(type="str", required=True, choices=["image", "boot_volume"]),
        ),
    ),
    fault_domain=dict(type="str"),
    dedicated_vm_host_id=dict(type="str"),
    launch_mode=dict(type="str", choices=["native", "emulated", "paravirtualized", "custom"]),
    launch_options=deepcopy(COMPUTE_LAUNCH_ARGS["launch_options"]),
    agent_config=deepcopy(COMPUTE_LAUNCH_ARGS["agent_config"]),
    is_pv_encryption_in_transit_enabled=dict(type="bool"),
    preferred_maintenance_action=dict(type="str", choices=["live_migrate", "reboot"]),
    instance_options=deepcopy(COMPUTE_LAUNCH_ARGS["instance_options"]),
    availability_config=deepcopy(COMPUTE_LAUNCH_ARGS["availability_config"]),
    preemptible_instance_config=dict(
        type="dict",
        options=dict(
            preemption_action=dict(
                type="dict",
                required=True,
                options=dict(
                    preserve_boot_volume=dict(type="bool"),
                ),
            )
        ),
    ),
)

# The configuration copy must require the fields declared by the SDK plugin model.
INSTANCE_CONFIGURATION_LAUNCH_ARGS["agent_config"]["options"]["plugins_config"]["options"]["name"][
    "required"
] = True
INSTANCE_CONFIGURATION_LAUNCH_ARGS["agent_config"]["options"]["plugins_config"]["options"][
    "desired_state"
]["required"] = True

INSTANCE_CONFIGURATION_BLOCK_VOLUME_ARGS = dict(
    attach_details=dict(
        type="dict",
        options=dict(
            use_chap=dict(type="bool"),
            name=dict(type="str"),
            is_read_only=dict(type="bool"),
            device=dict(type="str"),
            is_shareable=dict(type="bool"),
            type=dict(type="str", required=True, choices=["iscsi", "paravirtualized"]),
            is_pv_encryption_in_transit_enabled=dict(type="bool"),
        ),
    ),
    create_details=dict(
        type="dict",
        options=dict(
            availability_domain=dict(type="str"),
            backup_policy_id=dict(type="str"),
            compartment_id=dict(type="str"),
            is_auto_tune_enabled=dict(type="bool"),
            block_volume_replicas=dict(
                type="list",
                elements="dict",
                options=dict(
                    name=dict(type="str"),
                    availability_domain=dict(type="str", required=True),
                ),
            ),
            defined_tags=dict(type="dict"),
            name=dict(type="str"),
            freeform_tags=dict(type="dict"),
            kms_key_id=dict(type="str"),
            vpus_per_gb=dict(type="int"),
            size_in_gbs=dict(type="int"),
            source_details=dict(
                type="dict",
                options=dict(
                    type=dict(type="str", required=True, choices=["volume_backup", "volume"]),
                    id=dict(type="str"),
                ),
            ),
            autotune_policies=dict(
                type="list",
                elements="dict",
                options=dict(
                    max_vpus_per_gb=dict(type="int"),
                    autotune_type=dict(
                        type="str", required=True, choices=["performance_based", "detached_volume"]
                    ),
                ),
            ),
        ),
    ),
    volume_id=dict(type="str"),
)

INSTANCE_CONFIGURATION_SECONDARY_VNIC_ARGS = dict(
    create_vnic_details=dict(type="dict", options=INSTANCE_CONFIGURATION_VNIC_ARGS.copy()),
    name=dict(type="str"),
    nic_index=dict(type="int"),
)


def build_create_vnic_details(params):
    """Build create vnic details.

    Args:
        params: Module parameters.

    Returns:
        The SDK model, or None when the input is omitted.
    """
    details = filter_none_values(
        {
            "subnet_id": params.get("subnet_id"),
            "assign_public_ip": params.get("assign_public_ip"),
            "display_name": params.get("vnic_name"),
            "private_ip": params.get("private_ip"),
            "private_ip_id": params.get("private_ip_id"),
            "hostname_label": params.get("hostname_label"),
            "nsg_ids": params.get("nsg_ids"),
        }
    )
    if not details:
        return None
    return oci.core.models.CreateVnicDetails(**details)


def build_source_details(params):
    """Build source details.

    Args:
        params: Module parameters.

    Returns:
        The SDK model, or None when the input is omitted.
    """
    image_id = params.get("image_id")
    boot_volume_id = params.get("boot_volume_id")
    if image_id:
        details = filter_none_values(
            {
                "image_id": image_id,
                "boot_volume_size_in_gbs": params.get("boot_volume_size_in_gbs"),
                "boot_volume_vpus_per_gb": params.get("boot_volume_vpus_per_gb"),
                "kms_key_id": params.get("kms_key_id"),
            }
        )
        return oci.core.models.InstanceSourceViaImageDetails(**details)
    if boot_volume_id:
        return oci.core.models.InstanceSourceViaBootVolumeDetails(boot_volume_id=boot_volume_id)
    return None


def build_preemptible_instance_config(params):
    """Build preemptible instance config.

    Args:
        params: Module parameters.

    Returns:
        The SDK model, or None when the input is omitted.
    """
    preemptible_instance_config = params.get("preemptible_instance_config")
    if not preemptible_instance_config:
        return None
    preemption_action = oci.core.models.TerminatePreemptionAction(
        **filter_none_values(
            {"preserve_boot_volume": preemptible_instance_config.get("preserve_boot_volume")}
        )
    )
    return oci.core.models.PreemptibleInstanceConfigDetails(preemption_action=preemption_action)


def build_agent_config(params, model_class):
    """Build agent config.

    Args:
        params: Module parameters.
        model_class: The SDK model class.

    Returns:
        The SDK model, or None when the input is omitted.
    """
    agent_config = params.get("agent_config")
    if not agent_config:
        return None
    agent_config = rename_aliased_fields(agent_config, AGENT_CONFIG_PARAM_TO_OCI)
    plugins_config = agent_config.get("plugins_config")
    plugins = None
    if plugins_config:
        plugins = [
            build_model(
                plugin_config,
                oci.core.models.InstanceAgentPluginConfigDetails,
                enum_keys=ENUM_KEYS,
            )
            for plugin_config in plugins_config
        ]
    details = filter_none_values(
        {
            "are_all_plugins_disabled": agent_config.get("are_all_plugins_disabled"),
            "is_management_disabled": agent_config.get("is_management_disabled"),
            "is_monitoring_disabled": agent_config.get("is_monitoring_disabled"),
            "plugins_config": plugins,
        }
    )
    return model_class(**details)


def build_platform_config(params, class_suffix):
    """Build platform config.

    Args:
        params: Module parameters.
        class_suffix: The SDK model class suffix.

    Returns:
        The SDK model, or None when the input is omitted.
    """
    platform_config = params.get("platform_config")
    if not platform_config:
        return None
    normalized = normalize_enum_values(dict(platform_config), ENUM_KEYS)
    platform_type = normalized.pop("type", None)
    # OCI's SDK codegen names each polymorphic subtype's class after its
    # "type" discriminator converted to PascalCase, e.g. "AMD_MILAN_BM" ->
    # "AmdMilanBm". Deriving it avoids hand-maintaining a type->class map
    # that would otherwise need a manual update every time OCI adds a new
    # shape family.
    class_prefix = "".join(word.capitalize() for word in (platform_type or "").split("_"))
    model_class = getattr(oci.core.models, f"{class_prefix}{class_suffix}", None)
    if model_class is None:
        is_known_type = any(name.startswith(class_prefix) for name in dir(oci.core.models))
        if not is_known_type:
            raise ValueError(f"Unsupported platform_config type: {platform_config.get('type')}")
        raise ValueError(
            f"platform_config type {platform_config.get('type')} does not support this operation"
        )
    details = filter_none_values(normalized)
    details["type"] = platform_type
    return model_class(**details)


def build_create_instance_details(params):
    """Build create instance details.

    Args:
        params: Module parameters.

    Returns:
        The SDK model, or None when the input is omitted.
    """
    details = filter_none_values(
        {
            "availability_domain": params.get("availability_domain"),
            "compartment_id": params.get("compartment_id"),
            "display_name": params.get("name"),
            "shape": params.get("shape"),
            "shape_config": build_model(
                params.get("shape_config"),
                oci.core.models.LaunchInstanceShapeConfigDetails,
            ),
            "source_details": build_source_details(params),
            "create_vnic_details": build_create_vnic_details(params),
            "metadata": params.get("metadata"),
            "extended_metadata": params.get("extended_metadata"),
            "security_attributes": params.get("security_attributes"),
            "launch_options": build_model(
                params.get("launch_options") or None,
                oci.core.models.LaunchOptions,
                enum_keys=ENUM_KEYS,
            ),
            "instance_options": build_model(
                params.get("instance_options"), oci.core.models.InstanceOptions
            ),
            "availability_config": build_model(
                params.get("availability_config") or None,
                oci.core.models.LaunchInstanceAvailabilityConfigDetails,
                enum_keys=ENUM_KEYS,
            ),
            "preemptible_instance_config": build_preemptible_instance_config(params),
            "agent_config": build_agent_config(
                params, oci.core.models.LaunchInstanceAgentConfigDetails
            ),
            "platform_config": build_platform_config(params, "LaunchInstancePlatformConfig"),
            "fault_domain": params.get("fault_domain"),
            "capacity_reservation_id": params.get("capacity_reservation_id"),
            "dedicated_vm_host_id": params.get("dedicated_vm_host_id"),
            "cluster_placement_group_id": params.get("cluster_placement_group_id"),
            "compute_cluster_id": params.get("compute_cluster_id"),
            "instance_configuration_id": params.get("instance_configuration_id"),
            "ipxe_script": params.get("ipxe_script"),
            "is_pv_encryption_in_transit_enabled": params.get(
                "is_pv_encryption_in_transit_enabled"
            ),
            "is_ai_enterprise_enabled": params.get("is_ai_enterprise_enabled"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.core.models.LaunchInstanceDetails(**details)


def build_instance_configuration_details(fields):
    """Build a typed Compute instance-configuration details model.

    Args:
        fields: The ``instance_details`` mapping from the module input.

    Returns:
        A ComputeInstanceDetails or ComputeInstanceOptions model.
    """
    instance_type = (fields or {}).get("instance_type", "compute")
    model_name = {
        "compute": "ComputeInstanceDetails",
        "instance_options": "ComputeInstanceOptions",
    }.get(instance_type)
    if model_name is None:
        raise ValueError(f"Unsupported instance_details instance_type: {instance_type}")
    return _build_configuration_model(model_name, fields)
