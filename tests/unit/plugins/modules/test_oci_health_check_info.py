from __future__ import absolute_import, division, print_function

import types

from .conftest import DummyModule, FakeResponse, load_collection_module, make_module_instance


def test_info_dispatches_get_by_monitor_type():
    """Use the matching monitor getter and return one resource."""
    module = load_collection_module("oci_health_check_info")
    for monitor_type, operation in (
        ("http", "get_http_monitor"),
        ("ping", "get_ping_monitor"),
    ):
        calls = []
        client = types.SimpleNamespace(
            **{operation: lambda **kwargs: calls.append(kwargs) or FakeResponse("resource")}
        )
        instance = make_module_instance(
            module,
            "OciHealthCheckInfoModule",
            {"monitor_type": monitor_type, "monitor_id": "monitor1"},
            client=client,
        )
        instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
        assert instance.fetch_resources() == ["resource"]
        assert calls == [{"monitor_id": "monitor1"}]


def test_info_get_404_returns_empty_list():
    """Return an empty list when a monitor ID does not exist."""
    module = load_collection_module("oci_health_check_info")

    class Missing(Exception):
        status = 404

    def get_monitor(**kwargs):
        raise Missing()

    instance = make_module_instance(
        module,
        "OciHealthCheckInfoModule",
        {"monitor_type": "http", "monitor_id": "missing"},
        client=types.SimpleNamespace(get_http_monitor=get_monitor),
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    assert instance.fetch_resources() == []


def test_info_list_filters_include_home_region_and_name():
    """Pass supported list filters and apply the name filter locally."""
    module = load_collection_module("oci_health_check_info")
    instance = make_module_instance(
        module,
        "OciHealthCheckInfoModule",
        {
            "monitor_type": "ping", "compartment_id": "compartment1",
            "name": "monitor", "home_region": "us-phoenix-1",
        },
        client=types.SimpleNamespace(list_ping_monitors=lambda **kwargs: None),
    )
    captured = {}
    resources = [types.SimpleNamespace(display_name="monitor"), types.SimpleNamespace(display_name="other")]
    instance.list_all_resources = lambda fn, **kwargs: captured.update(kwargs) or resources
    assert instance.fetch_resources() == [resources[0]]
    assert captured == {
        "compartment_id": "compartment1",
        "home_region": "us-phoenix-1",
    }


def test_info_main_uses_canonical_names_and_result_key(monkeypatch):
    """Verify canonical info parameter names and the health_checks result key."""
    module = load_collection_module("oci_health_check_info")
    captured = {}
    info_class = module.OciHealthCheckInfoModule

    class FakeInfoModule:
        def __init__(self, instance):
            pass

        def execute_info_module(self):
            pass

    monkeypatch.setattr(
        module,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule(),
    )
    monkeypatch.setattr(module, "OciHealthCheckInfoModule", FakeInfoModule)
    module.main()
    spec = captured["argument_spec"]
    assert "aliases" not in spec["monitor_id"]
    assert "aliases" not in spec["name"]
    assert spec["home_region"]["type"] == "str"
    assert info_class.results_key == "health_checks"
