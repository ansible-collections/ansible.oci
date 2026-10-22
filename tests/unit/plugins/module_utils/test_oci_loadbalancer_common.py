"""Test shared load balancer models, declarations, and scoped lookups."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import copy
import inspect
import types

import oci
import pytest

from .conftest import load_collection_module


@pytest.mark.parametrize(
    "service,builder_name",
    [
        ("oci_loadbalancer", "build_load_balancer_model"),
        ("oci_network_loadbalancer", "build_network_load_balancer_model"),
    ],
)
@pytest.mark.parametrize("sequence_type", [list, tuple])
def test_service_builders_share_construction_and_preserve_values(
    monkeypatch, service, builder_name, sequence_type
):
    """Use the common constructor for parent and nested service models."""
    helper = load_collection_module(service)
    monkeypatch.setattr(helper, "oci", oci)
    models = (
        oci.load_balancer.models
        if service == "oci_loadbalancer"
        else oci.network_load_balancer.models
    )
    existing = models.BackendDetails(ip_address="10.0.0.1", port=80)
    offline_field = "offline" if service == "oci_loadbalancer" else "is_offline"
    fields = {
        "name": "MixedCasePool",
        "health_checker": {"protocol": "http", "port": 0, "unknown": "ignored"},
        "backends": sequence_type(
            [
                None,
                existing,
                {
                    "ip_address": "10.0.0.2",
                    "port": 80,
                    "weight": 0,
                    offline_field: False,
                },
            ]
        ),
        "policy": None,
        "unknown": {"protocol": "Unchanged"},
    }
    original = copy.deepcopy(fields)
    calls = []
    builder_globals = helper.build_nested_model.__globals__
    original_builder = builder_globals["build_model"]

    def capture_model(source, model_class, **kwargs):
        calls.append(model_class)
        return original_builder(source, model_class, **kwargs)

    monkeypatch.setitem(builder_globals, "build_model", capture_model)
    result = getattr(helper, builder_name)("CreateBackendSetDetails", fields)

    assert calls == [
        models.HealthCheckerDetails,
        models.BackendDetails,
        models.CreateBackendSetDetails,
    ]
    assert result.name == "MixedCasePool"
    assert result.health_checker.protocol == "HTTP"
    assert result.health_checker.port == 0
    assert len(result.backends) == 2
    assert result.backends[0] is existing
    assert result.backends[1].weight == 0
    assert getattr(result.backends[1], offline_field) is False
    assert result.policy is None
    assert not hasattr(result, "unknown")
    assert not hasattr(result.health_checker, "unknown")
    assert fields == original
    empty = getattr(helper, builder_name)("CreateBackendSetDetails", {"backends": []})
    assert empty.backends == []
    assert (
        getattr(helper, builder_name)("CreateBackendSetDetails", None).backends is None
    )


def test_routing_lists_preserve_none_and_unknown_actions(monkeypatch):
    """Keep routing list behavior while backend lists remove None entries."""
    helper = load_collection_module("oci_loadbalancer")
    monkeypatch.setattr(helper, "oci", oci)
    fields = {
        "rules": [
            None,
            {
                "name": "RuleA",
                "condition": "KeepCase",
                "actions": [None, {"name": "UNSUPPORTED", "backend_set_name": "PoolA"}],
            },
        ],
    }
    original = copy.deepcopy(fields)
    result = helper.build_load_balancer_model("CreateRoutingPolicyDetails", fields)

    assert result.rules[0] is None
    assert result.rules[1].actions == [
        None,
        {"name": "UNSUPPORTED", "backend_set_name": "PoolA"},
    ]
    assert result.condition_language_version == "V1"
    assert fields == original


@pytest.mark.parametrize(
    "missing_hook",
    [
        "build_resource_model",
        "invoke_resource_operation",
        "mutation_kwargs",
        "update_field_specs",
    ],
)
def test_incomplete_subresource_cannot_be_instantiated(missing_hook):
    """Require each service hook and explicit update declarations."""
    helper = load_collection_module("oci_loadbalancer_common")
    declarations = {
        "build_resource_model": lambda self, *args: None,
        "invoke_resource_operation": lambda self, *args, **kwargs: None,
        "mutation_kwargs": lambda self, operation: {},
        "get_resource_response": lambda self, resource_id: None,
        "update_field_specs": (),
    }
    del declarations[missing_hook]
    incomplete = type(
        "IncompleteSubresource",
        (helper.OciLoadBalancerSubresourceCommonBase,),
        declarations,
    )

    with pytest.raises(TypeError, match=missing_hook):
        incomplete(None)


@pytest.mark.parametrize(
    "service,class_prefix,kinds",
    [
        (
            "oci_loadbalancer",
            "OciLoadBalancer",
            ("backend", "backend_set", "listener", "health_checker", "routing_policy"),
        ),
        (
            "oci_network_loadbalancer",
            "OciNetworkLoadBalancer",
            ("backend", "backend_set", "listener", "health_checker"),
        ),
    ],
)
def test_concrete_modules_define_fixed_update_fields(service, class_prefix, kinds):
    """Confirm that each concrete child satisfies the abstract declarations."""
    for kind in kinds:
        module = load_collection_module(service + "_" + kind, plugin_dir="modules")
        cls = getattr(
            module,
            class_prefix + "".join(word.title() for word in kind.split("_")) + "Module",
        )
        assert not inspect.isabstract(cls)
        assert isinstance(cls.__dict__["update_field_specs"], tuple)


def _info_helper(params):
    """Create a scoped info helper without making an OCI client."""
    common = load_collection_module("oci_loadbalancer_common")
    helper = object.__new__(common.OciLoadBalancerInfoCommonBase)
    helper.module = types.SimpleNamespace(params=params)
    helper.get_scope_params = ("load_balancer_id", "backend_set_name")
    helper.resource_id_param = "name"
    helper.resource_id_kwarg = "backend_name"
    helper.resource_get_method = "get_backend"
    helper.list_resource_method = "list_backends"
    helper.list_filter_params = helper.get_scope_params
    helper.name_response_field = "name"
    helper.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    helper.list_all_resources = lambda fn, **kwargs: fn(**kwargs).data
    return helper


def test_info_scope_preserves_explicit_getter_arguments():
    """Use explicit parent IDs and omit unset scope parameters."""
    helper = _info_helper({"load_balancer_id": "from-module", "backend_set_name": None})
    captured = {}
    resource = object()

    def get_backend(**kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(data=resource)

    result = helper.get_resource_by_id(
        "BackendA", get_backend, load_balancer_id="explicit", backend_name="BackendA"
    )

    assert result == [resource]
    assert captured == {"load_balancer_id": "explicit", "backend_name": "BackendA"}


@pytest.mark.parametrize("name", [None, "BackendA"])
def test_info_get_and_list_use_declared_parent_scope(name):
    """Pass the configured scope to get and list operations."""
    helper = _info_helper(
        {"load_balancer_id": "lb1", "backend_set_name": "PoolA", "name": name}
    )
    resources = [
        types.SimpleNamespace(name="BackendA"),
        types.SimpleNamespace(name="BackendB"),
    ]
    calls = []
    helper.client = types.SimpleNamespace(
        get_backend=lambda **kwargs: calls.append(("get", kwargs))
        or types.SimpleNamespace(data=resources[0]),
        list_backends=lambda **kwargs: calls.append(("list", kwargs))
        or types.SimpleNamespace(data=resources),
    )

    assert helper.fetch_resources() == ([resources[0]] if name else resources)
    expected = {"load_balancer_id": "lb1", "backend_set_name": "PoolA"}
    if name:
        expected["backend_name"] = name
    assert calls == [("get" if name else "list", expected)]


@pytest.mark.parametrize("name", [None, "BackendA"])
@pytest.mark.parametrize("status", [404, 403, 500])
def test_info_only_suppresses_missing_resources(name, status):
    """Return empty results for 404 and propagate other errors unchanged."""
    helper = _info_helper({"load_balancer_id": "lb1", "name": name})
    error = oci.exceptions.ServiceError(status, "ServiceError", {}, "request failed")

    def fail(**kwargs):
        raise error

    helper.client = types.SimpleNamespace(get_backend=fail, list_backends=fail)
    if status == 404:
        assert helper.fetch_resources() == []
    else:
        with pytest.raises(oci.exceptions.ServiceError) as caught:
            helper.fetch_resources()
        assert caught.value is error


def test_merge_load_balancer_fields_preserves_unsupplied_values_and_replaces_lists():
    """Preserve omitted fields and replace explicitly supplied lists."""
    helper = load_collection_module("oci_loadbalancer_common")

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


def test_info_does_not_hide_unrelated_errors_with_a_status_attribute():
    """Only OCI service errors can report a missing scoped resource."""
    helper = _info_helper({"load_balancer_id": "lb1", "name": None})
    error = RuntimeError("local failure")
    error.status = 404

    def fail(**kwargs):
        raise error

    helper.client = types.SimpleNamespace(list_backends=fail)
    with pytest.raises(RuntimeError) as caught:
        helper.fetch_resources()
    assert caught.value is error


@pytest.mark.parametrize(
    "current,desired,expected",
    [
        (None, {"enabled": False}, {"enabled": False}),
        ({"port": 80}, None, {"port": 80}),
        (None, None, {}),
    ],
)
def test_merge_load_balancer_fields_accepts_missing_models(current, desired, expected):
    """Serialize missing resources before merging their fields."""
    helper = load_collection_module("oci_loadbalancer_common")
    assert helper.merge_load_balancer_fields(current, desired) == expected


def test_merge_load_balancer_fields_serializes_sdk_models():
    """Merge SDK model fields and preserve omitted current settings."""
    helper = load_collection_module("oci_loadbalancer_common")
    models = oci.network_load_balancer.models
    current = models.HealthChecker(protocol="TCP", port=80, retries=3)
    desired = models.HealthCheckerDetails(retries=4)

    merged = helper.merge_load_balancer_fields(current, desired)

    assert merged["protocol"] == "TCP"
    assert merged["port"] == 80
    assert merged["retries"] == 4
    assert current.retries == 3
    assert desired.port is None
