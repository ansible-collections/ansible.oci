from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    FailJsonCalled,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


class CompositeOperationError(Exception):
    def __init__(self, partial_results=None, cause=None):
        super().__init__(str(cause or "composite operation failed"))
        self.partial_results = partial_results or []
        self.cause = cause


class FakeCompositeOperations:
    def __init__(self, client):
        self.client = client

    def _call(self, operation, **kwargs):
        self.client.composite_calls.append((operation, kwargs))
        return self.client.composite_handler(operation, **kwargs)

    def create_load_balancer_and_wait_for_state(self, **kwargs):
        return self._call("create", **kwargs)

    def update_load_balancer_and_wait_for_state(self, **kwargs):
        return self._call("update", **kwargs)

    def update_load_balancer_shape_and_wait_for_state(self, **kwargs):
        return self._call("update_shape", **kwargs)


def install_fake_oci(monkeypatch):
    oci_module, service_error = shared_install_fake_oci(
        monkeypatch,
        model_names=(
            "CreateLoadBalancerDetails",
            "UpdateLoadBalancerDetails",
            "UpdateLoadBalancerShapeDetails",
            "ShapeDetails",
            "ReservedIP",
            "LoadBalancer",
        ),
    )
    oci_module.load_balancer = types.SimpleNamespace(
        LoadBalancerClient=type("FakeLoadBalancerClient", (), {}),
        LoadBalancerClientCompositeOperations=FakeCompositeOperations,
        models=oci_module.identity.models,
    )
    oci_module.exceptions.CompositeOperationError = CompositeOperationError
    return oci_module, service_error


def make_lb_module(module_obj, params, client=None, check_mode=False):
    instance = make_module_instance(
        module_obj,
        "OciLoadBalancerModule",
        params,
        client=client,
        check_mode=check_mode,
    )
    # Base modules cache their imported SDK at module load. Other unit modules
    # may leave a different fake SDK there, so fake-client tests keep their
    # reads focused on the client behavior and avoid depending on test order.
    instance.call_with_retry = lambda fn, *args, **kwargs: fn(*args, **kwargs)
    return instance


def base_create_params(**overrides):
    params = {
        "compartment_id": "ocid1.compartment.oc1..example",
        "name": "example-lb",
        "subnet_ids": ["ocid1.subnet.oc1..one"],
        "shape_name": "100Mbps",
    }
    params.update(overrides)
    return params


def test_main_exposes_load_balancer_arguments_without_defaulting_is_private(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule()

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(
        module_obj,
        "OciLoadBalancerModule",
        lambda module: types.SimpleNamespace(execute_resource_module=lambda: None),
    )

    module_obj.main()

    spec = captured["argument_spec"]
    assert spec["load_balancer_id"] == {"type": "str", "aliases": ["id"]}
    assert spec["name"] == {"type": "str", "aliases": ["display_name"]}
    assert spec["subnet_ids"] == {"type": "list", "elements": "str"}
    assert spec["is_private"] == {"type": "bool"}
    assert spec["ip_mode"]["choices"] == ["ipv4", "ipv6"]
    assert spec["shape_details"]["options"]["minimum_bandwidth_in_mbps"]["required"]
    assert spec["shape_details"]["options"]["maximum_bandwidth_in_mbps"]["required"]
    assert spec["reserved_ips"]["options"]["id"]["required"]
    assert captured["supports_check_mode"] is True


def test_create_maps_ansible_ip_mode_for_the_sdk(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")

    details = module_obj.build_create_load_balancer_details(
        base_create_params(ip_mode="ipv6")
    )

    assert details.ip_mode == "IPV6"


def test_explicit_ip_mode_map_drives_create_plan_and_update_payload(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    ip_mode_mapping = {
        "ipv4": "SDK_MODE_ALPHA",
        "ipv6": "SDK_MODE_BETA",
    }
    monkeypatch.setattr(module_obj, "IP_MODE_TO_OCI", ip_mode_mapping, raising=False)

    create_details = module_obj.build_create_load_balancer_details(
        base_create_params(ip_mode="ipv6")
    )
    assert create_details.ip_mode == ip_mode_mapping["ipv6"]

    resource = FakeModel(
        id="lb",
        display_name="example-lb",
        compartment_id="ocid1.compartment.oc1..example",
        subnet_ids=["subnet-a"],
        is_private=False,
        ip_mode=ip_mode_mapping["ipv4"],
        shape_name="100Mbps",
        shape_details=None,
        ip_addresses=[],
    )
    matching_instance = make_lb_module(module_obj, {"ip_mode": "ipv4"})
    matching_plan = matching_instance.get_update_plan(resource)
    assert matching_plan["update_needed"] is False
    assert matching_plan["update_model_fields"] == {}

    client = types.SimpleNamespace(
        composite_calls=[],
        retry_strategy=None,
        composite_handler=lambda operation, **kwargs: FakeResponse(
            FakeModel(id="lb", display_name="example-lb", ip_mode=ip_mode_mapping["ipv6"])
        ),
    )
    instance = make_lb_module(
        module_obj,
        {"ip_mode": "ipv6", "reserved_ips": [{"id": "reserved-new"}], "wait": True},
        client,
    )
    update_plan = instance.get_update_plan(resource)

    assert update_plan["update_needed"] is True
    assert update_plan["update_model_fields"] == {
        "ip_mode": ip_mode_mapping["ipv6"],
        "reserved_ips": [{"id": "reserved-new"}],
    }

    instance.update_resource(resource)

    operation, kwargs = client.composite_calls[0]
    assert operation == "update"
    details = kwargs["update_load_balancer_details"]
    assert details.ip_mode == ip_mode_mapping["ipv6"]
    assert {reserved.id for reserved in details.reserved_ips} == {"reserved-new"}


@pytest.mark.parametrize("shape_name", ["flexible", "Flexible", "FLEXIBLE"])
def test_build_create_details_uses_load_balancer_sdk_models(monkeypatch, shape_name):
    oci_module = install_fake_oci(monkeypatch)[0]
    module_obj = load_collection_module("oci_loadbalancer")

    details = module_obj.build_create_load_balancer_details(
        base_create_params(
            shape_name=shape_name,
            shape_details={
                "minimum_bandwidth_in_mbps": 100,
                "maximum_bandwidth_in_mbps": 800,
            },
            reserved_ips=[{"id": "ocid1.publicip.oc1..reserved"}],
            ip_mode="IPV6",
            is_private=True,
        )
    )

    assert isinstance(details, oci_module.load_balancer.models.CreateLoadBalancerDetails)
    assert details.shape_name == "flexible"
    assert details.display_name == "example-lb"
    assert details.shape_details.minimum_bandwidth_in_mbps == 100
    assert details.shape_details.maximum_bandwidth_in_mbps == 800
    assert details.reserved_ips[0].id == "ocid1.publicip.oc1..reserved"
    assert details.subnet_ids == ["ocid1.subnet.oc1..one"]
    assert details.ip_mode == "IPV6"
    assert details.is_private is True


@pytest.mark.parametrize(
    "params, expected_message",
    [
        ({"name": "example-lb"}, "compartment_id"),
        (base_create_params(subnet_ids=[]), "subnet_ids"),
        (base_create_params(shape_name="Flexible"), "shape_details"),
        (
            base_create_params(
                shape_name="Flexible",
                shape_details={
                    "minimum_bandwidth_in_mbps": 801,
                    "maximum_bandwidth_in_mbps": 800,
                },
            ),
            "10 <= minimum_bandwidth_in_mbps <= maximum_bandwidth_in_mbps <= 8000",
        ),
    ],
)
def test_create_validation_rejects_missing_or_invalid_required_values(
    monkeypatch, params, expected_message
):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    instance = make_lb_module(module_obj, params)

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert expected_message in exc_info.value.payload["msg"]


def test_flexible_shape_create_accepts_valid_bandwidth_bounds(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    instance = make_lb_module(
        module_obj,
        base_create_params(
            shape_name="Flexible",
            shape_details={
                "minimum_bandwidth_in_mbps": 10,
                "maximum_bandwidth_in_mbps": 8000,
            },
        ),
    )

    instance.validate_create_request()


def test_check_mode_predicts_create_without_mutating(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    client = types.SimpleNamespace(
        list_load_balancers=lambda **kwargs: FakeResponse(data=[]),
        composite_calls=[],
    )
    instance = make_lb_module(module_obj, base_create_params(), client, check_mode=True)
    monkeypatch.setattr(instance, "list_all_resources", lambda fn, **kwargs: [])

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload == {"changed": True}
    assert not hasattr(client, "composite_handler")


@pytest.mark.parametrize(
    "desired_ip_mode, resource_ip_mode",
    [("ipv4", "IPV4"), ("ipv6", "IPV6")],
)
def test_mapped_ip_mode_matches_oci_resource_without_update(
    monkeypatch, desired_ip_mode, resource_ip_mode
):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    instance = make_lb_module(module_obj, {"ip_mode": desired_ip_mode})
    resource = FakeModel(
        id="lb",
        ip_mode=resource_ip_mode,
        shape_name="100Mbps",
        shape_details=None,
        ip_addresses=[],
    )

    assert instance.needs_update(resource) is False


def test_update_planner_is_idempotent_for_matching_immutable_and_mutable_fields(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    instance = make_lb_module(
        module_obj,
        {
            "name": "example-lb",
            "compartment_id": "ocid1.compartment.oc1..example",
            "subnet_ids": ["subnet-b", "subnet-a"],
            "is_private": False,
            "ip_mode": "IPV4",
        },
    )
    resource = FakeModel(
        id="ocid1.loadbalancer.oc1..example",
        display_name="example-lb",
        compartment_id="ocid1.compartment.oc1..example",
        subnet_ids=["subnet-a", "subnet-b"],
        is_private=False,
        ip_mode="IPV4",
        shape_name="100Mbps",
        shape_details=None,
        ip_addresses=[],
    )

    assert instance.needs_update(resource) is False


@pytest.mark.parametrize(
    "desired, current",
    [
        ({"compartment_id": "ocid1.compartment.oc1..new"}, {"compartment_id": "ocid1.compartment.oc1..old"}),
        ({"subnet_ids": ["subnet-a"]}, {"subnet_ids": ["subnet-b"]}),
        ({"is_private": True}, {"is_private": False}),
    ],
)
def test_update_planner_rejects_immutable_network_drift(monkeypatch, desired, current):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    instance = make_lb_module(module_obj, desired)
    resource = FakeModel(
        id="ocid1.loadbalancer.oc1..example",
        display_name="example-lb",
        compartment_id=current.get("compartment_id", "ocid1.compartment.oc1..example"),
        subnet_ids=current.get("subnet_ids", ["subnet-a"]),
        is_private=current.get("is_private", False),
        shape_name="100Mbps",
        shape_details=None,
        ip_addresses=[],
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert any(key in exc_info.value.payload["msg"] for key in desired)


def test_name_lookup_uses_full_list_model_without_extra_get_before_planning(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    resource = FakeModel(
        id="ocid1.loadbalancer.oc1..example",
        display_name="example-lb",
        compartment_id="ocid1.compartment.oc1..example",
        subnet_ids=["subnet-a"],
        is_private=False,
        ip_mode="IPV4",
        shape_name="100Mbps",
        shape_details=None,
        ip_addresses=[],
    )
    instance = make_lb_module(
        module_obj,
        {
            "name": "example-lb",
            "compartment_id": "ocid1.compartment.oc1..example",
            "subnet_ids": ["subnet-a"],
            "is_private": False,
            "ip_mode": "IPV4",
        },
        types.SimpleNamespace(
            list_load_balancers=lambda **kwargs: None,
            get_load_balancer=raising(AssertionError("name lookup must reuse the listed model")),
        ),
    )
    monkeypatch.setattr(instance, "list_all_resources", lambda fn, **kwargs: [resource])

    resolved = instance.resolve_target_resource()

    assert resolved is resource
    assert instance.needs_update(resolved) is False


def test_name_lookup_fails_when_multiple_resources_match(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    instance = make_lb_module(
        module_obj,
        {"name": "duplicate", "compartment_id": "ocid1.compartment.oc1..example"},
        types.SimpleNamespace(list_load_balancers=lambda **kwargs: None),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda fn, **kwargs: [
            FakeModel(id="one", display_name="duplicate"),
            FakeModel(id="two", display_name="duplicate"),
        ],
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.resolve_resource_by_name()

    assert "Multiple load balancer resources" in exc_info.value.payload["msg"]
    assert "load_balancer_id" in exc_info.value.payload["msg"]


def test_reserved_ip_update_preserves_unmanaged_addresses(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    client = types.SimpleNamespace(
        composite_calls=[],
        retry_strategy=None,
        composite_handler=lambda operation, **kwargs: FakeResponse(
            FakeModel(id="ocid1.loadbalancer.oc1..example", display_name="example-lb")
        ),
    )
    instance = make_lb_module(
        module_obj,
        {"reserved_ips": [{"id": "reserved-new"}], "ip_mode": "ipv6"},
        client,
    )
    resource = FakeModel(
        id="ocid1.loadbalancer.oc1..example",
        display_name="example-lb",
        shape_name="100Mbps",
        shape_details=None,
        ip_mode="IPV4",
        ip_addresses=[
            FakeModel(reserved_ip=FakeModel(id="reserved-existing")),
            FakeModel(reserved_ip=None),
        ],
    )

    instance.update_resource(resource)

    details = client.composite_calls[0][1]["update_load_balancer_details"]
    assert {reserved.id for reserved in details.reserved_ips} == {
        "reserved-existing",
        "reserved-new",
    }
    assert details.ip_mode == "IPV6"


@pytest.mark.parametrize(
    "current_ip_mode, requested_ip_mode",
    [("IPV4", None), ("IPV6", "IPV6"), ("IPV4", "IPV4")],
)
def test_reserved_ip_update_requires_ipv4_to_ipv6_transition(
    monkeypatch, current_ip_mode, requested_ip_mode
):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    client = types.SimpleNamespace(
        composite_calls=[],
        composite_handler=lambda operation, **kwargs: FakeResponse(
            FakeModel(id="lb", ip_mode=requested_ip_mode)
        ),
        get_load_balancer=lambda load_balancer_id: FakeResponse(
            FakeModel(
                id=load_balancer_id,
                display_name="example-lb",
                compartment_id="compartment",
                subnet_ids=["subnet"],
                is_private=False,
                ip_mode=current_ip_mode,
                shape_name="100Mbps",
                shape_details=None,
                ip_addresses=[],
            )
        ),
    )
    params = {"load_balancer_id": "lb", "reserved_ips": [{"id": "reserved-new"}]}
    if requested_ip_mode is not None:
        params["ip_mode"] = requested_ip_mode
    instance = make_lb_module(module_obj, params, client)

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert "only while changing ip_mode from IPV4 to IPV6" in exc_info.value.payload["msg"]
    assert client.composite_calls == []


def test_reserved_ip_update_invalid_mode_fails_in_check_mode_without_mutation(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    client = types.SimpleNamespace(
        composite_calls=[],
        get_load_balancer=lambda load_balancer_id: FakeResponse(
            FakeModel(
                id=load_balancer_id,
                display_name="example-lb",
                compartment_id="compartment",
                subnet_ids=["subnet"],
                is_private=False,
                ip_mode="IPV4",
                shape_name="100Mbps",
                shape_details=None,
                ip_addresses=[],
            )
        ),
    )
    instance = make_lb_module(
        module_obj,
        {
            "load_balancer_id": "lb",
            "reserved_ips": [{"id": "reserved-new"}],
            "ip_mode": "IPV4",
        },
        client,
        check_mode=True,
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert "only while changing ip_mode from IPV4 to IPV6" in exc_info.value.payload["msg"]
    assert client.composite_calls == []


def test_empty_reserved_ip_list_does_not_detach_existing_addresses(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    instance = make_lb_module(module_obj, {"reserved_ips": []})
    resource = FakeModel(
        id="lb",
        display_name="example-lb",
        shape_name="100Mbps",
        shape_details=None,
        ip_addresses=[FakeModel(reserved_ip=FakeModel(id="reserved-existing"))],
    )

    assert instance.needs_update(resource) is False


def test_metadata_update_sends_ip_mode_to_update_model(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    client = types.SimpleNamespace(
        composite_calls=[],
        retry_strategy=None,
        composite_handler=lambda operation, **kwargs: FakeResponse(
            FakeModel(id="lb", display_name="example-lb", ip_mode="IPV6")
        ),
    )
    instance = make_lb_module(module_obj, {"ip_mode": "ipv6", "wait": True}, client)
    resource = FakeModel(
        id="lb", display_name="example-lb", shape_name="100Mbps", shape_details=None, ip_mode="IPV4", ip_addresses=[]
    )

    instance.update_resource(resource)

    operation, kwargs = client.composite_calls[0]
    assert operation == "update"
    assert kwargs["update_load_balancer_details"].ip_mode == "IPV6"
    assert kwargs["wait_for_states"] == ["SUCCEEDED"]


def test_shape_change_runs_after_metadata_update_and_uses_flexible_details(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    client = types.SimpleNamespace(
        composite_calls=[],
        retry_strategy=None,
        composite_handler=lambda operation, **kwargs: (
            FakeResponse(FakeModel(id="lb", display_name="renamed"))
            if operation == "update"
            else FakeResponse(FakeModel(id="wr-shape", lifecycle_state="SUCCEEDED"))
        ),
        get_load_balancer=lambda load_balancer_id: FakeResponse(
            FakeModel(id=load_balancer_id, display_name="renamed", shape_name="Flexible")
        ),
    )
    instance = make_lb_module(
        module_obj,
        {
            "name": "renamed",
            "shape_name": "Flexible",
            "shape_details": {
                "minimum_bandwidth_in_mbps": 50,
                "maximum_bandwidth_in_mbps": 500,
            },
            "wait": True,
        },
        client,
    )
    resource = FakeModel(
        id="lb", display_name="example-lb", shape_name="100Mbps", shape_details=None, ip_addresses=[]
    )

    instance.update_resource(resource)

    assert [call[0] for call in client.composite_calls] == ["update", "update_shape"]
    assert client.composite_calls[0][1]["wait_for_states"] == ["SUCCEEDED"]
    shape_details = client.composite_calls[1][1]["update_load_balancer_shape_details"]
    assert shape_details.shape_name == "flexible"
    assert shape_details.shape_details.minimum_bandwidth_in_mbps == 50
    assert shape_details.shape_details.maximum_bandwidth_in_mbps == 500


def test_bandwidth_only_update_reuses_current_shape_name(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    client = types.SimpleNamespace(
        composite_calls=[],
        retry_strategy=None,
        composite_handler=lambda operation, **kwargs: FakeResponse(
            FakeModel(id="wr-shape", lifecycle_state="SUCCEEDED")
        ),
        get_load_balancer=lambda load_balancer_id: FakeResponse(FakeModel(id=load_balancer_id)),
    )
    instance = make_lb_module(
        module_obj,
        {"shape_details": {"minimum_bandwidth_in_mbps": 100, "maximum_bandwidth_in_mbps": 200}},
        client,
    )
    resource = FakeModel(
        id="lb",
        display_name="example-lb",
        shape_name="Flexible",
        shape_details=FakeModel(
            minimum_bandwidth_in_mbps=50,
            maximum_bandwidth_in_mbps=100,
        ),
        ip_addresses=[],
    )

    instance.update_resource(resource)

    shape_details = client.composite_calls[0][1]["update_load_balancer_shape_details"]
    assert shape_details.shape_name == "flexible"
    assert shape_details.shape_details.minimum_bandwidth_in_mbps == 100


def test_bandwidth_only_update_rejects_invalid_bounds(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    instance = make_lb_module(
        module_obj,
        {"shape_details": {"minimum_bandwidth_in_mbps": 0, "maximum_bandwidth_in_mbps": 20}},
    )
    resource = FakeModel(id="lb", shape_name="Flexible", shape_details=None, ip_addresses=[])

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "10 <= minimum_bandwidth_in_mbps <= maximum_bandwidth_in_mbps <= 8000" in exc_info.value.payload["msg"]


def test_wait_false_with_combined_update_waits_between_operations(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    client = types.SimpleNamespace(
        composite_calls=[],
        retry_strategy=None,
        composite_handler=lambda operation, **kwargs: (
            FakeResponse(FakeModel(id="lb", display_name="renamed"))
            if operation == "update"
            else FakeResponse(FakeModel(id="wr-shape", lifecycle_state="SUCCEEDED"))
        ),
        get_load_balancer=lambda load_balancer_id: FakeResponse(
            FakeModel(id=load_balancer_id, display_name="renamed")
        ),
    )
    instance = make_lb_module(
        module_obj,
        {
            "name": "renamed",
            "shape_name": "Flexible",
            "shape_details": {
                "minimum_bandwidth_in_mbps": 10,
                "maximum_bandwidth_in_mbps": 100,
            },
            "wait": False,
        },
        client,
    )

    instance.update_resource(
        FakeModel(id="lb", display_name="example-lb", shape_name="100Mbps", shape_details=None, ip_addresses=[])
    )

    assert client.composite_calls[0][1]["wait_for_states"] == ["SUCCEEDED"]
    assert client.composite_calls[1][1]["wait_for_states"] == []


def test_wait_false_update_reads_snapshot_by_known_load_balancer_id(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    work_request_calls = []
    client = types.SimpleNamespace(
        composite_calls=[],
        retry_strategy=None,
        composite_handler=lambda operation, **kwargs: FakeResponse(
            headers={"opc-work-request-id": "wr-1"}
        ),
        get_work_request=work_request_calls.append,
        get_load_balancer=lambda load_balancer_id: FakeResponse(
            FakeModel(id=load_balancer_id, display_name="updated")
        ),
    )
    instance = make_lb_module(module_obj, {"name": "updated", "wait": False}, client)

    resource = instance.update_resource(
        FakeModel(id="lb", display_name="example-lb", shape_name="100Mbps", shape_details=None, ip_addresses=[])
    )

    assert resource.id == "lb"
    assert work_request_calls == []
    assert client.composite_calls[0][1]["wait_for_states"] == []


def test_wait_false_resource_snapshot_404_returns_id_only_result(monkeypatch):
    service_error = install_fake_oci(monkeypatch)[1]
    module_obj = load_collection_module("oci_loadbalancer")
    client = types.SimpleNamespace(
        composite_calls=[],
        retry_strategy=None,
        composite_handler=lambda operation, **kwargs: FakeResponse(
            headers={"opc-work-request-id": "wr-1"}
        ),
        get_work_request=raising(AssertionError("update must use known ID")),
        get_load_balancer=raising(service_error(404, "gone")),
    )
    instance = make_lb_module(module_obj, {"name": "updated", "wait": False}, client)

    resource = instance.update_resource(
        FakeModel(id="lb", display_name="example-lb", shape_name="100Mbps", shape_details=None, ip_addresses=[])
    )

    assert resource == {"id": "lb"}


def test_wait_false_missing_work_request_and_resource_id_fails_clearly(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    client = types.SimpleNamespace(
        composite_calls=[],
        retry_strategy=None,
        composite_handler=lambda operation, **kwargs: FakeResponse(),
    )
    instance = make_lb_module(module_obj, base_create_params(wait=False), client)

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.create_resource()

    assert "work request ID" in exc_info.value.payload["msg"]


def test_failed_work_request_fetch_reports_id_and_error_details(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    client = types.SimpleNamespace(
        composite_calls=[],
        retry_strategy=None,
        composite_handler=lambda operation, **kwargs: FakeResponse(),
        get_work_request=lambda work_request_id: FakeResponse(
            FakeModel(
                lifecycle_state="FAILED",
                error_details=[FakeModel(error_code="BAD_INPUT", message="invalid subnet")],
            )
        ),
    )
    instance = make_lb_module(module_obj, {"name": "updated", "wait": True}, client)
    fetch_failed_work_request = instance.make_work_request_fetcher()

    response = FakeResponse(FakeModel(id="wr-failed", lifecycle_state="IN_PROGRESS"))

    with pytest.raises(Exception, match="wr-failed.*BAD_INPUT.*invalid subnet"):
        fetch_failed_work_request(response=response)


def test_composite_timeout_error_reports_operation_and_work_request_id(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    client = types.SimpleNamespace(
        composite_calls=[],
        retry_strategy=None,
        composite_handler=raising(
            CompositeOperationError(
                partial_results=[FakeResponse(headers={"opc-work-request-id": "wr-timeout"})],
                cause=RuntimeError("Maximum wait time has been exceeded"),
            )
        ),
    )
    instance = make_lb_module(module_obj, base_create_params(), client)

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.create_resource()

    message = exc_info.value.payload["msg"]
    assert "create" in message.lower()
    assert "wr-timeout" in message
    assert "Maximum wait time" in message
    assert len(client.composite_calls) == 1


def test_delete_waits_until_load_balancer_is_not_found(monkeypatch):
    service_error = install_fake_oci(monkeypatch)[1]
    module_obj = load_collection_module("oci_loadbalancer")
    delete_calls = []
    get_calls = []
    deleted = [False]

    def delete_load_balancer(load_balancer_id):
        delete_calls.append(load_balancer_id)
        deleted[0] = True
        return FakeResponse(None)

    def get_load_balancer(load_balancer_id):
        get_calls.append(load_balancer_id)
        if deleted[0]:
            raise service_error(404, "deleted")
        return FakeResponse(FakeModel(id=load_balancer_id))

    client = types.SimpleNamespace(
        retry_strategy=None,
        delete_load_balancer=delete_load_balancer,
        get_load_balancer=get_load_balancer,
    )
    instance = make_lb_module(module_obj, {"wait": True}, client)

    assert instance.delete_resource(FakeModel(id="lb")) is None
    assert delete_calls == ["lb"]
    assert get_calls == ["lb"]


def test_delete_wait_false_does_not_poll_after_raw_delete(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    delete_calls = []
    client = types.SimpleNamespace(
        retry_strategy=None,
        delete_load_balancer=lambda load_balancer_id: delete_calls.append(load_balancer_id)
        or FakeResponse(None),
        get_load_balancer=raising(AssertionError("wait=False must not poll after delete")),
    )
    instance = make_lb_module(module_obj, {"wait": False}, client)

    assert instance.delete_resource(FakeModel(id="lb")) is None
    assert delete_calls == ["lb"]


def test_create_payload_uses_installed_load_balancer_models():
    module_obj = load_collection_module("oci_loadbalancer")
    models = module_obj.oci.load_balancer.models

    details = module_obj.build_create_load_balancer_details(
        base_create_params(
            shape_name="Flexible",
            shape_details={
                "minimum_bandwidth_in_mbps": 100,
                "maximum_bandwidth_in_mbps": 800,
            },
            reserved_ips=[{"id": "ocid1.publicip.oc1..reserved"}],
        )
    )

    assert isinstance(details, models.CreateLoadBalancerDetails)
    assert isinstance(details.shape_details, models.ShapeDetails)
    assert isinstance(details.reserved_ips[0], models.ReservedIP)


def test_real_sdk_create_composite_returns_refreshed_resource(monkeypatch):
    module_obj = load_collection_module("oci_loadbalancer")
    model = module_obj.oci.load_balancer.models
    calls = []
    client = types.SimpleNamespace(retry_strategy=None)
    client.create_load_balancer = lambda details: calls.append(details) or FakeResponse(
        headers={"opc-work-request-id": "wr-created"}
    )
    client.get_work_request = lambda work_request_id: FakeResponse(
        model.WorkRequest(
            id=work_request_id,
            load_balancer_id="lb-created",
            lifecycle_state="SUCCEEDED",
        )
    )
    client.get_load_balancer = lambda load_balancer_id: FakeResponse(
        model.LoadBalancer(id=load_balancer_id, display_name="example-lb")
    )
    instance = make_lb_module(module_obj, base_create_params(), client)

    resource = instance.create_resource()

    assert isinstance(calls[0], model.CreateLoadBalancerDetails)
    assert resource.id == "lb-created"
    assert client.retry_strategy is None


def test_real_sdk_create_composite_surfaces_failed_work_request(monkeypatch):
    module_obj = load_collection_module("oci_loadbalancer")
    model = module_obj.oci.load_balancer.models
    client = types.SimpleNamespace(retry_strategy=None)
    client.create_load_balancer = lambda details: FakeResponse(
        headers={"opc-work-request-id": "wr-failed"}
    )
    client.get_work_request = lambda work_request_id: FakeResponse(
        model.WorkRequest(
            id=work_request_id,
            lifecycle_state="IN_PROGRESS",
        )
    )

    def fetch_until_failed(client_arg, response, **kwargs):
        assert kwargs["evaluate_response"](response) is False
        return kwargs["fetch_func"](response=response)

    monkeypatch.setattr(module_obj.oci, "wait_until", fetch_until_failed)
    failed_request = model.WorkRequest(
        id="wr-failed",
        lifecycle_state="FAILED",
        error_details=[
            model.WorkRequestError(
                error_code="BAD_INPUT",
                message="invalid subnet",
            )
        ],
    )
    client.get_work_request = lambda work_request_id: FakeResponse(failed_request)
    instance = make_lb_module(module_obj, base_create_params(), client)

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.create_resource()

    assert "wr-failed" in exc_info.value.payload["msg"]
    assert "BAD_INPUT" in exc_info.value.payload["msg"]
    assert "invalid subnet" in exc_info.value.payload["msg"]
    assert client.retry_strategy is None


def test_check_mode_update_predicts_change_without_calling_composite(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    client = types.SimpleNamespace(
        composite_calls=[],
        get_load_balancer=lambda load_balancer_id: FakeResponse(
            FakeModel(
                id=load_balancer_id,
                display_name="example-lb",
                compartment_id="compartment",
                subnet_ids=["subnet"],
                is_private=False,
                ip_mode="IPV4",
                shape_name="100Mbps",
                shape_details=None,
                ip_addresses=[],
            )
        ),
    )
    instance = make_lb_module(
        module_obj,
        {"load_balancer_id": "lb", "ip_mode": "IPV6"},
        client,
        check_mode=True,
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload == {"changed": True}
    assert client.composite_calls == []


def test_check_mode_delete_predicts_change_without_calling_composite(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    client = types.SimpleNamespace(
        composite_calls=[],
        get_load_balancer=lambda load_balancer_id: FakeResponse(
            FakeModel(id=load_balancer_id, display_name="example-lb")
        ),
    )
    instance = make_lb_module(
        module_obj,
        {"state": "absent", "load_balancer_id": "lb"},
        client,
        check_mode=True,
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload == {"changed": True}
    assert client.composite_calls == []


def test_execute_create_then_matching_update_is_idempotent(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    resource = FakeModel(
        id="lb",
        display_name="example-lb",
        compartment_id="ocid1.compartment.oc1..example",
        subnet_ids=["ocid1.subnet.oc1..one"],
        shape_name="100Mbps",
        shape_details=None,
        is_private=None,
        ip_mode=None,
        freeform_tags=None,
        defined_tags=None,
        ip_addresses=[],
    )
    client = types.SimpleNamespace(
        composite_calls=[],
        retry_strategy=None,
        composite_handler=lambda operation, **kwargs: FakeResponse(resource),
        get_load_balancer=lambda load_balancer_id: FakeResponse(resource),
        list_load_balancers=lambda **kwargs: FakeResponse(data=[]),
    )
    create_instance = make_lb_module(module_obj, base_create_params(), client)
    monkeypatch.setattr(create_instance, "list_all_resources", lambda fn, **kwargs: [])

    with pytest.raises(ExitJsonCalled) as created:
        create_instance.execute_resource_module()

    assert created.value.payload["changed"] is True
    assert len(client.composite_calls) == 1

    update_instance = make_lb_module(
        module_obj,
        dict(base_create_params(), load_balancer_id="lb"),
        client,
    )
    with pytest.raises(ExitJsonCalled) as unchanged:
        update_instance.execute_resource_module()

    assert unchanged.value.payload["changed"] is False
    assert len(client.composite_calls) == 1


def test_execute_delete_then_repeated_absent_is_idempotent(monkeypatch):
    service_error = install_fake_oci(monkeypatch)[1]
    module_obj = load_collection_module("oci_loadbalancer")
    deleted = [False]
    resource = FakeModel(id="lb", display_name="example-lb")

    def get_load_balancer(load_balancer_id):
        if deleted[0]:
            raise service_error(404, "deleted")
        return FakeResponse(resource)

    delete_calls = []

    def delete_load_balancer(load_balancer_id):
        delete_calls.append(load_balancer_id)
        deleted[0] = True
        return FakeResponse(None)

    client = types.SimpleNamespace(
        retry_strategy=None,
        get_load_balancer=get_load_balancer,
        delete_load_balancer=delete_load_balancer,
    )
    delete_instance = make_lb_module(
        module_obj,
        {"state": "absent", "load_balancer_id": "lb"},
        client,
    )

    with pytest.raises(ExitJsonCalled) as deleted_result:
        delete_instance.execute_resource_module()

    repeat_instance = make_lb_module(
        module_obj,
        {"state": "absent", "load_balancer_id": "lb"},
        client,
    )
    with pytest.raises(ExitJsonCalled) as repeated_result:
        repeat_instance.execute_resource_module()

    assert deleted_result.value.payload == {"changed": True}
    assert repeated_result.value.payload == {"changed": False}
    assert delete_calls == ["lb"]


def test_lowercase_flexible_shape_is_valid_and_case_only_change_is_idempotent(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    details = {"minimum_bandwidth_in_mbps": 100, "maximum_bandwidth_in_mbps": 500}
    instance = make_lb_module(
        module_obj,
        {"shape_name": "Flexible", "shape_details": details},
    )
    resource = FakeModel(
        id="lb",
        shape_name="flexible",
        shape_details=FakeModel(**details),
        ip_addresses=[],
    )

    assert instance.needs_update(resource) is False


def test_create_accepts_lowercase_flexible_shape_name(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    instance = make_lb_module(
        module_obj,
        base_create_params(
            shape_name="flexible",
            shape_details={
                "minimum_bandwidth_in_mbps": 100,
                "maximum_bandwidth_in_mbps": 500,
            },
        ),
    )

    instance.validate_create_request()


def test_waited_create_without_completed_resource_fails_instead_of_snapshot(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    work_request_calls = []
    resource_calls = []
    client = types.SimpleNamespace(
        composite_calls=[],
        retry_strategy=None,
        composite_handler=lambda operation, **kwargs: FakeResponse(),
        get_work_request=work_request_calls.append,
        get_load_balancer=resource_calls.append,
    )
    instance = make_lb_module(module_obj, base_create_params(wait=True), client)

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.create_resource()

    assert "completed load balancer resource" in exc_info.value.payload["msg"]
    assert work_request_calls == []
    assert resource_calls == []


def test_waited_shape_change_fails_if_final_load_balancer_is_missing(monkeypatch):
    service_error = install_fake_oci(monkeypatch)[1]
    module_obj = load_collection_module("oci_loadbalancer")
    client = types.SimpleNamespace(
        composite_calls=[],
        retry_strategy=None,
        composite_handler=lambda operation, **kwargs: FakeResponse(
            FakeModel(id="wr-shape", lifecycle_state="SUCCEEDED")
        ),
        get_load_balancer=raising(
            service_error(404, "load balancer not found after resize")
        ),
    )
    instance = make_lb_module(
        module_obj,
        {
            "shape_name": "Flexible",
            "shape_details": {
                "minimum_bandwidth_in_mbps": 100,
                "maximum_bandwidth_in_mbps": 500,
            },
            "wait": True,
        },
        client,
    )

    resource = FakeModel(id="lb", shape_name="100Mbps", shape_details=None, ip_addresses=[])

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.update_resource(resource)

    assert "finished resizing" in exc_info.value.payload["msg"]


def test_wait_false_create_resolves_load_balancer_id_from_work_request(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    work_request_calls = []
    get_calls = []
    client = types.SimpleNamespace(
        composite_calls=[],
        retry_strategy=None,
        composite_handler=lambda operation, **kwargs: FakeResponse(
            headers={"opc-work-request-id": "wr-id"}
        ),
        get_work_request=lambda work_request_id: (
            work_request_calls.append(work_request_id)
            or FakeResponse(FakeModel(load_balancer_id="lb-id"))
        ),
        get_load_balancer=lambda load_balancer_id: (
            get_calls.append(load_balancer_id)
            or FakeResponse(FakeModel(id=load_balancer_id))
        ),
    )
    instance = make_lb_module(module_obj, base_create_params(wait=False), client)

    resource = instance.create_resource()

    assert resource.id == "lb-id"
    assert work_request_calls == ["wr-id"]
    assert get_calls == ["lb-id"]


def test_waited_delete_reports_raw_409_dependent_resource_error(monkeypatch):
    service_error = install_fake_oci(monkeypatch)[1]
    module_obj = load_collection_module("oci_loadbalancer")
    client = types.SimpleNamespace(
        retry_strategy=None,
        delete_load_balancer=raising(service_error(409, "listener rules still exist")),
    )
    instance = make_lb_module(module_obj, {"wait": True}, client)

    resource = FakeModel(id="lb")

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.delete_resource(resource)

    assert "Cannot delete load balancer lb while dependent resources exist" in exc_info.value.payload["msg"]
    assert "listener rules still exist" in exc_info.value.payload["msg"]


def test_work_request_fetcher_rejects_initial_failed_response_without_refetch(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    calls = []
    client = types.SimpleNamespace(
        retry_strategy=None,
        get_work_request=calls.append,
    )
    instance = make_lb_module(module_obj, {}, client)
    fetch_work_request = instance.make_work_request_fetcher()

    response = FakeResponse(
        FakeModel(
            id="wr-failed",
            lifecycle_state="FAILED",
            error_details=[
                FakeModel(error_code="BAD_INPUT", message="invalid subnet")
            ],
        )
    )

    with pytest.raises(RuntimeError, match="wr-failed.*BAD_INPUT.*invalid subnet"):
        fetch_work_request(response=response)

    assert calls == []


def test_execute_update_then_repeated_present_is_idempotent(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    current = [
        FakeModel(
            id="lb",
            display_name="example-lb",
            compartment_id="compartment",
            subnet_ids=["subnet"],
            is_private=False,
            ip_mode="IPV4",
            shape_name="100Mbps",
            shape_details=None,
            ip_addresses=[],
        )
    ]
    client = types.SimpleNamespace(
        composite_calls=[],
        retry_strategy=None,
        get_load_balancer=lambda load_balancer_id: FakeResponse(current[0]),
    )

    def composite_handler(operation, **kwargs):
        details = kwargs["update_load_balancer_details"]
        updated = FakeModel(
            **dict(
                vars(current[0]),
                ip_mode=details.ip_mode,
            )
        )
        current[0] = updated
        return FakeResponse(updated)

    client.composite_handler = composite_handler
    params = {"load_balancer_id": "lb", "ip_mode": "ipv6"}
    first = make_lb_module(module_obj, params, client)

    with pytest.raises(ExitJsonCalled) as first_result:
        first.execute_resource_module()

    second = make_lb_module(module_obj, params, client)
    with pytest.raises(ExitJsonCalled) as second_result:
        second.execute_resource_module()

    assert first_result.value.payload["changed"] is True
    assert second_result.value.payload["changed"] is False
    assert [call[0] for call in client.composite_calls] == ["update"]


def test_reserved_ip_desired_subset_already_attached_is_idempotent(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    instance = make_lb_module(
        module_obj,
        {"reserved_ips": [{"id": "reserved-managed"}]},
    )
    resource = FakeModel(
        id="lb",
        ip_addresses=[
            FakeModel(reserved_ip=FakeModel(id="reserved-managed")),
            FakeModel(reserved_ip=FakeModel(id="reserved-unmanaged")),
        ],
    )

    assert instance.needs_update(resource) is False


def test_switching_to_flexible_without_bandwidth_details_fails(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    instance = make_lb_module(module_obj, {"shape_name": "flexible"})

    resource = FakeModel(
        id="lb",
        shape_name="100Mbps",
        shape_details=None,
        ip_addresses=[],
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "shape_details is required" in exc_info.value.payload["msg"]


def test_switching_from_flexible_to_fixed_omits_current_bandwidth_details(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    client = types.SimpleNamespace(
        composite_calls=[],
        retry_strategy=None,
        composite_handler=lambda operation, **kwargs: FakeResponse(
            FakeModel(id="wr-shape", lifecycle_state="SUCCEEDED")
        ),
        get_load_balancer=lambda load_balancer_id: FakeResponse(
            FakeModel(id=load_balancer_id, shape_name="100Mbps", shape_details=None)
        ),
    )
    instance = make_lb_module(module_obj, {"shape_name": "100Mbps", "wait": True}, client)
    resource = FakeModel(
        id="lb",
        shape_name="flexible",
        shape_details=FakeModel(
            minimum_bandwidth_in_mbps=100,
            maximum_bandwidth_in_mbps=500,
        ),
        ip_addresses=[],
    )

    instance.update_resource(resource)

    operation, kwargs = client.composite_calls[0]
    assert operation == "update_shape"
    details = kwargs["update_load_balancer_shape_details"]
    assert details.shape_name == "100Mbps"
    assert not hasattr(details, "shape_details")


def test_switching_to_fixed_rejects_explicit_shape_details(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    instance = make_lb_module(
        module_obj,
        {
            "shape_name": "100Mbps",
            "shape_details": {
                "minimum_bandwidth_in_mbps": 100,
                "maximum_bandwidth_in_mbps": 500,
            },
        },
    )

    resource = FakeModel(
        id="lb",
        shape_name="flexible",
        shape_details=FakeModel(
            minimum_bandwidth_in_mbps=100,
            maximum_bandwidth_in_mbps=500,
        ),
        ip_addresses=[],
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "only be used with shape_name Flexible" in exc_info.value.payload["msg"]


def test_fixed_shape_with_reported_bandwidth_metadata_is_idempotent(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer")
    instance = make_lb_module(module_obj, {"shape_name": "100Mbps"})
    resource = FakeModel(
        id="lb",
        shape_name="100Mbps",
        shape_details=FakeModel(
            minimum_bandwidth_in_mbps=10,
            maximum_bandwidth_in_mbps=100,
        ),
        ip_addresses=[],
    )

    assert instance.needs_update(resource) is False
