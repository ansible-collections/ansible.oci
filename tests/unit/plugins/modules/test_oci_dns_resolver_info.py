from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

from .conftest import ExitJsonCalled, FakeModel, FakeResponse, install_fake_oci, load_collection_module, make_module_instance


def install_resolver_oci(monkeypatch):
    oci, error = install_fake_oci(monkeypatch)
    oci.dns = types.SimpleNamespace(DnsClient=type("DnsClient", (), {}), models=types.SimpleNamespace())
    oci.retry.RetryStrategyBuilder = lambda **kwargs: types.SimpleNamespace(
        get_retry_strategy=lambda: types.SimpleNamespace(
            make_retrying_call=lambda fn, *args, **call_kwargs: fn(*args, **call_kwargs)
        )
    )
    return oci, error


def test_info_gets_resolver_by_id(monkeypatch):
    install_resolver_oci(monkeypatch)
    module = load_collection_module("oci_dns_resolver_info")
    calls = []
    client = type("Client", (), {"get_resolver": lambda self, **kwargs: calls.append(kwargs) or FakeResponse(FakeModel(id="r1", display_name="dns"))})()
    instance = make_module_instance(module, "OciDnsResolverInfoModule", {"resolver_id": "r1"}, client=client)
    try:
        instance.execute_info_module()
    except ExitJsonCalled as exc:
        assert exc.payload["changed"] is False
        assert exc.payload["resolvers"] == [{"id": "r1", "name": "dns"}]
    assert calls == [{"resolver_id": "r1"}]


def test_info_lists_resolvers_with_filters(monkeypatch):
    install_resolver_oci(monkeypatch)
    module = load_collection_module("oci_dns_resolver_info")
    calls = []
    client = type("Client", (), {"list_resolvers": lambda self, **kwargs: calls.append(kwargs) or FakeResponse(
        [FakeModel(id="r1", display_name="dns"), FakeModel(id="r2", display_name="other")]
    )})()
    instance = make_module_instance(module, "OciDnsResolverInfoModule", {"compartment_id": "c1", "name": "dns"}, client=client)
    instance.list_all_resources = lambda fn, **kwargs: fn(**kwargs).data
    try:
        instance.execute_info_module()
    except ExitJsonCalled as exc:
        assert exc.payload["resolvers"] == [{"id": "r1", "name": "dns"}]
    assert calls == [{"compartment_id": "c1"}]
