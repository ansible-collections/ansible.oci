from __future__ import absolute_import, division, print_function

__metaclass__ = type

import oci
import oci.core

from .conftest import load_collection_module


def test_configuration_models_preserve_nested_values(monkeypatch):
    """Build concrete model types and preserve case-sensitive user data."""
    compute = load_collection_module("oci_instance", plugin_dir="module_utils")
    monkeypatch.setattr(compute, "oci", oci)
    details = compute.build_instance_configuration_details(
        {
            "launch_details": {
                "metadata": {"type": "KeepCase", "firmware": "KeepThisToo"},
                "platform_config": {"type": "amd_vm"},
                "source_details": {"source_type": "boot_volume", "boot_volume_id": "BootID"},
                "agent_config": {
                    "monitoring_disabled": True,
                    "plugins_config": [{"name": "PluginName", "desired_state": "enabled"}],
                },
                "preemptible_instance_config": {
                    "preemption_action": {"type": "terminate", "preserve_boot_volume": True},
                },
            },
            "block_volumes": [
                {
                    "create_details": {
                        "source_details": {"type": "volume_backup", "id": "BackupID"},
                        "autotune_policies": [
                            {"autotune_type": "performance_based", "max_vpus_per_gb": 20}
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
                {"instance_type": "compute", "launch_details": {"shape": "VM.Standard.E4.Flex"}}
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
