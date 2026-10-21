from __future__ import absolute_import, division, print_function

__metaclass__ = type

import types
from unittest.mock import Mock

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


def make_parent(params, resource=None, check_mode=False):
    """Create a parent adapter with mocked SDK operations.

    Args:
        params: Module parameters.
        resource: Resource returned by the get operation.
        check_mode: Whether to predict changes only.

    Returns:
        An adapter with isolated SDK calls.
    """
    module = load_collection_module("oci_network_loadbalancer")
    client = types.SimpleNamespace(
        get_network_load_balancer=Mock(return_value=FakeResponse(resource)),
        create_network_load_balancer=Mock(
            return_value=FakeResponse(
                FakeModel(id="nlb", lifecycle_state="CREATING"),
                {"opc-work-request-id": "create-request"},
            )
        ),
        update_network_load_balancer=Mock(
            return_value=FakeResponse(
                None,
                {"opc-work-request-id": "update-request"},
            )
        ),
        update_network_security_groups=Mock(
            return_value=FakeResponse(
                None,
                {"opc-work-request-id": "nsg-request"},
            )
        ),
        delete_network_load_balancer=Mock(
            return_value=FakeResponse(
                None,
                {"opc-work-request-id": "delete-request"},
            )
        ),
    )
    helper = make_module_instance(
        module,
        "OciNetworkLoadBalancerModule",
        params,
        client=client,
        check_mode=check_mode,
    )
    helper.call_with_retry = lambda operation, *args, **kwargs: operation(
        *args, **kwargs
    )
    helper.wait_for_work_request = Mock()
    return helper


@pytest.mark.parametrize("mode,expected", [("ipv4", "IPV4"), ("ipv6", "IPV4_AND_IPV6")])
def test_create_model_preserves_tags_and_maps_ip_mode(mode, expected):
    """Check typed reserved addresses and service-specific IP mapping."""
    module = load_collection_module("oci_network_loadbalancer")
    details = module.build_create_network_load_balancer_details(
        {
            "name": "MixedCase",
            "compartment_id": "compartment",
            "subnet_id": "subnet",
            "ip_mode": mode,
            "is_private": False,
            "reserved_ips": [{"id": "reserved"}],
            "freeform_tags": {"nlb_ip_version": "KeepCase", "protocol": "MixedCase"},
        }
    )
    assert details.nlb_ip_version == expected
    assert details.subnet_id == "subnet"
    assert details.display_name == "MixedCase"
    assert details.is_private is False
    assert isinstance(
        details.reserved_ips[0], oci.network_load_balancer.models.ReservedIP
    )
    assert details.freeform_tags == {
        "nlb_ip_version": "KeepCase",
        "protocol": "MixedCase",
    }


@pytest.mark.parametrize("mode,current", [("ipv4", "IPV4"), ("ipv6", "IPV4_AND_IPV6")])
def test_repeated_ip_mode_is_unchanged(mode, current):
    """Check that mapped modes compare against the actual SDK value."""
    resource = FakeModel(id="nlb", nlb_ip_version=current)
    helper = make_parent({"ip_mode": mode}, resource)
    assert not helper.needs_update(resource)


def test_reserved_ip_transition_preserves_existing_addresses():
    """Send only the new reserved IPv6 identifier to the update API."""
    resource = FakeModel(
        id="nlb",
        nlb_ip_version="IPV4",
        ip_addresses=[
            {"reserved_ip": {"id": "existing"}},
        ],
    )
    helper = make_parent(
        {
            "ip_mode": "ipv6",
            "reserved_ips": [{"id": "existing"}, {"id": "new"}],
        },
        resource,
    )
    details = helper.build_update_details(
        helper.get_update_plan(resource)["update_model_fields"]
    )
    assert details.reserved_ipv6_id == "new"
    assert details.nlb_ip_version == "IPV4_AND_IPV6"
    assert not hasattr(details, "reserved_ips")


@pytest.mark.parametrize("reserved", [[], [{"id": "existing"}]])
def test_reserved_ip_subset_or_empty_input_is_unchanged(reserved):
    """Preserve attached addresses omitted from the desired list."""
    resource = FakeModel(
        id="nlb",
        nlb_ip_version="IPV4_AND_IPV6",
        ip_addresses=[
            {"reserved_ip": {"id": "existing"}},
            {"reserved_ip": {"id": "unmanaged"}},
        ],
    )
    assert not make_parent({"reserved_ips": reserved}, resource).needs_update(resource)


@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize(
    "current,mode,ids",
    [
        ("IPV4_AND_IPV6", "ipv6", ["new"]),
        ("IPV4", None, ["new"]),
        ("IPV4", "ipv6", ["new", "another"]),
    ],
)
def test_invalid_reserved_additions_fail_without_mutation(
    check_mode, current, mode, ids
):
    """Reject unsupported reserved address changes before SDK mutations."""
    resource = FakeModel(id="nlb", nlb_ip_version=current, ip_addresses=[])
    helper = make_parent(
        {
            "network_load_balancer_id": "nlb",
            "ip_mode": mode,
            "reserved_ips": [{"id": value} for value in ids],
        },
        resource,
        check_mode,
    )
    with pytest.raises(FailJsonCalled) as error:
        helper.execute_resource_module()
    assert "one reserved IPv6" in error.value.payload["msg"]
    helper.client.update_network_load_balancer.assert_not_called()


@pytest.mark.parametrize(
    "field,value",
    [
        ("assigned_ipv6", "2001:db8:0:0:0:0:0:5"),
        ("subnet_ipv6_cidr", "2001:db8::/64"),
        ("assigned_private_ipv4", "10.0.0.5"),
    ],
)
def test_address_options_match_actual_addresses(field, value):
    """Compare address options with canonical addresses and prefix membership."""
    resource = FakeModel(
        id="nlb",
        ip_addresses=[
            {"ip_address": "2001:db8::5", "is_public": False},
            {"ip_address": "10.0.0.5", "is_public": False},
        ],
    )
    assert not make_parent({field: value}, resource).needs_update(resource)


def test_ipv6_address_change_requires_enablement():
    """Reject address replacement on an existing dual-stack resource."""
    resource = FakeModel(id="nlb", nlb_ip_version="IPV4_AND_IPV6", ip_addresses=[])
    helper = make_parent({"assigned_ipv6": "2001:db8::8", "ip_mode": "ipv6"}, resource)
    with pytest.raises(FailJsonCalled):
        helper.needs_update(resource)


def test_private_ipv4_does_not_match_a_public_address():
    """Reject a public address supplied as the assigned private address."""
    resource = FakeModel(
        id="nlb", ip_addresses=[{"ip_address": "192.0.2.5", "is_public": True}]
    )
    helper = make_parent({"assigned_private_ipv4": "192.0.2.5"}, resource)
    with pytest.raises(FailJsonCalled):
        helper.needs_update(resource)


@pytest.mark.parametrize("wait", [False, True])
def test_combined_update_waits_between_operations_and_reads_once(wait):
    """Wait for the parent update before changing security groups."""
    resource = FakeModel(
        id="nlb", display_name="before", network_security_group_ids=["old"]
    )
    latest = FakeModel(
        id="nlb", display_name="after", network_security_group_ids=["new"]
    )
    helper = make_parent(
        {"name": "after", "network_security_group_ids": ["new"], "wait": wait}, latest
    )
    events = []
    helper.client.update_network_load_balancer.side_effect = lambda **kwargs: (
        events.append("parent") or FakeResponse(None, {"opc-work-request-id": "parent"})
    )
    helper.client.update_network_security_groups.side_effect = lambda **kwargs: (
        events.append("groups") or FakeResponse(None, {"opc-work-request-id": "groups"})
    )
    helper.wait_for_work_request.side_effect = (
        lambda client, request, **kwargs: events.append("wait:" + request)
    )
    assert helper.update_resource(resource) is latest
    assert events == ["parent", "wait:parent", "groups"] + (
        ["wait:groups"] if wait else []
    )
    helper.client.get_network_load_balancer.assert_called_once_with("nlb")
    details = helper.client.update_network_security_groups.call_args.kwargs[
        "update_network_security_groups_details"
    ]
    assert details.network_security_group_ids == ["new"]


@pytest.mark.parametrize("wait", [False, True])
def test_create_returns_completed_or_immediate_resource(wait):
    """Refetch after waiting and preserve the immediate result otherwise."""
    ready = FakeModel(id="nlb", lifecycle_state="ACTIVE")
    helper = make_parent({"wait": wait}, ready)
    result = helper.create_resource()
    assert result.lifecycle_state == ("ACTIVE" if wait else "CREATING")
    assert helper.client.get_network_load_balancer.call_count == int(wait)
    assert helper.wait_for_work_request.call_count == int(wait)


@pytest.mark.parametrize("status", [404, 403])
def test_nonwaiting_update_only_uses_identifier_fallback_for_missing_resource(status):
    """Preserve service errors and allow an identifier result only for 404."""
    resource = oci.network_load_balancer.models.NetworkLoadBalancer(
        id="nlb", display_name="before"
    )
    helper = make_parent({"name": "after", "wait": False}, resource)
    helper.client.get_network_load_balancer.side_effect = oci.exceptions.ServiceError(
        status, "error", {}, "message"
    )
    if status == 404:
        assert helper.update_resource(resource) == {"id": "nlb"}
    else:
        with pytest.raises(oci.exceptions.ServiceError):
            helper.update_resource(resource)


@pytest.mark.parametrize(
    "state,resource,params",
    [
        (
            "present",
            None,
            {"name": "nlb", "compartment_id": "compartment", "subnet_id": "subnet"},
        ),
        (
            "present",
            FakeModel(id="nlb", display_name="before"),
            {"network_load_balancer_id": "nlb", "name": "after"},
        ),
        ("absent", FakeModel(id="nlb"), {"network_load_balancer_id": "nlb"}),
    ],
)
def test_check_mode_predicts_without_mutating(state, resource, params):
    """Cover create, update, and delete through the inherited check-mode flow."""
    helper = make_parent(dict(params, state=state), resource, check_mode=True)
    helper.resolve_target_resource = lambda: resource
    with pytest.raises(ExitJsonCalled) as result:
        helper.execute_resource_module()
    assert result.value.payload["changed"] is True
    helper.client.create_network_load_balancer.assert_not_called()
    helper.client.update_network_load_balancer.assert_not_called()
    helper.client.delete_network_load_balancer.assert_not_called()


@pytest.mark.parametrize("check_mode", [False, True])
def test_present_and_absent_repeats_are_unchanged(check_mode):
    """Verify repeated desired states in normal mode and check mode."""
    for state, resource in [
        ("present", FakeModel(id="nlb", display_name="same")),
        ("absent", None),
    ]:
        helper = make_parent(
            {"state": state, "network_load_balancer_id": "nlb", "name": "same"},
            resource,
            check_mode,
        )
        with pytest.raises(ExitJsonCalled) as result:
            helper.execute_resource_module()
        assert result.value.payload["changed"] is False


def test_main_keeps_existing_load_balancer_ip_interface(monkeypatch):
    """Expose only the approved IP options and unchanged mutable defaults."""
    module = load_collection_module("oci_network_loadbalancer")
    captured = {}

    def construct(**kwargs):
        """Capture the Ansible argument specification."""
        captured.update(kwargs)
        return DummyModule({})

    monkeypatch.setattr(module, "AnsibleModule", construct)
    monkeypatch.setattr(
        module,
        "OciNetworkLoadBalancerModule",
        lambda value: types.SimpleNamespace(execute_resource_module=lambda: None),
    )
    module.main()
    spec = captured["argument_spec"]
    assert spec["ip_mode"] == {"type": "str", "choices": ["ipv4", "ipv6"]}
    assert "nlb_ip_version" not in spec
    assert "reserved_ipv6_id" not in spec
    assert "default" not in spec["is_private"]
    assert captured["supports_check_mode"]


def test_info_lists_all_pages_with_compartment_and_uppercase_state():
    """Use SDK pagination for collection responses and preserve IP result values."""
    module = load_collection_module("oci_network_loadbalancer_info")
    models = oci.network_load_balancer.models
    client = types.SimpleNamespace(
        list_network_load_balancers=Mock(
            side_effect=[
                oci.response.Response(
                    200,
                    {"opc-next-page": "next"},
                    models.NetworkLoadBalancerCollection(
                        items=[
                            models.NetworkLoadBalancerSummary(
                                id="first",
                                display_name="same",
                                nlb_ip_version="IPV4_AND_IPV6",
                            ),
                        ]
                    ),
                    None,
                ),
                oci.response.Response(
                    200,
                    {},
                    models.NetworkLoadBalancerCollection(
                        items=[
                            models.NetworkLoadBalancerSummary(
                                id="second", display_name="other"
                            ),
                        ]
                    ),
                    None,
                ),
            ]
        )
    )
    client.list_network_load_balancers.__name__ = "list_network_load_balancers"
    helper = make_module_instance(
        module,
        "OciNetworkLoadBalancerInfoModule",
        {
            "compartment_id": "compartment",
            "lifecycle_state": "active",
            "name": "same",
        },
        client=client,
    )
    with pytest.raises(ExitJsonCalled) as result:
        helper.execute_info_module()
    data = result.value.payload
    assert data["changed"] is False
    assert [item["id"] for item in data["network_load_balancers"]] == ["first"]
    assert data["network_load_balancers"][0]["ip_mode"] == "IPV4_AND_IPV6"
    assert client.list_network_load_balancers.call_count == 2
    for call in client.list_network_load_balancers.call_args_list:
        assert call.kwargs["compartment_id"] == "compartment"
        assert call.kwargs["lifecycle_state"] == "ACTIVE"


@pytest.mark.parametrize("status", [404, 403])
def test_info_get_handles_only_missing_resource_as_empty(status):
    """Return an empty list for a missing resource and preserve authorization errors."""
    module = load_collection_module("oci_network_loadbalancer_info")
    client = types.SimpleNamespace(
        get_network_load_balancer=Mock(
            side_effect=oci.exceptions.ServiceError(status, "error", {}, "message")
        )
    )
    helper = make_module_instance(
        module,
        "OciNetworkLoadBalancerInfoModule",
        {"network_load_balancer_id": "nlb"},
        client=client,
    )
    helper.call_with_retry = lambda operation, **kwargs: operation(**kwargs)
    if status == 404:
        assert helper.fetch_resources() == []
    else:
        with pytest.raises(oci.exceptions.ServiceError):
            helper.fetch_resources()
