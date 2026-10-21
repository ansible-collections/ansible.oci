from __future__ import absolute_import, division, print_function

__metaclass__ = type

import types

import oci
import pytest

from .conftest import (
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    load_collection_module,
    make_module_instance,
)


def make_child(module_obj, class_name, params, client=None, check_mode=False):
    """Create a child module helper with a fake OCI client.

    Args:
        module_obj: Imported Ansible module.
        class_name: Resource helper class name.
        params: Ansible parameters.
        client: Optional OCI client replacement.
        check_mode: Whether Ansible check mode is active.

    Returns:
        An initialized resource helper.
    """
    return make_module_instance(
        module_obj, class_name, params, client=client, check_mode=check_mode
    )


def test_backend_set_membership_is_order_independent_and_preserves_omitted_fields():
    """Compare backend membership by name and retain unrequested settings."""
    module_obj = load_collection_module("oci_network_loadbalancer_backend_set")
    current = FakeModel(
        policy="FIVE_TUPLE",
        ip_version="IPV4",
        health_checker=FakeModel(protocol="TCP", port=80),
        backends=[
            FakeModel(
                name="a", ip_address="10.0.0.1", port=80, weight=5, is_backup=False
            ),
            FakeModel(
                name="b", ip_address="10.0.0.2", port=80, weight=2, is_backup=True
            ),
        ],
    )
    helper = make_child(
        module_obj,
        "OciNetworkLoadBalancerBackendSetModule",
        {
            "name": "pool",
            "policy": "five_tuple",
            "ip_version": "ipv4",
            "backends": [
                {"name": "b", "ip_address": "10.0.0.2", "port": 80},
                {"name": "a", "ip_address": "10.0.0.1", "port": 80},
            ],
        },
    )

    plan = helper.build_update_plan(current)

    assert not plan["update_needed"]
    assert "backends" not in plan["update_model_fields"]

    helper.module.params["backends"][0]["weight"] = 9
    plan = helper.build_update_plan(current)
    desired = {item["name"]: item for item in plan["update_model_fields"]["backends"]}
    assert plan["update_needed"]
    assert desired["a"]["weight"] == 5
    assert desired["a"]["is_backup"] is False
    assert desired["b"]["weight"] == 9
    assert desired["b"]["is_backup"] is True


def test_backend_set_rejects_duplicate_membership_names():
    """Reject ambiguous backend membership before an update."""
    module_obj = load_collection_module("oci_network_loadbalancer_backend_set")
    helper = make_child(
        module_obj,
        "OciNetworkLoadBalancerBackendSetModule",
        {"name": "pool", "backends": [{"name": "same"}, {"name": "same"}]},
    )
    current = FakeModel(backends=[])

    with pytest.raises(Exception) as exc:
        helper.build_update_plan(current)

    assert "unique" in str(getattr(exc.value, "payload", {}))


def test_backend_requires_locator_and_keeps_creation_identity_immutable():
    """Require a backend target and expose only mutable update settings."""
    module_obj = load_collection_module("oci_network_loadbalancer_backend")
    helper = make_child(
        module_obj,
        "OciNetworkLoadBalancerBackendModule",
        {"name": "backend-a", "port": 8080},
    )
    with pytest.raises(Exception) as exc:
        helper.validate_create_request()
    assert "ip_address or target_id" in str(getattr(exc.value, "payload", {}))

    names = {spec.param_name: spec.is_mutable for spec in helper.update_field_specs}
    assert names["ip_address"] is False
    assert names["target_id"] is False
    assert names["port"] is False
    assert names["weight"] is True


def test_listener_check_mode_predicts_create_without_mutation():
    """Predict listener creation in check mode without an OCI write."""
    module_obj = load_collection_module("oci_network_loadbalancer_listener")
    calls = []

    class Missing(Exception):
        status = 404

    client = types.SimpleNamespace(
        get_listener=lambda **kwargs: (unused for unused in ()).throw(Missing()),
        create_listener=lambda **kwargs: calls.append(kwargs),
    )
    helper = make_child(
        module_obj,
        "OciNetworkLoadBalancerListenerModule",
        {
            "network_load_balancer_id": "nlb",
            "name": "listener",
            "default_backend_set_name": "pool",
            "port": 80,
            "protocol": "tcp",
        },
        client=client,
        check_mode=True,
    )

    with pytest.raises(ExitJsonCalled) as exc:
        helper.execute_resource_module()

    assert exc.value.payload["changed"] is True
    assert calls == []


def test_health_checker_fails_clearly_when_backend_set_is_missing():
    """Report a missing parent backend set before health checker update."""
    module_obj = load_collection_module("oci_network_loadbalancer_health_checker")

    class Missing(Exception):
        status = 404

    helper = make_child(
        module_obj,
        "OciNetworkLoadBalancerHealthCheckerModule",
        {"network_load_balancer_id": "nlb", "name": "missing"},
        client=types.SimpleNamespace(
            get_health_checker=lambda **kwargs: (unused for unused in ()).throw(Missing())
        ),
    )

    with pytest.raises(Exception) as exc:
        helper.resolve_target_resource()

    assert "Backend set missing was not found" in str(getattr(exc.value, "payload", {}))


def test_info_get_and_list_return_named_results():
    """Fetch one named backend set and list all backend sets."""
    module_obj = load_collection_module("oci_network_loadbalancer_backend_set_info")
    pool = FakeModel(name="pool")
    calls = []
    client = types.SimpleNamespace(
        get_backend_set=lambda **kwargs: calls.append(("get", kwargs))
        or FakeResponse(pool),
        list_backend_sets=lambda **kwargs: calls.append(("list", kwargs))
        or FakeResponse([pool]),
    )
    named = make_child(
        module_obj,
        "OciNetworkLoadBalancerBackendSetInfoModule",
        {"network_load_balancer_id": "nlb", "name": "pool"},
        client=client,
    )
    assert named.fetch_resources() == [pool]

    listed = make_child(
        module_obj,
        "OciNetworkLoadBalancerBackendSetInfoModule",
        {"network_load_balancer_id": "nlb"},
        client=client,
    )
    listed.list_all_resources = lambda fn, **kwargs: calls.append(("list", kwargs)) or [
        pool
    ]
    assert listed.fetch_resources() == [pool]
    assert [call[0] for call in calls] == ["get", "list"]


def test_info_get_404_returns_empty_results():
    """Return an empty list when a named child does not exist."""
    module_obj = load_collection_module("oci_network_loadbalancer_listener_info")

    class Missing(Exception):
        status = 404

    helper = make_child(
        module_obj,
        "OciNetworkLoadBalancerListenerInfoModule",
        {"network_load_balancer_id": "nlb", "name": "missing"},
        client=types.SimpleNamespace(
            get_listener=lambda **kwargs: (unused for unused in ()).throw(Missing())
        ),
    )

    assert helper.fetch_resources() == []


@pytest.mark.parametrize(
    "kind,class_name,resource,desired",
    [
        (
            "backend",
            "OciNetworkLoadBalancerBackendModule",
            FakeModel(name="child", weight=1),
            {"weight": 2},
        ),
        (
            "backend_set",
            "OciNetworkLoadBalancerBackendSetModule",
            FakeModel(name="child", policy="FIVE_TUPLE"),
            {"policy": "three_tuple"},
        ),
        (
            "listener",
            "OciNetworkLoadBalancerListenerModule",
            FakeModel(name="child", port=80),
            {"port": 81},
        ),
        (
            "health_checker",
            "OciNetworkLoadBalancerHealthCheckerModule",
            FakeModel(protocol="TCP", retries=3),
            {"retries": 4},
        ),
    ],
)
@pytest.mark.parametrize("check_mode", [False, True])
def test_child_update_calls_correct_sdk_operation_only_outside_check_mode(
    kind, class_name, resource, desired, check_mode
):
    """Verify child update scope, model type, and check mode behavior."""
    from unittest.mock import Mock

    module_obj = load_collection_module("oci_network_loadbalancer_" + kind)
    operation = Mock(
        return_value=FakeResponse(None, {"opc-work-request-id": "request"})
    )
    getter = Mock(return_value=FakeResponse(resource))
    client = types.SimpleNamespace(
        **{"update_" + kind: operation, "get_" + kind: getter}
    )
    params = dict(
        network_load_balancer_id="nlb", name="child", backend_set_name="pool", **desired
    )
    helper = make_child(
        module_obj, class_name, params, client=client, check_mode=check_mode
    )
    helper.call_with_retry = lambda fn, *args, **kwargs: fn(*args, **kwargs)
    helper.wait_for_work_request = Mock()
    with pytest.raises(ExitJsonCalled) as result:
        helper.execute_resource_module()
    assert result.value.payload["changed"] is True
    if check_mode:
        operation.assert_not_called()
        helper.wait_for_work_request.assert_not_called()
    else:
        operation.assert_called_once()
        kwargs = operation.call_args.kwargs
        assert kwargs["network_load_balancer_id"] == "nlb"
        identity_key = (
            "backend_set_name" if kind == "health_checker" else kind + "_name"
        )
        assert kwargs[identity_key] == "child"
        if kind == "backend":
            assert kwargs["backend_set_name"] == "pool"
        model = kwargs["update_" + kind + "_details"]
        model_name = (
            "Update" + "".join(part.title() for part in kind.split("_")) + "Details"
        )
        assert isinstance(model, getattr(oci.network_load_balancer.models, model_name))
        helper.wait_for_work_request.assert_called_once_with(client, "request")


@pytest.mark.parametrize(
    "kind,class_name,resource,desired",
    [
        (
            "backend",
            "OciNetworkLoadBalancerBackendModule",
            FakeModel(name="child", ip_address="10.0.0.1", port=80, weight=2),
            {"ip_address": "10.0.0.1", "port": 80, "weight": 2},
        ),
        (
            "backend_set",
            "OciNetworkLoadBalancerBackendSetModule",
            FakeModel(
                name="child",
                policy="FIVE_TUPLE",
                health_checker=FakeModel(
                    protocol="DNS", dns=FakeModel(query_type="A", rcodes=["NOERROR"])
                ),
            ),
            {
                "policy": "five_tuple",
                "health_checker": {
                    "protocol": "dns",
                    "dns": {"query_type": "a", "rcodes": ["noerror"]},
                },
            },
        ),
        (
            "listener",
            "OciNetworkLoadBalancerListenerModule",
            FakeModel(name="child", protocol="TCP", ip_version="IPV4"),
            {"protocol": "tcp", "ip_version": "ipv4"},
        ),
        (
            "health_checker",
            "OciNetworkLoadBalancerHealthCheckerModule",
            FakeModel(
                protocol="DNS", dns=FakeModel(query_type="A", rcodes=["NOERROR"])
            ),
            {"protocol": "dns", "dns": {"query_type": "a", "rcodes": ["noerror"]}},
        ),
    ],
)
@pytest.mark.parametrize("check_mode", [False, True])
def test_child_repeated_state_is_unchanged(
    kind, class_name, resource, desired, check_mode
):
    """Keep repeated desired fields unchanged in normal and check mode."""
    module_obj = load_collection_module("oci_network_loadbalancer_" + kind)
    helper = make_child(
        module_obj, class_name, dict(name="child", **desired), check_mode=check_mode
    )
    helper.resolve_target_resource = lambda: resource
    with pytest.raises(ExitJsonCalled) as result:
        helper.execute_resource_module()
    assert result.value.payload["changed"] is False


@pytest.mark.parametrize(
    "kind,class_name,field,current,desired",
    [
        (
            "listener",
            "OciNetworkLoadBalancerListenerModule",
            "default_backend_set_name",
            "TCP",
            "tcp",
        ),
        (
            "health_checker",
            "OciNetworkLoadBalancerHealthCheckerModule",
            "response_body_regex",
            "DNS",
            "dns",
        ),
    ],
)
def test_case_sensitive_text_is_not_treated_as_an_enum(
    kind, class_name, field, current, desired
):
    """Preserve case-sensitive names and regular expressions during comparison."""
    module_obj = load_collection_module("oci_network_loadbalancer_" + kind)
    helper = make_child(module_obj, class_name, {field: desired})
    assert helper.needs_update(FakeModel(**{field: current}))


@pytest.mark.parametrize(
    "field,value",
    [("ip_address", "10.0.0.2"), ("port", 81), ("target_id", "new-target")],
)
@pytest.mark.parametrize("check_mode", [False, True])
def test_backend_identity_change_fails_before_mutation(field, value, check_mode):
    """Reject changes to backend identity in normal and check mode."""
    from .conftest import FailJsonCalled

    module_obj = load_collection_module("oci_network_loadbalancer_backend")
    helper = make_child(
        module_obj,
        "OciNetworkLoadBalancerBackendModule",
        {field: value},
        check_mode=check_mode,
    )
    helper.resolve_target_resource = lambda: FakeModel(
        ip_address="10.0.0.1", port=80, target_id="target"
    )
    with pytest.raises(FailJsonCalled) as result:
        helper.execute_resource_module()
    assert field in result.value.payload["msg"]


@pytest.mark.parametrize(
    "kind,class_name,result_key,identity_key,scope",
    [
        (
            "backend",
            "OciNetworkLoadBalancerBackendInfoModule",
            "backends",
            "backend_name",
            {"backend_set_name": "pool"},
        ),
        (
            "backend_set",
            "OciNetworkLoadBalancerBackendSetInfoModule",
            "backend_sets",
            "backend_set_name",
            {},
        ),
        (
            "listener",
            "OciNetworkLoadBalancerListenerInfoModule",
            "listeners",
            "listener_name",
            {},
        ),
        (
            "health_checker",
            "OciNetworkLoadBalancerHealthCheckerInfoModule",
            "health_checkers",
            "backend_set_name",
            {},
        ),
    ],
)
def test_info_get_uses_parent_scope_and_returns_unchanged(
    kind, class_name, result_key, identity_key, scope
):
    """Check required parent identifiers and the public result key for each info module."""
    from unittest.mock import Mock

    module_obj = load_collection_module("oci_network_loadbalancer_" + kind + "_info")
    getter = Mock(return_value=FakeResponse(FakeModel(name="child")))
    client = types.SimpleNamespace(**{"get_" + kind: getter})
    helper = make_child(
        module_obj,
        class_name,
        dict(network_load_balancer_id="nlb", name="child", **scope),
        client=client,
    )
    helper.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    with pytest.raises(ExitJsonCalled) as result:
        helper.execute_info_module()
    assert result.value.payload["changed"] is False
    assert result.value.payload[result_key] == [{"name": "child"}]
    getter.assert_called_once_with(
        network_load_balancer_id="nlb", **{identity_key: "child"}, **scope
    )


@pytest.mark.parametrize(
    "kind,class_name",
    [
        ("backend", "OciNetworkLoadBalancerBackendInfoModule"),
        ("backend_set", "OciNetworkLoadBalancerBackendSetInfoModule"),
        ("listener", "OciNetworkLoadBalancerListenerInfoModule"),
    ],
)
@pytest.mark.parametrize("status", [404, 403])
def test_info_list_only_suppresses_missing_resources(kind, class_name, status):
    """Return empty lists for missing parents and preserve authorization errors."""
    from unittest.mock import Mock

    module_obj = load_collection_module("oci_network_loadbalancer_" + kind + "_info")
    list_name = "list_" + ("backend_sets" if kind == "backend_set" else kind + "s")
    client = types.SimpleNamespace(**{list_name: Mock()})
    helper = make_child(
        module_obj,
        class_name,
        {"network_load_balancer_id": "nlb", "backend_set_name": "pool"},
        client=client,
    )
    helper.list_all_resources = Mock(
        side_effect=oci.exceptions.ServiceError(status, "error", {}, "message")
    )
    if status == 404:
        assert helper.fetch_resources() == []
    else:
        with pytest.raises(oci.exceptions.ServiceError):
            helper.fetch_resources()


@pytest.mark.parametrize("desired,changed", [(None, False), ([], True)])
def test_backend_set_distinguishes_omitted_and_empty_membership(desired, changed):
    """Preserve omitted membership and send an empty list when clearing it."""
    module_obj = load_collection_module("oci_network_loadbalancer_backend_set")
    current = FakeModel(
        policy="FIVE_TUPLE",
        health_checker=FakeModel(protocol="TCP", port=80),
        backends=[FakeModel(name="a", ip_address="10.0.0.1", port=80)],
    )
    helper = make_child(
        module_obj, "OciNetworkLoadBalancerBackendSetModule", {"backends": desired}
    )
    plan = helper.build_update_plan(current)
    assert plan["update_needed"] is changed
    if changed:
        details = helper.build_update_details(plan["update_model_fields"], current)
        assert details.backends == []
        assert details.policy == "FIVE_TUPLE"
        assert details.health_checker.protocol == "TCP"


@pytest.mark.parametrize("kind", ["backend", "backend_set"])
@pytest.mark.parametrize("fields", [{"ip_address": "10.0.0.1"}, {"port": 80}])
def test_new_backend_requires_locator_and_port_in_both_interfaces(kind, fields):
    """Validate required fields for standalone and embedded backend creation."""
    from .conftest import FailJsonCalled

    module_obj = load_collection_module("oci_network_loadbalancer_" + kind)
    params = dict(name="a", **fields)
    if kind == "backend_set":
        params = {
            "policy": "five_tuple",
            "health_checker": {"protocol": "tcp"},
            "backends": [params],
        }
    class_name = (
        "OciNetworkLoadBalancer"
        + ("BackendSet" if kind == "backend_set" else "Backend")
        + "Module"
    )
    helper = make_child(module_obj, class_name, params)
    with pytest.raises(FailJsonCalled) as result:
        helper.validate_create_request()
    assert "requires" in result.value.payload["msg"]
