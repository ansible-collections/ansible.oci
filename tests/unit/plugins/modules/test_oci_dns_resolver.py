from __future__ import absolute_import, division, print_function
__metaclass__ = type

import importlib
import types

from .conftest import (
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
)


def install_resolver_oci(monkeypatch, model_names=()):
    oci, error = install_fake_oci(monkeypatch, model_names=model_names)
    oci.dns = types.SimpleNamespace(
        DnsClient=type("DnsClient", (), {}),
        models=types.SimpleNamespace(**{name: FakeModel for name in model_names}),
    )
    oci.retry.RetryStrategyBuilder = lambda **kwargs: types.SimpleNamespace(
        get_retry_strategy=lambda: types.SimpleNamespace(
            make_retrying_call=lambda fn, *args, **call_kwargs: fn(*args, **call_kwargs)
        )
    )
    base = importlib.import_module("ansible_collections.ansible.oci.plugins.module_utils.oci_base")
    monkeypatch.setattr(base, "oci", oci)
    return oci, error


def test_update_details_builds_attached_views_and_forward_rules(monkeypatch):
    oci = install_resolver_oci(
        monkeypatch,
        model_names=(
            "AttachedViewDetails",
            "ResolverForwardRuleDetails",
            "UpdateResolverDetails",
        ),
    )
    oci = oci[0]
    module = load_collection_module("oci_dns_resolver")
    details = module.build_resolver_update_details(
        {
            "name": "resolver",
            "attached_views": [{"view_id": "view-1"}],
            "forward_rules": [
                {
                    "destination_addresses": ["10.0.0.10"],
                    "source_endpoint_name": "endpoint",
                }
            ],
        }
    )
    assert details.display_name == "resolver"
    assert details.attached_views[0].view_id == "view-1"
    assert details.rules[0].action == "FORWARD"
    assert oci.dns.models.UpdateResolverDetails is FakeModel


def test_check_mode_predicts_resolver_update(monkeypatch):
    install_resolver_oci(monkeypatch, ("UpdateResolverDetails",))
    module = load_collection_module("oci_dns_resolver")
    calls = []
    client = types.SimpleNamespace(
        get_resolver=lambda **kwargs: FakeResponse(
            FakeModel(display_name="old", freeform_tags={}, defined_tags={}, attached_views=[], rules=[])
        ),
        update_resolver=lambda **kwargs: calls.append(kwargs),
    )
    instance = make_module_instance(
        module,
        "OciDnsResolverModule",
        {"resolver_id": "resolver-1", "name": "new", "wait": False},
        client=client,
        check_mode=True,
    )
    try:
        instance.execute()
    except ExitJsonCalled as exc:
        assert exc.payload["changed"] is True
        assert exc.payload["resource"]["name"] == "old"
    assert calls == []


def test_update_applies_resolver_change(monkeypatch):
    install_resolver_oci(monkeypatch, ("UpdateResolverDetails",))
    module = load_collection_module("oci_dns_resolver")
    update_calls = []
    client = types.SimpleNamespace(
        get_resolver=lambda **kwargs: FakeResponse(
            FakeModel(display_name="old", freeform_tags={}, defined_tags={}, attached_views=[], rules=[])
        ),
        update_resolver=lambda **kwargs: (
            update_calls.append(kwargs)
            or FakeResponse(FakeModel(display_name="new"))
        ),
    )
    instance = make_module_instance(
        module,
        "OciDnsResolverModule",
        {"resolver_id": "resolver-1", "name": "new", "wait": False},
        client=client,
    )
    try:
        instance.execute()
    except ExitJsonCalled as exc:
        assert exc.payload["changed"] is True
        assert exc.payload["resource"]["name"] == "new"
    assert len(update_calls) == 1
    assert update_calls[0]["resolver_id"] == "resolver-1"


def test_no_change_does_not_call_update(monkeypatch):
    install_resolver_oci(monkeypatch, ("UpdateResolverDetails",))
    module = load_collection_module("oci_dns_resolver")
    calls = []
    client = types.SimpleNamespace(
        get_resolver=lambda **kwargs: FakeResponse(FakeModel(display_name="same")),
        update_resolver=lambda **kwargs: calls.append(kwargs),
    )
    instance = make_module_instance(
        module,
        "OciDnsResolverModule",
        {"resolver_id": "resolver-1", "name": "same"},
        client=client,
    )
    try:
        instance.execute()
    except ExitJsonCalled as exc:
        assert exc.payload["changed"] is False
    assert calls == []


def test_forward_rule_does_not_drift_on_sdk_action_or_null_fields(monkeypatch):
    install_resolver_oci(monkeypatch, ("UpdateResolverDetails",))
    module = load_collection_module("oci_dns_resolver")
    calls = []
    client = types.SimpleNamespace(
        get_resolver=lambda **kwargs: FakeResponse(
            FakeModel(
                rules=[
                    {
                        "action": "FORWARD",
                        "destination_addresses": ["10.0.0.10"],
                        "source_endpoint_name": "endpoint",
                        "client_address_conditions": None,
                        "qname_cover_conditions": None,
                    }
                ]
            )
        ),
        update_resolver=lambda **kwargs: calls.append(kwargs),
    )
    instance = make_module_instance(
        module,
        "OciDnsResolverModule",
        {
            "resolver_id": "resolver-1",
            "forward_rules": [
                {
                    "destination_addresses": ["10.0.0.10"],
                    "source_endpoint_name": "endpoint",
                }
            ],
        },
        client=client,
    )
    try:
        instance.execute()
    except ExitJsonCalled as exc:
        assert exc.payload["changed"] is False
    assert calls == []


def test_update_uses_shared_resolver_waiter(monkeypatch):
    install_resolver_oci(monkeypatch, ("UpdateResolverDetails",))
    module = load_collection_module("oci_dns_resolver")
    waited = []
    client = types.SimpleNamespace(
        get_resolver=lambda **kwargs: FakeResponse(FakeModel(display_name="old")),
        update_resolver=lambda **kwargs: FakeResponse(FakeModel(display_name="new")),
    )
    instance = make_module_instance(
        module,
        "OciDnsResolverModule",
        {"resolver_id": "resolver-1", "name": "new", "wait": True},
        client=client,
    )

    def get_mutation_result(response_data, resource_id, target_states):
        waited.append((response_data, resource_id, target_states))
        return response_data

    instance.get_mutation_result = get_mutation_result
    try:
        instance.execute()
    except ExitJsonCalled as exc:
        assert exc.payload["changed"] is True
        assert exc.payload["resource"]["name"] == "new"
    assert len(waited) == 1
    assert waited[0][1:] == ("resolver-1", ("ACTIVE",))
