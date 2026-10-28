from __future__ import absolute_import, division, print_function

__metaclass__ = type

import types

import pytest

from .conftest import (
    FailJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)

MODEL_NAMES = ("CreateNetworkFirewallDetails", "UpdateNetworkFirewallDetails")


def install_fake_oci(monkeypatch):
    """Install isolated OCI types for this test."""
    return shared_install_fake_oci(monkeypatch, model_names=MODEL_NAMES)


def attach_firewall_sdk(module):
    """Attach the service models used by the test."""
    module.oci.network_firewall = types.SimpleNamespace(
        models=types.SimpleNamespace(
            CreateNetworkFirewallDetails=FakeModel,
            UpdateNetworkFirewallDetails=FakeModel,
        ),
        NetworkFirewallClient=object,
    )


def make_firewall(module_obj, params, client=None):
    """Return a module instance without OCI authentication."""
    return make_module_instance(
        module_obj, "OciNetworkFirewallModule", params, client=client
    )


def test_build_create_details(monkeypatch):
    """Verify build create details."""
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_firewall")
    attach_firewall_sdk(module)
    details = module.build_create_network_firewall_details(
        {
            "compartment_id": "c",
            "subnet_id": "s",
            "network_firewall_policy_id": "p",
            "name": "f",
            "network_security_group_ids": ["n2", "n1"],
        }
    )
    assert details.display_name == "f"
    assert details.network_security_group_ids == ["n2", "n1"]


def test_named_lookup_hydrates_full_firewall(monkeypatch):
    """Verify named lookup hydrates full firewall."""
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_firewall")
    attach_firewall_sdk(module)
    instance = make_firewall(
        module,
        {},
        types.SimpleNamespace(
            get_network_firewall=lambda **kw: FakeResponse(
                data=FakeModel(
                    id=kw["network_firewall_id"], network_security_group_ids=["n"]
                )
            )
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kw: fn(**kw))
    assert instance.hydrate_named_resource(
        FakeModel(id="f")
    ).network_security_group_ids == ["n"]


def test_nsg_order_does_not_trigger_update(monkeypatch):
    """Verify nsg order does not trigger update."""
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_firewall")
    attach_firewall_sdk(module)
    instance = make_firewall(module, {"network_security_group_ids": ["n2", "n1"]})
    assert (
        instance.needs_update(
            FakeModel(id="f", network_security_group_ids=["n1", "n2"])
        )
        is False
    )


def test_immutable_subnet_fails(monkeypatch):
    """Verify immutable subnet fails."""
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_firewall")
    attach_firewall_sdk(module)
    instance = make_firewall(module, {"subnet_id": "s2"})
    try:
        instance.needs_update(FakeModel(id="f", subnet_id="s1"))
    except Exception as exc:
        assert "subnet_id" in str(getattr(exc, "payload", {}))
    else:
        raise AssertionError("expected immutable field failure")


def test_create_without_wait_returns_immediate_resource(monkeypatch):
    """Return the SDK create response when waiting is disabled."""
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_firewall")
    attach_firewall_sdk(module)
    instance = make_firewall(
        module,
        {
            "compartment_id": "c",
            "subnet_id": "s",
            "network_firewall_policy_id": "p",
            "name": "f",
            "wait": False,
        },
        types.SimpleNamespace(
            create_network_firewall=lambda **kwargs: FakeResponse(
                data=FakeModel(id="f")
            )
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kw: fn(**kw))
    assert instance.create_resource().id == "f"


def test_update_waits_on_network_firewall_client_work_request(monkeypatch):
    """Use the Network Firewall client to wait for an asynchronous update."""
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_firewall")
    attach_firewall_sdk(module)
    waits = []
    client = types.SimpleNamespace(
        update_network_firewall=lambda **kwargs: FakeResponse(
            data=FakeModel(id="f"), headers={"opc-work-request-id": "wr"}
        ),
        get_network_firewall=lambda **kwargs: FakeResponse(
            data=FakeModel(id="f", display_name="new")
        ),
    )
    instance = make_firewall(module, {"name": "new", "wait": True}, client=client)
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kw: fn(**kw))
    monkeypatch.setattr(
        instance,
        "wait_for_work_request",
        lambda service, work_request_id: waits.append((service, work_request_id)),
    )
    assert (
        instance.update_resource(FakeModel(id="f", display_name="old")).display_name
        == "new"
    )
    assert waits == [(client, "wr")]


def test_create_requires_policy_and_subnet(monkeypatch):
    """Fail creation when required Network Firewall fields are absent."""
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_firewall")
    instance = make_firewall(module, {"compartment_id": "c", "name": "f"})
    with pytest.raises(FailJsonCalled) as error:
        instance.validate_create_request()
    assert "subnet_id" in error.value.payload["msg"]
