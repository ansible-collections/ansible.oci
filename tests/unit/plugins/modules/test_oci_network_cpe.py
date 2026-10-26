from __future__ import absolute_import, division, print_function

import types

import pytest

from .conftest import (
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(
        monkeypatch,
        model_names=("CreateCpeDetails", "UpdateCpeDetails"),
    )


def make_cpe_module(module_obj, params, client=None, check_mode=False):
    return make_module_instance(
        module_obj,
        "OciNetworkCpeModule",
        params,
        client=client,
        check_mode=check_mode,
    )


def test_create_request_maps_fields(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_cpe")
    captured = {}

    def create_cpe(**kwargs):
        captured.update(kwargs)
        return FakeResponse(FakeModel(id="cpe-id"))

    instance = make_cpe_module(
        module_obj,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-cpe",
            "ip_address": "203.0.113.2",
            "cpe_device_shape_id": "shape",
            "freeform_tags": {"env": "dev"},
            "defined_tags": None,
            "state": "present",
        },
        client=types.SimpleNamespace(create_cpe=create_cpe),
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    assert instance.create_resource().id == "cpe-id"
    details = captured["create_cpe_details"]
    assert isinstance(details, FakeModel)
    assert details.display_name == "example-cpe"
    assert details.ip_address == "203.0.113.2"
    assert details.cpe_device_shape_id == "shape"
    assert details.compartment_id == "ocid1.compartment.oc1..example"
    assert details.freeform_tags == {"env": "dev"}
    assert not hasattr(details, "defined_tags")
    assert not hasattr(details, "state")


def test_update_plan_maps_mutable_fields(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_cpe")
    instance = make_cpe_module(
        module_obj,
        {"name": "new-cpe", "cpe_device_shape_id": "new-shape"},
    )
    resource = FakeModel(
        id="ocid1.cpe.oc1..example",
        display_name="old-cpe",
        cpe_device_shape_id="old-shape",
    )
    plan = instance.build_update_plan(resource)
    assert plan["update_needed"] is True
    assert plan["update_model_fields"] == {
        "display_name": "new-cpe",
        "cpe_device_shape_id": "new-shape",
    }


def test_create_update_delete_use_direct_operations(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_cpe")
    calls = []

    def create_cpe(**kwargs):
        calls.append(("create", kwargs))
        return FakeResponse(FakeModel(id="cpe-id"))

    def update_cpe(**kwargs):
        calls.append(("update", kwargs))
        return FakeResponse(FakeModel(id="cpe-id", display_name="new"))

    def delete_cpe(**kwargs):
        calls.append(("delete", kwargs))
        return FakeResponse(None)

    client = types.SimpleNamespace(
        create_cpe=create_cpe,
        update_cpe=update_cpe,
        delete_cpe=delete_cpe,
    )
    instance = make_cpe_module(
        module_obj,
        {"compartment_id": "compartment", "name": "name", "ip_address": "1.2.3.4"},
        client=client,
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    instance.call_delete_fn = lambda resource, fn, **kwargs: fn(**kwargs)
    assert instance.create_resource().id == "cpe-id"
    resource = FakeModel(
        id="cpe-id",
        display_name="old",
        ip_address="1.2.3.4",
        compartment_id="compartment",
    )
    instance.module.params["name"] = "new"
    assert instance.update_resource(resource).display_name == "new"
    assert instance.delete_resource(resource) is None
    assert [call[0] for call in calls] == ["create", "update", "delete"]


def test_main_uses_cpe_identifier(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_cpe")
    captured = {}

    class FakeAnsibleModule:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    class FakeCpeModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["executed"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", FakeAnsibleModule)
    monkeypatch.setattr(module_obj, "OciNetworkCpeModule", FakeCpeModule)
    module_obj.main()
    assert captured["executed"] is True
    assert captured["argument_spec"]["cpe_id"] == {"type": "str"}


def test_execute_create_check_mode_does_not_call_create(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_cpe")
    instance = make_cpe_module(
        module_obj,
        {
            "state": "present",
            "compartment_id": "compartment",
            "name": "example-cpe",
            "ip_address": "1.2.3.4",
        },
        check_mode=True,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)
    monkeypatch.setattr(
        instance, "create_resource", raising(AssertionError("create called"))
    )
    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()
    assert exc_info.value.payload == {"changed": True}


def test_execute_create_and_unchanged_rerun(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_cpe")
    params = {
        "state": "present",
        "compartment_id": "compartment",
        "name": "example-cpe",
        "ip_address": "1.2.3.4",
    }
    instance = make_cpe_module(module_obj, params)
    created = FakeModel(
        id="cpe-id",
        display_name="example-cpe",
        compartment_id="compartment",
        ip_address="1.2.3.4",
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)
    monkeypatch.setattr(instance, "create_resource", lambda: created)
    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()
    assert exc_info.value.payload["changed"] is True
    assert exc_info.value.payload["resource"]["id"] == "cpe-id"

    monkeypatch.setattr(instance, "resolve_target_resource", lambda: created)
    with pytest.raises(ExitJsonCalled) as rerun:
        instance.execute_resource_module()
    assert rerun.value.payload["changed"] is False


def test_execute_update_check_and_direct_update(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_cpe")
    resource = FakeModel(
        id="cpe-id",
        display_name="old",
        compartment_id="compartment",
        ip_address="1.2.3.4",
    )
    instance = make_cpe_module(
        module_obj,
        {"state": "present", "cpe_id": "cpe-id", "name": "new"},
        check_mode=True,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: resource)
    monkeypatch.setattr(
        instance, "update_resource", raising(AssertionError("update called"))
    )
    with pytest.raises(ExitJsonCalled) as check:
        instance.execute_resource_module()
    assert check.value.payload == {"changed": True}

    instance.check_mode = False
    monkeypatch.setattr(
        instance,
        "update_resource",
        lambda current: FakeModel(id=current.id, display_name="new"),
    )
    with pytest.raises(ExitJsonCalled) as updated:
        instance.execute_resource_module()
    assert updated.value.payload["changed"] is True


def test_execute_delete_check_direct_delete_and_absent_rerun(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_cpe")
    resource = FakeModel(id="cpe-id", display_name="example-cpe")
    instance = make_cpe_module(
        module_obj,
        {"state": "absent", "cpe_id": "cpe-id"},
        check_mode=True,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: resource)
    monkeypatch.setattr(
        instance, "delete_resource", raising(AssertionError("delete called"))
    )
    with pytest.raises(ExitJsonCalled) as check:
        instance.execute_resource_module()
    assert check.value.payload == {"changed": True}

    instance.check_mode = False
    calls = []
    monkeypatch.setattr(
        instance, "delete_resource", lambda current: calls.append(current.id)
    )
    with pytest.raises(ExitJsonCalled) as deleted:
        instance.execute_resource_module()
    assert deleted.value.payload == {"changed": True}
    assert calls == ["cpe-id"]

    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)
    with pytest.raises(ExitJsonCalled) as rerun:
        instance.execute_resource_module()
    assert rerun.value.payload == {"changed": False}
