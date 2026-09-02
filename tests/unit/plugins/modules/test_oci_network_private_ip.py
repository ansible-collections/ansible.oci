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


PRIVATE_IP_MODEL_NAMES = (
    "CreatePrivateIpDetails",
    "UpdatePrivateIpDetails",
)


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(
        monkeypatch,
        model_names=PRIVATE_IP_MODEL_NAMES,
    )


def make_private_ip_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciNetworkPrivateIpModule",
        params,
        client=client,
    )


def test_main_exposes_private_ip_arguments_without_waiters(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_private_ip")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule({})

    class FakePrivateIpModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciNetworkPrivateIpModule", FakePrivateIpModule)

    module_obj.main()

    argument_spec = captured["argument_spec"]
    assert captured["run_called"] is True
    assert captured["supports_check_mode"] is True
    assert argument_spec["private_ip_id"] == {"type": "str"}
    assert argument_spec["cidr_prefix_length"] == {"type": "int"}
    assert argument_spec["lifetime"]["choices"] == ["ephemeral", "reserved"]
    assert captured["mutually_exclusive"] == [
        ("vnic_id", "vlan_id", "subnet_id")
    ]
    assert "wait" not in argument_spec
    assert "compartment_id" not in argument_spec


def test_build_create_details_includes_and_normalizes_supported_fields(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_private_ip")

    details = module_obj.build_create_private_ip_details(
        {
            "name": "application-private-ip",
            "ip_address": "10.0.1.20",
            "cidr_prefix_length": 28,
            "vnic_id": "ocid1.vnic.oc1..example",
            "ipv4_subnet_cidr_at_creation": "10.0.0.0/16",
            "hostname_label": "application",
            "lifetime": "reserved",
            "route_table_id": "ocid1.routetable.oc1..example",
            "freeform_tags": {"phase": "create"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        }
    )

    assert details.display_name == "application-private-ip"
    assert details.ip_address == "10.0.1.20"
    assert details.cidr_prefix_length == 28
    assert details.vnic_id == "ocid1.vnic.oc1..example"
    assert details.ipv4_subnet_cidr_at_creation == "10.0.0.0/16"
    assert details.hostname_label == "application"
    assert details.lifetime == "RESERVED"
    assert details.route_table_id == "ocid1.routetable.oc1..example"
    assert details.freeform_tags == {"phase": "create"}
    assert details.defined_tags == {"Operations": {"CostCenter": "42"}}


@pytest.mark.parametrize("scope_field", ["vnic_id", "vlan_id", "subnet_id"])
def test_name_lookup_uses_one_scope_and_ignores_primary_ips(
    monkeypatch, scope_field
):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_private_ip")
    list_method = object()
    list_calls = []
    instance = make_private_ip_module(
        module_obj,
        {
            "name": "application-private-ip",
            scope_field: f"ocid1.{scope_field}.oc1..example",
        },
        client=types.SimpleNamespace(list_private_ips=list_method),
    )

    def list_all_resources(method, **kwargs):
        list_calls.append((method, kwargs))
        return [
            FakeModel(
                id="primary",
                display_name="application-private-ip",
                is_primary=True,
            ),
            FakeModel(
                id="secondary",
                display_name="application-private-ip",
                is_primary=False,
            ),
            FakeModel(id="other", display_name="other", is_primary=False),
        ]

    monkeypatch.setattr(instance, "list_all_resources", list_all_resources)

    matches = instance.find_resources_by_name()

    assert [resource.id for resource in matches] == ["secondary"]
    assert list_calls == [
        (
            list_method,
            {scope_field: f"ocid1.{scope_field}.oc1..example"},
        )
    ]


@pytest.mark.parametrize(
    "params",
    [
        {"name": "application-private-ip"},
        {
            "name": "application-private-ip",
            "vnic_id": "ocid1.vnic.oc1..example",
            "subnet_id": "ocid1.subnet.oc1..example",
        },
    ],
)
def test_create_requires_exactly_one_scope(monkeypatch, params):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_private_ip")
    instance = make_private_ip_module(module_obj, params)

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "exactly one" in exc_info.value.payload["msg"]


def test_create_requires_name(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_private_ip")
    instance = make_private_ip_module(
        module_obj,
        {"vnic_id": "ocid1.vnic.oc1..example"},
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "name" in exc_info.value.payload["msg"]


def test_explicit_primary_private_ip_is_rejected(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_private_ip")
    instance = make_private_ip_module(
        module_obj,
        {"private_ip_id": "ocid1.privateip.oc1..primary"},
    )
    monkeypatch.setattr(
        instance,
        "get_resource_by_id",
        lambda resource_id: FakeModel(id=resource_id, is_primary=True),
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.resolve_target_resource()

    assert "only secondary private IPs" in exc_info.value.payload["msg"]


def test_update_plan_maps_mutable_fields_and_normalizes_lifetime(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_private_ip")
    instance = make_private_ip_module(
        module_obj,
        {
            "name": "updated-private-ip",
            "hostname_label": "updated",
            "vnic_id": "ocid1.vnic.oc1..updated",
            "lifetime": "reserved",
            "route_table_id": "ocid1.routetable.oc1..updated",
            "freeform_tags": {"phase": "update"},
        },
    )
    current = FakeModel(
        id="ocid1.privateip.oc1..example",
        display_name="original-private-ip",
        hostname_label="original",
        vnic_id="ocid1.vnic.oc1..original",
        lifetime="EPHEMERAL",
        route_table_id=None,
        freeform_tags={"phase": "create"},
    )

    update_plan = instance.build_update_plan(current)
    details = instance.build_update_details(update_plan["update_model_fields"])

    assert update_plan["update_needed"] is True
    assert details.display_name == "updated-private-ip"
    assert details.hostname_label == "updated"
    assert details.vnic_id == "ocid1.vnic.oc1..updated"
    assert details.lifetime == "RESERVED"
    assert details.route_table_id == "ocid1.routetable.oc1..updated"
    assert details.freeform_tags == {"phase": "update"}


def test_lifetime_comparison_is_case_insensitive(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_private_ip")
    instance = make_private_ip_module(module_obj, {"lifetime": "ephemeral"})

    assert instance.needs_update(FakeModel(lifetime="EPHEMERAL")) is False


@pytest.mark.parametrize(
    "field,current,desired",
    [
        ("ip_address", "10.0.1.20", "10.0.1.21"),
        ("cidr_prefix_length", 28, 27),
        ("vlan_id", "ocid1.vlan.oc1..current", "ocid1.vlan.oc1..desired"),
        ("subnet_id", "ocid1.subnet.oc1..current", "ocid1.subnet.oc1..desired"),
        ("ipv4_subnet_cidr_at_creation", "10.0.0.0/16", "10.1.0.0/16"),
    ],
)
def test_update_rejects_immutable_fields(monkeypatch, field, current, desired):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_private_ip")
    instance = make_private_ip_module(module_obj, {field: desired})

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(FakeModel(**{field: current}))

    assert field in exc_info.value.payload["msg"]


def test_synchronous_crud_calls_use_private_ip_sdk_models(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_private_ip")
    calls = []

    def get_private_ip(**kwargs):
        calls.append(("get", kwargs))
        return FakeResponse(data=FakeModel(id=kwargs["private_ip_id"]))

    def create_private_ip(**kwargs):
        calls.append(("create", kwargs))
        return FakeResponse(
            data=FakeModel(
                id="ocid1.privateip.oc1..example",
                display_name=kwargs["create_private_ip_details"].display_name,
            )
        )

    def update_private_ip(**kwargs):
        calls.append(("update", kwargs))
        return FakeResponse(
            data=FakeModel(
                id=kwargs["private_ip_id"],
                display_name=kwargs["update_private_ip_details"].display_name,
            )
        )

    def delete_private_ip(**kwargs):
        calls.append(("delete", kwargs))
        return FakeResponse(data=None)

    client = types.SimpleNamespace(
        get_private_ip=get_private_ip,
        create_private_ip=create_private_ip,
        update_private_ip=update_private_ip,
        delete_private_ip=delete_private_ip,
    )
    instance = make_private_ip_module(
        module_obj,
        {
            "name": "application-private-ip",
            "vnic_id": "ocid1.vnic.oc1..example",
        },
        client=client,
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    response = instance.get_resource_response("ocid1.privateip.oc1..example")
    created = instance.create_resource()
    current = FakeModel(
        id=created.id,
        display_name="original-private-ip",
        vnic_id="ocid1.vnic.oc1..example",
    )
    updated = instance.update_resource(current)
    deleted = instance.delete_resource(updated)

    assert response.data.id == "ocid1.privateip.oc1..example"
    assert created.display_name == "application-private-ip"
    assert updated.display_name == "application-private-ip"
    assert deleted is None
    assert calls[0] == (
        "get",
        {"private_ip_id": "ocid1.privateip.oc1..example"},
    )
    assert calls[1][0] == "create"
    assert calls[2][0] == "update"
    assert calls[2][1]["private_ip_id"] == created.id
    assert calls[3] == (
        "delete",
        {"private_ip_id": "ocid1.privateip.oc1..example"},
    )
