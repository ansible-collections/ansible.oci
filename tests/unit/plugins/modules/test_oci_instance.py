from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from conftest import (
    DummyModule,
    FakeModel,
    FakeResponse,
    FailJsonCalled,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)


INSTANCE_MODEL_NAMES = (
    "LaunchInstanceDetails",
    "UpdateInstanceDetails",
    "CreateVnicDetails",
    "InstanceSourceViaImageDetails",
    "InstanceSourceViaBootVolumeDetails",
    "LaunchInstanceShapeConfigDetails",
    "UpdateInstanceShapeConfigDetails",
    "LaunchOptions",
    "InstanceOptions",
    "LaunchInstanceAvailabilityConfigDetails",
    "UpdateInstanceAvailabilityConfigDetails",
    "PreemptibleInstanceConfigDetails",
    "TerminatePreemptionAction",
    "LaunchInstanceAgentConfigDetails",
    "UpdateInstanceAgentConfigDetails",
    "InstanceAgentPluginConfigDetails",
    "AmdVmLaunchInstancePlatformConfig",
    "AmdMilanBmLaunchInstancePlatformConfig",
)


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(
        monkeypatch,
        model_names=INSTANCE_MODEL_NAMES,
    )


def make_instance_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciInstanceModule",
        params,
        client=client,
    )


def test_main_exposes_power_state_argument(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_instance")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        return DummyModule({})

    class FakeInstanceModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciInstanceModule", FakeInstanceModule)

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["argument_spec"]["power_state"] == {
        "type": "str",
        "choices": ["running", "stopped"],
    }
    assert captured["argument_spec"]["shape_config"]["type"] == "dict"
    assert "display_name" not in captured["argument_spec"]
    assert captured["argument_spec"]["boot_volume_id"] == {"type": "str"}
    assert (
        captured["argument_spec"]["availability_config"]["options"]["recovery_action"][
            "choices"
        ]
        == ["restore_instance", "stop_instance"]
    )


def test_build_create_instance_details_includes_supported_fields(monkeypatch):
    install_fake_oci(monkeypatch)

    instance_module = load_collection_module("oci_instance")
    details = instance_module.build_create_instance_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "availability_domain": "Uocm:PHX-AD-1",
            "name": "example-instance",
            "shape": "VM.Standard.E4.Flex",
            "shape_config": {"ocpus": 1.0, "memory_in_gbs": 16.0},
            "image_id": "ocid1.image.oc1..example",
            "subnet_id": "ocid1.subnet.oc1..example",
            "assign_public_ip": True,
            "metadata": {"ssh_authorized_keys": "ssh-rsa AAAA"},
            "freeform_tags": {"env": "dev"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        }
    )

    assert isinstance(details, FakeModel)
    assert details.compartment_id == "ocid1.compartment.oc1..example"
    assert details.availability_domain == "Uocm:PHX-AD-1"
    assert details.display_name == "example-instance"
    assert details.shape == "VM.Standard.E4.Flex"
    assert isinstance(details.shape_config, FakeModel)
    assert details.shape_config.ocpus == 1.0
    assert details.shape_config.memory_in_gbs == 16.0
    assert isinstance(details.source_details, FakeModel)
    assert details.source_details.image_id == "ocid1.image.oc1..example"
    assert isinstance(details.create_vnic_details, FakeModel)
    assert details.create_vnic_details.subnet_id == "ocid1.subnet.oc1..example"
    assert details.create_vnic_details.assign_public_ip is True
    assert details.metadata == {"ssh_authorized_keys": "ssh-rsa AAAA"}
    assert details.freeform_tags == {"env": "dev"}
    assert details.defined_tags == {"Operations": {"CostCenter": "42"}}


def test_build_update_plan_maps_name_and_shape_fields(monkeypatch):
    install_fake_oci(monkeypatch)

    instance_module = load_collection_module("oci_instance")
    instance = make_instance_module(
        instance_module,
        {
            "name": "updated-instance",
            "shape": "VM.Standard.E4.Flex",
        },
    )
    resource = FakeModel(
        id="ocid1.instance.oc1..example",
        display_name="current-instance",
        shape="VM.Standard.E3.Flex",
        lifecycle_state="STOPPED",
    )

    update_plan = instance.build_update_plan(resource)

    assert update_plan["update_needed"] is True
    assert update_plan["update_model_fields"] == {
        "display_name": "updated-instance",
        "shape": "VM.Standard.E4.Flex",
    }


def test_needs_update_ignores_shape_config_extra_fields(monkeypatch):
    install_fake_oci(monkeypatch)

    instance_module = load_collection_module("oci_instance")
    instance = make_instance_module(
        instance_module,
        {"shape_config": {"ocpus": 1.0, "memory_in_gbs": 16.0}},
    )
    resource = FakeModel(
        id="ocid1.instance.oc1..example",
        shape_config={
            "ocpus": 1.0,
            "memory_in_gbs": 16.0,
            "networking_bandwidth_in_gbps": 1.0,
            "max_vnic_attachments": 2,
        },
        lifecycle_state="RUNNING",
    )

    assert instance.needs_update(resource) is False


def test_needs_update_returns_true_for_shape_config_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    instance_module = load_collection_module("oci_instance")
    instance = make_instance_module(
        instance_module,
        {"shape_config": {"ocpus": 2.0, "memory_in_gbs": 32.0}},
    )
    resource = FakeModel(
        id="ocid1.instance.oc1..example",
        shape_config={"ocpus": 1.0, "memory_in_gbs": 16.0},
        lifecycle_state="STOPPED",
    )

    assert instance.needs_update(resource) is True


def test_needs_update_rejects_availability_domain_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    instance_module = load_collection_module("oci_instance")
    instance = make_instance_module(
        instance_module,
        {"availability_domain": "Uocm:PHX-AD-2"},
    )
    resource = FakeModel(
        id="ocid1.instance.oc1..example",
        availability_domain="Uocm:PHX-AD-1",
        lifecycle_state="RUNNING",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "availability_domain" in exc_info.value.payload["msg"]


def test_needs_update_rejects_image_id_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    instance_module = load_collection_module("oci_instance")
    instance = make_instance_module(
        instance_module,
        {"image_id": "ocid1.image.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.instance.oc1..example",
        image_id="ocid1.image.oc1..current",
        lifecycle_state="RUNNING",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "image_id" in exc_info.value.payload["msg"]


def test_plan_power_state_strategy_returns_start_action(monkeypatch):
    install_fake_oci(monkeypatch)

    instance_module = load_collection_module("oci_instance")
    instance = make_instance_module(
        instance_module,
        {"power_state": "running"},
    )
    resource = FakeModel(id="ocid1.instance.oc1..example", lifecycle_state="STOPPED")

    update_plan = instance.build_update_plan(resource)

    assert update_plan["update_needed"] is True
    assert update_plan["strategy_operations"] == [
        {"param_name": "power_state", "operations": ["START"]}
    ]


def test_plan_power_state_strategy_noop_when_already_matching(monkeypatch):
    install_fake_oci(monkeypatch)

    instance_module = load_collection_module("oci_instance")
    instance = make_instance_module(
        instance_module,
        {"power_state": "running"},
    )
    resource = FakeModel(id="ocid1.instance.oc1..example", lifecycle_state="RUNNING")

    update_plan = instance.build_update_plan(resource)

    assert update_plan["strategy_operations"] == []


def test_create_resource_launches_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    instance_module = load_collection_module("oci_instance")
    launch_calls = []
    response = FakeResponse(data=FakeModel(id="ocid1.instance.oc1..example"))

    def launch_instance(launch_instance_details):
        launch_calls.append(launch_instance_details)
        return response

    instance = make_instance_module(
        instance_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "availability_domain": "Uocm:PHX-AD-1",
            "name": "example-instance",
            "shape": "VM.Standard.E4.Flex",
            "image_id": "ocid1.image.oc1..example",
            "subnet_id": "ocid1.subnet.oc1..example",
            "wait": True,
        },
        client=types.SimpleNamespace(launch_instance=launch_instance),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: FakeModel(
            id=resource_id,
            lifecycle_state="RUNNING",
        ),
    )

    resource = instance.create_resource()

    assert launch_calls[0].display_name == "example-instance"
    assert resource.id == "ocid1.instance.oc1..example"
    assert resource.lifecycle_state == "RUNNING"


def test_create_resource_stops_instance_when_power_state_stopped(monkeypatch):
    install_fake_oci(monkeypatch)

    instance_module = load_collection_module("oci_instance")
    response = FakeResponse(data=FakeModel(id="ocid1.instance.oc1..example"))
    action_calls = []

    def instance_action(instance_id, action, **kwargs):
        action_calls.append((instance_id, action))

    instance = make_instance_module(
        instance_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "availability_domain": "Uocm:PHX-AD-1",
            "name": "example-instance",
            "shape": "VM.Standard.E4.Flex",
            "image_id": "ocid1.image.oc1..example",
            "subnet_id": "ocid1.subnet.oc1..example",
            "power_state": "stopped",
            "wait": True,
        },
        client=types.SimpleNamespace(
            launch_instance=lambda launch_instance_details: response,
            instance_action=instance_action,
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    wait_calls = []

    def fake_wait_for_resource_id(resource_id, target_states, **kwargs):
        wait_calls.append(target_states)
        state = "RUNNING" if len(wait_calls) == 1 else "STOPPED"
        return FakeModel(id=resource_id, lifecycle_state=state)

    monkeypatch.setattr(instance, "wait_for_resource_id", fake_wait_for_resource_id)

    resource = instance.create_resource()

    assert action_calls == [("ocid1.instance.oc1..example", "STOP")]
    assert resource.lifecycle_state == "STOPPED"


def test_update_resource_applies_power_action_then_field_update(monkeypatch):
    install_fake_oci(monkeypatch)

    instance_module = load_collection_module("oci_instance")
    action_calls = []
    update_calls = []
    update_response = FakeResponse(data=FakeModel(id="ocid1.instance.oc1..example"))

    def instance_action(instance_id, action, **kwargs):
        action_calls.append((instance_id, action))

    def update_instance(instance_id, update_instance_details):
        update_calls.append((instance_id, update_instance_details))
        return update_response

    resource = FakeModel(
        id="ocid1.instance.oc1..example",
        display_name="current-instance",
        lifecycle_state="RUNNING",
    )
    instance = make_instance_module(
        instance_module,
        {
            "name": "updated-instance",
            "power_state": "stopped",
            "wait": True,
        },
        client=types.SimpleNamespace(
            instance_action=instance_action,
            update_instance=update_instance,
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: FakeModel(
            id=resource_id,
            display_name="current-instance",
            lifecycle_state="STOPPED",
        ),
    )

    updated_resource = instance.update_resource(resource)

    assert action_calls == [("ocid1.instance.oc1..example", "STOP")]
    assert update_calls[0][1].display_name == "updated-instance"
    assert updated_resource.id == "ocid1.instance.oc1..example"


def test_delete_resource_terminates_instance(monkeypatch):
    install_fake_oci(monkeypatch)

    instance_module = load_collection_module("oci_instance")
    terminate_calls = []
    response = FakeResponse(data=FakeModel(id="ocid1.instance.oc1..example"))

    def terminate_instance(instance_id):
        terminate_calls.append(instance_id)
        return response

    resource = FakeModel(id="ocid1.instance.oc1..example")
    instance = make_instance_module(
        instance_module,
        {"wait": True},
        client=types.SimpleNamespace(terminate_instance=terminate_instance),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: None,
    )

    instance.delete_resource(resource)

    assert terminate_calls == ["ocid1.instance.oc1..example"]


def test_normalize_enum_values_upper_cases_known_keys_recursively(monkeypatch):
    install_fake_oci(monkeypatch)

    instance_module = load_collection_module("oci_instance")

    normalized = instance_module.normalize_enum_values(
        {
            "recovery_action": "stop_instance",
            "nested": {"type": "amd_vm"},
            "items": [{"desired_state": "enabled"}],
            "unrelated": "left_alone",
        }
    )

    assert normalized == {
        "recovery_action": "STOP_INSTANCE",
        "nested": {"type": "AMD_VM"},
        "items": [{"desired_state": "ENABLED"}],
        "unrelated": "left_alone",
    }


def test_build_source_details_uses_boot_volume_when_image_id_absent(monkeypatch):
    install_fake_oci(monkeypatch)

    instance_module = load_collection_module("oci_instance")
    details = instance_module.build_source_details(
        {"boot_volume_id": "ocid1.bootvolume.oc1..example"}
    )

    assert isinstance(details, FakeModel)
    assert details.boot_volume_id == "ocid1.bootvolume.oc1..example"
    assert not hasattr(details, "image_id")


def test_build_agent_config_normalizes_plugin_desired_state(monkeypatch):
    install_fake_oci(monkeypatch)

    instance_module = load_collection_module("oci_instance")
    agent_config = instance_module.build_agent_config(
        {
            "agent_config": {
                "are_all_plugins_disabled": False,
                "plugins_config": [{"name": "Bastion", "desired_state": "enabled"}],
            }
        },
        instance_module.oci.core.models.LaunchInstanceAgentConfigDetails,
    )

    assert isinstance(agent_config, FakeModel)
    assert agent_config.are_all_plugins_disabled is False
    assert len(agent_config.plugins_config) == 1
    assert agent_config.plugins_config[0].name == "Bastion"
    assert agent_config.plugins_config[0].desired_state == "ENABLED"


def test_build_platform_config_resolves_type_specific_class(monkeypatch):
    install_fake_oci(monkeypatch)

    instance_module = load_collection_module("oci_instance")
    platform_config = instance_module.build_platform_config(
        {
            "platform_config": {
                "type": "amd_vm",
                "is_secure_boot_enabled": True,
            }
        },
        "LaunchInstancePlatformConfig",
    )

    assert isinstance(platform_config, FakeModel)
    assert platform_config.type == "AMD_VM"
    assert platform_config.is_secure_boot_enabled is True


def test_build_platform_config_rejects_unknown_type(monkeypatch):
    install_fake_oci(monkeypatch)

    instance_module = load_collection_module("oci_instance")

    with pytest.raises(ValueError):
        instance_module.build_platform_config(
            {"platform_config": {"type": "not_a_type"}}, "LaunchInstancePlatformConfig"
        )


def test_build_platform_config_rejects_unsupported_operation_for_type(monkeypatch):
    """Bare metal platform_config types have no UpdateInstancePlatformConfig
    class at all (OCI does not support updating them after launch)."""
    install_fake_oci(monkeypatch)

    instance_module = load_collection_module("oci_instance")

    with pytest.raises(ValueError):
        instance_module.build_platform_config(
            {"platform_config": {"type": "generic_bm"}}, "UpdateInstancePlatformConfig"
        )


def test_needs_update_ignores_unset_availability_config_suboptions(monkeypatch):
    """Regression test: Ansible fills every declared suboption with ``None``
    when the caller only sets one of them. Comparing those ``None``
    placeholders against the resource's real values would otherwise report
    spurious drift on every run.
    """
    install_fake_oci(monkeypatch)

    instance_module = load_collection_module("oci_instance")
    instance = make_instance_module(
        instance_module,
        {
            "availability_config": {
                "is_live_migration_preferred": None,
                "recovery_action": "restore_instance",
            }
        },
    )
    resource = FakeModel(
        id="ocid1.instance.oc1..example",
        availability_config={
            "is_live_migration_preferred": False,
            "recovery_action": "RESTORE_INSTANCE",
        },
        lifecycle_state="RUNNING",
    )

    assert instance.needs_update(resource) is False


def test_needs_update_returns_true_for_availability_config_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    instance_module = load_collection_module("oci_instance")
    instance = make_instance_module(
        instance_module,
        {"availability_config": {"recovery_action": "stop_instance"}},
    )
    resource = FakeModel(
        id="ocid1.instance.oc1..example",
        availability_config={"recovery_action": "RESTORE_INSTANCE"},
        lifecycle_state="RUNNING",
    )

    assert instance.needs_update(resource) is True


def test_validate_create_request_requires_image_id_or_boot_volume_id(monkeypatch):
    install_fake_oci(monkeypatch)

    instance_module = load_collection_module("oci_instance")
    instance = make_instance_module(
        instance_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "availability_domain": "Uocm:PHX-AD-1",
            "shape": "VM.Standard.E4.Flex",
            "subnet_id": "ocid1.subnet.oc1..example",
            "name": "example-instance",
        },
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "image_id or boot_volume_id" in exc_info.value.payload["msg"]


def test_validate_create_request_passes_with_boot_volume_id(monkeypatch):
    install_fake_oci(monkeypatch)

    instance_module = load_collection_module("oci_instance")
    instance = make_instance_module(
        instance_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "availability_domain": "Uocm:PHX-AD-1",
            "shape": "VM.Standard.E4.Flex",
            "subnet_id": "ocid1.subnet.oc1..example",
            "name": "example-instance",
            "boot_volume_id": "ocid1.bootvolume.oc1..example",
        },
    )

    instance.validate_create_request()
