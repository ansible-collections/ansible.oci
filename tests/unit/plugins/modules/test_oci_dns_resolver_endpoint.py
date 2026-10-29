from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

from .conftest import (
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
)


def load_endpoint_module(monkeypatch):
    oci = install_fake_oci(monkeypatch, model_names=(
        "CreateResolverVnicEndpointDetails",
        "UpdateResolverVnicEndpointDetails",
    ))[0]
    oci.dns = types.SimpleNamespace(
        DnsClient=type("DnsClient", (), {}),
        models=oci.core.models,
    )
    return load_collection_module("oci_dns_resolver_endpoint")


def make_endpoint_instance(module, params, client, check_mode=False):
    return make_module_instance(
        module,
        "OciDnsResolverEndpointModule",
        params,
        client=client,
        check_mode=check_mode,
    )


def test_create_details_uses_vnic_model(monkeypatch):
    module = load_endpoint_module(monkeypatch)
    details = module.build_create_details(
        {
            "name": "private-endpoint",
            "subnet_id": "subnet-1",
            "is_listening": True,
            "nsg_ids": ["nsg-1"],
        }
    )
    assert details.name == "private-endpoint"
    assert details.subnet_id == "subnet-1"
    assert details.nsg_ids == ["nsg-1"]


def test_check_mode_predicts_endpoint_create_without_api_call(monkeypatch):
    module = load_endpoint_module(monkeypatch)
    calls = []

    def get_missing_endpoint(**kwargs):
        raise type("NotFound", (Exception,), {"status": 404})()

    client = types.SimpleNamespace(
        get_resolver_endpoint=get_missing_endpoint,
        create_resolver_endpoint=lambda **kwargs: calls.append(kwargs),
    )
    instance = make_endpoint_instance(
        module,
        {"resolver_id": "resolver-1", "name": "endpoint-1"},
        client,
        check_mode=True,
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    try:
        instance.execute_resource_module()
    except ExitJsonCalled as exc:
        assert exc.payload["changed"] is True
    assert calls == []


def test_update_calls_resolver_endpoint_api_with_vnic_update_model(monkeypatch):
    module = load_endpoint_module(monkeypatch)
    calls = []
    client = types.SimpleNamespace(
        update_resolver_endpoint=lambda **kwargs: (
            calls.append(kwargs) or FakeResponse(FakeModel(name="endpoint-1", nsg_ids=["nsg-2"]))
        ),
    )
    instance = make_endpoint_instance(
        module,
        {"name": "endpoint-1", "resolver_id": "resolver-1", "nsg_ids": ["nsg-2"], "wait": False},
        client,
        check_mode=False,
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    resource = FakeModel(name="endpoint-1", nsg_ids=["nsg-1"])
    updated = instance.update_resource(resource)
    assert calls[0]["resolver_id"] == "resolver-1"
    assert calls[0]["resolver_endpoint_name"] == "endpoint-1"
    assert isinstance(calls[0]["update_resolver_endpoint_details"], FakeModel)
    assert calls[0]["update_resolver_endpoint_details"].nsg_ids == ["nsg-2"]
    assert updated.nsg_ids == ["nsg-2"]


def test_delete_uses_composite_endpoint_identity(monkeypatch):
    module = load_endpoint_module(monkeypatch)
    calls = []
    client = types.SimpleNamespace(
        delete_resolver_endpoint=lambda **kwargs: (
            calls.append(kwargs) or FakeResponse(FakeModel())
        ),
    )
    instance = make_endpoint_instance(
        module,
        {"name": "endpoint-1", "resolver_id": "resolver-1", "wait": False},
        client,
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    instance.call_delete_fn = lambda resource, fn, action_verb="delete", **kwargs: fn(**kwargs)
    instance.delete_resource(FakeModel(id="endpoint-ocid", name="endpoint-1"))
    assert calls == [{"resolver_id": "resolver-1", "resolver_endpoint_name": "endpoint-1"}]
