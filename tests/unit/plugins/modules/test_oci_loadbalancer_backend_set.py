from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import oci
import pytest
from ansible.module_utils.common.arg_spec import ModuleArgumentSpecValidator
from oci.base_client import BaseClient

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FailJsonCalled,
    FakeModel,
    FakeResponse,
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
                return FakeResponse(FakeModel(name="pool-a", policy="ROUND_ROBIN"))

            return invoke

    monkeypatch.setattr(
        helper.oci.load_balancer,
        "LoadBalancerClientCompositeOperations",
        Composite,
    )


def _backend_set(params, *, check_mode=False, client=None):
    module = _load("oci_loadbalancer_backend_set")
    instance = make_module_instance(
        module,
        "OciLoadBalancerBackendSetModule",
        params,
        client=client or types.SimpleNamespace(),
        check_mode=check_mode,
    )
    return instance


def _backend_set_argument_spec(monkeypatch, return_captured=False):
    module = _load("oci_loadbalancer_backend_set")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule({})

    class FakeBackendSetModule:
        def __init__(self, active_module):
            self.module = active_module

        def execute_resource_module(self):
            pass

    monkeypatch.setattr(module, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(
        module, "OciLoadBalancerBackendSetModule", FakeBackendSetModule
    )
    module.main()
    if return_captured:
        return captured
    return captured["argument_spec"]


def test_main_exposes_only_resource_and_nested_parameters(monkeypatch):
    module = _load("oci_loadbalancer_backend_set")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule({})

    class FakeBackendSetModule:
        def __init__(self, active_module):
            self.module = active_module

        def execute_resource_module(self):
            captured["executed"] = True

    monkeypatch.setattr(module, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(
        module, "OciLoadBalancerBackendSetModule", FakeBackendSetModule
    )

    module.main()

    argument_spec = captured["argument_spec"]
    assert argument_spec["load_balancer_id"] == {
        "type": "str",
        "required": True,
    }
    assert argument_spec["name"] == {"type": "str", "required": True}
    assert argument_spec["policy"] == {
        "type": "str",
        "choices": ["round_robin", "least_connections", "ip_hash"],
    }
    assert argument_spec["backends"]["options"] == {
        "ip_address": {"type": "str", "required": True},
        "port": {"type": "int", "required": True},
        "weight": {"type": "int"},
        "backup": {"type": "bool"},
        "drain": {"type": "bool"},
        "offline": {"type": "bool"},
    }
    assert argument_spec["health_checker"]["options"]["protocol"] == {
        "type": "str",
        "default": "http",
        "choices": ["http", "tcp"],
    }
    assert argument_spec["health_checker"]["options"] == {
        "protocol": {"type": "str", "default": "http", "choices": ["http", "tcp"]},
        "url_path": {"type": "str", "default": "/"},
        "port": {"type": "int", "default": 80},
        "return_code": {"type": "int", "default": 200},
        "retries": {"type": "int", "default": 3},
        "timeout_in_millis": {"type": "int", "default": 3000},
        "interval_in_millis": {"type": "int", "default": 10000},
        "response_body_regex": {"type": "str", "default": ""},
    }
    assert "server_order_preference" not in argument_spec["ssl_configuration"]["options"]
    assert argument_spec["ssl_configuration"]["options"]["protocols"] == {
        "type": "list",
        "elements": "str",
        "choices": ["tlsv1", "tlsv1.1", "tlsv1.2", "tlsv1.3"],
    }
    assert argument_spec["session_persistence_configuration"]["options"]["cookie_name"] == {
        "type": "str",
        "required": True,
    }
    assert argument_spec["lb_cookie_session_persistence_configuration"]["options"][
        "max_age_in_seconds"
    ] == {"type": "int"}
    assert argument_spec["state"] == {
        "type": "str",
        "choices": ["present", "absent"],
        "default": "present",
    }
    assert "compartment_id" not in argument_spec
    assert "freeform_tags" not in argument_spec
    assert "allow_duplicate_name" not in argument_spec
    assert captured["supports_check_mode"] is True
    assert captured["mutually_exclusive"] == [
        [
            "session_persistence_configuration",
            "lb_cookie_session_persistence_configuration",
        ]
    ]
    assert captured["executed"] is True


def test_health_checker_parser_defaults_only_apply_to_supplied_dict(monkeypatch):
    argument_spec = _backend_set_argument_spec(monkeypatch)
    validator = ModuleArgumentSpecValidator(argument_spec)
    prefix = {"load_balancer_id": "lb-ocid", "name": "pool-a"}

    omitted = validator.validate(prefix)
    assert omitted.error_messages == []
    assert omitted.validated_parameters.get("health_checker") is None

    supplied = validator.validate(dict(prefix, health_checker={"url_path": "/ready"}))
    assert supplied.error_messages == []
    health_checker = supplied.validated_parameters["health_checker"]
    assert health_checker == {
        "protocol": "http",
        "url_path": "/ready",
        "port": 80,
        "return_code": 200,
        "retries": 3,
        "timeout_in_millis": 3000,
        "interval_in_millis": 10000,
        "response_body_regex": "",
    }

    explicit = validator.validate(
        dict(
            prefix,
            health_checker={
                "port": 0,
                "return_code": 0,
                "retries": 0,
                "response_body_regex": "",
            },
        )
    )
    assert explicit.error_messages == []
    assert explicit.validated_parameters["health_checker"]["port"] == 0
    assert explicit.validated_parameters["health_checker"]["return_code"] == 0
    assert explicit.validated_parameters["health_checker"]["retries"] == 0
    assert explicit.validated_parameters["health_checker"]["response_body_regex"] == ""

    backend_set = _backend_set(dict(supplied.validated_parameters))
    current = FakeModel(
        name="pool-a",
        health_checker=FakeModel(
            protocol="HTTP",
            url_path="/",
            port=80,
            return_code=200,
            retries=7,
            timeout_in_millis=3000,
            interval_in_millis=10000,
            response_body_regex="",
            is_force_plain_text=True,
        ),
    )
    assert backend_set.needs_update(current) is True
    plan = backend_set.get_update_plan(current)
    details = backend_set.build_update_details(plan["update_model_fields"], current)
    assert details.health_checker.url_path == "/ready"
    assert details.health_checker.retries == 3
    assert details.health_checker.is_force_plain_text is True

    omitted_backend_set = _backend_set(dict(omitted.validated_parameters))
    assert omitted_backend_set.needs_update(current) is False
    omitted_check = _backend_set(
        dict(omitted.validated_parameters), check_mode=True
    )
    omitted_check.resolve_target_resource = lambda: current
    with pytest.raises(ExitJsonCalled) as unchanged:
        omitted_check.execute_resource_module()
    assert unchanged.value.payload["changed"] is False

    empty_dict = validator.validate(dict(prefix, health_checker={}))
    assert empty_dict.error_messages == []
    default_values = empty_dict.validated_parameters["health_checker"]
    assert default_values["protocol"] == "http"
    assert default_values["url_path"] == "/"
    assert default_values["port"] == 80
    assert default_values["return_code"] == 200
    assert default_values["retries"] == 3
    assert default_values["timeout_in_millis"] == 3000
    assert default_values["interval_in_millis"] == 10000
    assert default_values["response_body_regex"] == ""

    default_current = FakeModel(
        name="pool-a",
        health_checker=FakeModel(
            protocol="HTTP",
            url_path="/",
            port=80,
            return_code=200,
            retries=3,
            timeout_in_millis=3000,
            interval_in_millis=10000,
            response_body_regex="",
            is_force_plain_text=True,
        ),
    )
    empty_backend_set = _backend_set(dict(empty_dict.validated_parameters))
    assert empty_backend_set.needs_update(default_current) is False
    empty_check = _backend_set(
        dict(empty_dict.validated_parameters), check_mode=True
    )
    empty_check.resolve_target_resource = lambda: default_current
    with pytest.raises(ExitJsonCalled) as unchanged_empty:
        empty_check.execute_resource_module()
    assert unchanged_empty.value.payload["changed"] is False


def test_persistence_inputs_are_mutually_exclusive(monkeypatch):
    captured = _backend_set_argument_spec(monkeypatch, return_captured=True)
    validator = ModuleArgumentSpecValidator(
        captured["argument_spec"],
        mutually_exclusive=captured["mutually_exclusive"],
    )
    result = validator.validate(
        {
            "load_balancer_id": "lb-ocid",
            "name": "pool-a",
            "session_persistence_configuration": {"cookie_name": "app"},
            "lb_cookie_session_persistence_configuration": {"cookie_name": "lb"},
        }
    )

    assert result.error_messages


@pytest.mark.parametrize(
    ("selected_field", "opposite_field", "selected_value"),
    [
        (
            "session_persistence_configuration",
            "lb_cookie_session_persistence_configuration",
            {"cookie_name": "app"},
        ),
        (
            "lb_cookie_session_persistence_configuration",
            "session_persistence_configuration",
            {"cookie_name": "lb"},
        ),
    ],
)
def test_persistence_switch_clears_opposite_with_serialized_null(
    selected_field, opposite_field, selected_value
):
    backend_set = _backend_set(
        {
            "load_balancer_id": "lb-ocid",
            "name": "pool-a",
            selected_field: selected_value,
        }
    )
    current = FakeModel(
        name="pool-a",
        policy="ROUND_ROBIN",
        **{opposite_field: FakeModel(cookie_name="old")},
    )

    update_plan = backend_set.get_update_plan(current)
    assert update_plan["update_needed"] is True
    details = backend_set.build_update_details(
        update_plan["update_model_fields"], current
    )
    client = object.__new__(BaseClient)
    client.complex_type_mappings = vars(oci.load_balancer.models)
    serialized = client.sanitize_for_serialization(details)
    opposite_api_name = "".join(
        [opposite_field.split("_")[0]]
        + [part[:1].upper() + part[1:] for part in opposite_field.split("_")[1:]]
    )

    assert serialized[opposite_api_name] is None
    assert serialized[
        "sessionPersistenceConfiguration"
        if selected_field == "session_persistence_configuration"
        else "lbCookieSessionPersistenceConfiguration"
    ]["cookieName"] == selected_value["cookie_name"]


@pytest.mark.parametrize(
    ("current_field", "current_value"),
    [
        ("session_persistence_configuration", FakeModel(cookie_name="app")),
        (
            "lb_cookie_session_persistence_configuration",
            FakeModel(cookie_name="lb"),
        ),
    ],
)
def test_persistence_omission_preserves_current_configuration(
    current_field, current_value
):
    backend_set = _backend_set(
        {"load_balancer_id": "lb-ocid", "name": "pool-a", "policy": "round_robin"}
    )
    current = FakeModel(
        name="pool-a",
        policy="ROUND_ROBIN",
        **{current_field: current_value},
    )

    details = backend_set.build_update_details({"policy": "ROUND_ROBIN"}, current)
    client = object.__new__(BaseClient)
    client.complex_type_mappings = vars(oci.load_balancer.models)
    serialized = client.sanitize_for_serialization(details)

    api_name = (
        "sessionPersistenceConfiguration"
        if current_field == "session_persistence_configuration"
        else "lbCookieSessionPersistenceConfiguration"
    )
    assert serialized[api_name]["cookieName"] == current_value.cookie_name
    opposite_api_name = (
        "lbCookieSessionPersistenceConfiguration"
        if current_field == "session_persistence_configuration"
        else "sessionPersistenceConfiguration"
    )
    assert opposite_api_name not in serialized


def test_backend_set_update_strips_ignored_ssl_server_order_preference():
    backend_set = _backend_set(
        {"load_balancer_id": "lb-ocid", "name": "pool-a", "policy": "round_robin"}
    )
    current = FakeModel(
        name="pool-a",
        policy="ROUND_ROBIN",
        ssl_configuration=FakeModel(
            server_order_preference="ENABLED", protocols=["TLSv1.2"]
        ),
    )

    details = backend_set.build_update_details({"policy": "ROUND_ROBIN"}, current)
    client = object.__new__(BaseClient)
    client.complex_type_mappings = vars(oci.load_balancer.models)
    serialized = client.sanitize_for_serialization(details)

    assert serialized["sslConfiguration"] == {"protocols": ["TLSv1.2"]}


def test_removed_ssl_server_order_preference_is_rejected(monkeypatch):
    argument_spec = _backend_set_argument_spec(monkeypatch)
    validator = ModuleArgumentSpecValidator(argument_spec)
    result = validator.validate(
        {
            "load_balancer_id": "lb-ocid",
            "name": "pool-a",
            "ssl_configuration": {"server_order_preference": "enabled"},
        }
    )

    assert result.error_messages


@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("session_persistence_configuration", {"cookie_name": "app"}),
        ("lb_cookie_session_persistence_configuration", {"cookie_name": "lb"}),
    ],
)
def test_same_persistence_configuration_is_idempotent(check_mode, field, value):
    backend_set = _backend_set(
        {"load_balancer_id": "lb-ocid", "name": "pool-a", field: value},
        check_mode=check_mode,
    )
    current = FakeModel(name="pool-a", policy="ROUND_ROBIN", **{field: FakeModel(**value)})
    backend_set.resolve_target_resource = lambda: current
    calls = []
    backend_set.update_resource = calls.append

    with pytest.raises(ExitJsonCalled) as exc:
        backend_set.execute_resource_module()

    assert exc.value.payload["changed"] is False
    assert calls == []


@pytest.mark.parametrize(
    ("parameter", "values", "invalid_values"),
    [
        (
            "policy",
            ["round_robin", "least_connections", "ip_hash"],
            ["ROUND_ROBIN", "unsupported"],
        ),
        ("health_checker.protocol", ["http", "tcp"], ["HTTP", "udp"]),
        (
            "ssl_configuration.protocols",
            ["tlsv1", "tlsv1.1", "tlsv1.2", "tlsv1.3"],
            ["TLSv1.2", "ssl3"],
        ),
    ],
)
def test_enum_arguments_validate_only_supported_lowercase_values(
    monkeypatch, parameter, values, invalid_values
):
    argument_spec = _backend_set_argument_spec(monkeypatch)
    validator = ModuleArgumentSpecValidator(argument_spec)
    prefix = {"load_balancer_id": "lb-ocid", "name": "pool-a"}

    def params_for(value):
        params = dict(prefix)
        if parameter == "policy":
            params[parameter] = value
        elif parameter == "health_checker.protocol":
            params["health_checker"] = {"protocol": value}
        else:
            params["ssl_configuration"] = {"protocols": [value]}
        return params

    for value in values:
        assert validator.validate(params_for(value)).error_messages == []
    for value in invalid_values:
        assert validator.validate(params_for(value)).error_messages


def test_create_backend_set_builds_typed_nested_models(monkeypatch):
    helper = _load_helper()
    backend_set = _backend_set(
        {
            "load_balancer_id": "lb-ocid",
            "name": "pool-a",
            "policy": "round_robin",
            "backends": [
                {
                    "ip_address": "10.0.0.7",
                    "port": 8080,
                    "weight": 0,
                    "backup": False,
                    "drain": False,
                    "offline": False,
                }
            ],
            "health_checker": {
                "protocol": "http",
                "port": 0,
                "url_path": "/health",
                "retries": 0,
            },
            "ssl_configuration": {
                "verify_peer_certificate": False,
                "verify_depth": 0,
                "protocols": ["tlsv1.2"],
            },
            "wait": False,
        }
    )
    calls = []
    _install_composite(monkeypatch, helper, calls)
    backend_set.get_resource_response = lambda name: FakeResponse(
        FakeModel(name=name, policy="ROUND_ROBIN")
    )

    backend_set.create_resource()

    operation, kwargs = calls[0]
    assert operation == "create_backend_set_and_wait_for_state"
    details = kwargs["create_backend_set_details"]
    assert isinstance(details, oci.load_balancer.models.CreateBackendSetDetails)
    assert details.name == "pool-a"
    assert details.policy == "ROUND_ROBIN"
    assert isinstance(details.backends[0], oci.load_balancer.models.BackendDetails)
    assert details.backends[0].weight == 0
    assert details.backends[0].backup is False
    assert details.health_checker.protocol == "HTTP"
    assert details.health_checker.port == 0
    assert details.health_checker.retries == 0
    assert details.ssl_configuration.verify_depth == 0
    assert details.ssl_configuration.verify_peer_certificate is False
    assert details.ssl_configuration.protocols == ["TLSv1.2"]


def test_create_validation_requires_policy_and_health_checker(monkeypatch):
    backend_set = _backend_set(
        {"load_balancer_id": "lb-ocid", "name": "pool-a"}
    )

    with pytest.raises(FailJsonCalled) as exc:
        backend_set.validate_create_request()
    assert "policy" in exc.value.payload["msg"]
    assert "health_checker" in exc.value.payload["msg"]


def test_backend_membership_is_order_independent_and_compares_only_supplied_fields():
    backend_set = _backend_set(
        {
            "load_balancer_id": "lb-ocid",
            "name": "pool-a",
            "backends": [
                {"ip_address": "10.0.0.8", "port": 8080, "weight": 5},
                {"ip_address": "10.0.0.9", "port": 8080},
            ],
            "health_checker": {"url_path": "/health"},
        }
    )
    current = FakeModel(
        name="pool-a",
        policy="ROUND_ROBIN",
        backends=[
            FakeModel(
                ip_address="10.0.0.9",
                port=8080,
                weight=1,
                backup=False,
                drain=False,
                offline=False,
            ),
            FakeModel(
                ip_address="10.0.0.8",
                port=8080,
                weight=5,
                backup=False,
                drain=False,
                offline=False,
            ),
        ],
        health_checker=FakeModel(
            protocol="HTTP",
            url_path="/health",
            port=80,
            retries=3,
            timeout_in_millis=3000,
        ),
    )

    assert backend_set.needs_update(current) is False


def test_empty_backend_list_clears_membership_and_partial_update_preserves_fields(
    monkeypatch,
):
    helper = _load_helper()
    backend_set = _backend_set(
        {
            "load_balancer_id": "lb-ocid",
            "name": "pool-a",
            "backends": [],
            "health_checker": {"url_path": "/ready"},
            "wait": False,
        }
    )
    current = oci.load_balancer.models.BackendSet(
        name="pool-a",
        policy="ROUND_ROBIN",
        backend_max_connections=100,
        health_checker=oci.load_balancer.models.HealthChecker(
            protocol="HTTP", port=80, url_path="/health", retries=3
        ),
        backends=[oci.load_balancer.models.Backend(ip_address="10.0.0.7", port=8080)],
    )

    assert backend_set.needs_update(current) is True
    update_plan = backend_set.get_update_plan(current)
    assert update_plan["update_model_fields"]["backends"] == []
    calls = []
    _install_composite(monkeypatch, helper, calls)
    backend_set.get_resource_response = lambda name: FakeResponse(current)

    backend_set.update_resource(current)

    operation, kwargs = calls[0]
    assert operation == "update_backend_set_and_wait_for_state"
    details = kwargs["update_backend_set_details"]
    assert isinstance(details, oci.load_balancer.models.UpdateBackendSetDetails)
    assert details.policy == "ROUND_ROBIN"
    assert details.backend_max_connections == 100
    assert details.backends == []
    assert details.health_checker.protocol == "HTTP"
    assert details.health_checker.port == 80
    assert details.health_checker.url_path == "/ready"
    assert details.health_checker.retries == 3


def test_backend_membership_update_preserves_omitted_existing_fields(monkeypatch):
    helper = _load_helper()
    backend_set = _backend_set(
        {
            "load_balancer_id": "lb-ocid",
            "name": "pool-a",
            "backends": [
                {"ip_address": "10.0.0.7", "port": 8080},
                {"ip_address": "10.0.0.8", "port": 8080, "weight": 2},
            ],
            "wait": False,
        }
    )
    current = oci.load_balancer.models.BackendSet(
        name="pool-a",
        policy="ROUND_ROBIN",
        backend_max_connections=100,
        backends=[
            oci.load_balancer.models.Backend(
                ip_address="10.0.0.7",
                port=8080,
                weight=5,
                max_connections=77,
                backup=False,
            )
        ],
    )
    calls = []
    _install_composite(monkeypatch, helper, calls)
    backend_set.get_resource_response = lambda name: FakeResponse(current)

    backend_set.update_resource(current)

    details = calls[0][1]["update_backend_set_details"]
    assert details.backend_max_connections == 100
    existing, new = details.backends
    assert existing.ip_address == "10.0.0.7"
    assert existing.weight == 5
    assert existing.max_connections == 77
    assert existing.backup is False
    assert new.ip_address == "10.0.0.8"
    assert new.weight == 2
    assert new.max_connections is None


def test_backend_set_check_mode_predicts_delete_without_mutation():
    backend_set = _backend_set(
        {"state": "absent", "load_balancer_id": "lb-ocid", "name": "pool-a"},
        check_mode=True,
    )
    current = FakeModel(name="pool-a", policy="ROUND_ROBIN")
    calls = []
    backend_set.resolve_target_resource = lambda: current
    backend_set.delete_resource = calls.append

    with pytest.raises(ExitJsonCalled) as exc:
        backend_set.execute_resource_module()

    assert exc.value.payload["changed"] is True
    assert calls == []


def test_backend_set_update_check_mode_predicts_change_without_mutation():
    backend_set = _backend_set(
        {"load_balancer_id": "lb-ocid", "name": "pool-a", "policy": "least_connections"},
        check_mode=True,
    )
    current = FakeModel(name="pool-a", policy="ROUND_ROBIN")
    backend_set.resolve_target_resource = lambda: current
    calls = []
    backend_set.update_resource = calls.append

    with pytest.raises(ExitJsonCalled) as exc:
        backend_set.execute_resource_module()

    assert exc.value.payload["changed"] is True
    assert calls == []


@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize(
    ("desired_policy", "sdk_policy"),
    [
        ("round_robin", "ROUND_ROBIN"),
        ("least_connections", "LEAST_CONNECTIONS"),
        ("ip_hash", "IP_HASH"),
    ],
)
def test_matching_backend_set_is_unchanged_in_normal_and_check_mode(
    check_mode, desired_policy, sdk_policy
):
    backend_set = _backend_set(
        {
            "load_balancer_id": "lb-ocid",
            "name": "pool-a",
            "policy": desired_policy,
            "health_checker": {"protocol": "http", "url_path": "/health"},
            "ssl_configuration": {
                "protocols": ["tlsv1.2"],
            },
            "backends": [{"ip_address": "10.0.0.7", "port": 8080}],
        },
        check_mode=check_mode,
    )
    current = FakeModel(
        name="pool-a",
        policy=sdk_policy,
        health_checker=FakeModel(protocol="HTTP", url_path="/health", port=80),
        ssl_configuration=FakeModel(
            server_order_preference="ENABLED", protocols=["TLSv1.2"]
        ),
        backends=[
            FakeModel(
                ip_address="10.0.0.7",
                port=8080,
                weight=1,
                backup=False,
                drain=False,
                offline=False,
            )
        ],
    )
    backend_set.resolve_target_resource = lambda: current
    calls = []
    backend_set.update_resource = calls.append

    with pytest.raises(ExitJsonCalled) as exc:
        backend_set.execute_resource_module()

    assert exc.value.payload["changed"] is False
    assert calls == []


def test_policy_update_converts_lowercase_input_to_sdk_value(monkeypatch):
    helper = _load_helper()
    backend_set = _backend_set(
        {
            "load_balancer_id": "lb-ocid",
            "name": "pool-a",
            "policy": "least_connections",
            "wait": False,
        }
    )
    current = oci.load_balancer.models.BackendSet(
        name="pool-a", policy="ROUND_ROBIN"
    )

    assert backend_set.needs_update(current) is True
    plan = backend_set.get_update_plan(current)
    assert plan["update_model_fields"]["policy"] == "LEAST_CONNECTIONS"

    calls = []
    _install_composite(monkeypatch, helper, calls)
    backend_set.get_resource_response = lambda name: FakeResponse(current)
    backend_set.update_resource(current)

    details = calls[0][1]["update_backend_set_details"]
    assert details.policy == "LEAST_CONNECTIONS"


def test_repeated_backend_set_delete_with_missing_target_is_unchanged():
    backend_set = _backend_set(
        {"state": "absent", "load_balancer_id": "lb-ocid", "name": "pool-a"}
    )
    backend_set.resolve_target_resource = lambda: None
    calls = []
    backend_set.delete_resource = calls.append

    with pytest.raises(ExitJsonCalled) as exc:
        backend_set.execute_resource_module()

    assert exc.value.payload["changed"] is False
    assert calls == []


def test_backend_set_create_check_mode_predicts_change_without_mutation():
    backend_set = _backend_set(
        {
            "load_balancer_id": "lb-ocid",
            "name": "pool-a",
            "policy": "round_robin",
            "health_checker": {"protocol": "http"},
        },
        check_mode=True,
    )
    backend_set.resolve_target_resource = lambda: None
    calls = []
    backend_set.create_resource = lambda: calls.append("create")

    with pytest.raises(ExitJsonCalled) as exc:
        backend_set.execute_resource_module()

    assert exc.value.payload["changed"] is True
    assert calls == []


def test_backend_set_absent_delete_uses_parent_and_backend_set_name(monkeypatch):
    helper = _load_helper()
    backend_set = _backend_set(
        {
            "load_balancer_id": "lb-ocid",
            "name": "pool-a",
            "wait": False,
        }
    )
    calls = []
    _install_composite(monkeypatch, helper, calls)

    backend_set.delete_resource(FakeModel(name="pool-a"))

    operation, kwargs = calls[0]
    assert operation == "delete_backend_set_and_wait_for_state"
    assert kwargs["load_balancer_id"] == "lb-ocid"
    assert kwargs["backend_set_name"] == "pool-a"


def test_backend_set_info_get_list_and_not_found_are_scoped():
    module = _load("oci_loadbalancer_backend_set_info")
    backend_set = FakeModel(name="pool-a", policy="ROUND_ROBIN")
    calls = []

    class NotFound(Exception):
        status = 404

    client = types.SimpleNamespace(
        get_backend_set=lambda **kwargs: calls.append(("get", kwargs))
        or FakeResponse(backend_set),
        list_backend_sets=lambda **kwargs: calls.append(("list", kwargs))
        or FakeResponse([backend_set]),
    )
    get_instance = make_module_instance(
        module,
        "OciLoadBalancerBackendSetInfoModule",
        {"load_balancer_id": "lb-ocid", "name": "pool-a"},
        client=client,
    )
    get_instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)

    assert get_instance.fetch_resources() == [backend_set]
    assert calls[-1] == (
        "get",
        {"load_balancer_id": "lb-ocid", "backend_set_name": "pool-a"},
    )

    list_instance = make_module_instance(
        module,
        "OciLoadBalancerBackendSetInfoModule",
        {"load_balancer_id": "lb-ocid"},
        client=client,
    )
    list_instance.list_all_resources = lambda fn, **kwargs: fn(**kwargs).data
    assert list_instance.fetch_resources() == [backend_set]
    assert calls[-1] == ("list", {"load_balancer_id": "lb-ocid"})

    missing_instance = make_module_instance(
        module,
        "OciLoadBalancerBackendSetInfoModule",
        {"load_balancer_id": "lb-ocid", "name": "missing"},
        client=types.SimpleNamespace(
            get_backend_set=lambda **kwargs: (_unused for _unused in ()).throw(
                NotFound("missing")
            )
        ),
    )
    missing_instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    assert missing_instance.fetch_resources() == []

    missing_parent_instance = make_module_instance(
        module,
        "OciLoadBalancerBackendSetInfoModule",
        {"load_balancer_id": "missing-lb"},
        client=types.SimpleNamespace(list_backend_sets=lambda **kwargs: None),
    )
    missing_parent_instance.list_all_resources = lambda fn, **kwargs: (_unused for _unused in ()).throw(
        NotFound("missing parent")
    )
    assert missing_parent_instance.fetch_resources() == []

    service_error = NotFound("service unavailable")
    service_error.status = 503
    failing_instance = make_module_instance(
        module,
        "OciLoadBalancerBackendSetInfoModule",
        {"load_balancer_id": "lb-ocid"},
        client=types.SimpleNamespace(list_backend_sets=lambda **kwargs: None),
    )
    failing_instance.list_all_resources = lambda fn, **kwargs: (_unused for _unused in ()).throw(
        service_error
    )
    with pytest.raises(NotFound):
        failing_instance.fetch_resources()
