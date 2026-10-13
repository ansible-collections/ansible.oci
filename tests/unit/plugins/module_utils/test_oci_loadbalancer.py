from __future__ import absolute_import, division, print_function
__metaclass__ = type

import copy
import types

import oci
import pytest

from .conftest import load_collection_module
from .test_oci_resource_and_info import (
    DummyModule,
    ExitJsonCalled,
    FailJsonCalled,
)


UpdateFieldSpec = load_collection_module("oci_resource").UpdateFieldSpec


def _load_helper(monkeypatch):
    helper = load_collection_module("oci_loadbalancer")
    # Other module utility tests temporarily replace sys.modules['oci']; keep
    # this model-construction and serialization coverage on the installed SDK.
    monkeypatch.setattr(helper, "oci", oci)
    oci_module_base = helper.OciResourceBase.__mro__[1]
    monkeypatch.setitem(
        oci_module_base.__init__.__globals__,
        "create_service_client",
        lambda module, client_class: types.SimpleNamespace(retry_strategy="original"),
    )
    return helper


def test_build_load_balancer_model_filters_fields_and_types_nested_values(monkeypatch):
    helper = _load_helper(monkeypatch)

    details = helper.build_load_balancer_model(
        "CreateBackendSetDetails",
        {
            "name": "pool-a",
            "policy": "ROUND_ROBIN",
            "unsupported_parameter": "ignored",
            "health_checker": {
                "protocol": "HTTP",
                "port": 8080,
                "url_path": "/health",
                "unsupported_parameter": "ignored",
            },
            "backends": [
                {"ip_address": "10.0.0.8", "port": 8080, "weight": 3},
                {"ip_address": "10.0.0.9", "port": 8080},
            ],
            "ssl_configuration": None,
        },
    )

    assert isinstance(details, oci.load_balancer.models.CreateBackendSetDetails)
    assert details.name == "pool-a"
    assert isinstance(details.health_checker, oci.load_balancer.models.HealthCheckerDetails)
    assert details.health_checker.url_path == "/health"
    assert not hasattr(details.health_checker, "unsupported_parameter")
    assert all(
        isinstance(backend, oci.load_balancer.models.BackendDetails)
        for backend in details.backends
    )
    assert details.backends[0].weight == 3
    assert details.ssl_configuration is None


@pytest.mark.parametrize(
    "key,value,expected",
    [
        ("policy", "least_connections", "LEAST_CONNECTIONS"),
        ("protocol", "http", "HTTP"),
        ("server_order_preference", "enabled", "ENABLED"),
    ],
)
def test_normalize_load_balancer_fields_converts_only_known_enum_keys(
    key, value, expected
):
    helper = load_collection_module("oci_loadbalancer")

    assert helper.normalize_load_balancer_fields({key: value}) == {key: expected}


def test_routing_policy_normalization_is_scoped_to_schema_enum_fields():
    helper = load_collection_module("oci_loadbalancer")
    fields = {
        "rules": [
            {
                "name": "KeepCase",
                "condition": "http.request.url.path eq '/Images'",
                "actions": [
                    {"backend_set_name": "PoolA"}
                ],
            }
        ],
    }

    assert helper.normalize_load_balancer_fields(fields) == {
        "rules": [
            {
                "name": "KeepCase",
                "condition": "http.request.url.path eq '/Images'",
                "actions": [
                    {"name": "FORWARD_TO_BACKENDSET", "backend_set_name": "PoolA"}
                ],
            }
        ],
    }
    assert "name" not in fields["rules"][0]["actions"][0]


def test_build_routing_policy_model_uses_typed_rules_and_actions(monkeypatch):
    helper = _load_helper(monkeypatch)
    fields = {
        "name": "image-routing",
        "rules": [
            {
                "name": "image-requests",
                "condition": "http.request.url.path eq '/Images'",
                "actions": [{"backend_set_name": "ImagePool"}],
            }
        ],
    }
    details = helper.build_load_balancer_model(
        "CreateRoutingPolicyDetails",
        fields,
    )

    assert isinstance(details, oci.load_balancer.models.CreateRoutingPolicyDetails)
    assert details.condition_language_version == "V1"
    assert isinstance(details.rules[0], oci.load_balancer.models.RoutingRule)
    assert isinstance(details.rules[0].actions[0], oci.load_balancer.models.ForwardToBackendSet)
    assert details.rules[0].condition == "http.request.url.path eq '/Images'"
    assert details.rules[0].actions[0].name == "FORWARD_TO_BACKENDSET"
    assert details.rules[0].actions[0].backend_set_name == "ImagePool"
    assert "name" not in fields["rules"][0]["actions"][0]


def test_normalize_load_balancer_fields_preserves_case_sensitive_values_and_tls_spellings():
    helper = load_collection_module("oci_loadbalancer")
    fields = {
        "ssl_configuration": {
            "protocols": ["tlsv1", "tlsv1.1", "tlsv1.2", "tlsv1.3", "tlsv1.5"],
            "cipher_suite_name": "MyCustomCipher",
        },
        "session_persistence_configuration": {"cookie_name": "SessionID"},
    }

    assert helper.normalize_load_balancer_fields(fields) == {
        "ssl_configuration": {
            "protocols": ["TLSv1", "TLSv1.1", "TLSv1.2", "TLSv1.3", "tlsv1.5"],
            "cipher_suite_name": "MyCustomCipher",
        },
        "session_persistence_configuration": {"cookie_name": "SessionID"},
    }
    assert fields["ssl_configuration"]["protocols"][0] == "tlsv1"


def test_build_model_normalizes_nested_enums_without_filling_omitted_fields(monkeypatch):
    helper = _load_helper(monkeypatch)

    details = helper.build_load_balancer_model(
        "CreateBackendSetDetails",
        {
            "policy": "least_connections",
            "health_checker": {"protocol": "http", "url_path": "/ready"},
            "ssl_configuration": {
                "protocols": ["tlsv1.2"],
                "server_order_preference": "enabled",
                "cipher_suite_name": "CustomCipher",
            },
        },
    )

    assert details.policy == "LEAST_CONNECTIONS"
    assert details.health_checker.protocol == "HTTP"
    assert details.health_checker.port is None
    assert details.ssl_configuration.protocols == ["TLSv1.2"]
    assert details.ssl_configuration.server_order_preference == "ENABLED"
    assert details.ssl_configuration.cipher_suite_name == "CustomCipher"


@pytest.mark.parametrize("sequence_type", [list, tuple])
def test_normalization_preserves_nested_values_and_input(sequence_type):
    helper = load_collection_module("oci_loadbalancer")
    fields = {
        "nested": sequence_type([
            {
                "protocols": sequence_type(["tlsv1.2", "UnknownTLS", None, 7]),
                "name": "KeepCase",
                "enabled": False,
            },
            None,
        ]),
        "protocols": sequence_type([]),
    }
    original = copy.deepcopy(fields)

    normalized = helper.normalize_load_balancer_fields(fields)

    assert normalized["nested"] == sequence_type([
        {
            "protocols": ["TLSv1.2", "UnknownTLS", None, 7],
            "name": "KeepCase",
            "enabled": False,
        },
        None,
    ])
    assert normalized["protocols"] == []
    assert fields == original


@pytest.mark.parametrize("sequence_type", [list, tuple])
def test_model_building_preserves_sdk_instances_and_backend_values(
    monkeypatch, sequence_type
):
    helper = _load_helper(monkeypatch)
    models = oci.load_balancer.models
    existing_backend = models.BackendDetails(ip_address="10.0.0.1", port=80)
    health_checker = models.HealthCheckerDetails(protocol="HTTP", port=80)
    fields = {
        "name": "PoolA",
        "policy": "round_robin",
        "health_checker": health_checker,
        "ssl_configuration": None,
        "unsupported_parameter": "ignored",
        "backends": sequence_type([
            None,
            existing_backend,
            {"ip_address": "10.0.0.2", "port": 80, "weight": 0, "backup": False},
        ]),
    }
    original = copy.deepcopy(fields)

    details = helper.build_load_balancer_model("CreateBackendSetDetails", fields)

    assert details.health_checker is health_checker
    assert details.ssl_configuration is None
    assert not hasattr(details, "unsupported_parameter")
    assert len(details.backends) == 2
    assert details.backends[0] is existing_backend
    assert isinstance(details.backends[1], models.BackendDetails)
    assert details.backends[1].ip_address == "10.0.0.2"
    assert details.backends[1].weight == 0
    assert details.backends[1].backup is False
    assert fields == original

    empty_details = helper.build_load_balancer_model(
        "CreateBackendSetDetails", {"backends": sequence_type([])}
    )
    assert empty_details.backends == []


@pytest.mark.parametrize("sequence_type", [list, tuple])
def test_routing_model_building_preserves_sdk_instances_and_order(
    monkeypatch, sequence_type
):
    helper = _load_helper(monkeypatch)
    models = oci.load_balancer.models
    existing_action = models.ForwardToBackendSet(backend_set_name="PoolA")
    existing_rule = models.RoutingRule(
        name="First",
        condition="http.request.url.path eq '/First'",
        actions=[existing_action],
    )
    fields = {
        "name": "RouteA",
        "rules": sequence_type([
            existing_rule,
            {
                "name": "Second",
                "condition": "http.request.url.path eq '/Second'",
                "actions": sequence_type([
                    existing_action,
                    {"backend_set_name": "PoolB"},
                ]),
            },
        ]),
    }
    original = copy.deepcopy(fields)

    details = helper.build_load_balancer_model("CreateRoutingPolicyDetails", fields)

    assert details.condition_language_version == "V1"
    assert details.rules[0] is existing_rule
    assert isinstance(details.rules[1], models.RoutingRule)
    assert details.rules[1].name == "Second"
    assert details.rules[1].actions[0] is existing_action
    assert isinstance(details.rules[1].actions[1], models.ForwardToBackendSet)
    assert details.rules[1].actions[1].backend_set_name == "PoolB"
    assert fields == original


def test_merge_load_balancer_fields_preserves_unsupplied_values_and_replaces_lists():
    helper = load_collection_module("oci_loadbalancer")

    merged = helper.merge_load_balancer_fields(
        {
            "policy": "ROUND_ROBIN",
            "backend_max_connections": 100,
            "health_checker": {
                "protocol": "HTTP",
                "port": 80,
                "url_path": "/old",
            },
            "backends": [{"ip_address": "10.0.0.1", "port": 80}],
        },
        {
            "health_checker": {"url_path": "/ready", "port": None},
            "backends": [{"ip_address": "10.0.0.2", "port": 80}],
        },
    )

    assert merged == {
        "policy": "ROUND_ROBIN",
        "backend_max_connections": 100,
        "health_checker": {
            "protocol": "HTTP",
            "port": 80,
            "url_path": "/ready",
        },
        "backends": [{"ip_address": "10.0.0.2", "port": 80}],
    }


def test_subset_comparison_treats_lowercase_nested_enums_as_oci_values(monkeypatch):
    helper = _load_helper(monkeypatch)

    class BackendSet(helper.OciLoadBalancerSubresourceBase):
        def get_resource_response(self, resource_id):
            raise AssertionError("comparison should not fetch a resource")

    adapter = BackendSet(DummyModule())
    current = {
        "protocol": "HTTP",
        "port": 80,
        "url_path": "/ready",
    }

    assert not adapter.compare_update_field_values(
        current,
        {"protocol": "http", "url_path": "/ready"},
        compare="subset_dict",
    )
    assert adapter.compare_update_field_values(
        current,
        {"protocol": "tcp"},
        compare="subset_dict",
    )


def test_subset_comparison_preserves_case_sensitive_names_ciphers_and_cookies(monkeypatch):
    helper = _load_helper(monkeypatch)

    class BackendSet(helper.OciLoadBalancerSubresourceBase):
        def get_resource_response(self, resource_id):
            raise AssertionError("comparison should not fetch a resource")

    adapter = BackendSet(DummyModule())
    current = {
        "ssl_configuration": {
            "certificate_name": "BackendCert",
            "cipher_suite_name": "CustomCipher",
        },
        "session_persistence_configuration": {"cookie_name": "SessionCookie"},
    }

    assert adapter.compare_update_field_values(
        current,
        {
            "ssl_configuration": {
                "certificate_name": "backendcert",
                "cipher_suite_name": "customcipher",
            },
            "session_persistence_configuration": {"cookie_name": "sessioncookie"},
        },
        compare="subset_dict",
    )


def test_enum_update_strategy_is_idempotent_and_uses_normalized_update_value(monkeypatch):
    helper = _load_helper(monkeypatch)
    resource_base = helper.OciLoadBalancerSubresourceBase

    class BackendSet(resource_base):
        update_field_specs = (
            UpdateFieldSpec(
                param_name="policy", is_mutable=True, strategy="plan_enum_update"
            ),
        )

        def get_resource_response(self, resource_id):
            raise AssertionError("planning should not fetch a resource")

    unchanged = BackendSet(DummyModule({"policy": "round_robin"}))
    unchanged_plan = unchanged.get_update_plan({"policy": "ROUND_ROBIN"})
    assert unchanged_plan["update_needed"] is False
    assert unchanged_plan["update_model_fields"] == {}

    changed = BackendSet(DummyModule({"policy": "least_connections"}))
    changed_plan = changed.get_update_plan({"policy": "ROUND_ROBIN"})
    assert changed_plan["update_needed"] is True
    assert changed_plan["update_model_fields"] == {"policy": "LEAST_CONNECTIONS"}
    assert changed_plan["strategy_operations"] == [
        {"param_name": "policy", "operations": [{"policy": "LEAST_CONNECTIONS"}]}
    ]


def test_check_mode_enum_update_reports_change_without_calling_api(monkeypatch):
    helper = _load_helper(monkeypatch)
    resource_base = helper.OciLoadBalancerSubresourceBase
    current = {"policy": "ROUND_ROBIN"}

    class CheckModeModule(DummyModule):
        def __init__(self):
            super(CheckModeModule, self).__init__({"policy": "least_connections"})
            self.check_mode = True

    class BackendSet(resource_base):
        update_method_name = "update_backend_set_and_wait_for_state"
        update_details_name = "update_backend_set_details"
        update_field_specs = (
            UpdateFieldSpec(
                param_name="policy", is_mutable=True, strategy="plan_enum_update"
            ),
        )

        def get_resource_response(self, resource_id):
            raise AssertionError("check mode should not fetch a resource")

        def resolve_target_resource(self):
            return current

        def update_resource(self, resource):
            raise AssertionError("check mode must not call the OCI update API")

    adapter = BackendSet(CheckModeModule())
    with pytest.raises(ExitJsonCalled) as exc:
        adapter.execute_resource_module()

    assert exc.value.payload["changed"] is True


def test_update_preserves_required_values_and_waits_then_reads_child(monkeypatch):
    helper = _load_helper(monkeypatch)
    resource_base = helper.OciLoadBalancerSubresourceBase

    class BackendSet(resource_base):
        update_model_name = "UpdateBackendSetDetails"
        update_method_name = "update_backend_set_and_wait_for_state"
        update_details_name = "update_backend_set_details"
        resource_name = "pool-a"
        update_field_specs = (
            UpdateFieldSpec(param_name="health_checker", is_mutable=True),
        )

        def get_resource_response(self, name):
            assert name == "pool-a"
            return types.SimpleNamespace(data=refetched)

        def mutation_kwargs(self, operation):
            return super(BackendSet, self).mutation_kwargs(operation) | {
                "backend_set_name": "pool-a"
            }

    module = DummyModule(
        {
            "load_balancer_id": "lb-ocid",
            "wait": True,
            "wait_timeout": 17,
            "wait_interval": 3,
            "health_checker": {"url_path": "/ready"},
        }
    )
    adapter = BackendSet(module)
    current = oci.load_balancer.models.BackendSet(
        name="pool-a",
        policy="ROUND_ROBIN",
        backend_max_connections=100,
        health_checker=oci.load_balancer.models.HealthChecker(
            protocol="HTTP", port=80, url_path="/old"
        ),
        backends=[oci.load_balancer.models.Backend(ip_address="10.0.0.1", port=80)],
    )
    refetched = oci.load_balancer.models.BackendSet(
        name="pool-a", policy="ROUND_ROBIN", health_checker=None
    )
    calls = []

    class Composite:
        def __init__(self, client):
            self.client = client

        def update_backend_set_and_wait_for_state(self, **kwargs):
            calls.append(kwargs)
            return types.SimpleNamespace(
                data=types.SimpleNamespace(
                    id="work-request-1", lifecycle_state="SUCCEEDED"
                )
            )

    monkeypatch.setattr(
        helper.oci.load_balancer,
        "LoadBalancerClientCompositeOperations",
        Composite,
    )
    monkeypatch.setattr(adapter, "get_update_plan", lambda resource: {
        "update_model_fields": {"health_checker": {"url_path": "/ready"}},
        "strategy_operations": [],
    })

    result = adapter.update_resource(current)

    assert result is refetched
    assert len(calls) == 1
    call = calls[0]
    assert call["wait_for_states"] == ["SUCCEEDED", "FAILED"]
    assert call["waiter_kwargs"] == {
        "max_wait_seconds": 17,
        "max_interval_seconds": 3,
    }
    details = call["update_backend_set_details"]
    assert isinstance(details, oci.load_balancer.models.UpdateBackendSetDetails)
    assert details.policy == "ROUND_ROBIN"
    assert details.backend_max_connections == 100
    assert details.backends[0].ip_address == "10.0.0.1"
    assert details.health_checker.protocol == "HTTP"
    assert details.health_checker.port == 80
    assert details.health_checker.url_path == "/ready"
    base_client = object.__new__(oci.base_client.BaseClient)
    base_client.complex_type_mappings = (
        oci.load_balancer.LoadBalancerClient.__init__.__globals__[
            "load_balancer_type_mapping"
        ]
    )
    serialized_details = base_client.sanitize_for_serialization(details)
    assert serialized_details["policy"] == "ROUND_ROBIN"
    assert serialized_details["backendMaxConnections"] == 100
    assert serialized_details["healthChecker"] == {
        "protocol": "HTTP",
        "port": 80,
        "urlPath": "/ready",
    }
    assert serialized_details["backends"] == [
        {"ipAddress": "10.0.0.1", "port": 80}
    ]


def test_create_builds_typed_details_waits_and_reads_child(monkeypatch):
    helper = _load_helper(monkeypatch)
    resource_base = helper.OciLoadBalancerSubresourceBase
    created_resource = types.SimpleNamespace(name="pool-a", policy="ROUND_ROBIN")

    class BackendSet(resource_base):
        create_model_name = "CreateBackendSetDetails"
        create_method_name = "create_backend_set_and_wait_for_state"
        create_details_name = "create_backend_set_details"
        create_required_fields = ("name", "policy")
        resource_name = "pool-a"
        update_field_specs = ()

        def get_resource_response(self, name):
            assert name == "pool-a"
            return types.SimpleNamespace(data=created_resource)

        def mutation_kwargs(self, operation):
            return {"load_balancer_id": "lb-ocid"}

    adapter = BackendSet(
        DummyModule(
            {
                "load_balancer_id": "lb-ocid",
                "name": "pool-a",
                "policy": "ROUND_ROBIN",
                "backends": [{"ip_address": "10.0.0.7", "port": 8080}],
                "wait": True,
            }
        )
    )
    calls = []

    class Composite:
        def __init__(self, client):
            pass

        def create_backend_set_and_wait_for_state(self, **kwargs):
            calls.append(kwargs)
            return types.SimpleNamespace(
                data=types.SimpleNamespace(id="work-request-create", lifecycle_state="SUCCEEDED")
            )

    monkeypatch.setattr(
        helper.oci.load_balancer,
        "LoadBalancerClientCompositeOperations",
        Composite,
    )

    result = adapter.create_resource()

    assert result is created_resource
    call = calls[0]
    assert call["wait_for_states"] == ["SUCCEEDED", "FAILED"]
    assert isinstance(
        call["create_backend_set_details"],
        oci.load_balancer.models.CreateBackendSetDetails,
    )
    assert call["create_backend_set_details"].backends[0].port == 8080


def test_delete_waits_for_successful_work_request(monkeypatch):
    helper = _load_helper(monkeypatch)
    resource_base = helper.OciLoadBalancerSubresourceBase

    class BackendSet(resource_base):
        delete_method_name = "delete_backend_set_and_wait_for_state"
        resource_name = "pool-a"
        update_field_specs = ()

        def mutation_kwargs(self, operation):
            return {"load_balancer_id": "lb-ocid", "backend_set_name": "pool-a"}

        def get_resource_response(self, name):
            raise AssertionError("delete should not read the child")

    adapter = BackendSet(
        DummyModule({"load_balancer_id": "lb-ocid", "wait": True})
    )
    calls = []

    class Composite:
        def __init__(self, client):
            pass

        def delete_backend_set_and_wait_for_state(self, **kwargs):
            calls.append(kwargs)
            return types.SimpleNamespace(
                data=types.SimpleNamespace(id="work-request-delete", lifecycle_state="SUCCEEDED")
            )

    monkeypatch.setattr(
        helper.oci.load_balancer,
        "LoadBalancerClientCompositeOperations",
        Composite,
    )

    result = adapter.delete_resource(object())

    assert result.data.id == "work-request-delete"
    assert calls[0]["wait_for_states"] == ["SUCCEEDED", "FAILED"]
    assert calls[0]["backend_set_name"] == "pool-a"


def test_wait_false_does_not_poll_and_returns_minimal_snapshot_when_child_is_not_visible(monkeypatch):
    helper = _load_helper(monkeypatch)
    resource_base = helper.OciLoadBalancerSubresourceBase

    class BackendSet(resource_base):
        update_model_name = "UpdateBackendSetDetails"
        update_method_name = "update_backend_set_and_wait_for_state"
        update_details_name = "update_backend_set_details"
        resource_name = "pool-a"
        update_field_specs = ()

        def get_resource_response(self, name):
            raise oci.exceptions.ServiceError(404, "", {}, "not found")

        def mutation_kwargs(self, operation):
            return {"load_balancer_id": "lb-ocid", "backend_set_name": "pool-a"}

    adapter = BackendSet(
        DummyModule({"load_balancer_id": "lb-ocid", "wait": False})
    )
    calls = []

    class Composite:
        def __init__(self, client):
            pass

        def update_backend_set_and_wait_for_state(self, **kwargs):
            calls.append(kwargs)
            return types.SimpleNamespace(data=object())

    monkeypatch.setattr(
        helper.oci.load_balancer,
        "LoadBalancerClientCompositeOperations",
        Composite,
    )
    monkeypatch.setattr(adapter, "get_update_plan", lambda resource: {
        "update_model_fields": {"policy": "LEAST_CONNECTIONS"},
        "strategy_operations": [],
    })

    result = adapter.update_resource(
        oci.load_balancer.models.BackendSet(name="pool-a", policy="ROUND_ROBIN")
    )

    assert result == {"name": "pool-a"}
    assert calls[0]["wait_for_states"] == []
    assert calls[0]["waiter_kwargs"] == {}
    assert (
        calls[0]["operation_kwargs"]["retry_strategy"]
        is oci.retry.DEFAULT_RETRY_STRATEGY
    )


def test_non_not_found_read_error_fails_with_operation_context(monkeypatch):
    helper = _load_helper(monkeypatch)
    resource_base = helper.OciLoadBalancerSubresourceBase

    class BackendSet(resource_base):
        resource_name = "pool-a"
        update_field_specs = ()

        def get_resource_response(self, name):
            raise oci.exceptions.ServiceError(500, "Unavailable", {}, "service down")

    adapter = BackendSet(
        DummyModule({"load_balancer_id": "lb-ocid", "wait": False})
    )
    with pytest.raises(FailJsonCalled) as exc:
        adapter._read_after_operation("update")

    assert "read load balancer subresource after update" in exc.value.payload["msg"]
    assert "service down" in exc.value.payload["msg"]


def test_failed_work_request_includes_request_id_and_error_details(monkeypatch):
    helper = _load_helper(monkeypatch)
    resource_base = helper.OciLoadBalancerSubresourceBase

    class BackendSet(resource_base):
        create_model_name = "CreateBackendSetDetails"
        create_method_name = "create_backend_set_and_wait_for_state"
        create_details_name = "create_backend_set_details"
        resource_name = "pool-a"
        update_field_specs = ()

        def mutation_kwargs(self, operation):
            return {"load_balancer_id": "lb-ocid"}

        def get_resource_response(self, name):
            raise AssertionError("failed create should not read the child")

    adapter = BackendSet(DummyModule({"load_balancer_id": "lb-ocid", "wait": True}))

    class Composite:
        def __init__(self, client):
            pass

        def create_backend_set_and_wait_for_state(self, **kwargs):
            return types.SimpleNamespace(
                data=types.SimpleNamespace(
                    id="work-request-42",
                    lifecycle_state="FAILED",
                    error_details=[
                        types.SimpleNamespace(error_code="BadRequest", message="bad pool")
                    ],
                )
            )

    monkeypatch.setattr(
        helper.oci.load_balancer,
        "LoadBalancerClientCompositeOperations",
        Composite,
    )
    with pytest.raises(FailJsonCalled) as exc:
        adapter.create_resource()

    assert "work-request-42" in exc.value.payload["msg"]
    assert "BadRequest: bad pool" in exc.value.payload["msg"]


def test_composite_timeout_fails_with_operation_context(monkeypatch):
    helper = _load_helper(monkeypatch)
    resource_base = helper.OciLoadBalancerSubresourceBase

    class BackendSet(resource_base):
        update_method_name = "update_backend_set_and_wait_for_state"
        update_details_name = "update_backend_set_details"
        update_field_specs = ()

        def mutation_kwargs(self, operation):
            return {"load_balancer_id": "lb-ocid", "backend_set_name": "pool-a"}

        def get_resource_response(self, name):
            raise AssertionError("timeout should fail before reading the child")

    adapter = BackendSet(
        DummyModule({"load_balancer_id": "lb-ocid", "wait": True})
    )

    class Composite:
        def __init__(self, client):
            pass

        def update_backend_set_and_wait_for_state(self, **kwargs):
            partial_result = types.SimpleNamespace(
                headers={"opc-work-request-id": "work-request-43"}
            )
            raise oci.exceptions.CompositeOperationError(
                partial_results=[partial_result],
                cause=oci.exceptions.MaximumWaitTimeExceeded("timed out"),
            )

    monkeypatch.setattr(
        helper.oci.load_balancer,
        "LoadBalancerClientCompositeOperations",
        Composite,
    )
    with pytest.raises(FailJsonCalled) as exc:
        adapter._composite_call("update", "update_backend_set_and_wait_for_state")

    assert "update" in exc.value.payload["msg"]
    assert "work-request-43" in exc.value.payload["msg"]
    assert "timed out" in exc.value.payload["msg"].lower()
