from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from .conftest import (
    DummyModule,
    FakeModel,
    FakeResponse,
    FailJsonCalled,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)


BASTION_MODEL_NAMES = (
    "CreateBastionDetails",
    "UpdateBastionDetails",
)


def install_fake_oci(monkeypatch):
    oci_module, service_error = shared_install_fake_oci(monkeypatch)
    oci_module.bastion = types.SimpleNamespace(
        BastionClient=type("FakeBastionClient", (), {}),
        models=types.SimpleNamespace(
            **{model_name: FakeModel for model_name in BASTION_MODEL_NAMES}
        ),
    )
    return oci_module, service_error


def make_bastion_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciBastionModule",
        params,
        client=client,
    )


def test_main_wires_argument_spec_and_runs_module(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_bastion")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        captured["supports_check_mode"] = kwargs.get("supports_check_mode")
        return DummyModule({})

    class FakeBastionModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciBastionModule", FakeBastionModule)

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["supports_check_mode"] is True
    # name/compartment_id come from the shared OCI_COMMON_ARGS.
    assert captured["argument_spec"]["name"] == {"type": "str"}
    assert captured["argument_spec"]["compartment_id"] == {"type": "str"}
    assert captured["argument_spec"]["allow_duplicate_name"] == {
        "type": "bool",
        "default": False,
    }
    # bastion-specific params.
    assert captured["argument_spec"]["bastion_id"] == {"type": "str"}
    assert captured["argument_spec"]["bastion_type"] == {
        "type": "str",
        "default": "standard",
    }
    assert captured["argument_spec"]["target_subnet_id"] == {"type": "str"}
    assert captured["argument_spec"]["client_cidr_block_allow_list"] == {
        "type": "list",
        "elements": "str",
    }
    assert captured["argument_spec"]["max_session_ttl_in_seconds"] == {"type": "int"}
    assert captured["argument_spec"]["dns_proxy_status"] == {
        "type": "str",
        "choices": ["ENABLED", "DISABLED"],
    }
    assert captured["argument_spec"]["security_attributes"] == {"type": "dict"}
    assert "display_name" not in captured["argument_spec"]


def test_class_metadata_resolves_name_against_name_field(monkeypatch):
    install_fake_oci(monkeypatch)

    bastion_module = load_collection_module("oci_bastion")

    assert bastion_module.OciBastionModule.resource_id_param == "bastion_id"
    assert bastion_module.OciBastionModule.list_resource_method == "list_bastions"
    assert bastion_module.OciBastionModule.name_response_field == "name"
    assert bastion_module.OciBastionModule.update_method_name == "update_bastion"
    assert bastion_module.OciBastionModule.update_details_name == "update_bastion_details"
    assert bastion_module.OciBastionModule.create_resource_name == "bastion"


def test_build_create_bastion_details_maps_name_and_fields(monkeypatch):
    install_fake_oci(monkeypatch)

    bastion_module = load_collection_module("oci_bastion")
    details = bastion_module.build_create_bastion_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-bastion",
            "bastion_type": "standard",
            "target_subnet_id": "ocid1.subnet.oc1..example",
            "client_cidr_block_allow_list": ["0.0.0.0/0"],
            "max_session_ttl_in_seconds": 1800,
            "phone_book_entry": "team-entry",
            "static_jump_host_ip_addresses": ["10.0.1.5"],
            "dns_proxy_status": "ENABLED",
            "security_attributes": {"ns": {"level": "high"}},
            "freeform_tags": {"env": "dev"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        }
    )

    assert isinstance(details, FakeModel)
    # The bastion model uses ``name`` directly, never ``display_name``.
    assert details.name == "example-bastion"
    assert not hasattr(details, "display_name")
    assert details.compartment_id == "ocid1.compartment.oc1..example"
    assert details.bastion_type == "standard"
    assert details.target_subnet_id == "ocid1.subnet.oc1..example"
    assert details.client_cidr_block_allow_list == ["0.0.0.0/0"]
    assert details.max_session_ttl_in_seconds == 1800
    assert details.phone_book_entry == "team-entry"
    assert details.static_jump_host_ip_addresses == ["10.0.1.5"]
    assert details.dns_proxy_status == "ENABLED"
    assert details.security_attributes == {"ns": {"level": "high"}}
    assert details.freeform_tags == {"env": "dev"}
    assert details.defined_tags == {"Operations": {"CostCenter": "42"}}


def test_build_create_bastion_details_omits_unset_values(monkeypatch):
    install_fake_oci(monkeypatch)

    bastion_module = load_collection_module("oci_bastion")
    details = bastion_module.build_create_bastion_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-bastion",
            "bastion_type": "standard",
            "target_subnet_id": "ocid1.subnet.oc1..example",
            "client_cidr_block_allow_list": None,
            "max_session_ttl_in_seconds": None,
            "phone_book_entry": None,
            "static_jump_host_ip_addresses": None,
            "dns_proxy_status": None,
            "security_attributes": None,
            "freeform_tags": None,
            "defined_tags": None,
        }
    )

    assert not hasattr(details, "max_session_ttl_in_seconds")
    assert not hasattr(details, "dns_proxy_status")
    assert not hasattr(details, "freeform_tags")


def test_needs_update_returns_true_for_max_session_ttl_change(monkeypatch):
    install_fake_oci(monkeypatch)

    bastion_module = load_collection_module("oci_bastion")
    instance = make_bastion_module(
        bastion_module,
        {"max_session_ttl_in_seconds": 3600},
    )
    resource = FakeModel(
        id="ocid1.bastion.oc1..example",
        max_session_ttl_in_seconds=1800,
    )

    assert instance.needs_update(resource) is True


def test_needs_update_ignores_client_cidr_order(monkeypatch):
    install_fake_oci(monkeypatch)

    bastion_module = load_collection_module("oci_bastion")
    instance = make_bastion_module(
        bastion_module,
        {"client_cidr_block_allow_list": ["10.0.0.0/8", "192.168.0.0/16"]},
    )
    resource = FakeModel(
        id="ocid1.bastion.oc1..example",
        client_cidr_block_allow_list=["192.168.0.0/16", "10.0.0.0/8"],
    )

    assert instance.needs_update(resource) is False


def test_needs_update_returns_true_for_client_cidr_content_change(monkeypatch):
    install_fake_oci(monkeypatch)

    bastion_module = load_collection_module("oci_bastion")
    instance = make_bastion_module(
        bastion_module,
        {"client_cidr_block_allow_list": ["10.0.0.0/8", "172.16.0.0/12"]},
    )
    resource = FakeModel(
        id="ocid1.bastion.oc1..example",
        client_cidr_block_allow_list=["10.0.0.0/8", "192.168.0.0/16"],
    )

    assert instance.needs_update(resource) is True


def test_needs_update_returns_true_for_security_attributes_change(monkeypatch):
    install_fake_oci(monkeypatch)

    bastion_module = load_collection_module("oci_bastion")
    instance = make_bastion_module(
        bastion_module,
        {"security_attributes": {"ns": {"level": "high"}}},
    )
    resource = FakeModel(
        id="ocid1.bastion.oc1..example",
        security_attributes={"ns": {"level": "low"}},
    )

    assert instance.needs_update(resource) is True


@pytest.mark.parametrize(
    "params, resource_attrs, expected_field",
    [
        (
            {"name": "renamed-bastion"},
            {"name": "example-bastion"},
            "name",
        ),
        (
            {"target_subnet_id": "ocid1.subnet.oc1..other"},
            {"target_subnet_id": "ocid1.subnet.oc1..example"},
            "target_subnet_id",
        ),
        (
            {"compartment_id": "ocid1.compartment.oc1..other"},
            {"compartment_id": "ocid1.compartment.oc1..example"},
            "compartment_id",
        ),
        (
            {"dns_proxy_status": "ENABLED"},
            {"dns_proxy_status": "DISABLED"},
            "dns_proxy_status",
        ),
    ],
)
def test_needs_update_rejects_immutable_field_drift(
    monkeypatch, params, resource_attrs, expected_field
):
    install_fake_oci(monkeypatch)

    bastion_module = load_collection_module("oci_bastion")
    instance = make_bastion_module(bastion_module, params)
    resource = FakeModel(id="ocid1.bastion.oc1..example", **resource_attrs)

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert expected_field in exc_info.value.payload["msg"]


def test_create_resource_uses_create_bastion_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    bastion_module = load_collection_module("oci_bastion")
    create_calls = []
    response = FakeResponse(
        data=FakeModel(id="ocid1.bastion.oc1..example"),
    )

    def create_bastion(create_bastion_details):
        create_calls.append(create_bastion_details)
        return response

    instance = make_bastion_module(
        bastion_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-bastion",
            "bastion_type": "standard",
            "target_subnet_id": "ocid1.subnet.oc1..example",
            "client_cidr_block_allow_list": ["0.0.0.0/0"],
            "max_session_ttl_in_seconds": 1800,
            "wait": True,
        },
        client=types.SimpleNamespace(create_bastion=create_bastion),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: FakeModel(
            id=resource_id,
            lifecycle_state="ACTIVE",
        ),
    )

    resource = instance.create_resource()

    assert create_calls[0].name == "example-bastion"
    assert create_calls[0].target_subnet_id == "ocid1.subnet.oc1..example"
    assert create_calls[0].client_cidr_block_allow_list == ["0.0.0.0/0"]
    assert resource.id == "ocid1.bastion.oc1..example"
    assert resource.lifecycle_state == "ACTIVE"


def test_update_resource_uses_update_bastion_details_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    bastion_module = load_collection_module("oci_bastion")
    update_calls = []
    response = FakeResponse(
        data=FakeModel(id="ocid1.bastion.oc1..example"),
    )

    def update_bastion(bastion_id, update_bastion_details):
        update_calls.append((bastion_id, update_bastion_details))
        return response

    resource = FakeModel(id="ocid1.bastion.oc1..example")
    instance = make_bastion_module(
        bastion_module,
        {
            "max_session_ttl_in_seconds": 3600,
            "freeform_tags": {"env": "prod"},
            "wait": True,
        },
        client=types.SimpleNamespace(update_bastion=update_bastion),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: FakeModel(
            id=resource_id,
            lifecycle_state="ACTIVE",
        ),
    )

    updated_resource = instance.update_resource(resource)

    assert update_calls[0][0] == "ocid1.bastion.oc1..example"
    assert update_calls[0][1].max_session_ttl_in_seconds == 3600
    assert update_calls[0][1].freeform_tags == {"env": "prod"}
    assert updated_resource.id == "ocid1.bastion.oc1..example"


def test_delete_resource_calls_delete_bastion(monkeypatch):
    install_fake_oci(monkeypatch)

    bastion_module = load_collection_module("oci_bastion")
    delete_calls = []
    response = FakeResponse(data=FakeModel(id="ocid1.bastion.oc1..example"))

    def delete_bastion(bastion_id):
        delete_calls.append(bastion_id)
        return response

    resource = FakeModel(id="ocid1.bastion.oc1..example")
    instance = make_bastion_module(
        bastion_module,
        {"wait": True},
        client=types.SimpleNamespace(delete_bastion=delete_bastion),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: None,
    )

    instance.delete_resource(resource)

    assert delete_calls == ["ocid1.bastion.oc1..example"]
