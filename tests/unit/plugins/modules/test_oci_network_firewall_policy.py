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

MODEL_NAMES = (
    "CreateNetworkFirewallPolicyDetails",
    "UpdateNetworkFirewallPolicyDetails",
)


def install_fake_oci(monkeypatch):
    """Install isolated OCI types for this test."""
    return shared_install_fake_oci(monkeypatch, model_names=MODEL_NAMES)


def attach_firewall_sdk(module):
    """Attach the service models used by the test."""
    module.oci.network_firewall = types.SimpleNamespace(
        models=types.SimpleNamespace(
            CreateNetworkFirewallPolicyDetails=FakeModel,
            UpdateNetworkFirewallPolicyDetails=FakeModel,
        ),
        NetworkFirewallClient=object,
    )


def make_policy(module_obj, params, client=None):
    """Return a module instance without OCI authentication."""
    return make_module_instance(
        module_obj, "OciNetworkFirewallPolicyModule", params, client=client
    )


def test_build_create_details(monkeypatch):
    """Verify build create details."""
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_firewall_policy")
    attach_firewall_sdk(module)
    details = module.build_create_network_firewall_policy_details(
        {
            "compartment_id": "c",
            "name": "p",
            "description": "d",
            "freeform_tags": {"a": "b"},
        }
    )
    assert details.compartment_id == "c"
    assert details.display_name == "p"
    assert details.description == "d"
    assert details.freeform_tags == {"a": "b"}


def test_update_resource_uses_policy_model(monkeypatch):
    """Verify update resource uses policy model."""
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_firewall_policy")
    attach_firewall_sdk(module)
    calls = []
    instance = make_policy(
        module,
        {"name": "new", "description": "updated", "wait": True},
        types.SimpleNamespace(
            update_network_firewall_policy=lambda **kw: calls.append(kw)
            or FakeResponse(data=FakeModel(id="p"))
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kw: fn(**kw))
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda rid, states: FakeModel(
            id=rid, display_name="new", description="updated"
        ),
    )
    resource = instance.update_resource(
        FakeModel(id="p", display_name="old", description="old")
    )
    assert resource.description == "updated"
    assert calls[0]["network_firewall_policy_id"] == "p"


def test_get_resource_response_uses_policy_id(monkeypatch):
    """Verify get resource response uses policy id."""
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_firewall_policy")
    attach_firewall_sdk(module)
    instance = make_policy(
        module,
        {},
        types.SimpleNamespace(
            get_network_firewall_policy=lambda **kw: FakeResponse(
                data=FakeModel(id=kw["network_firewall_policy_id"])
            )
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kw: fn(**kw))
    assert instance.get_resource_response("p").data.id == "p"


def test_create_without_wait_returns_immediate_resource(monkeypatch):
    """Return the SDK create response when waiting is disabled."""
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_firewall_policy")
    attach_firewall_sdk(module)
    instance = make_policy(
        module,
        {"compartment_id": "c", "name": "p", "wait": False},
        types.SimpleNamespace(
            create_network_firewall_policy=lambda **kwargs: FakeResponse(
                data=FakeModel(id="p")
            )
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kw: fn(**kw))
    assert instance.create_resource().id == "p"


def test_create_requires_compartment_and_name(monkeypatch):
    """Fail creation when required Network Firewall policy fields are absent."""
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_firewall_policy")
    instance = make_policy(module, {})
    with pytest.raises(FailJsonCalled) as error:
        instance.validate_create_request()
    assert "compartment_id" in error.value.payload["msg"]
