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


def load_endpoint_info_module(monkeypatch):
    oci = install_fake_oci(monkeypatch)[0]
    oci.dns = types.SimpleNamespace(DnsClient=type("DnsClient", (), {}))
    return load_collection_module("oci_dns_resolver_endpoint_info")


def test_get_endpoint_passes_resolver_and_name(monkeypatch):
    module = load_endpoint_info_module(monkeypatch)
    calls = []
    client = types.SimpleNamespace(
        get_resolver_endpoint=lambda **kwargs: (
            calls.append(kwargs) or FakeResponse(FakeModel(name="endpoint-1"))
        ),
    )
    instance = make_module_instance(
        module,
        "OciDnsResolverEndpointInfoModule",
        {"resolver_id": "resolver-1", "name": "endpoint-1"},
        client=client,
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    try:
        instance.execute_info_module()
    except ExitJsonCalled as exc:
        assert exc.payload["changed"] is False
        assert exc.payload["endpoints"] == [{"name": "endpoint-1"}]
    assert calls == [{"resolver_id": "resolver-1", "resolver_endpoint_name": "endpoint-1"}]


def test_list_endpoints_uses_resolver_id(monkeypatch):
    module = load_endpoint_info_module(monkeypatch)
    calls = []
    client = types.SimpleNamespace(
        list_resolver_endpoints=lambda **kwargs: (
            calls.append(kwargs) or FakeResponse([FakeModel(name="endpoint-1")])
        ),
    )
    instance = make_module_instance(
        module,
        "OciDnsResolverEndpointInfoModule",
        {"resolver_id": "resolver-1"},
        client=client,
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    instance.list_all_resources = lambda fn, **kwargs: fn(**kwargs).data
    try:
        instance.execute_info_module()
    except ExitJsonCalled as exc:
        assert exc.payload["changed"] is False
        assert exc.payload["endpoints"] == [{"name": "endpoint-1"}]
    assert calls == [{"resolver_id": "resolver-1"}]
