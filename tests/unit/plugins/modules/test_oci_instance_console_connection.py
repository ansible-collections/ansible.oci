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
    raising,
)


CONSOLE_CONNECTION_MODEL_NAMES = (
    "CreateInstanceConsoleConnectionDetails",
    "UpdateInstanceConsoleConnectionDetails",
)


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(
        monkeypatch,
        model_names=CONSOLE_CONNECTION_MODEL_NAMES,
    )


def make_console_connection_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciInstanceConsoleConnectionModule",
        params,
        client=client,
    )


def test_main_exposes_expected_arguments(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_instance_console_connection")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        return DummyModule({})

    class FakeConsoleConnectionModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(
        module_obj,
        "OciInstanceConsoleConnectionModule",
        FakeConsoleConnectionModule,
    )

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["argument_spec"]["instance_id"] == {"type": "str"}
    assert captured["argument_spec"]["compartment_id"] == {"type": "str"}
    assert captured["argument_spec"]["public_key"] == {"type": "str"}
    assert captured["argument_spec"]["freeform_tags"] == {"type": "dict"}
    # This resource has no display_name in the OCI API, so the shared
    # name-lookup argument group must not be exposed.
    assert "name" not in captured["argument_spec"]
    assert "allow_duplicate_name" not in captured["argument_spec"]


def test_build_create_console_connection_details_includes_supported_fields(monkeypatch):
    install_fake_oci(monkeypatch)

    console_connection_module = load_collection_module(
        "oci_instance_console_connection"
    )
    details = console_connection_module.build_create_console_connection_details(
        {
            "instance_id": "ocid1.instance.oc1..example",
            "public_key": "ssh-rsa AAAA",
            "freeform_tags": {"env": "dev"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        }
    )

    assert isinstance(details, FakeModel)
    assert details.instance_id == "ocid1.instance.oc1..example"
    assert details.public_key == "ssh-rsa AAAA"
    assert details.freeform_tags == {"env": "dev"}
    assert details.defined_tags == {"Operations": {"CostCenter": "42"}}
    assert not hasattr(details, "compartment_id")


def test_needs_update_rejects_instance_id_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    console_connection_module = load_collection_module(
        "oci_instance_console_connection"
    )
    instance = make_console_connection_module(
        console_connection_module,
        {"instance_id": "ocid1.instance.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.instanceconsoleconnection.oc1..example",
        instance_id="ocid1.instance.oc1..current",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "instance_id" in exc_info.value.payload["msg"]


def test_needs_update_returns_true_for_freeform_tags_change(monkeypatch):
    install_fake_oci(monkeypatch)

    console_connection_module = load_collection_module(
        "oci_instance_console_connection"
    )
    instance = make_console_connection_module(
        console_connection_module,
        {"freeform_tags": {"role": "sre-runbook"}},
    )
    resource = FakeModel(
        id="ocid1.instanceconsoleconnection.oc1..example",
        freeform_tags={"role": "old"},
    )

    assert instance.needs_update(resource) is True


def test_create_resource_uses_create_console_connection_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    console_connection_module = load_collection_module(
        "oci_instance_console_connection"
    )
    create_calls = []
    response = FakeResponse(
        data=FakeModel(id="ocid1.instanceconsoleconnection.oc1..example"),
    )

    def create_instance_console_connection(create_instance_console_connection_details):
        create_calls.append(create_instance_console_connection_details)
        return response

    instance = make_console_connection_module(
        console_connection_module,
        {
            "instance_id": "ocid1.instance.oc1..example",
            "public_key": "ssh-rsa AAAA",
            "wait": True,
        },
        client=types.SimpleNamespace(
            create_instance_console_connection=create_instance_console_connection
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: FakeModel(
            id=resource_id,
            lifecycle_state="ACTIVE",
        ),
    )

    resource = instance.create_resource()

    assert create_calls[0].instance_id == "ocid1.instance.oc1..example"
    assert create_calls[0].public_key == "ssh-rsa AAAA"
    assert resource.id == "ocid1.instanceconsoleconnection.oc1..example"
    assert resource.lifecycle_state == "ACTIVE"


def test_delete_resource_deletes_console_connection(monkeypatch):
    install_fake_oci(monkeypatch)

    console_connection_module = load_collection_module(
        "oci_instance_console_connection"
    )
    delete_calls = []
    response = FakeResponse(data=None)

    def delete_instance_console_connection(instance_console_connection_id):
        delete_calls.append(instance_console_connection_id)
        return response

    resource = FakeModel(id="ocid1.instanceconsoleconnection.oc1..example")
    instance = make_console_connection_module(
        console_connection_module,
        {"wait": True},
        client=types.SimpleNamespace(
            delete_instance_console_connection=delete_instance_console_connection
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: None,
    )

    instance.delete_resource(resource)

    assert delete_calls == ["ocid1.instanceconsoleconnection.oc1..example"]


def test_resolve_target_resource_prefers_explicit_id(monkeypatch):
    install_fake_oci(monkeypatch)

    console_connection_module = load_collection_module(
        "oci_instance_console_connection"
    )
    instance = make_console_connection_module(
        console_connection_module,
        {"instance_console_connection_id": "ocid1.instanceconsoleconnection.oc1..example"},
    )
    monkeypatch.setattr(
        instance,
        "get_resource_by_id",
        lambda resource_id: FakeModel(id=resource_id, lifecycle_state="ACTIVE"),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        raising(AssertionError("list_all_resources should not be called")),
    )

    resource = instance.resolve_target_resource()

    assert resource.id == "ocid1.instanceconsoleconnection.oc1..example"


def test_resolve_target_resource_finds_active_connection_by_instance(monkeypatch):
    install_fake_oci(monkeypatch)

    console_connection_module = load_collection_module(
        "oci_instance_console_connection"
    )
    instance = make_console_connection_module(
        console_connection_module,
        {
            "instance_id": "ocid1.instance.oc1..example",
            "compartment_id": "ocid1.compartment.oc1..example",
        },
        client=types.SimpleNamespace(list_instance_console_connections="list_method"),
    )
    active_connection = FakeModel(
        id="ocid1.instanceconsoleconnection.oc1..active",
        lifecycle_state="ACTIVE",
    )
    deleted_connection = FakeModel(
        id="ocid1.instanceconsoleconnection.oc1..deleted",
        lifecycle_state="DELETED",
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: [deleted_connection, active_connection],
    )

    resource = instance.resolve_target_resource()

    assert resource is active_connection


def test_resolve_target_resource_returns_none_without_instance_or_compartment(monkeypatch):
    install_fake_oci(monkeypatch)

    console_connection_module = load_collection_module(
        "oci_instance_console_connection"
    )
    instance = make_console_connection_module(console_connection_module, {})

    assert instance.resolve_target_resource() is None


def test_resolve_target_resource_fails_on_multiple_active_connections(monkeypatch):
    install_fake_oci(monkeypatch)

    console_connection_module = load_collection_module(
        "oci_instance_console_connection"
    )
    instance = make_console_connection_module(
        console_connection_module,
        {
            "instance_id": "ocid1.instance.oc1..example",
            "compartment_id": "ocid1.compartment.oc1..example",
        },
        client=types.SimpleNamespace(list_instance_console_connections="list_method"),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: [
            FakeModel(id="ocid1.instanceconsoleconnection.oc1..one", lifecycle_state="ACTIVE"),
            FakeModel(id="ocid1.instanceconsoleconnection.oc1..two", lifecycle_state="ACTIVE"),
        ],
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.resolve_target_resource()

    assert "instance_id" in exc_info.value.payload["msg"]


def test_validate_delete_request_allows_explicit_id(monkeypatch):
    install_fake_oci(monkeypatch)

    console_connection_module = load_collection_module(
        "oci_instance_console_connection"
    )
    instance = make_console_connection_module(
        console_connection_module,
        {"instance_console_connection_id": "ocid1.instanceconsoleconnection.oc1..example"},
    )

    instance.validate_delete_request()


def test_validate_delete_request_allows_instance_and_compartment(monkeypatch):
    install_fake_oci(monkeypatch)

    console_connection_module = load_collection_module(
        "oci_instance_console_connection"
    )
    instance = make_console_connection_module(
        console_connection_module,
        {
            "instance_id": "ocid1.instance.oc1..example",
            "compartment_id": "ocid1.compartment.oc1..example",
        },
    )

    instance.validate_delete_request()


def test_validate_delete_request_fails_without_enough_scope(monkeypatch):
    install_fake_oci(monkeypatch)

    console_connection_module = load_collection_module(
        "oci_instance_console_connection"
    )
    instance = make_console_connection_module(
        console_connection_module,
        {"instance_id": "ocid1.instance.oc1..example"},
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_delete_request()

    assert "instance_console_connection_id" in exc_info.value.payload["msg"]
