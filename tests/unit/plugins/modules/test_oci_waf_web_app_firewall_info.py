from __future__ import absolute_import, division, print_function

__metaclass__ = type

import types

from .conftest import (
    DummyModule,
    FakeModel,
    FakeResponse,
    load_collection_module,
    make_module_instance,
)


def install_fake_oci(monkeypatch):
    """Install a fake OCI SDK with the shared test helper."""
    from .conftest import install_fake_oci as shared_install_fake_oci

    oci_module = shared_install_fake_oci(monkeypatch)[0]
    oci_module.waf = types.SimpleNamespace(WafClient=type("FakeWafClient", (), {}))


def test_lifecycle_filter_is_uppercase(monkeypatch):
    """Verify lifecycle filters use the SDK list shape and enum casing."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_waf_web_app_firewall_info")
    instance = make_module_instance(
        module_obj,
        "OciWafWebAppFirewallInfoModule",
        {"lifecycle_state": "active"},
    )
    assert instance.collect_list_filters(("compartment_id", "lifecycle_state")) == {
        "lifecycle_state": ["ACTIVE"]
    }


def test_main_requires_id_or_compartment(monkeypatch):
    """Verify info module lookup arguments require an ID or compartment."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_waf_web_app_firewall_info")
    captured = {}

    def fake_ansible_module(**kwargs):
        """Capture the module constructor arguments."""
        captured.update(kwargs)
        return DummyModule()

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(
        module_obj,
        "OciWafWebAppFirewallInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )
    module_obj.main()
    assert captured["required_one_of"] == [["web_app_firewall_id", "compartment_id"]]


def test_info_get_returns_one_resource(monkeypatch):
    """Verify info get requests return one serialized resource."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_waf_web_app_firewall_info")
    instance = make_module_instance(
        module_obj, "OciWafWebAppFirewallInfoModule", {"web_app_firewall_id": "waf"}
    )
    instance.client.get_web_app_firewall = lambda **kwargs: FakeResponse(
        data=FakeModel(id="waf")
    )
    instance.call_with_retry = lambda fn, **kwargs: FakeResponse(
        data=FakeModel(id="waf")
    )
    assert instance.fetch_resources()[0].id == "waf"


def test_info_list_passes_compartment_and_lifecycle(monkeypatch):
    """Verify info list requests pass compartment and uppercase lifecycle filters."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_waf_web_app_firewall_info")
    instance = make_module_instance(
        module_obj,
        "OciWafWebAppFirewallInfoModule",
        {"compartment_id": "compartment", "lifecycle_state": "active"},
    )
    instance.client.list_web_app_firewalls = lambda **kwargs: []
    calls = []
    instance.list_all_resources = lambda fn, **kwargs: calls.append(kwargs) or [
        FakeModel(id="waf")
    ]
    assert instance.fetch_resources()[0].id == "waf"
    assert calls == [{"compartment_id": "compartment", "lifecycle_state": ["ACTIVE"]}]


def test_info_get_404_returns_empty_list(monkeypatch):
    """Verify info get converts an OCI 404 response into an empty result."""
    from .conftest import install_fake_oci as shared_install_fake_oci

    oci_module, service_error = shared_install_fake_oci(monkeypatch)
    oci_module.waf = types.SimpleNamespace(WafClient=type("FakeWafClient", (), {}))
    module_obj = load_collection_module("oci_waf_web_app_firewall_info")
    instance = make_module_instance(
        module_obj, "OciWafWebAppFirewallInfoModule", {"web_app_firewall_id": "waf"}
    )
    instance.client.get_web_app_firewall = lambda **kwargs: FakeResponse(data=None)
    error = service_error(404)
    instance.call_with_retry = lambda fn, **kwargs: (item for item in ()).throw(error)
    assert instance.fetch_resources() == []
