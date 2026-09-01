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


VNIC_ATTACHMENT_MODEL_NAMES = (
    "AttachVnicDetails",
    "CreateVnicDetails",
    "Ipv6AddressIpv6SubnetCidrPairDetails",
)


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(
        monkeypatch,
        model_names=VNIC_ATTACHMENT_MODEL_NAMES,
    )


def make_vnic_attachment_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciVnicAttachmentModule",
        params,
        client=client,
    )


def test_main_exposes_expected_arguments(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_vnic_attachment")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule({})

    class FakeVnicAttachmentModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(
        module_obj,
        "OciVnicAttachmentModule",
        FakeVnicAttachmentModule,
    )

    module_obj.main()

    assert captured["run_called"] is True
    spec = captured["argument_spec"]
    assert spec["vnic_attachment_id"] == {"type": "str"}
    assert spec["instance_id"] == {"type": "str"}
    assert spec["nic_index"] == {"type": "int"}
    vnic_options = spec["create_vnic_details"]["options"]
    assert vnic_options["subnet_id"] == {"type": "str"}
    assert vnic_options["vlan_id"] == {"type": "str"}
    assert vnic_options["nsg_ids"] == {"type": "list", "elements": "str"}
    ipv6_options = vnic_options[
        "ipv6_address_ipv6_subnet_cidr_pair_details"
    ]["options"]
    assert set(ipv6_options) == {"ipv6_id", "ipv6_subnet_cidr", "ipv6_address"}


def test_build_attach_vnic_details_builds_nested_sdk_models(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_vnic_attachment")

    details = module_obj.build_attach_vnic_details(
        {
            "name": "example-attachment",
            "instance_id": "ocid1.instance.oc1..example",
            "nic_index": 1,
            "create_vnic_details": {
                "subnet_id": "ocid1.subnet.oc1..example",
                "display_name": "example-vnic",
                "assign_public_ip": False,
                "nsg_ids": ["ocid1.networksecuritygroup.oc1..example"],
                "ipv6_address_ipv6_subnet_cidr_pair_details": [
                    {
                        "ipv6_id": "ocid1.ipv6.oc1..example",
                        "ipv6_subnet_cidr": None,
                        "ipv6_address": None,
                    }
                ],
                "private_ip": None,
            },
        }
    )

    assert isinstance(details, FakeModel)
    assert details.display_name == "example-attachment"
    assert details.instance_id == "ocid1.instance.oc1..example"
    assert details.nic_index == 1
    assert isinstance(details.create_vnic_details, FakeModel)
    assert details.create_vnic_details.display_name == "example-vnic"
    assert details.create_vnic_details.assign_public_ip is False
    ipv6_pair = details.create_vnic_details.ipv6_address_ipv6_subnet_cidr_pair_details[0]
    assert isinstance(ipv6_pair, FakeModel)
    assert ipv6_pair.ipv6_id == "ocid1.ipv6.oc1..example"
    assert not hasattr(ipv6_pair, "ipv6_address")
    assert not hasattr(details.create_vnic_details, "private_ip")


@pytest.mark.parametrize(
    "details, expected_message",
    (
        ({}, "exactly one of subnet_id or vlan_id"),
        (
            {
                "subnet_id": "ocid1.subnet.oc1..example",
                "vlan_id": "ocid1.vlan.oc1..example",
            },
            "exactly one of subnet_id or vlan_id",
        ),
        (
            {
                "subnet_id": "ocid1.subnet.oc1..example",
                "private_ip": "10.0.0.10",
                "private_ip_id": "ocid1.privateip.oc1..example",
            },
            "mutually exclusive",
        ),
        (
            {
                "subnet_id": "ocid1.subnet.oc1..example",
                "hostname_label": "example",
                "assign_private_dns_record": False,
            },
            "assign_private_dns_record cannot be false",
        ),
        (
            {
                "vlan_id": "ocid1.vlan.oc1..example",
                "nsg_ids": ["ocid1.networksecuritygroup.oc1..example"],
                "assign_public_ip": True,
            },
            "vlan_id cannot be combined with",
        ),
    ),
)
def test_validate_create_vnic_details_rejects_invalid_combinations(
    monkeypatch, details, expected_message
):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_vnic_attachment")

    def fail_json(**kwargs):
        raise FailJsonCalled(kwargs)

    with pytest.raises(FailJsonCalled) as exc_info:
        module_obj.validate_create_vnic_details(details, fail_json)

    assert expected_message in exc_info.value.payload["msg"]


def test_validate_create_vnic_details_accepts_subnet_and_vlan_forms(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_vnic_attachment")

    for details in (
        {"subnet_id": "ocid1.subnet.oc1..example"},
        {"vlan_id": "ocid1.vlan.oc1..example", "assign_public_ip": False},
    ):
        module_obj.validate_create_vnic_details(
            details,
            lambda **kwargs: pytest.fail(kwargs["msg"]),
        )


def test_create_only_vnic_details_do_not_trigger_update(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_vnic_attachment")
    instance = make_vnic_attachment_module(
        module_obj,
        {
            "name": "example-attachment",
            "instance_id": "ocid1.instance.oc1..example",
            "create_vnic_details": {
                "subnet_id": "ocid1.subnet.oc1..different"
            },
        },
    )
    resource = FakeModel(
        display_name="example-attachment",
        instance_id="ocid1.instance.oc1..example",
        nic_index=0,
        subnet_id="ocid1.subnet.oc1..current",
    )

    assert instance.needs_update(resource) is False


@pytest.mark.parametrize(
    "params, field",
    (
        ({"name": "different"}, "name"),
        ({"instance_id": "ocid1.instance.oc1..different"}, "instance_id"),
        ({"nic_index": 1}, "nic_index"),
    ),
)
def test_attachment_identity_fields_are_immutable(monkeypatch, params, field):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_vnic_attachment")
    instance = make_vnic_attachment_module(module_obj, params)
    resource = FakeModel(
        display_name="example-attachment",
        instance_id="ocid1.instance.oc1..example",
        nic_index=0,
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert field in exc_info.value.payload["msg"]


def test_create_resource_attaches_and_waits_for_attached(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_vnic_attachment")
    attach_calls = []
    wait_calls = []

    def attach_vnic(attach_vnic_details):
        attach_calls.append(attach_vnic_details)
        return FakeResponse(
            data=FakeModel(id="ocid1.vnicattachment.oc1..example")
        )

    instance = make_vnic_attachment_module(
        module_obj,
        {
            "name": "example-attachment",
            "instance_id": "ocid1.instance.oc1..example",
            "create_vnic_details": {
                "subnet_id": "ocid1.subnet.oc1..example"
            },
            "wait": True,
        },
        client=types.SimpleNamespace(attach_vnic=attach_vnic),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states: wait_calls.append(
            (resource_id, target_states)
        )
        or FakeModel(id=resource_id, lifecycle_state="ATTACHED"),
    )

    resource = instance.create_resource()

    assert attach_calls[0].display_name == "example-attachment"
    assert wait_calls == [("ocid1.vnicattachment.oc1..example", ("ATTACHED",))]
    assert resource.lifecycle_state == "ATTACHED"


def test_delete_resource_detaches_and_uses_shared_dead_states(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_vnic_attachment")
    detach_calls = []
    wait_calls = []

    def detach_vnic(vnic_attachment_id):
        detach_calls.append(vnic_attachment_id)
        return FakeResponse(data=None)

    resource = FakeModel(id="ocid1.vnicattachment.oc1..example")
    instance = make_vnic_attachment_module(
        module_obj,
        {"wait": True},
        client=types.SimpleNamespace(detach_vnic=detach_vnic),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states: wait_calls.append(
            (resource_id, target_states)
        ),
    )

    instance.delete_resource(resource)

    assert detach_calls == ["ocid1.vnicattachment.oc1..example"]
    assert wait_calls == [
        ("ocid1.vnicattachment.oc1..example", ("DETACHED",))
    ]


def test_resolve_target_resource_treats_detached_as_absent(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_vnic_attachment")
    instance = make_vnic_attachment_module(
        module_obj,
        {"vnic_attachment_id": "ocid1.vnicattachment.oc1..example"},
    )
    monkeypatch.setattr(
        instance,
        "get_resource_by_id",
        lambda resource_id: FakeModel(
            id=resource_id,
            lifecycle_state="DETACHED",
        ),
    )

    assert instance.resolve_target_resource() is None


def test_create_required_fields_and_name_lookup_scope(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_vnic_attachment")
    instance = make_vnic_attachment_module(module_obj, {"name": "example"})

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()
    assert "compartment_id" in exc_info.value.payload["msg"]
    assert "instance_id" in exc_info.value.payload["msg"]
    assert "create_vnic_details" in exc_info.value.payload["msg"]

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_name_lookup_scope()
    assert "compartment_id" in exc_info.value.payload["msg"]
    assert "instance_id" in exc_info.value.payload["msg"]
