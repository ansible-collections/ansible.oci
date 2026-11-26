from types import SimpleNamespace

import oci
import pytest

from .conftest import FailJsonCalled, ExitJsonCalled, load_collection_module, make_module_instance


@pytest.fixture
def adapter(monkeypatch):
    module = load_collection_module("oci_instance")
    monkeypatch.setattr(module, "oci", oci)
    monkeypatch.setitem(module.build_platform_config.__globals__, "oci", oci)

    def make(params, **kwargs):
        instance = make_module_instance(module, "OciInstanceModule", params, **kwargs)

        def direct(fn, **values):
            values.pop("max_retries", None)
            values.pop("retry_on", None)
            return fn(**values)
        instance.call_with_retry = direct
        return instance
    return make


def resource(**kwargs):
    return oci.core.models.Instance(id="InstanceID", **kwargs)


@pytest.mark.parametrize("wait", [False, True])
@pytest.mark.parametrize("action", ["START", "STOP"])
def test_configuration_and_power_order(adapter, wait, action):
    calls = []
    old_state, new_state = ("STOPPED", "RUNNING") if action == "START" else ("RUNNING", "STOPPED")
    instance = adapter({"wait": wait, "power_state": new_state.lower(), "name": "new"})
    instance.client = SimpleNamespace(
        update_instance=lambda **kw: calls.append("UPDATE") or SimpleNamespace(data=resource(display_name="new")),
        instance_action=lambda **kw: calls.append(kw["action"]),
    )

    def poll(identifier, states, **kwargs):
        calls.append((tuple(states), kwargs.get("wait", wait)))
        return resource(lifecycle_state=new_state, display_name="new")
    instance.wait_for_resource_id = poll
    instance.update_resource(resource(lifecycle_state=old_state, display_name="old"))
    operations = [value for value in calls if isinstance(value, str)]
    assert operations == (["UPDATE", "START"] if action == "START" else ["STOP", "UPDATE"])
    first_wait = next(value for value in calls if isinstance(value, tuple))
    assert first_wait[1] is True
    if action == "STOP" and not wait:
        assert calls[-1] == "UPDATE"
    else:
        assert calls[-1][1] is wait


def test_create_without_final_wait_still_stops(adapter):
    calls = []
    instance = adapter({"wait": False, "power_state": "stopped"})
    instance.client = SimpleNamespace(
        launch_instance=lambda **kw: SimpleNamespace(data=resource(lifecycle_state="PROVISIONING")),
        instance_action=lambda **kw: calls.append(kw["action"]),
    )

    def poll(identifier, states, **kwargs):
        calls.append((states, kwargs.get("wait", False)))
        return resource(lifecycle_state="RUNNING")
    instance.wait_for_resource_id = poll
    instance.create_resource()
    assert calls == [(["RUNNING"], True), "STOP", (["STOPPED"], False)]


def test_cluster_launch_value_does_not_break_repeat_runs(adapter):
    instance = adapter({"compute_cluster_id": "ClusterID"})
    assert not instance.needs_update(resource())


@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize("field,desired,current", [
    ("launch_options", {"firmware": "uefi_64"}, oci.core.models.LaunchOptions(firmware="BIOS")),
    ("platform_config", {"type": "amd_vm", "is_secure_boot_enabled": True},
     oci.core.models.AmdVmPlatformConfig(is_secure_boot_enabled=False)),
    ("metadata", {"user_data": "changed"}, {"user_data": "original"}),
])
def test_invalid_update_fails_before_power_action(adapter, check_mode, field, desired, current):
    instance = adapter({field: desired, "power_state": "running"}, check_mode=check_mode)
    existing = resource(lifecycle_state="STOPPED", **{field: current})
    instance.resolve_target_resource = lambda: existing
    with pytest.raises(FailJsonCalled):
        instance.execute_resource_module()


def test_unchanged_creation_fields_are_removed_from_update(adapter):
    instance = adapter({"launch_options": {"firmware": "bios", "network_type": "paravirtualized"}})
    plan = instance.build_update_plan(resource(launch_options=oci.core.models.LaunchOptions(
        firmware="BIOS", network_type="E1000")))
    details = instance.build_update_details(plan["update_model_fields"])
    assert isinstance(details.launch_options, oci.core.models.UpdateLaunchOptions)
    assert details.launch_options.network_type == "PARAVIRTUALIZED"
    assert "firmware" not in oci.util.to_dict(details.launch_options)


def test_platform_update_infers_type_and_keeps_false(adapter):
    instance = adapter({"platform_config": {"is_symmetric_multi_threading_enabled": False,
                                            "is_secure_boot_enabled": True}})
    plan = instance.build_update_plan(resource(platform_config=oci.core.models.AmdVmPlatformConfig(
        is_symmetric_multi_threading_enabled=True, is_secure_boot_enabled=True)))
    details = instance.build_update_details(plan["update_model_fields"])
    assert isinstance(details.platform_config, oci.core.models.AmdVmUpdateInstancePlatformConfig)
    assert details.platform_config.is_symmetric_multi_threading_enabled is False


@pytest.mark.parametrize("field", ["metadata", "extended_metadata"])
def test_metadata_preserves_reserved_values_and_replaces_other_keys(adapter, field):
    instance = adapter({field: {"new": "value"}})
    plan = instance.build_update_plan(resource(**{field: {"user_data": "original", "old": "value"}}))
    effective = {"user_data": "original", "new": "value"}
    assert plan["update_model_fields"][field] == effective
    assert not instance.build_update_plan(resource(**{field: effective}))["update_needed"]
    assert instance.module.params[field] == {"new": "value"}


@pytest.mark.parametrize("params", [
    {"metadata": {"user_data": "new"}},
    {"extended_metadata": {"user_data": "original"}},
])
def test_reserved_metadata_cannot_be_added_or_moved(adapter, params):
    existing = resource(metadata={"user_data": "original"}) if "extended_metadata" in params else resource()
    instance = adapter(params)
    with pytest.raises(FailJsonCalled):
        instance.build_update_plan(existing)


@pytest.mark.parametrize("plugins,changed", [
    ([{"name": "Bastion", "desired_state": "enabled"}], False),
    ([{"name": "Monitor", "desired_state": "disabled"}, {"name": "Bastion", "desired_state": "enabled"}], False),
    ([], False),
    ([{"name": "Missing", "desired_state": "enabled"}], True),
    ([{"name": "Bastion", "desired_state": "disabled"}], True),
])
def test_plugin_subset_comparison(adapter, plugins, changed):
    instance = adapter({"agent_config": {"plugins_config": plugins}})
    current = resource(agent_config=oci.core.models.InstanceAgentConfig(plugins_config=[
        oci.core.models.InstanceAgentPluginConfigDetails(name="Bastion", desired_state="ENABLED"),
        oci.core.models.InstanceAgentPluginConfigDetails(name="Monitor", desired_state="DISABLED"),
    ]))
    assert instance.needs_update(current) is changed


@pytest.mark.parametrize("plugins", [
    [{"name": "Bastion"}], [{"desired_state": "enabled"}],
    [{"name": "Bastion", "desired_state": "enabled"}] * 2,
])
def test_invalid_plugin_entries_fail(adapter, plugins):
    instance = adapter({"agent_config": {"plugins_config": plugins}})
    existing = resource()
    with pytest.raises(FailJsonCalled):
        instance.build_update_plan(existing)


def test_valid_check_mode_does_not_mutate(adapter):
    instance = adapter({"name": "new", "power_state": "running"}, check_mode=True)
    instance.resolve_target_resource = lambda: resource(display_name="old", lifecycle_state="STOPPED")
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload["changed"] is True


def test_wait_override_uses_waiter(adapter, monkeypatch):
    instance = adapter({"wait": False})
    response = SimpleNamespace(data=resource(lifecycle_state="RUNNING"))
    calls = []
    instance.get_resource_response = lambda identifier: response
    globals_ = instance.wait_for_resource_id.__func__.__globals__
    monkeypatch.setitem(globals_, "oci", SimpleNamespace(wait_until=lambda *a, **kw: calls.append(kw) or response))
    instance.wait_for_resource_id("InstanceID", ["RUNNING"])
    assert not calls
    instance.wait_for_resource_id("InstanceID", ["RUNNING"], wait=True)
    assert len(calls) == 1


@pytest.mark.parametrize("check_mode", [False, True])
def test_create_validation_rejects_incomplete_plugin(adapter, check_mode):
    instance = adapter({
        "compartment_id": "CompartmentID", "availability_domain": "AD", "shape": "Shape",
        "subnet_id": "SubnetID", "name": "instance", "image_id": "ImageID",
        "agent_config": {"plugins_config": [{"name": "Bastion"}]},
    }, check_mode=check_mode)
    instance.resolve_target_resource = lambda: None
    with pytest.raises(FailJsonCalled):
        instance.execute_resource_module()


def test_partial_plugin_update_payload(adapter):
    requested = [{"name": "Bastion", "desired_state": "disabled"}]
    instance = adapter({"agent_config": {"plugins_config": requested}})
    existing = resource(agent_config=oci.core.models.InstanceAgentConfig(plugins_config=[
        oci.core.models.InstanceAgentPluginConfigDetails(name="Bastion", desired_state="ENABLED"),
        oci.core.models.InstanceAgentPluginConfigDetails(name="Monitor", desired_state="ENABLED"),
    ]))
    plan = instance.build_update_plan(existing)
    details = instance.build_update_details(plan["update_model_fields"])
    assert len(details.agent_config.plugins_config) == 1
    assert details.agent_config.plugins_config[0].desired_state == "DISABLED"
