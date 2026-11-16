from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    FailJsonCalled,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)


MODEL_NAMES = ("CreateRemotePeeringConnectionDetails", "UpdateRemotePeeringConnectionDetails")


def install_fake_oci(monkeypatch):
    """Install the SDK models used by the RPC resource module tests."""
    return shared_install_fake_oci(monkeypatch, model_names=MODEL_NAMES)


def make_rpc_module(module_obj, params, client=None, check_mode=False):
    """Build an RPC module instance without creating an OCI client."""
    return make_module_instance(
        module_obj,
        "OciNetworkRemotePeeringConnectionModule",
        params,
        client=client,
        check_mode=check_mode,
    )


def test_main_exposes_collection_inputs(monkeypatch):
    """Verify the resource module argument names and choices."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_remote_peering_connection")
    captured = {}

    class FakeRpcModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["called"] = True

    def fake_ansible_module(**kwargs):
        captured["spec"] = kwargs["argument_spec"]
        return DummyModule({})

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciNetworkRemotePeeringConnectionModule", FakeRpcModule)
    module_obj.main()

    assert captured["called"] is True
    assert captured["spec"]["remote_peering_connection_id"] == {"type": "str"}
    assert captured["spec"]["drg_id"] == {"type": "str"}
    assert captured["spec"]["name"] == {"type": "str"}
    assert "display_name" not in captured["spec"]
    assert "id" not in captured["spec"]


def test_build_create_details_maps_name_and_tags(monkeypatch):
    """Verify create input mapping to the SDK model."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_remote_peering_connection")
    details = module_obj.build_create_remote_peering_connection_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "drg_id": "ocid1.drg.oc1..example",
            "name": "example-rpc",
            "freeform_tags": {"env": "dev"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        }
    )

    assert details.compartment_id == "ocid1.compartment.oc1..example"
    assert details.drg_id == "ocid1.drg.oc1..example"
    assert details.display_name == "example-rpc"
    assert details.freeform_tags == {"env": "dev"}
    assert details.defined_tags == {"Operations": {"CostCenter": "42"}}


def test_create_requires_compartment_drg_and_name(monkeypatch):
    """Verify missing create fields fail before an SDK call."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_remote_peering_connection")
    instance = make_rpc_module(module_obj, {"compartment_id": "c", "drg_id": "d"})

    try:
        instance.validate_create_request()
    except FailJsonCalled as exc:
        assert "name" in exc.payload["msg"]
    else:
        raise AssertionError("validate_create_request should fail")


def test_update_plan_maps_name_and_tags(monkeypatch):
    """Verify mutable RPC fields produce an update plan."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_remote_peering_connection")
    instance = make_rpc_module(
        module_obj,
        {"name": "updated-rpc", "freeform_tags": {"env": "prod"}},
    )
    plan = instance.build_update_plan(
        FakeModel(
            id="rpc-id",
            display_name="current-rpc",
            freeform_tags={"env": "dev"},
        )
    )

    assert plan["update_needed"] is True
    assert plan["update_model_fields"] == {
        "display_name": "updated-rpc",
        "freeform_tags": {"env": "prod"},
    }


def test_create_update_delete_use_expected_sdk_methods(monkeypatch):
    """Verify lifecycle methods call the SDK with RPC identifiers."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_remote_peering_connection")
    calls = []

    def create_remote_peering_connection(**kwargs):
        calls.append(("create", kwargs))
        return FakeResponse(data=FakeModel(id="rpc-id"))

    def update_remote_peering_connection(**kwargs):
        calls.append(("update", kwargs))
        return FakeResponse(data=FakeModel(id="rpc-id"))

    def delete_remote_peering_connection(**kwargs):
        calls.append(("delete", kwargs))
        return FakeResponse(data=None)

    client = types.SimpleNamespace(
        create_remote_peering_connection=create_remote_peering_connection,
        update_remote_peering_connection=update_remote_peering_connection,
        delete_remote_peering_connection=delete_remote_peering_connection,
    )
    instance = make_rpc_module(
        module_obj,
        {
            "compartment_id": "c",
            "drg_id": "d",
            "name": "rpc",
            "wait": True,
        },
        client=client,
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: FakeModel(
            id=resource_id, lifecycle_state="AVAILABLE"
        ),
    )

    created = instance.create_resource()
    update_instance = make_rpc_module(
        module_obj,
        {"name": "updated-rpc", "wait": True},
        client=client,
    )
    update_instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    update_instance.wait_for_resource_id = lambda resource_id, target_states, **kwargs: FakeModel(
        id=resource_id, lifecycle_state="AVAILABLE"
    )
    update_instance.update_resource(FakeModel(id="rpc-id", display_name="rpc"))
    instance.delete_resource(FakeModel(id="rpc-id"))

    assert created.id == "rpc-id"
    assert [item[0] for item in calls] == ["create", "update", "delete"]
    assert calls[1][1]["remote_peering_connection_id"] == "rpc-id"
    assert calls[2][1] == {"remote_peering_connection_id": "rpc-id"}


def test_check_mode_create_does_not_call_sdk(monkeypatch):
    """Verify check mode predicts create without an OCI mutation."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_remote_peering_connection")
    calls = []
    instance = make_rpc_module(
        module_obj,
        {"compartment_id": "c", "drg_id": "d", "name": "rpc"},
        client=types.SimpleNamespace(create_remote_peering_connection=lambda **kwargs: calls.append(kwargs)),
        check_mode=True,
    )
    instance.resolve_target_resource = lambda: None
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload["changed"] is True
    assert calls == []


def test_check_mode_update_and_delete_do_not_call_sdk(monkeypatch):
    """Verify check mode predicts update and delete without OCI mutations."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_remote_peering_connection")
    calls = []
    client = types.SimpleNamespace(
        update_remote_peering_connection=lambda **kwargs: calls.append(("update", kwargs)),
        delete_remote_peering_connection=lambda **kwargs: calls.append(("delete", kwargs)),
    )
    update = make_rpc_module(module_obj, {"name": "updated"}, client=client, check_mode=True)
    update.resolve_target_resource = lambda: FakeModel(id="rpc-id", display_name="current")
    with pytest.raises(ExitJsonCalled) as update_result:
        update.execute_resource_module()
    assert update_result.value.payload["changed"] is True
    delete = make_rpc_module(
        module_obj,
        {"state": "absent", "remote_peering_connection_id": "rpc-id"},
        client=client,
        check_mode=True,
    )
    delete.resolve_target_resource = lambda: FakeModel(id="rpc-id", display_name="current")
    with pytest.raises(ExitJsonCalled) as delete_result:
        delete.execute_resource_module()
    assert delete_result.value.payload["changed"] is True
    assert calls == []


def test_present_is_idempotent_when_resource_matches(monkeypatch):
    """Verify repeated desired state exits without a change."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_remote_peering_connection")
    instance = make_rpc_module(module_obj, {"name": "current"})
    instance.resolve_target_resource = lambda: FakeModel(id="rpc-id", display_name="current")
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload["changed"] is False
    assert instance.module.params["name"] == "current"


def test_name_lookup_uses_drg_scope_and_rejects_duplicates(monkeypatch):
    """Verify scoped name lookup passes the DRG filter and rejects duplicates."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_remote_peering_connection")
    instance = make_rpc_module(
        module_obj,
        {"compartment_id": "c", "drg_id": "d", "name": "rpc"},
        client=types.SimpleNamespace(list_remote_peering_connections="list-rpcs"),
    )
    calls = []
    instance.list_all_resources = lambda list_fn, **kwargs: calls.append(kwargs) or [
        FakeModel(display_name="rpc", lifecycle_state="AVAILABLE"),
        FakeModel(display_name="rpc", lifecycle_state="AVAILABLE"),
    ]
    with pytest.raises(FailJsonCalled) as error:
        instance.resolve_resource_by_name()
    assert calls == [{"compartment_id": "c", "drg_id": "d"}]
    assert "Multiple" in error.value.payload["msg"]


@pytest.mark.parametrize("field", ["compartment_id", "drg_id"])
def test_immutable_scope_fields_fail_update(monkeypatch, field):
    """Verify compartment and DRG changes fail during update planning."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_remote_peering_connection")
    instance = make_rpc_module(module_obj, {field: "new-value"})
    resource = FakeModel(id="rpc-id", compartment_id="old-value", drg_id="old-value")
    with pytest.raises(FailJsonCalled):
        instance.build_update_plan(resource)
