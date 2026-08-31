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


NETWORK_SECURITY_GROUP_MODEL_NAMES = (
    "CreateNetworkSecurityGroupDetails",
    "UpdateNetworkSecurityGroupDetails",
)


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(
        monkeypatch,
        model_names=NETWORK_SECURITY_GROUP_MODEL_NAMES,
    )


def make_network_security_group_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciNetworkSecurityGroupModule",
        params,
        client=client,
    )


def test_main_exposes_full_network_security_group_arguments(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_security_group")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule({})

    class FakeNetworkSecurityGroupModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(
        module_obj,
        "OciNetworkSecurityGroupModule",
        FakeNetworkSecurityGroupModule,
    )

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["supports_check_mode"] is True
    assert captured["argument_spec"]["network_security_group_id"] == {"type": "str"}
    assert captured["argument_spec"]["vcn_id"] == {"type": "str"}


def test_build_create_details_includes_supported_fields(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_security_group")

    details = module_obj.build_create_network_security_group_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-network-security-group",
            "freeform_tags": {"environment": "test"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        }
    )

    assert details.compartment_id == "ocid1.compartment.oc1..example"
    assert details.vcn_id == "ocid1.vcn.oc1..example"
    assert details.display_name == "example-network-security-group"
    assert details.freeform_tags == {"environment": "test"}
    assert details.defined_tags == {"Operations": {"CostCenter": "42"}}


def test_get_resource_response_uses_full_id_kwarg(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_security_group")
    get_calls = []

    def get_network_security_group(**kwargs):
        get_calls.append(kwargs)
        return FakeResponse(data=FakeModel(id=kwargs["network_security_group_id"]))

    instance = make_network_security_group_module(
        module_obj,
        {},
        client=types.SimpleNamespace(
            get_network_security_group=get_network_security_group
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    resource = instance.get_resource_response(
        "ocid1.networksecuritygroup.oc1..example"
    ).data

    assert resource.id == "ocid1.networksecuritygroup.oc1..example"
    assert get_calls == [
        {"network_security_group_id": "ocid1.networksecuritygroup.oc1..example"}
    ]


def test_create_resource_uses_shared_wait_path(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_security_group")
    create_calls = []

    def create_network_security_group(**kwargs):
        create_calls.append(kwargs)
        return FakeResponse(
            data=FakeModel(id="ocid1.networksecuritygroup.oc1..example")
        )

    instance = make_network_security_group_module(
        module_obj,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-network-security-group",
            "wait": True,
        },
        client=types.SimpleNamespace(
            create_network_security_group=create_network_security_group
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states: FakeModel(
            id=resource_id,
            lifecycle_state="AVAILABLE",
        ),
    )

    resource = instance.create_resource()

    assert resource.lifecycle_state == "AVAILABLE"
    assert create_calls[0][
        "create_network_security_group_details"
    ].display_name == "example-network-security-group"


def test_update_resource_uses_shared_update_planner_and_waiter(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_security_group")
    update_calls = []

    def update_network_security_group(**kwargs):
        update_calls.append(kwargs)
        return FakeResponse(
            data=FakeModel(id=kwargs["network_security_group_id"])
        )

    instance = make_network_security_group_module(
        module_obj,
        {
            "name": "updated-network-security-group",
            "freeform_tags": {"phase": "update"},
            "wait": True,
        },
        client=types.SimpleNamespace(
            update_network_security_group=update_network_security_group
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states: FakeModel(
            id=resource_id,
            display_name="updated-network-security-group",
            freeform_tags={"phase": "update"},
            lifecycle_state="AVAILABLE",
        ),
    )
    current = FakeModel(
        id="ocid1.networksecuritygroup.oc1..example",
        display_name="original-network-security-group",
        freeform_tags={"phase": "create"},
    )

    resource = instance.update_resource(current)

    assert resource.display_name == "updated-network-security-group"
    assert update_calls[0]["network_security_group_id"] == current.id
    details = update_calls[0]["update_network_security_group_details"]
    assert details.display_name == "updated-network-security-group"
    assert details.freeform_tags == {"phase": "update"}


@pytest.mark.parametrize(
    "field,current,desired",
    [
        ("vcn_id", "ocid1.vcn.oc1..current", "ocid1.vcn.oc1..desired"),
        (
            "compartment_id",
            "ocid1.compartment.oc1..current",
            "ocid1.compartment.oc1..desired",
        ),
    ],
)
def test_needs_update_rejects_immutable_scope(
    monkeypatch, field, current, desired
):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_security_group")
    instance = make_network_security_group_module(module_obj, {field: desired})

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(
            FakeModel(
                id="ocid1.networksecuritygroup.oc1..example",
                **{field: current},
            )
        )

    assert field in exc_info.value.payload["msg"]


def test_delete_resource_uses_full_id_kwarg(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_security_group")
    delete_calls = []

    def delete_network_security_group(**kwargs):
        delete_calls.append(kwargs)
        return FakeResponse(data=None)

    instance = make_network_security_group_module(
        module_obj,
        {"wait": False},
        client=types.SimpleNamespace(
            delete_network_security_group=delete_network_security_group
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    instance.delete_resource(FakeModel(id="ocid1.networksecuritygroup.oc1..example"))

    assert delete_calls == [
        {"network_security_group_id": "ocid1.networksecuritygroup.oc1..example"}
    ]
