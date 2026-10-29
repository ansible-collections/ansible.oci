from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types
from unittest.mock import Mock

import pytest
from ansible.module_utils.common.arg_spec import ModuleArgumentSpecValidator

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FailJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
)


@pytest.fixture
def module_obj(monkeypatch):
    """Load the VNIC module with a local SDK model substitute.

    Args:
        monkeypatch: Pytest patch fixture.

    Returns:
        The imported VNIC module.
    """
    install_fake_oci(monkeypatch, model_names=("UpdateVnicDetails",))
    return load_collection_module("oci_network_vnic_update")


def make_helper(module_obj, params, resource, check_mode=False):
    """Build a helper with recorded SDK calls and the inherited update flow.

    Args:
        module_obj: Imported VNIC module.
        params: Module inputs.
        resource: Current VNIC model.
        check_mode: Whether to predict changes only.

    Returns:
        A helper whose client records get and update calls.
    """
    client = types.SimpleNamespace(
        get_vnic=Mock(return_value=FakeResponse(resource)),
        update_vnic=Mock(return_value=FakeResponse(resource)),
    )
    helper = make_module_instance(
        module_obj, "OciNetworkVnicUpdateModule", params, client, check_mode
    )
    helper.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    return helper


@pytest.mark.parametrize("params,error", [
    ({"vnic_id": "vnic", "name": "MixedCase"}, None),
    ({"vnic_id": "vnic", "display_name": "MixedCase"}, "display_name"),
    ({"vnic_id": "vnic", "id": "vnic"}, "id"),
    ({"vnic_id": "vnic", "state": "absent"}, "state"),
    ({}, "vnic_id"),
    ({"vnic_id": ""}, "cannot be empty"),
])
def test_main_validates_inputs_and_canonical_options(module_obj, monkeypatch, params, error):
    """Verify canonical inputs, rejected aliases, and update defaults."""
    captured = {}

    def validate_arguments(**kwargs):
        """Validate inputs with the argument validator used by Ansible."""
        result = ModuleArgumentSpecValidator(kwargs["argument_spec"]).validate(params)
        if result.error_messages:
            raise FailJsonCalled({"msg": "; ".join(result.error_messages)})
        captured.update(kwargs)
        return DummyModule(result.validated_parameters)

    adapter = Mock()
    monkeypatch.setattr(module_obj, "AnsibleModule", validate_arguments)
    monkeypatch.setattr(module_obj, "OciNetworkVnicUpdateModule", adapter)
    if error:
        with pytest.raises(FailJsonCalled, match=error):
            module_obj.main()
        adapter.assert_not_called()
        return
    module_obj.main()
    inputs = adapter.call_args.args[0].params
    assert inputs["vnic_id"] == "vnic"
    assert inputs["name"] == "MixedCase"
    assert inputs["skip_source_dest_check"] is None
    assert inputs["wait"] is True
    assert inputs["wait_timeout"] == 1200
    assert inputs["wait_interval"] == 30
    assert captured["supports_check_mode"] is True


@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize("changed", [False, True])
def test_execute_update_and_repeat(module_obj, check_mode, changed):
    """Exercise change detection and SDK dispatch in normal and check mode."""
    desired = "NewName" if changed else "OriginalName"
    resource = FakeModel(id="vnic", display_name="OriginalName", lifecycle_state="AVAILABLE")
    helper = make_helper(
        module_obj,
        {"vnic_id": "vnic", "name": desired, "wait": False},
        resource,
        check_mode,
    )
    updated = FakeModel(id="vnic", display_name=desired, lifecycle_state="AVAILABLE")
    helper.client.update_vnic.return_value = FakeResponse(updated)
    with pytest.raises(ExitJsonCalled) as exc:
        helper.execute_resource_module()
    assert exc.value.payload["changed"] is changed
    helper.client.get_vnic.assert_called_once_with(vnic_id="vnic")
    if changed and not check_mode:
        helper.client.update_vnic.assert_called_once()
        kwargs = helper.client.update_vnic.call_args.kwargs
        assert kwargs["vnic_id"] == "vnic"
        assert kwargs["update_vnic_details"].display_name == desired
        assert exc.value.payload["resource"]["name"] == desired
    else:
        helper.client.update_vnic.assert_not_called()
    if check_mode and changed:
        assert "resource" not in exc.value.payload
    else:
        assert "display_name" not in exc.value.payload["resource"]


@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize("missing_kind", ["404", "TERMINATED"])
def test_missing_target_never_creates(module_obj, check_mode, missing_kind):
    """Reject missing and terminated VNICs before any mutation."""
    resource = FakeModel(id="vnic", lifecycle_state="TERMINATED")
    helper = make_helper(module_obj, {"vnic_id": "vnic"}, resource, check_mode)
    if missing_kind == "404":
        error = Exception("not found")
        error.status = 404
        helper.client.get_vnic.side_effect = error
    with pytest.raises(FailJsonCalled, match="must already exist"):
        helper.execute_resource_module()
    helper.client.update_vnic.assert_not_called()


@pytest.mark.parametrize("wait", [False, True])
def test_update_payload_and_wait(module_obj, wait):
    """Preserve field values and use the shared waiter only when requested."""
    desired = {
        "display_name": "MixedCase",
        "hostname_label": "host",
        "route_table_id": "RouteId",
        "skip_source_dest_check": False,
        "nsg_ids": [],
        "freeform_tags": {},
        "defined_tags": {"CaseSensitive": {"Key": "Value"}},
        "security_attributes": {"Namespace": {"Attribute": {"value": "Value", "mode": "audit"}}},
    }
    resource = FakeModel(
        id="vnic", lifecycle_state="AVAILABLE", display_name="old",
        nsg_ids=["nsg"], skip_source_dest_check=True, freeform_tags={"old": "value"},
    )
    params = dict(desired, vnic_id="vnic", wait=wait)
    params["name"] = params.pop("display_name")
    helper = make_helper(module_obj, params, resource)
    waited = FakeModel(id="vnic", **desired)
    helper.wait_for_resource_id = Mock(return_value=waited)
    result = helper.update_resource(resource)
    details = helper.client.update_vnic.call_args.kwargs["update_vnic_details"]
    assert vars(details) == desired
    if wait:
        helper.wait_for_resource_id.assert_called_once_with("vnic", ("AVAILABLE",))
        assert result is waited
    else:
        helper.wait_for_resource_id.assert_not_called()
        assert result is resource


@pytest.mark.parametrize("check_mode", [False, True])
def test_omitted_fields_and_nsg_order_are_unchanged(module_obj, check_mode):
    """Ignore NSG order and preserve fields that the caller omits."""
    resource = FakeModel(
        id="vnic", display_name="KeepCase", nsg_ids=["a", "b"],
        skip_source_dest_check=True, freeform_tags={"KeepKey": "KeepValue"},
    )
    helper = make_helper(module_obj, {"vnic_id": "vnic", "nsg_ids": ["b", "a"]}, resource, check_mode)
    with pytest.raises(ExitJsonCalled) as exc:
        helper.execute_resource_module()
    expected = dict(vars(resource))
    expected["name"] = expected.pop("display_name")
    assert exc.value.payload == {"changed": False, "resource": expected}
    helper.client.update_vnic.assert_not_called()


@pytest.mark.parametrize("rename", [False, True])
def test_vlan_ignored_fields_preserve_supported_updates(module_obj, rename):
    """Exclude ignored VLAN fields without discarding supported changes."""
    resource = FakeModel(
        id="vnic", vlan_id="vlan", display_name="old", nsg_ids=["old"], skip_source_dest_check=True,
    )
    params = {"vnic_id": "vnic", "nsg_ids": [], "skip_source_dest_check": False}
    if rename:
        params["name"] = "new"
    helper = make_helper(module_obj, params, resource)
    plan = helper.get_update_plan(resource)
    assert plan["update_needed"] is rename
    assert plan["update_model_fields"] == ({"display_name": "new"} if rename else {})


def test_empty_tag_and_security_maps_are_sent(module_obj):
    """Send empty maps when the caller requests removal of existing data."""
    resource = FakeModel(
        id="vnic", freeform_tags={"key": "value"},
        defined_tags={"ns": {"key": "value"}}, security_attributes={"ns": {"key": "value"}},
    )
    params = dict(vnic_id="vnic", freeform_tags={}, defined_tags={}, security_attributes={}, wait=False)
    helper = make_helper(module_obj, params, resource)
    helper.update_resource(resource)
    details = helper.client.update_vnic.call_args.kwargs["update_vnic_details"]
    assert vars(details) == {"freeform_tags": {}, "defined_tags": {}, "security_attributes": {}}


@pytest.mark.parametrize("operation", ["get_vnic", "update_vnic"])
def test_service_errors_propagate(module_obj, operation):
    """Preserve OCI errors from reads and updates."""
    helper = make_helper(module_obj, {"vnic_id": "vnic", "name": "new"}, FakeModel(id="vnic"))
    error = Exception("service failure")
    error.status = 403
    getattr(helper.client, operation).side_effect = error
    with pytest.raises(Exception, match="^service failure$") as exc:
        helper.execute_resource_module()
    assert exc.value is error
