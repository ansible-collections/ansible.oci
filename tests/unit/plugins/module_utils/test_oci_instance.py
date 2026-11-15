from __future__ import absolute_import, division, print_function

__metaclass__ = type

from copy import deepcopy

import pytest
import oci
import oci.core

from .conftest import load_collection_module


CONFIGURATION_LAUNCH_FIELDS = {
    "cluster_placement_group_id": "PlacementID",
    "compute_cluster_id": "ClusterID",
    "is_ai_enterprise_enabled": False,
    "security_attributes": {"Namespace": {"Key": "KeepCase"}},
    "licensing_configs": [
        {"type": "windows", "license_type": "bring_your_own_license"}
    ],
    "placement_constraint_details": {
        "type": "host_group",
        "compute_host_group_id": "HostID",
    },
}


def test_configuration_models_preserve_nested_values(monkeypatch):
    """Build concrete model types and preserve case-sensitive user data."""
    compute = load_collection_module("oci_instance", plugin_dir="module_utils")
    monkeypatch.setattr(compute, "oci", oci)
    details = compute.build_instance_configuration_details(
        {
            "launch_details": {
                **CONFIGURATION_LAUNCH_FIELDS,
                "metadata": {"type": "KeepCase", "firmware": "KeepThisToo"},
                "platform_config": {"type": "amd_vm"},
                "source_details": {
                    "source_type": "boot_volume",
                    "boot_volume_id": "BootID",
                },
                "agent_config": {
                    "monitoring_disabled": True,
                    "plugins_config": [
                        {"name": "PluginName", "desired_state": "enabled"}
                    ],
                },
                "preemptible_instance_config": {
                    "preemption_action": {
                        "type": "terminate",
                        "preserve_boot_volume": True,
                    },
                },
            },
            "block_volumes": [
                {
                    "create_details": {
                        "source_details": {"type": "volume_backup", "id": "BackupID"},
                        "autotune_policies": [
                            {
                                "autotune_type": "performance_based",
                                "max_vpus_per_gb": 20,
                            }
                        ],
                    },
                }
            ],
        }
    )
    launch = details.launch_details
    assert isinstance(details, oci.core.models.ComputeInstanceDetails)
    assert isinstance(
        launch.platform_config,
        oci.core.models.InstanceConfigurationAmdVmLaunchInstancePlatformConfig,
    )
    assert launch.cluster_placement_group_id == "PlacementID"
    assert launch.compute_cluster_id == "ClusterID"
    assert launch.is_ai_enterprise_enabled is False
    assert launch.security_attributes == {"Namespace": {"Key": "KeepCase"}}
    assert isinstance(
        launch.licensing_configs[0],
        oci.core.models.LaunchInstanceWindowsLicensingConfig,
    )
    assert launch.licensing_configs[0].type == "WINDOWS"
    assert launch.licensing_configs[0].license_type == "BRING_YOUR_OWN_LICENSE"
    assert isinstance(
        launch.placement_constraint_details,
        oci.core.models.InstanceConfigurationHostGroupPlacementConstraintDetails,
    )
    assert launch.placement_constraint_details.type == "HOST_GROUP"
    assert launch.placement_constraint_details.compute_host_group_id == "HostID"
    assert launch.metadata == {"type": "KeepCase", "firmware": "KeepThisToo"}
    assert launch.source_details.boot_volume_id == "BootID"
    assert launch.source_details.source_type == "bootVolume"
    assert launch.agent_config.is_monitoring_disabled is True
    assert launch.agent_config.plugins_config[0].name == "PluginName"
    assert launch.agent_config.plugins_config[0].desired_state == "ENABLED"
    assert isinstance(
        launch.preemptible_instance_config.preemption_action,
        oci.core.models.TerminatePreemptionAction,
    )
    assert launch.preemptible_instance_config.preemption_action.preserve_boot_volume is True
    volume = details.block_volumes[0].create_details
    assert volume.source_details.type == "volumeBackup"
    assert volume.source_details.id == "BackupID"
    assert isinstance(
        volume.autotune_policies[0],
        oci.core.models.InstanceConfigurationPerformanceBasedAutotunePolicy,
    )
    assert volume.autotune_policies[0].max_vpus_per_gb == 20


def test_configuration_options_build_concrete_compute_entries(monkeypatch):
    """Keep every option as a typed Compute template."""
    compute = load_collection_module("oci_instance", plugin_dir="module_utils")
    monkeypatch.setattr(compute, "oci", oci)
    details = compute.build_instance_configuration_details(
        {
            "instance_type": "instance_options",
            "options": [
                {
                    "instance_type": "compute",
                    "launch_details": {
                        "shape": "VM.Standard.E4.Flex",
                        **CONFIGURATION_LAUNCH_FIELDS,
                    },
                }
            ],
        }
    )
    assert isinstance(details, oci.core.models.ComputeInstanceOptions)
    assert isinstance(details.options[0], oci.core.models.ComputeInstanceDetails)
    assert isinstance(
        details.options[0].launch_details,
        oci.core.models.InstanceConfigurationLaunchInstanceDetails,
    )
    assert details.options[0].launch_details.shape == "VM.Standard.E4.Flex"
    from ansible.module_utils.common.arg_spec import ArgumentSpecValidator

    launch_fields = deepcopy(CONFIGURATION_LAUNCH_FIELDS)
    result = ArgumentSpecValidator(compute.INSTANCE_CONFIGURATION_LAUNCH_ARGS).validate(
        launch_fields
    )
    assert not result.error_messages
    launch = details.options[0].launch_details
    assert launch.compute_cluster_id == "ClusterID"
    assert launch.cluster_placement_group_id == "PlacementID"
    assert launch.is_ai_enterprise_enabled is False
    assert launch.security_attributes == launch_fields["security_attributes"]
    assert launch.licensing_configs[0].license_type == "BRING_YOUR_OWN_LICENSE"
    assert launch.placement_constraint_details.compute_host_group_id == "HostID"


def test_configuration_name_maps_only_declared_sdk_model_fields():
    """Map nested name inputs to SDK fields and preserve arbitrary dictionaries."""
    compute = load_collection_module("oci_instance", plugin_dir="module_utils")
    mappings = {
        "InstanceConfigurationLaunchInstanceDetails": "display_name",
        "InstanceConfigurationCreateVnicDetails": "display_name",
        "InstanceConfigurationAttachVnicDetails": "display_name",
        "InstanceConfigurationAttachVolumeDetails": "display_name",
        "InstanceConfigurationIscsiAttachVolumeDetails": "display_name",
        "InstanceConfigurationParavirtualizedAttachVolumeDetails": "display_name",
        "InstanceConfigurationCreateVolumeDetails": "display_name",
        "InstanceConfigurationBlockVolumeReplicaDetails": "display_name",
    }

    for model_name, sdk_field in mappings.items():
        assert compute._configuration_model_fields(model_name, {"name": "MixedCase"}) == {
            sdk_field: "MixedCase"
        }

    assert compute._configuration_model_fields(
        "InstanceAgentPluginConfigDetails", {"name": "Plugin"}
    ) == {"name": "Plugin"}
    assert compute._configuration_model_fields(
        "InstanceConfigurationLaunchInstanceDetails", {"metadata": {"name": "KeepName"}}
    ) == {"metadata": {"name": "KeepName"}}


def test_configuration_launch_schema_accepts_new_platform_types():
    """Keep platform types open and keep the type field required."""
    compute = load_collection_module("oci_instance", plugin_dir="module_utils")
    type_spec = compute.INSTANCE_CONFIGURATION_LAUNCH_ARGS["platform_config"]["options"]["type"]
    assert type_spec == {"type": "str", "required": True}

    details = compute.build_instance_configuration_details(
        {"launch_details": {"platform_config": {"type": "generic_bm"}}}
    )
    assert isinstance(
        details.launch_details.platform_config,
        oci.core.models.InstanceConfigurationGenericBmLaunchInstancePlatformConfig,
    )


def test_platform_config_builds_a_future_sdk_model(monkeypatch):
    """Derive platform model names from SDK types without an allowlist."""
    compute = load_collection_module("oci_instance", plugin_dir="module_utils")

    class FuturePlatformConfig:
        swagger_types = {"type": "str"}

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            if isinstance(getattr(self, "type", None), str):
                self.type = self.type.upper()

    monkeypatch.setattr(
        oci.core.models,
        "InstanceConfigurationFuturePlatformLaunchInstancePlatformConfig",
        FuturePlatformConfig,
        raising=False,
    )
    monkeypatch.setattr(compute, "oci", oci)
    details = compute.build_instance_configuration_details(
        {"launch_details": {"platform_config": {"type": "future_platform"}}}
    )
    assert isinstance(details.launch_details.platform_config, FuturePlatformConfig)
    assert details.launch_details.platform_config.type == "FUTURE_PLATFORM"


def test_preemptible_config_uses_terminate_without_input_discriminator(monkeypatch):
    """Build terminate actions when users provide only boot volume preservation."""
    compute = load_collection_module("oci_instance", plugin_dir="module_utils")
    monkeypatch.setattr(compute, "oci", oci)

    options = compute.INSTANCE_CONFIGURATION_LAUNCH_ARGS["preemptible_instance_config"]["options"][
        "preemption_action"
    ]["options"]
    assert "type" not in options
    for preserve_boot_volume in (True, False):
        details = compute.build_instance_configuration_details(
            {
                "launch_details": {
                    "preemptible_instance_config": {
                        "preemption_action": {"preserve_boot_volume": preserve_boot_volume}
                    }
                }
            }
        )
        action = details.launch_details.preemptible_instance_config.preemption_action
        assert isinstance(action, oci.core.models.TerminatePreemptionAction)
        assert action.type == "TERMINATE"
        assert action.preserve_boot_volume is preserve_boot_volume


def test_configuration_generic_bm_accepts_nps6():
    """Accept NPS6 through argument validation and SDK conversion."""
    from ansible.module_utils.common.arg_spec import ArgumentSpecValidator

    compute = load_collection_module("oci_instance", plugin_dir="module_utils")
    fields = {"platform_config": {"type": "generic_bm", "numa_nodes_per_socket": "nps6"}}
    result = ArgumentSpecValidator(compute.INSTANCE_CONFIGURATION_LAUNCH_ARGS).validate(fields)
    assert not result.error_messages
    details = compute.build_instance_configuration_details({"launch_details": fields})
    assert details.launch_details.platform_config.numa_nodes_per_socket == "NPS6"


def test_configuration_conversion_preserves_original_template():
    """Preserve inputs through repeated recursive conversions."""
    compute = load_collection_module("oci_instance", plugin_dir="module_utils")
    fields = {
        "launch_details": {
            "name": "TemplateName",
            "source_details": {"source_type": "boot_volume", "boot_volume_id": "BootID"},
            "agent_config": {
                "monitoring_disabled": False,
                "plugins_config": [{"name": "PluginName", "desired_state": "enabled"}],
            },
            "metadata": {"type": "KeepCase", "name": "KeepName"},
            "defined_tags": {"Namespace": {"Key": "MixedCase"}},
        },
        "block_volumes": [
            {"create_details": {"source_details": {"type": "volume_backup", "id": "BackupID"}}}
        ],
    }
    original = deepcopy(fields)
    first = compute.build_instance_configuration_details(fields)
    second = compute.build_instance_configuration_details(fields)
    assert fields == original
    assert oci.util.to_dict(first) == oci.util.to_dict(second)
    assert first.launch_details.source_details.source_type == "bootVolume"
    assert first.launch_details.agent_config.plugins_config[0].desired_state == "ENABLED"


@pytest.mark.parametrize(
    "fields, unsupported",
    [
        ({"instance_type": "compute", "options": []}, "options"),
        ({"instance_type": "instance_options", "launch_details": {}}, "launch_details"),
        (
            {
                "launch_details": {
                    "source_details": {"source_type": "image", "boot_volume_id": "BootID"}
                }
            },
            "boot_volume_id",
        ),
        (
            {
                "launch_details": {
                    "platform_config": {"type": "intel_vm", "percentage_of_cores_enabled": 0}
                }
            },
            "percentage_of_cores_enabled",
        ),
        (
            {
                "launch_details": {
                    "platform_config": {
                        "type": "intel_vm",
                        "are_virtual_instructions_enabled": False,
                    }
                }
            },
            "are_virtual_instructions_enabled",
        ),
        (
            {
                "instance_type": "instance_options",
                "options": [{"instance_type": "compute", "options": []}],
            },
            "options",
        ),
    ],
)
def test_configuration_rejects_fields_outside_selected_model(fields, unsupported):
    """Reject supplied fields that the selected SDK model cannot retain."""
    compute = load_collection_module("oci_instance", plugin_dir="module_utils")
    original = deepcopy(fields)
    with pytest.raises(ValueError, match=unsupported):
        compute.build_instance_configuration_details(fields)
    assert fields == original


def test_configuration_ignores_omitted_fields_and_preserves_false_and_zero():
    """Ignore None placeholders and retain supported false and zero values."""
    compute = load_collection_module("oci_instance", plugin_dir="module_utils")
    details = compute.build_instance_configuration_details(
        {
            "instance_type": "compute",
            "options": None,
            "launch_details": {
                "platform_config": {
                    "type": "generic_bm",
                    "percentage_of_cores_enabled": 0,
                    "are_virtual_instructions_enabled": False,
                }
            },
        }
    )
    assert details.launch_details.platform_config.percentage_of_cores_enabled == 0
    assert details.launch_details.platform_config.are_virtual_instructions_enabled is False


@pytest.mark.parametrize(
    "assign_ipv6_ip,pairs",
    [
        (None, None),
        (False, []),
        (True, [{"ipv6_subnet_cidr": "2001:db8::/64", "ipv6_address": None}]),
    ],
)
def test_primary_vnic_network_inputs(assign_ipv6_ip, pairs):
    """Preserve omission, false values, and typed IPv6 inputs."""
    compute = load_collection_module("oci_instance")
    params = dict(
        assign_ipv6_ip=assign_ipv6_ip,
        ipv6_address_ipv6_subnet_cidr_pair_details=pairs,
        subnet_cidr="10.0.1.0/24",
    )
    original = deepcopy(params)
    details = compute.build_create_vnic_details(params)
    assert details.subnet_cidr == params["subnet_cidr"]
    assert details.assign_ipv6_ip is assign_ipv6_ip
    assert params == original
    actual = details.ipv6_address_ipv6_subnet_cidr_pair_details
    if pairs:
        assert isinstance(actual[0], oci.core.models.Ipv6AddressIpv6SubnetCidrPairDetails)
        assert actual[0].ipv6_subnet_cidr == "2001:db8::/64"
        assert actual[0].ipv6_address is None
    else:
        assert actual == pairs


@pytest.mark.parametrize("variant", ["compute", "instance_options"])
def test_configuration_network_and_local_storage(variant):
    """Build the new inputs in both template forms and both VNIC locations."""
    from ansible.module_utils.common.arg_spec import ArgumentSpecValidator

    compute = load_collection_module("oci_instance")
    vnic = dict(
        assign_ipv6_ip=False,
        subnet_cidr="10.0.1.0/24",
        ipv6_address_ipv6_subnet_cidr_pair_details=[{"ipv6_id": "IPv6ID"}],
    )
    launch = dict(create_vnic_details=vnic, shape_config={"local_volume_size_in_gbs": 100})
    assert (
        not ArgumentSpecValidator(compute.INSTANCE_CONFIGURATION_LAUNCH_ARGS)
        .validate(launch)
        .error_messages
    )
    entry = dict(
        instance_type="compute",
        launch_details=launch,
        secondary_vnics=[{"create_vnic_details": deepcopy(vnic)}],
    )
    fields = entry if variant == "compute" else dict(instance_type=variant, options=[entry])
    original = deepcopy(fields)
    first = compute.build_instance_configuration_details(fields)
    second = compute.build_instance_configuration_details(fields)
    assert oci.util.to_dict(first) == oci.util.to_dict(second)
    assert fields == original
    module_obj = load_collection_module("oci_instance_configuration", plugin_dir="modules")
    adapter = object.__new__(module_obj.OciInstanceConfigurationModule)
    assert not adapter.compare_update_field_values(oci.util.to_dict(first), fields, "subset_dict")
    resource = first if variant == "compute" else first.options[0]
    assert resource.launch_details.shape_config.local_volume_size_in_gbs == 100
    for model in (
        resource.launch_details.create_vnic_details,
        resource.secondary_vnics[0].create_vnic_details,
    ):
        assert model.assign_ipv6_ip is False
        assert model.subnet_cidr == "10.0.1.0/24"
        pair = model.ipv6_address_ipv6_subnet_cidr_pair_details[0]
        assert isinstance(
            pair, oci.core.models.InstanceConfigurationIpv6AddressIpv6SubnetCidrPairDetails
        )
        assert pair.ipv6_id == "IPv6ID"


def test_shared_vnic_schemas_are_independent():
    """Keep module-specific argument changes out of other VNIC schemas."""
    from ansible_collections.ansible.oci.plugins.module_utils.oci_network import VNIC_ARGS

    compute = load_collection_module("oci_instance")
    key = "ipv6_address_ipv6_subnet_cidr_pair_details"
    direct = compute.COMPUTE_LAUNCH_ARGS[key]
    template = compute.INSTANCE_CONFIGURATION_VNIC_ARGS[key]
    assert direct == template == VNIC_ARGS[key]
    assert direct is not template
    assert direct["options"] is not template["options"]
    assert template["options"] is not VNIC_ARGS[key]["options"]
