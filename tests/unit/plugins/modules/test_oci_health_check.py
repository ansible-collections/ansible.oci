from __future__ import absolute_import, division, print_function

import json
import types

from ansible.module_utils import basic

import pytest

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FakeResponse,
    FailJsonCalled,
    load_collection_module,
    make_module_instance,
)


def test_main_declares_monitor_options_without_aliases(monkeypatch):
    """Verify monitor argument choices and canonical parameter names."""
    module = load_collection_module("oci_health_check")
    captured = {}

    class FakeResourceModule:
        def __init__(self, instance):
            pass

        def execute_resource_module(self):
            pass

    monkeypatch.setattr(module, "AnsibleModule", lambda **kwargs: captured.update(kwargs) or DummyModule())
    monkeypatch.setattr(module, "OciHealthCheckModule", FakeResourceModule)
    module.main()
    spec = captured["argument_spec"]
    assert captured["supports_check_mode"] is True
    assert spec["monitor_type"]["choices"] == ["http", "ping"]
    assert "aliases" not in spec["name"]
    assert "aliases" not in spec["monitor_id"]
    assert spec["protocol"]["choices"] == ["http", "https", "icmp", "tcp"]
    assert spec["method"]["choices"] == ["get", "head"]
    assert spec["timeout_in_seconds"]["choices"] == [10, 20, 30, 60]
    assert spec["interval_in_seconds"]["choices"] == [10, 30, 60]


def test_type_validation_and_timeout_validation():
    """Reject protocols, fields, and timeout values that conflict with monitor type."""
    module = load_collection_module("oci_health_check")
    validate = module.validate_monitor_params
    ping_http = DummyModule({"method": "head"})
    with pytest.raises(FailJsonCalled):
        validate(ping_http, "ping")
    ping_protocol = DummyModule({"protocol": "https"})
    with pytest.raises(FailJsonCalled):
        validate(ping_protocol, "ping")
    invalid_timeout = DummyModule({"timeout_in_seconds": 20, "interval_in_seconds": 10})
    with pytest.raises(FailJsonCalled):
        validate(invalid_timeout, "http")
    partial_update = DummyModule({"timeout_in_seconds": 20})
    current = types.SimpleNamespace(protocol="HTTP", timeout_in_seconds=10, interval_in_seconds=10)
    with pytest.raises(FailJsonCalled):
        validate(partial_update, "http", current)


@pytest.mark.parametrize(
    "monitor_type,operation,details_key,model_type",
    [
        ("http", "create_http_monitor", "create_http_monitor_details", "CreateHttpMonitorDetails"),
        ("ping", "create_ping_monitor", "create_ping_monitor_details", "CreatePingMonitorDetails"),
    ],
)
def test_create_dispatches_to_matching_sdk_model(monitor_type, operation, details_key, model_type):
    """Create each monitor type with its matching SDK operation and model."""
    import oci

    module = load_collection_module("oci_health_check")
    params = {
        "monitor_type": monitor_type,
        "compartment_id": "compartment1",
        "name": "Monitor",
        "targets": ["host.example"],
        "protocol": "HTTP" if monitor_type == "http" else "ICMP",
        "interval_in_seconds": 30,
    }
    calls = []
    client = types.SimpleNamespace(**{operation: lambda **kwargs: calls.append(kwargs) or FakeResponse(types.SimpleNamespace(id="monitor1"))})
    instance = make_module_instance(module, "OciHealthCheckModule", params, client=client)
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    instance.create_resource()
    assert isinstance(calls[0][details_key], getattr(oci.healthchecks.models, model_type))
    assert calls[0][details_key].protocol == params["protocol"].upper()
    other_key = "create_ping_monitor_details" if monitor_type == "http" else "create_http_monitor_details"
    assert other_key not in calls[0]
    assert calls[0][details_key].display_name == "Monitor"


def test_named_summary_is_hydrated_and_targets_are_order_independent(monkeypatch):
    """Fetch a complete named monitor before comparison and ignore list order."""
    module = load_collection_module("oci_health_check")
    instance = make_module_instance(module, "OciHealthCheckModule", {"monitor_type": "http", "targets": ["b", "a"]})
    full = types.SimpleNamespace(id="monitor1", targets=["a", "b"])
    calls = []
    monkeypatch.setattr(instance, "get_resource_by_id", lambda monitor_id: calls.append(monitor_id) or full)
    assert instance.hydrate_named_resource(types.SimpleNamespace(id="monitor1")) is full
    assert calls == ["monitor1"]
    assert instance.needs_update(full) is False


def test_update_dispatches_http_details_and_preserves_false_and_empty_values():
    """Send HTTP fields, false values, and empty lists in one update."""
    import oci

    module = load_collection_module("oci_health_check")
    params = {
        "monitor_type": "http", "targets": [], "is_enabled": False,
        "method": "HEAD", "path": "/", "headers": {},
    }
    current = types.SimpleNamespace(
        id="monitor1", targets=["old"], is_enabled=True, method="GET",
        path="/old", headers={"X-Test": "old"},
    )
    calls = []
    client = types.SimpleNamespace(
        update_http_monitor=lambda **kwargs: calls.append(kwargs)
        or FakeResponse(current)
    )
    instance = make_module_instance(module, "OciHealthCheckModule", params, client=client)
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    instance.update_resource(current)
    assert set(calls[0]) == {"monitor_id", "update_http_monitor_details"}
    details = calls[0]["update_http_monitor_details"]
    assert isinstance(details, oci.healthchecks.models.UpdateHttpMonitorDetails)
    assert details.targets == []
    assert details.is_enabled is False
    assert details.method == "HEAD"
    assert details.path == "/"
    assert details.headers == {}


@pytest.mark.parametrize(
    "monitor_type,operation",
    [("http", "delete_http_monitor"), ("ping", "delete_ping_monitor")],
)
def test_delete_dispatches_by_monitor_type(monitor_type, operation):
    """Call the delete operation for the selected monitor type."""
    module = load_collection_module("oci_health_check")
    calls = []
    instance = make_module_instance(
        module,
        "OciHealthCheckModule",
        {"monitor_type": monitor_type},
        client=types.SimpleNamespace(**{operation: lambda **kwargs: calls.append(kwargs)}),
    )
    instance.call_delete_fn = lambda resource, function, **kwargs: function(**kwargs)
    instance.delete_resource(types.SimpleNamespace(id="monitor1"))
    assert calls == [{"monitor_id": "monitor1"}]


def test_compartment_change_is_immutable():
    """Reject an update that changes the monitor compartment."""
    module = load_collection_module("oci_health_check")
    instance = make_module_instance(
        module,
        "OciHealthCheckModule",
        {"monitor_type": "http", "compartment_id": "compartment2"},
    )
    current = types.SimpleNamespace(compartment_id="compartment1")
    with pytest.raises(FailJsonCalled):
        instance.needs_update(current)


def test_update_check_mode_and_idempotent_run():
    """Predict an update in check mode and report no drift for the same values."""
    module = load_collection_module("oci_health_check")
    params = {"monitor_type": "ping", "targets": ["target-a", "target-b"]}
    current = types.SimpleNamespace(
        id="monitor1", targets=["target-a", "old-target"],
        protocol="ICMP", interval_in_seconds=30, timeout_in_seconds=10,
    )
    check = make_module_instance(module, "OciHealthCheckModule", params, check_mode=True)
    check.resolve_target_resource = lambda: current
    with pytest.raises(ExitJsonCalled) as planned:
        check.execute_resource_module()
    assert planned.value.payload["changed"] is True

    unchanged = types.SimpleNamespace(
        id="monitor1", targets=["target-b", "target-a"],
        protocol="ICMP", interval_in_seconds=30, timeout_in_seconds=10,
    )
    same = make_module_instance(module, "OciHealthCheckModule", params, check_mode=True)
    same.resolve_target_resource = lambda: unchanged
    with pytest.raises(ExitJsonCalled) as result:
        same.execute_resource_module()
    assert result.value.payload["changed"] is False


def test_delete_check_mode_keeps_monitor_and_repeat_delete_is_unchanged():
    """Predict a delete without calling OCI and leave missing monitors unchanged."""
    module = load_collection_module("oci_health_check")
    resource = types.SimpleNamespace(id="monitor1")
    calls = []
    check = make_module_instance(
        module,
        "OciHealthCheckModule",
        {"monitor_type": "ping", "monitor_id": "monitor1", "state": "absent"},
        check_mode=True,
    )
    check.resolve_target_resource = lambda: resource
    check.delete_resource = calls.append
    with pytest.raises(ExitJsonCalled) as planned:
        check.execute_resource_module()
    assert planned.value.payload["changed"] is True
    assert calls == []

    repeated = make_module_instance(
        module,
        "OciHealthCheckModule",
        {"monitor_type": "ping", "monitor_id": "monitor1", "state": "absent"},
    )
    repeated.resolve_target_resource = lambda: None
    with pytest.raises(ExitJsonCalled) as result:
        repeated.execute_resource_module()
    assert result.value.payload["changed"] is False


def test_missing_id_fails_and_check_mode_predicts_create():
    """Fail for a missing explicit ID and report a planned create in check mode."""
    module = load_collection_module("oci_health_check")
    params = {"monitor_type": "http", "monitor_id": "missing"}
    instance = make_module_instance(module, "OciHealthCheckModule", params)
    instance.resolve_target_resource = lambda: None
    with pytest.raises(FailJsonCalled):
        instance.execute_resource_module()
    params = {
        "monitor_type": "http", "compartment_id": "compartment1", "name": "Monitor",
        "targets": ["host.example"], "protocol": "http", "interval_in_seconds": 30,
    }
    instance = make_module_instance(module, "OciHealthCheckModule", params, check_mode=True)
    instance.resolve_target_resource = lambda: None
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload["changed"] is True


@pytest.mark.parametrize("check_mode", [False, True])
def test_headers_are_hidden_in_ansible_output(monkeypatch, capsys, check_mode):
    """Hide supplied header values in the actual Ansible JSON response."""
    module = load_collection_module("oci_health_check")
    params = {
        "monitor_type": "http", "monitor_id": "monitor1",
        "headers": {"X-Api-Key": "synthetic-api-key", "Cookie": "synthetic-cookie"},
        "_ansible_check_mode": check_mode,
    }
    if "inject_invocation" in basic.PASS_VARS:
        params["_ansible_inject_invocation"] = True
    monkeypatch.setattr(basic, "_ANSIBLE_ARGS", json.dumps({"ANSIBLE_MODULE_ARGS": params}).encode())
    monkeypatch.setattr(basic, "_ANSIBLE_PROFILE", "legacy", raising=False)
    monkeypatch.setattr(basic, "_PARSED_MODULE_ARGS", params.copy(), raising=False)

    class FakeResourceModule:
        def __init__(self, instance):
            self.module = instance

        def execute_resource_module(self):
            assert self.module.params["headers"] == params["headers"]
            assert set(params["headers"].values()) <= self.module.no_log_values
            self.module.exit_json(changed=False)

    monkeypatch.setattr(module, "OciHealthCheckModule", FakeResourceModule)
    with pytest.raises(SystemExit) as result:
        module.main()
    assert result.value.code == 0
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["changed"] is False
    assert set(payload["invocation"]["module_args"]["headers"]) == {"X-Api-Key", "Cookie"}
    # Ansible 2.22 sends secrets to the controller for masking.
    payload.pop("_ansible_new_secrets", None)
    output = json.dumps(payload)
    try:
        from ansible.module_utils.secrets import mask_secrets
    except ImportError:
        pass  # Older Ansible versions mask values before serialization.
    else:
        output = mask_secrets(output)
    assert "synthetic-api-key" not in output
    assert "synthetic-cookie" not in output


@pytest.mark.parametrize("operation", ["create", "update", "unchanged", "check_unchanged"])
def test_resource_results_omit_stored_headers(operation):
    """Remove stored headers from results without changing the resource."""
    module = load_collection_module("oci_health_check")
    params = {"monitor_type": "http", "monitor_id": "monitor1"}
    resource = types.SimpleNamespace(id="monitor1", display_name="Monitor", headers={"Cookie": "stored-cookie"})
    instance = make_module_instance(
        module, "OciHealthCheckModule", params, check_mode=operation == "check_unchanged",
    )
    if operation == "create":
        params.pop("monitor_id")
        instance.resolve_target_resource = lambda: None
        instance.validate_create_request = lambda: None
        instance.create_resource = lambda: resource
    else:
        instance.resolve_target_resource = lambda: resource
        instance.needs_update = lambda current: operation == "update"
        instance.update_resource = lambda current: resource
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload["changed"] is (operation in ("create", "update"))
    assert result.value.payload["resource"] == {"id": "monitor1", "name": "Monitor"}
    assert resource.headers == {"Cookie": "stored-cookie"}


@pytest.mark.parametrize("check_mode", [False, True])
def test_matching_headers_remain_unchanged(check_mode):
    """Keep stored headers available for comparison while omitting them from results."""
    module = load_collection_module("oci_health_check")
    headers = {"X-Api-Key": "synthetic-api-key"}
    instance = make_module_instance(
        module, "OciHealthCheckModule",
        {"monitor_type": "http", "monitor_id": "monitor1", "headers": headers.copy()},
        check_mode=check_mode,
    )
    resource = types.SimpleNamespace(id="monitor1", headers=headers.copy())
    instance.resolve_target_resource = lambda: resource
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload == {"changed": False, "resource": {"id": "monitor1"}}
    assert resource.headers == headers


def test_header_values_reach_sdk_models():
    """Preserve supplied headers in create and update requests."""
    module = load_collection_module("oci_health_check")
    headers = {"X-Api-Key": "synthetic-api-key", "Cookie": "synthetic-cookie"}
    for creating in (False, True):
        details = module.build_monitor_details({"headers": headers.copy()}, "http", creating=creating)
        assert details.headers == headers
