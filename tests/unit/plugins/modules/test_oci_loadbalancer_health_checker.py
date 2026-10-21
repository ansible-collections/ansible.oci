from __future__ import absolute_import, division, print_function
__metaclass__ = type

import importlib
import types

import oci
import pytest
from ansible.module_utils.common.arg_spec import ModuleArgumentSpecValidator

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FakeResponse,
    FailJsonCalled,
    load_collection_module,
    make_module_instance,
    raising,
)


def make_health_checker(**overrides):
    fields = {
        "protocol": "HTTP",
        "url_path": "/health",
        "port": 8080,
        "return_code": 200,
        "retries": 3,
        "timeout_in_millis": 3000,
        "interval_in_millis": 10000,
        "response_body_regex": "^ok$",
        "is_force_plain_text": True,
    }
    fields.update(overrides)
    return oci.load_balancer.models.HealthChecker(**fields)


def make_health_checker_module(module_obj, params, client=None, check_mode=False):
    return make_module_instance(
        module_obj,
        "OciLoadBalancerHealthCheckerModule",
        params,
        client=client,
        check_mode=check_mode,
    )


def desired_health_checker(**overrides):
    params = {
        "load_balancer_id": "lb-ocid",
        "name": "pool-a",
        "protocol": "http",
        "port": 8080,
        "return_code": 200,
        "retries": 3,
        "timeout_in_millis": 3000,
        "interval_in_millis": 10000,
        "response_body_regex": "^ok$",
        "url_path": "/health",
        "state": "present",
    }
    params.update(overrides)
    return params


def test_main_exposes_documented_update_options_name_and_present_state_only(monkeypatch):
    module_obj = load_collection_module("oci_loadbalancer_health_checker")
    captured = {}

    class FakeHealthCheckerModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["executed"] = True

    monkeypatch.setattr(
        module_obj,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule({}),
    )
    monkeypatch.setattr(
        module_obj,
        "OciLoadBalancerHealthCheckerModule",
        FakeHealthCheckerModule,
    )

    module_obj.main()

    args = captured["argument_spec"]
    assert captured["supports_check_mode"] is True
    assert args["load_balancer_id"]["required"] is True
    assert all("aliases" not in option for option in args.values())
    assert args["name"]["required"] is True
    assert args["protocol"] == {
        "type": "str",
        "choices": ["http", "tcp"],
        "default": "http",
    }
    assert args["url_path"] == {"type": "str", "default": "/"}
    assert args["port"] == {"type": "int", "default": 80}
    assert args["return_code"] == {"type": "int", "default": 200}
    assert args["retries"] == {"type": "int", "default": 3}
    assert args["timeout_in_millis"] == {"type": "int", "default": 3000}
    assert args["interval_in_millis"] == {"type": "int", "default": 10000}
    assert args["response_body_regex"] == {"type": "str", "default": ""}
    assert args["state"]["choices"] == ["present"]
    assert args["state"]["default"] == "present"
    assert "is_force_plain_text" not in args
    assert {"wait", "wait_timeout", "wait_interval"} <= set(args)
    assert "compartment_id" not in args

    validator = ModuleArgumentSpecValidator({"protocol": args["protocol"]})
    for protocol in ("http", "tcp"):
        assert not validator.validate({"protocol": protocol}).error_messages
    for protocol in ("HTTP", "udp"):
        assert validator.validate({"protocol": protocol}).error_messages


def test_parser_defaults_reset_retry_and_keep_zero_or_empty_overrides(monkeypatch):
    module_obj = load_collection_module("oci_loadbalancer_health_checker")
    captured = {}
    original_module_class = module_obj.OciLoadBalancerHealthCheckerModule

    class FakeHealthCheckerModule:
        def __init__(self, module):
            pass

        def execute_resource_module(self):
            pass

    monkeypatch.setattr(
        module_obj,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule({}),
    )
    monkeypatch.setattr(module_obj, "OciLoadBalancerHealthCheckerModule", FakeHealthCheckerModule)
    module_obj.main()
    monkeypatch.setattr(
        module_obj, "OciLoadBalancerHealthCheckerModule", original_module_class
    )
    validator = ModuleArgumentSpecValidator(captured["argument_spec"])

    omitted = validator.validate({"load_balancer_id": "lb-ocid", "name": "pool-a"})
    assert omitted.error_messages == []
    params = omitted.validated_parameters
    assert params["protocol"] == "http"
    assert params["url_path"] == "/"
    assert params["port"] == 80
    assert params["return_code"] == 200
    assert params["retries"] == 3
    assert params["timeout_in_millis"] == 3000
    assert params["interval_in_millis"] == 10000
    assert params["response_body_regex"] == ""

    overrides = validator.validate(
        {
            "load_balancer_id": "lb-ocid",
            "name": "pool-a",
            "port": 0,
            "retries": 0,
            "response_body_regex": "",
        }
    )
    assert overrides.error_messages == []
    assert overrides.validated_parameters["port"] == 0
    assert overrides.validated_parameters["retries"] == 0
    assert overrides.validated_parameters["response_body_regex"] == ""

    instance = make_health_checker_module(module_obj, params)
    current = make_health_checker(retries=7)
    assert instance.needs_update(current) is True
    plan = instance.get_update_plan(current)
    details = instance.build_update_details(plan["update_model_fields"], current)
    assert details.retries == 3
    assert details.port == 80
    assert details.response_body_regex == ""
    assert details.is_force_plain_text is True

    reset_check = make_health_checker_module(module_obj, params, check_mode=True)
    monkeypatch.setattr(reset_check, "resolve_target_resource", lambda: current)
    with pytest.raises(ExitJsonCalled) as reset_changed:
        reset_check.execute_resource_module()
    assert reset_changed.value.payload["changed"] is True

    same_defaults = make_health_checker(
        protocol="HTTP",
        url_path="/",
        port=80,
        return_code=200,
        retries=3,
        timeout_in_millis=3000,
        interval_in_millis=10000,
        response_body_regex="",
    )
    idempotent = make_health_checker_module(module_obj, params, check_mode=True)
    monkeypatch.setattr(idempotent, "resolve_target_resource", lambda: same_defaults)
    with pytest.raises(ExitJsonCalled) as unchanged:
        idempotent.execute_resource_module()
    assert unchanged.value.payload["changed"] is False


def test_health_checker_resolves_with_both_scope_parameters(monkeypatch):
    module_obj = load_collection_module("oci_loadbalancer_health_checker")
    checker = make_health_checker()
    calls = []
    instance = make_health_checker_module(
        module_obj,
        desired_health_checker(),
        client=types.SimpleNamespace(
            get_health_checker=lambda **kwargs: calls.append(kwargs) or FakeResponse(checker)
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.resolve_target_resource() is checker
    assert calls == [{"load_balancer_id": "lb-ocid", "backend_set_name": "pool-a"}]


def test_missing_health_checker_fails_even_in_check_mode(monkeypatch):
    module_obj = load_collection_module("oci_loadbalancer_health_checker")

    class NotFound(oci.exceptions.ServiceError):
        def __init__(self):
            super(NotFound, self).__init__(404, "NotFound", {}, "not found")

    instance = make_health_checker_module(
        module_obj,
        desired_health_checker(),
        client=types.SimpleNamespace(
            get_health_checker=lambda **kwargs: (_unused for _unused in ()).throw(NotFound())
        ),
        check_mode=True,
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.resolve_target_resource()
    assert "pool-a" in exc_info.value.payload["msg"]


def test_health_checker_update_specs_exclude_sdk_only_field(monkeypatch):
    module_obj = load_collection_module("oci_loadbalancer_health_checker")
    assert {spec.param_name for spec in module_obj.OciLoadBalancerHealthCheckerModule.update_field_specs} == {
        "protocol",
        "url_path",
        "port",
        "return_code",
        "retries",
        "timeout_in_millis",
        "interval_in_millis",
        "response_body_regex",
    }
    assert "is_force_plain_text" not in {
        spec.param_name for spec in module_obj.OciLoadBalancerHealthCheckerModule.update_field_specs
    }


@pytest.mark.parametrize(
    ("protocol", "expected", "current_protocol"),
    [("http", "HTTP", "TCP"), ("tcp", "TCP", "HTTP")],
)
def test_health_checker_protocol_lowercase_updates_use_uppercase_sdk_values(
    protocol, expected, current_protocol
):
    module_obj = load_collection_module("oci_loadbalancer_health_checker")
    instance = make_health_checker_module(
        module_obj, desired_health_checker(protocol=protocol)
    )
    current = make_health_checker(protocol=current_protocol)

    plan = instance.get_update_plan(current)
    details = instance.build_update_details(plan["update_model_fields"], current)

    assert plan["update_model_fields"]["protocol"] == expected
    assert details.protocol == expected


def test_partial_health_checker_update_preserves_required_and_sdk_only_values(monkeypatch):
    module_obj = load_collection_module("oci_loadbalancer_health_checker")
    instance = make_health_checker_module(module_obj, desired_health_checker())

    details = instance.build_update_details(
        {"url_path": "/ready"},
        make_health_checker(),
    )

    assert isinstance(details, oci.load_balancer.models.UpdateHealthCheckerDetails)
    assert details.protocol == "HTTP"
    assert details.url_path == "/ready"
    assert details.port == 8080
    assert details.return_code == 200
    assert details.retries == 3
    assert details.timeout_in_millis == 3000
    assert details.interval_in_millis == 10000
    assert details.response_body_regex == "^ok$"
    assert details.is_force_plain_text is True


def test_health_checker_check_mode_predicts_update_and_same_state_is_noop(monkeypatch):
    module_obj = load_collection_module("oci_loadbalancer_health_checker")
    checker = make_health_checker()
    check = make_health_checker_module(
        module_obj,
        desired_health_checker(url_path="/ready"),
        check_mode=True,
    )
    monkeypatch.setattr(check, "resolve_target_resource", lambda: checker)
    monkeypatch.setattr(
        check,
        "update_resource",
        lambda resource: pytest.fail("check mode called update_resource"),
    )

    with pytest.raises(ExitJsonCalled) as changed:
        check.execute_resource_module()
    assert changed.value.payload["changed"] is True

    noop = make_health_checker_module(
        module_obj,
        desired_health_checker(),
        check_mode=True,
    )
    monkeypatch.setattr(noop, "resolve_target_resource", lambda: checker)
    with pytest.raises(ExitJsonCalled) as unchanged:
        noop.execute_resource_module()
    assert unchanged.value.payload["changed"] is False


def test_health_checker_normal_execution_skips_lowercase_values_matching_sdk_state(
    monkeypatch,
):
    module_obj = load_collection_module("oci_loadbalancer_health_checker")
    checker = make_health_checker(protocol="HTTP")
    instance = make_health_checker_module(
        module_obj, desired_health_checker(protocol="http")
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: checker)
    monkeypatch.setattr(
        instance,
        "update_resource",
        lambda resource: pytest.fail("unchanged lowercase input called update_resource"),
    )

    with pytest.raises(ExitJsonCalled) as unchanged:
        instance.execute_resource_module()
    assert unchanged.value.payload["changed"] is False


def test_health_checker_absent_is_rejected_by_argument_choices(monkeypatch):
    module_obj = load_collection_module("oci_loadbalancer_health_checker")
    captured = {}

    class FakeHealthCheckerModule:
        def __init__(self, module):
            pass

        def execute_resource_module(self):
            pass

    monkeypatch.setattr(
        module_obj,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule({}),
    )
    monkeypatch.setattr(
        module_obj,
        "OciLoadBalancerHealthCheckerModule",
        FakeHealthCheckerModule,
    )

    module_obj.main()
    assert captured["argument_spec"]["state"]["choices"] == ["present"]


def test_health_checker_info_returns_singleton_and_normalizes_404(monkeypatch):
    module_obj = load_collection_module("oci_loadbalancer_health_checker_info")
    checker = make_health_checker()
    calls = []
    instance = make_module_instance(
        module_obj,
        "OciLoadBalancerHealthCheckerInfoModule",
        {"load_balancer_id": "lb-ocid", "name": "pool-a"},
        client=types.SimpleNamespace(
            get_health_checker=lambda **kwargs: calls.append(kwargs) or FakeResponse(checker)
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.fetch_resources() == [checker]
    assert calls == [{"load_balancer_id": "lb-ocid", "backend_set_name": "pool-a"}]

    class NotFound(oci.exceptions.ServiceError):
        def __init__(self):
            super(NotFound, self).__init__(404, "NotFound", {}, "not found")

    instance.client.get_health_checker = lambda **kwargs: (_unused for _unused in ()).throw(NotFound())
    assert instance.fetch_resources() == []


@pytest.mark.parametrize("status", [403, 500])
def test_health_checker_info_propagates_other_service_errors(monkeypatch, status):
    module_obj = load_collection_module("oci_loadbalancer_health_checker_info")
    error = oci.exceptions.ServiceError(status, "ServiceError", {}, "lookup failed")
    instance = make_module_instance(
        module_obj,
        "OciLoadBalancerHealthCheckerInfoModule",
        {"load_balancer_id": "lb-ocid", "name": "pool-a"},
        client=types.SimpleNamespace(get_health_checker=raising(error)),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    with pytest.raises(oci.exceptions.ServiceError) as exc_info:
        instance.fetch_resources()

    assert exc_info.value is error


def test_health_checker_update_calls_composite_with_backend_set_scope(monkeypatch):
    module_obj = load_collection_module("oci_loadbalancer_health_checker")
    current = make_health_checker()
    updated = make_health_checker(protocol="TCP", url_path="/ready")
    calls = []
    instance = make_health_checker_module(
        module_obj,
        desired_health_checker(
            protocol="tcp",
            url_path="/ready",
            wait=True,
            wait_timeout=21,
            wait_interval=2,
        ),
        client=types.SimpleNamespace(
            retry_strategy=None,
            get_health_checker=lambda **kwargs: FakeResponse(updated)
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    class Composite:
        def __init__(self, client):
            pass

        def update_health_checker_and_wait_for_state(self, **kwargs):
            calls.append(kwargs)
            return FakeResponse(types.SimpleNamespace(lifecycle_state="SUCCEEDED"))

    helper = importlib.import_module(
        "ansible_collections.ansible.oci.plugins.module_utils.oci_loadbalancer"
    )
    monkeypatch.setattr(helper, "oci", oci)
    monkeypatch.setattr(
        helper.oci.load_balancer,
        "LoadBalancerClientCompositeOperations",
        Composite,
    )

    result = instance.update_resource(current)
    assert result is updated
    assert calls[0]["load_balancer_id"] == "lb-ocid"
    assert calls[0]["backend_set_name"] == "pool-a"
    assert calls[0]["wait_for_states"] == ["SUCCEEDED", "FAILED"]
    assert calls[0]["waiter_kwargs"] == {
        "max_wait_seconds": 21,
        "max_interval_seconds": 2,
    }
    details = calls[0]["health_checker"]
    assert isinstance(details, oci.load_balancer.models.UpdateHealthCheckerDetails)
    assert details.protocol == "TCP"
    assert details.url_path == "/ready"
    assert details.port == 8080
    assert details.is_force_plain_text is True
