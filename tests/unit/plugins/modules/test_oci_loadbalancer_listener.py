from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import oci
import pytest
from ansible.module_utils.common.arg_spec import ModuleArgumentSpecValidator

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FakeResponse,
    load_collection_module,
    make_module_instance,
)


def make_listener(**overrides):
    fields = {
        "name": "web",
        "default_backend_set_name": "pool-a",
        "port": 80,
        "protocol": "HTTP",
        "hostname_names": ["app.example.com"],
        "path_route_set_name": None,
        "routing_policy_name": None,
        "ssl_configuration": None,
        "connection_configuration": None,
        "rule_set_names": [],
    }
    fields.update(overrides)
    return oci.load_balancer.models.Listener(**fields)


def make_listener_module(module_obj, params, client=None, check_mode=False):
    return make_module_instance(
        module_obj,
        "OciLoadBalancerListenerModule",
        params,
        client=client,
        check_mode=check_mode,
    )


def test_main_exposes_oracle_listener_options_and_standard_auth_wait(monkeypatch):
    module_obj = load_collection_module("oci_loadbalancer_listener")
    captured = {}

    class FakeListenerModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["executed"] = True

    monkeypatch.setattr(
        module_obj,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule({}),
    )
    monkeypatch.setattr(module_obj, "OciLoadBalancerListenerModule", FakeListenerModule)

    module_obj.main()

    args = captured["argument_spec"]
    assert captured["supports_check_mode"] is True
    assert captured["executed"] is True
    assert args["load_balancer_id"]["required"] is True
    assert args["name"]["required"] is True
    assert args["default_backend_set_name"] == {"type": "str"}
    assert args["port"] == {"type": "int"}
    assert args["protocol"] == {
        "type": "str",
        "choices": ["http", "http2", "grpc", "tcp"],
    }
    assert args["ssl_configuration"]["options"]["protocols"] == {
        "type": "list",
        "elements": "str",
        "choices": ["tlsv1", "tlsv1.1", "tlsv1.2", "tlsv1.3"],
    }
    assert args["ssl_configuration"]["options"]["server_order_preference"]["choices"] == [
        "enabled",
        "disabled",
    ]
    assert args["connection_configuration"]["options"]["idle_timeout"]["required"] is True
    assert args["state"]["choices"] == ["present", "absent"]
    assert {"wait", "wait_timeout", "wait_interval"} <= set(args)
    assert not ({"id", "compartment_id", "freeform_tags", "defined_tags"} & set(args))
    assert captured["executed"]

    validator = ModuleArgumentSpecValidator({"protocol": args["protocol"]})
    for protocol in ("http", "http2", "grpc", "tcp"):
        assert not validator.validate({"protocol": protocol}).error_messages
    for protocol in ("HTTP", "udp"):
        assert validator.validate({"protocol": protocol}).error_messages

    ssl_options = args["ssl_configuration"]["options"]
    tls_validator = ModuleArgumentSpecValidator(
        {"protocols": ssl_options["protocols"]}
    )
    for protocol in ("tlsv1", "tlsv1.1", "tlsv1.2", "tlsv1.3"):
        assert not tls_validator.validate({"protocols": [protocol]}).error_messages
    for value in (["TLSv1.2"], ["ssl3"]):
        assert tls_validator.validate({"protocols": value}).error_messages
    order_validator = ModuleArgumentSpecValidator(
        {"server_order_preference": ssl_options["server_order_preference"]}
    )
    for preference in ("enabled", "disabled"):
        assert not order_validator.validate({"server_order_preference": preference}).error_messages
    for preference in ("ENABLED", "automatic"):
        assert order_validator.validate({"server_order_preference": preference}).error_messages


def test_listener_lookup_uses_parent_load_balancer_listener_map(monkeypatch):
    module_obj = load_collection_module("oci_loadbalancer_listener")
    listener = make_listener()
    parent_calls = []

    def get_load_balancer(load_balancer_id):
        parent_calls.append(load_balancer_id)
        return FakeResponse(types.SimpleNamespace(listeners={"web": listener}))

    instance = make_listener_module(
        module_obj,
        {"load_balancer_id": "lb-ocid", "name": "web"},
        client=types.SimpleNamespace(get_load_balancer=get_load_balancer),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.resolve_target_resource() is listener
    assert parent_calls == ["lb-ocid"]


def test_listener_lookup_returns_missing_for_unknown_name_and_parent_404(monkeypatch):
    module_obj = load_collection_module("oci_loadbalancer_listener")
    instance = make_listener_module(
        module_obj,
        {"load_balancer_id": "lb-ocid", "name": "missing"},
        client=types.SimpleNamespace(
            get_load_balancer=lambda **kwargs: FakeResponse(
                types.SimpleNamespace(listeners={"web": make_listener()})
            )
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    assert instance.resolve_target_resource() is None

    class NotFound(oci.exceptions.ServiceError):
        def __init__(self):
            super(NotFound, self).__init__(404, "NotFound", {}, "not found")

    instance.client.get_load_balancer = lambda **kwargs: (_unused for _unused in ()).throw(NotFound())
    assert instance.resolve_target_resource() is None


def test_listener_update_specs_cover_documented_mutable_fields_only(monkeypatch):
    module_obj = load_collection_module("oci_loadbalancer_listener")
    assert {spec.param_name for spec in module_obj.OciLoadBalancerListenerModule.update_field_specs} == {
        "default_backend_set_name",
        "port",
        "protocol",
        "hostname_names",
        "path_route_set_name",
        "routing_policy_name",
        "ssl_configuration",
        "connection_configuration",
        "rule_set_names",
    }
    assert "has_session_resumption" not in {
        spec.param_name for spec in module_obj.OciLoadBalancerListenerModule.update_field_specs
    }
    assert "backend_tcp_proxy_protocol_options" not in {
        spec.param_name for spec in module_obj.OciLoadBalancerListenerModule.update_field_specs
    }


@pytest.mark.parametrize(
    ("protocol", "expected"),
    [("http", "HTTP"), ("http2", "HTTP2"), ("grpc", "GRPC"), ("tcp", "TCP")],
)
def test_listener_protocol_lowercase_updates_use_uppercase_sdk_values(protocol, expected):
    module_obj = load_collection_module("oci_loadbalancer_listener")
    instance = make_listener_module(
        module_obj,
        {"load_balancer_id": "lb-ocid", "name": "web", "protocol": protocol},
    )
    current_protocol = "HTTP" if protocol == "tcp" else "TCP"
    current = make_listener(protocol=current_protocol)

    plan = instance.get_update_plan(current)
    details = instance.build_update_details(plan["update_model_fields"], current)

    assert plan["update_model_fields"]["protocol"] == expected
    assert details.protocol == expected


def test_listener_partial_update_preserves_omitted_and_sdk_only_nested_values(monkeypatch):
    module_obj = load_collection_module("oci_loadbalancer_listener")
    instance = make_listener_module(
        module_obj,
        {
            "load_balancer_id": "lb-ocid",
            "name": "web",
            "ssl_configuration": {
                "verify_depth": 7,
                "protocols": ["tlsv1", "tlsv1.1", "tlsv1.2", "tlsv1.3"],
                "server_order_preference": "enabled",
            },
        },
    )
    current = make_listener(
        ssl_configuration=oci.load_balancer.models.SSLConfiguration(
            verify_depth=4,
            verify_peer_certificate=True,
            has_session_resumption=True,
            certificate_ids=["cert-1"],
            protocols=["TLSv1.2"],
            cipher_suite_name="suite-a",
            server_order_preference="DISABLED",
        ),
        connection_configuration=oci.load_balancer.models.ConnectionConfiguration(
            idle_timeout=1200,
            backend_tcp_proxy_protocol_version=1,
            backend_tcp_proxy_protocol_options=["PP2_TYPE_AUTHORITY"],
        ),
    )

    plan = instance.get_update_plan(current)
    details = instance.build_update_details(plan["update_model_fields"], current)

    assert isinstance(details, oci.load_balancer.models.UpdateListenerDetails)
    assert details.default_backend_set_name == "pool-a"
    assert details.port == 80
    assert details.protocol == "HTTP"
    assert details.ssl_configuration.verify_depth == 7
    assert details.ssl_configuration.verify_peer_certificate is True
    assert details.ssl_configuration.has_session_resumption is True
    assert details.ssl_configuration.certificate_ids == ["cert-1"]
    assert details.ssl_configuration.protocols == ["TLSv1", "TLSv1.1", "TLSv1.2", "TLSv1.3"]
    assert details.ssl_configuration.server_order_preference == "ENABLED"
    assert details.connection_configuration.idle_timeout == 1200
    assert details.connection_configuration.backend_tcp_proxy_protocol_options == [
        "PP2_TYPE_AUTHORITY"
    ]


def test_listener_update_and_delete_scope_to_parent_and_child_names(monkeypatch):
    module_obj = load_collection_module("oci_loadbalancer_listener")
    instance = make_listener_module(
        module_obj,
        {"load_balancer_id": "lb-ocid", "name": "web"},
    )

    assert instance.mutation_kwargs("update") == {
        "load_balancer_id": "lb-ocid",
        "listener_name": "web",
    }
    assert instance.mutation_kwargs("delete") == {
        "load_balancer_id": "lb-ocid",
        "listener_name": "web",
    }


def test_listener_check_mode_predicts_change_without_mutating_and_same_state_is_noop(monkeypatch):
    module_obj = load_collection_module("oci_loadbalancer_listener")
    current = make_listener(
        ssl_configuration=oci.load_balancer.models.SSLConfiguration(
            protocols=["TLSv1.2"],
            server_order_preference="ENABLED",
        )
    )
    calls = []
    instance = make_listener_module(
        module_obj,
        {
            "load_balancer_id": "lb-ocid",
            "name": "web",
            "default_backend_set_name": "pool-a",
            "port": 8080,
            "protocol": "http",
            "state": "present",
            "wait": True,
            "wait_timeout": 30,
            "wait_interval": 1,
        },
        client=types.SimpleNamespace(),
        check_mode=True,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: current)
    monkeypatch.setattr(
        instance,
        "update_resource",
        lambda resource: calls.append(resource) or pytest.fail("check mode mutated OCI"),
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()
    assert exc_info.value.payload["changed"] is True
    assert calls == []

    noop = make_listener_module(
        module_obj,
        {
            "load_balancer_id": "lb-ocid",
            "name": "web",
            "default_backend_set_name": "pool-a",
            "port": 80,
            "protocol": "http",
            "ssl_configuration": {
                "protocols": ["tlsv1.2"],
                "server_order_preference": "enabled",
            },
            "state": "present",
        },
        check_mode=True,
    )
    monkeypatch.setattr(noop, "resolve_target_resource", lambda: current)
    with pytest.raises(ExitJsonCalled) as noop_result:
        noop.execute_resource_module()
    assert noop_result.value.payload["changed"] is False


def test_listener_normal_execution_skips_lowercase_values_matching_sdk_state(monkeypatch):
    module_obj = load_collection_module("oci_loadbalancer_listener")
    current = make_listener(protocol="HTTP")
    instance = make_listener_module(
        module_obj,
        {"load_balancer_id": "lb-ocid", "name": "web", "protocol": "http"},
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: current)
    monkeypatch.setattr(
        instance,
        "update_resource",
        lambda resource: pytest.fail("unchanged lowercase input called update_resource"),
    )

    with pytest.raises(ExitJsonCalled) as unchanged:
        instance.execute_resource_module()
    assert unchanged.value.payload["changed"] is False


class TestListenerInfo:
    @pytest.mark.parametrize(
        "requested_name, expected_names",
        [(None, ["api", "web"]), ("api", ["api"]), ("web", ["web"]), ("API", []), ("missing", [])],
    )
    def test_fetches_parent_list_and_filters_optional_name(self, monkeypatch, requested_name, expected_names):
        module_obj = load_collection_module("oci_loadbalancer_listener_info")
        listener = make_listener()
        client = types.SimpleNamespace(
            get_load_balancer=lambda load_balancer_id: FakeResponse(
                types.SimpleNamespace(listeners={"web": listener, "api": make_listener(name="api")})
            )
        )
        instance = make_module_instance(
            module_obj,
            "OciLoadBalancerListenerInfoModule",
            {"load_balancer_id": "lb-ocid", "name": requested_name},
            client=client,
        )
        monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

        assert [resource.name for resource in instance.fetch_resources()] == expected_names

    def test_named_missing_and_parent_404_return_empty_list(self, monkeypatch):
        module_obj = load_collection_module("oci_loadbalancer_listener_info")
        instance = make_module_instance(
            module_obj,
            "OciLoadBalancerListenerInfoModule",
            {"load_balancer_id": "lb-ocid", "name": "missing"},
            client=types.SimpleNamespace(
                get_load_balancer=lambda **kwargs: FakeResponse(
                    types.SimpleNamespace(listeners={})
                )
            ),
        )
        monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
        assert instance.fetch_resources() == []

        class NotFound(oci.exceptions.ServiceError):
            def __init__(self):
                super(NotFound, self).__init__(404, "NotFound", {}, "not found")

        instance.client.get_load_balancer = lambda **kwargs: (_unused for _unused in ()).throw(NotFound())
        assert instance.fetch_resources() == []


def test_listener_create_uses_typed_sdk_details_and_waited_composite(monkeypatch):
    module_obj = load_collection_module("oci_loadbalancer_listener")
    listener = make_listener()
    calls = []
    instance = make_listener_module(
        module_obj,
        {
            "load_balancer_id": "lb-ocid",
            "name": "web",
            "default_backend_set_name": "pool-a",
            "port": 80,
            "protocol": "http",
            "ssl_configuration": {
                "protocols": ["tlsv1.2"],
                "server_order_preference": "enabled",
            },
            "wait": True,
            "wait_timeout": 17,
            "wait_interval": 3,
        },
        client=types.SimpleNamespace(
            get_load_balancer=lambda **kwargs: FakeResponse(
                types.SimpleNamespace(listeners={"web": listener})
            )
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    class Composite:
        def __init__(self, client):
            pass

        def create_listener_and_wait_for_state(self, **kwargs):
            calls.append(kwargs)
            return FakeResponse(types.SimpleNamespace(lifecycle_state="SUCCEEDED"))

    monkeypatch.setattr(
        module_obj.oci.load_balancer,
        "LoadBalancerClientCompositeOperations",
        Composite,
    )

    assert instance.create_resource() is listener
    assert calls[0]["load_balancer_id"] == "lb-ocid"
    assert calls[0]["wait_for_states"] == ["SUCCEEDED", "FAILED"]
    assert calls[0]["waiter_kwargs"] == {
        "max_wait_seconds": 17,
        "max_interval_seconds": 3,
    }
    details = calls[0]["create_listener_details"]
    assert isinstance(details, oci.load_balancer.models.CreateListenerDetails)
    assert details.name == "web"
    assert details.default_backend_set_name == "pool-a"
    assert details.port == 80
    assert details.protocol == "HTTP"
    assert details.ssl_configuration.protocols == ["TLSv1.2"]
    assert details.ssl_configuration.server_order_preference == "ENABLED"


def test_listener_delete_uses_parent_and_name_and_check_mode_skips_delete(monkeypatch):
    module_obj = load_collection_module("oci_loadbalancer_listener")
    listener = make_listener()
    instance = make_listener_module(
        module_obj,
        {
            "load_balancer_id": "lb-ocid",
            "name": "web",
            "wait": True,
        },
    )
    calls = []

    class Composite:
        def __init__(self, client):
            pass

        def delete_listener_and_wait_for_state(self, **kwargs):
            calls.append(kwargs)
            return FakeResponse(types.SimpleNamespace(lifecycle_state="SUCCEEDED"))

    monkeypatch.setattr(
        module_obj.oci.load_balancer,
        "LoadBalancerClientCompositeOperations",
        Composite,
    )
    instance.delete_resource(listener)
    assert calls[0]["load_balancer_id"] == "lb-ocid"
    assert calls[0]["listener_name"] == "web"

    check = make_listener_module(
        module_obj,
        {"load_balancer_id": "lb-ocid", "name": "web", "state": "absent"},
        check_mode=True,
    )
    monkeypatch.setattr(check, "resolve_target_resource", lambda: listener)
    monkeypatch.setattr(
        check,
        "delete_resource",
        lambda resource: pytest.fail("check mode called delete_resource"),
    )
    with pytest.raises(ExitJsonCalled) as result:
        check.execute_resource_module()
    assert result.value.payload["changed"] is True
