from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import oci
import pytest

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    FailJsonCalled,
    load_collection_module,
    make_module_instance,
)


def _load(name):
    return load_collection_module(name)


def _load_helper():
    return load_collection_module("oci_loadbalancer", plugin_dir="module_utils")


def _install_composite(monkeypatch, helper, calls):
    class Composite:
        def __init__(self, client):
            self.client = client

        def __getattr__(self, operation):
            def invoke(**kwargs):
                calls.append((operation, kwargs))
                return FakeResponse(FakeModel(ip_address="10.0.0.7", port=8080))

            return invoke

    monkeypatch.setattr(
        helper.oci.load_balancer,
        "LoadBalancerClientCompositeOperations",
        Composite,
    )


def _backend(params, *, check_mode=False, client=None):
    module = _load("oci_loadbalancer_backend")
    instance = make_module_instance(
        module,
        "OciLoadBalancerBackendModule",
        params,
        client=client or types.SimpleNamespace(),
        check_mode=check_mode,
    )
    return instance


def test_main_exposes_source_parameters_and_common_auth_wait_options(monkeypatch):
    module = _load("oci_loadbalancer_backend")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule({})

    class FakeBackendModule:
        def __init__(self, active_module):
            self.module = active_module

        def execute_resource_module(self):
            captured["executed"] = True

    monkeypatch.setattr(module, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module, "OciLoadBalancerBackendModule", FakeBackendModule)

    module.main()

    argument_spec = captured["argument_spec"]
    assert argument_spec["load_balancer_id"] == {"type": "str", "required": True}
    assert argument_spec["backend_set_name"] == {"type": "str", "required": True}
    assert argument_spec["name"] == {"type": "str", "required": True}
    assert argument_spec["ip_address"] == {"type": "str"}
    assert argument_spec["port"] == {"type": "int"}
    assert argument_spec["weight"] == {"type": "int"}
    assert argument_spec["backup"] == {"type": "bool"}
    assert argument_spec["drain"] == {"type": "bool"}
    assert argument_spec["offline"] == {"type": "bool"}
    assert argument_spec["state"] == {
        "type": "str",
        "choices": ["present", "absent"],
        "default": "present",
    }
    assert "id" not in argument_spec["load_balancer_id"].get("aliases", [])
    assert "compartment_id" not in argument_spec
    assert "freeform_tags" not in argument_spec
    assert argument_spec["auth_type"]["choices"] == [
        "api_key",
        "instance_principal",
        "resource_principal",
        "session_token",
    ]
    assert argument_spec["wait"]["default"] is True
    assert captured["supports_check_mode"] is True
    assert captured["executed"] is True


def test_create_backend_uses_typed_details_and_preserves_false_and_zero(monkeypatch):
    helper = _load_helper()
    backend = _backend(
        {
            "load_balancer_id": "lb-ocid",
            "backend_set_name": "pool-a",
            "name": "10.0.0.7:8080",
            "ip_address": "10.0.0.7",
            "port": 8080,
            "weight": 0,
            "backup": False,
            "drain": False,
            "offline": False,
            "wait": False,
        }
    )
    calls = []
    _install_composite(monkeypatch, helper, calls)

    def get_created_backend(name):
        assert name == "10.0.0.7:8080"
        return FakeResponse(FakeModel(ip_address="10.0.0.7", port=8080))

    backend.get_resource_response = get_created_backend

    backend.create_resource()

    operation, kwargs = calls[0]
    assert operation == "create_backend_and_wait_for_state"
    details = kwargs["create_backend_details"]
    assert isinstance(details, oci.load_balancer.models.CreateBackendDetails)
    assert details.ip_address == "10.0.0.7"
    assert details.port == 8080
    assert details.weight == 0
    assert details.backup is False
    assert details.drain is False
    assert details.offline is False
    assert kwargs["load_balancer_id"] == "lb-ocid"
    assert kwargs["backend_set_name"] == "pool-a"


def test_create_backend_requires_ip_address_and_port():
    backend = _backend(
        {
            "load_balancer_id": "lb-ocid",
            "backend_set_name": "pool-a",
            "name": "10.0.0.7:8080",
        }
    )

    with pytest.raises(FailJsonCalled) as exc:
        backend.validate_create_request()

    assert "ip_address, port" in exc.value.payload["msg"]


def test_create_backend_name_must_match_ip_address_and_port():
    backend = _backend(
        {
            "load_balancer_id": "lb-ocid",
            "backend_set_name": "pool-a",
            "name": "10.0.0.8:8080",
            "ip_address": "10.0.0.7",
            "port": 8080,
        }
    )

    with pytest.raises(FailJsonCalled) as exc:
        backend.validate_create_request()

    assert "name parameter must match" in exc.value.payload["msg"]


def test_backend_update_detects_false_and_zero_values(monkeypatch):
    backend = _backend(
        {
            "load_balancer_id": "lb-ocid",
            "backend_set_name": "pool-a",
            "name": "10.0.0.7:8080",
            "weight": 0,
            "backup": False,
            "drain": False,
            "offline": False,
        }
    )
    current = FakeModel(
        ip_address="10.0.0.7",
        port=8080,
        weight=5,
        backup=True,
        drain=True,
        offline=True,
    )

    plan = backend.build_update_plan(current)

    assert plan["update_needed"] is True
    assert plan["update_model_fields"] == {
        "weight": 0,
        "backup": False,
        "drain": False,
        "offline": False,
    }
    assert backend.needs_update(current) is True


def test_backend_update_sends_typed_details_and_preserves_false_and_zero(monkeypatch):
    helper = _load_helper()
    backend = _backend(
        {
            "load_balancer_id": "lb-ocid",
            "backend_set_name": "pool-a",
            "name": "10.0.0.7:8080",
            "weight": 0,
            "backup": False,
            "drain": False,
            "offline": False,
            "wait": False,
        }
    )
    current = FakeModel(
        ip_address="10.0.0.7",
        port=8080,
        weight=5,
        backup=True,
        drain=True,
        offline=True,
    )
    calls = []
    _install_composite(monkeypatch, helper, calls)

    def get_updated_backend(name):
        assert name == "10.0.0.7:8080"
        return FakeResponse(current)

    backend.get_resource_response = get_updated_backend

    backend.update_resource(current)

    operation, kwargs = calls[0]
    assert operation == "update_backend_and_wait_for_state"
    details = kwargs["update_backend_details"]
    assert isinstance(details, oci.load_balancer.models.UpdateBackendDetails)
    assert details.weight == 0
    assert details.backup is False
    assert details.drain is False
    assert details.offline is False
    assert kwargs["backend_name"] == "10.0.0.7:8080"


def test_backend_present_check_mode_predicts_update_without_mutation(monkeypatch):
    backend = _backend(
        {
            "load_balancer_id": "lb-ocid",
            "backend_set_name": "pool-a",
            "name": "10.0.0.7:8080",
            "weight": 0,
        },
        check_mode=True,
    )
    current = FakeModel(ip_address="10.0.0.7", port=8080, weight=1)
    calls = []
    backend.resolve_target_resource = lambda: current
    backend.update_resource = calls.append

    with pytest.raises(ExitJsonCalled) as exc:
        backend.execute_resource_module()

    assert exc.value.payload["changed"] is True
    assert calls == []


def test_backend_create_check_mode_predicts_change_without_mutation():
    backend = _backend(
        {
            "load_balancer_id": "lb-ocid",
            "backend_set_name": "pool-a",
            "name": "10.0.0.7:8080",
            "ip_address": "10.0.0.7",
            "port": 8080,
        },
        check_mode=True,
    )
    backend.resolve_target_resource = lambda: None
    calls = []
    backend.create_resource = lambda: calls.append("create")

    with pytest.raises(ExitJsonCalled) as exc:
        backend.execute_resource_module()

    assert exc.value.payload["changed"] is True
    assert calls == []


def test_backend_matching_desired_state_is_idempotent(monkeypatch):
    backend = _backend(
        {
            "load_balancer_id": "lb-ocid",
            "backend_set_name": "pool-a",
            "name": "10.0.0.7:8080",
            "weight": 0,
            "backup": False,
            "drain": False,
            "offline": False,
        }
    )
    current = FakeModel(
        ip_address="10.0.0.7",
        port=8080,
        weight=0,
        backup=False,
        drain=False,
        offline=False,
    )
    calls = []
    backend.resolve_target_resource = lambda: current
    backend.update_resource = calls.append

    with pytest.raises(ExitJsonCalled) as exc:
        backend.execute_resource_module()

    assert exc.value.payload["changed"] is False
    assert calls == []


@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize("field", ["ip_address", "port"])
def test_backend_identity_changes_fail_before_mutation(check_mode, field):
    params = {
        "load_balancer_id": "lb-ocid",
        "backend_set_name": "pool-a",
        "name": "10.0.0.7:8080",
        "ip_address": "10.0.0.8" if field == "ip_address" else "10.0.0.7",
        "port": 8081 if field == "port" else 8080,
    }
    backend = _backend(params, check_mode=check_mode)
    backend.resolve_target_resource = lambda: FakeModel(
        ip_address="10.0.0.7", port=8080
    )
    calls = []
    backend.update_resource = calls.append

    with pytest.raises(FailJsonCalled) as exc:
        backend.execute_resource_module()

    assert field in exc.value.payload["msg"]
    assert "creation identity" in exc.value.payload["msg"]
    assert calls == []


@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize("identity", [None, {"ip_address": "10.0.0.7", "port": 8080}])
def test_backend_matching_or_omitted_identity_is_idempotent(identity, check_mode):
    params = {
        "load_balancer_id": "lb-ocid",
        "backend_set_name": "pool-a",
        "name": "10.0.0.7:8080",
        "weight": 3,
    }
    if identity:
        params.update(identity)
    backend = _backend(params, check_mode=check_mode)
    backend.resolve_target_resource = lambda: FakeModel(
        ip_address="10.0.0.7", port=8080, weight=3
    )
    calls = []
    backend.update_resource = calls.append

    with pytest.raises(ExitJsonCalled) as exc:
        backend.execute_resource_module()

    assert exc.value.payload["changed"] is False
    assert calls == []


def test_backend_absent_check_mode_predicts_delete_and_keeps_resource(monkeypatch):
    backend = _backend(
        {
            "state": "absent",
            "load_balancer_id": "lb-ocid",
            "backend_set_name": "pool-a",
            "name": "10.0.0.7:8080",
        },
        check_mode=True,
    )
    current = FakeModel(ip_address="10.0.0.7", port=8080)
    calls = []
    backend.resolve_target_resource = lambda: current
    backend.delete_resource = calls.append

    with pytest.raises(ExitJsonCalled) as exc:
        backend.execute_resource_module()

    assert exc.value.payload["changed"] is True
    assert calls == []


def test_repeated_backend_delete_with_missing_target_is_unchanged():
    backend = _backend(
        {
            "state": "absent",
            "load_balancer_id": "lb-ocid",
            "backend_set_name": "pool-a",
            "name": "10.0.0.7:8080",
        }
    )
    backend.resolve_target_resource = lambda: None
    calls = []
    backend.delete_resource = calls.append

    with pytest.raises(ExitJsonCalled) as exc:
        backend.execute_resource_module()

    assert exc.value.payload["changed"] is False
    assert calls == []


def test_backend_delete_uses_scoped_ip_and_port_identity(monkeypatch):
    helper = _load_helper()
    backend = _backend(
        {
            "load_balancer_id": "lb-ocid",
            "backend_set_name": "pool-a",
            "name": "10.0.0.7:8080",
            "wait": False,
        }
    )
    current = FakeModel(ip_address="10.0.0.7", port=8080)
    calls = []
    _install_composite(monkeypatch, helper, calls)

    backend.delete_resource(current)

    operation, kwargs = calls[0]
    assert operation == "delete_backend_and_wait_for_state"
    assert kwargs["load_balancer_id"] == "lb-ocid"
    assert kwargs["backend_set_name"] == "pool-a"
    assert kwargs["backend_name"] == "10.0.0.7:8080"


def test_backend_info_get_list_and_not_found_are_scoped(monkeypatch):
    module = _load("oci_loadbalancer_backend_info")
    backend = FakeModel(ip_address="10.0.0.7", port=8080)
    calls = []

    class NotFound(Exception):
        status = 404

    client = types.SimpleNamespace(
        get_backend=lambda **kwargs: calls.append(("get", kwargs))
        or FakeResponse(backend),
        list_backends=lambda **kwargs: calls.append(("list", kwargs))
        or FakeResponse([backend]),
    )
    get_instance = make_module_instance(
        module,
        "OciLoadBalancerBackendInfoModule",
        {
            "load_balancer_id": "lb-ocid",
            "backend_set_name": "pool-a",
            "name": "10.0.0.7:8080",
        },
        client=client,
    )
    get_instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)

    assert get_instance.fetch_resources() == [backend]
    assert calls[-1] == (
        "get",
        {
            "load_balancer_id": "lb-ocid",
            "backend_set_name": "pool-a",
            "backend_name": "10.0.0.7:8080",
        },
    )

    list_instance = make_module_instance(
        module,
        "OciLoadBalancerBackendInfoModule",
        {"load_balancer_id": "lb-ocid", "backend_set_name": "pool-a"},
        client=client,
    )
    list_instance.list_all_resources = lambda fn, **kwargs: fn(**kwargs).data
    assert list_instance.fetch_resources() == [backend]
    assert calls[-1] == (
        "list",
        {"load_balancer_id": "lb-ocid", "backend_set_name": "pool-a"},
    )

    missing_client = types.SimpleNamespace(
        get_backend=lambda **kwargs: (_unused for _unused in ()).throw(NotFound("missing"))
    )
    missing_instance = make_module_instance(
        module,
        "OciLoadBalancerBackendInfoModule",
        {
            "load_balancer_id": "lb-ocid",
            "backend_set_name": "pool-a",
            "name": "10.0.0.8:8080",
        },
        client=missing_client,
    )
    missing_instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    assert missing_instance.fetch_resources() == []

    missing_parent_instance = make_module_instance(
        module,
        "OciLoadBalancerBackendInfoModule",
        {"load_balancer_id": "missing-lb", "backend_set_name": "pool-a"},
        client=types.SimpleNamespace(list_backends=lambda **kwargs: None),
    )
    missing_parent_instance.list_all_resources = lambda fn, **kwargs: (_unused for _unused in ()).throw(
        NotFound("missing parent")
    )
    assert missing_parent_instance.fetch_resources() == []

    service_error = NotFound("service unavailable")
    service_error.status = 503
    failing_instance = make_module_instance(
        module,
        "OciLoadBalancerBackendInfoModule",
        {"load_balancer_id": "lb-ocid", "backend_set_name": "pool-a"},
        client=types.SimpleNamespace(list_backends=lambda **kwargs: None),
    )
    failing_instance.list_all_resources = lambda fn, **kwargs: (_unused for _unused in ()).throw(
        service_error
    )
    with pytest.raises(NotFound):
        failing_instance.fetch_resources()
