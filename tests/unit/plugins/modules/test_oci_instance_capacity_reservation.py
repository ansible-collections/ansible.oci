from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types
from itertools import permutations

import pytest

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FailJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


MODEL_NAMES = (
    "InstanceReservationConfigDetails",
    "InstanceReservationShapeConfigDetails",
    "ClusterConfigDetails",
    "CreateComputeCapacityReservationDetails",
    "UpdateComputeCapacityReservationDetails",
)


def install_fake_oci(monkeypatch):
    """Install fake OCI classes needed by capacity reservation tests."""
    return shared_install_fake_oci(monkeypatch, model_names=MODEL_NAMES)


def make_reservation_module(module_obj, params, client=None, check_mode=False):
    """Create a resource module instance without calling its constructor."""
    instance = make_module_instance(
        module_obj,
        "OciComputeCapacityReservationModule",
        params,
        client=client,
        check_mode=check_mode,
        work_request_client=types.SimpleNamespace(),
    )
    return instance


def test_main_exposes_reservation_inputs(monkeypatch):
    """Expose nested reservation inputs and shared wait options."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_capacity_reservation")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        return DummyModule({})

    class FakeReservationModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciComputeCapacityReservationModule", FakeReservationModule)
    module_obj.main()

    spec = captured["argument_spec"]
    assert captured["run_called"] is True
    assert spec["state"]["choices"] == ["present", "absent"]
    assert spec["instance_reservation_configs"]["type"] == "list"
    assert spec["instance_reservation_configs"]["options"]["reserved_count"]["type"] == "int"
    assert spec["is_default_reservation"]["type"] == "bool"


def test_build_details_maps_all_nested_models_and_preserves_zero_false(monkeypatch):
    """Build typed nested models and retain false and zero values."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_capacity_reservation")
    details = module_obj.build_capacity_reservation_details(
        {
            "display_name": "reserved",
            "is_default_reservation": False,
            "instance_reservation_configs": [
                {
                    "instance_shape": "VM.Standard.E5.Flex",
                    "reserved_count": 0,
                    "instance_shape_config": {"ocpus": 0.0, "memory_in_gbs": 16.0},
                    "cluster_config": {"hpc_island_id": "island", "network_block_ids": ["net"]},
                }
            ],
        },
        module_obj.oci.core.models.CreateComputeCapacityReservationDetails,
    )

    config = details.instance_reservation_configs[0]
    assert isinstance(details, FakeModel)
    assert details.display_name == "reserved"
    assert details.is_default_reservation is False
    assert isinstance(config, FakeModel)
    assert config.reserved_count == 0
    assert isinstance(config.instance_shape_config, FakeModel)
    assert config.instance_shape_config.ocpus == 0.0
    assert isinstance(config.cluster_config, FakeModel)
    assert config.cluster_config.network_block_ids == ["net"]


def test_build_details_omits_unset_optional_fields(monkeypatch):
    """Leave omitted optional reservation fields unset."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_capacity_reservation")
    config = module_obj.build_instance_reservation_config(
        {"instance_shape": "VM.Standard.E5.Flex", "reserved_count": 1}
    )

    assert not hasattr(config, "instance_shape_config")
    assert not hasattr(config, "cluster_config")
    assert not hasattr(config, "fault_domain")


def test_build_update_details_keeps_false_zero_and_empty_list(monkeypatch):
    """Keep false, zero, and an empty config list in update details."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_capacity_reservation")
    instance = make_reservation_module(module_obj, {})

    details = instance.build_update_details(
        {"is_default_reservation": False, "instance_reservation_configs": []}
    )

    assert details.is_default_reservation is False
    assert details.instance_reservation_configs == []


def test_update_comparison_ignores_order_and_server_used_count(monkeypatch):
    """Compare reservation configurations without order or server-only fields."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_capacity_reservation")
    desired = [
        {"instance_shape": "shape-a", "reserved_count": 2},
        {"instance_shape": "shape-b", "reserved_count": 1},
    ]
    current = [
        FakeModel(instance_shape="shape-b", reserved_count=1, used_count=0),
        FakeModel(instance_shape="shape-a", reserved_count=2, used_count=1),
    ]
    instance = make_reservation_module(module_obj, {"instance_reservation_configs": desired})

    resource = FakeModel(instance_reservation_configs=current)
    assert instance.build_update_plan(resource)["update_needed"] is False


def test_empty_configuration_list_is_a_requested_clear(monkeypatch):
    """Treat an empty desired config list as a request to clear current configs."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_capacity_reservation")
    instance = make_reservation_module(module_obj, {"instance_reservation_configs": []})

    resource = FakeModel(
        instance_reservation_configs=[FakeModel(instance_shape="shape", reserved_count=1)]
    )
    plan = instance.build_update_plan(resource)
    assert plan["update_needed"] is True
    assert plan["update_model_fields"]["instance_reservation_configs"] == []


def test_build_update_plan_marks_compartment_and_domain_immutable(monkeypatch):
    """Reject updates that change immutable reservation placement fields."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_capacity_reservation")
    instance = make_reservation_module(
        module_obj,
        {"compartment_id": "new-compartment", "availability_domain": "AD-2"},
    )
    resource = FakeModel(id="reservation", compartment_id="old-compartment", availability_domain="AD-1")

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.build_update_plan(resource)

    assert "compartment_id" in exc_info.value.payload["msg"] or "availability_domain" in exc_info.value.payload["msg"]


def test_hydrate_summary_fetches_full_reservation(monkeypatch):
    """Fetch full resource data after a summary name lookup."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_capacity_reservation")
    full = FakeModel(id="reservation", display_name="full")
    instance = make_reservation_module(module_obj, {}, client=types.SimpleNamespace())
    calls = []
    instance.get_resource_by_id = lambda resource_id: calls.append(resource_id) or full
    summary = FakeModel(id="reservation", display_name="summary")

    assert instance.hydrate_named_resource(summary) is full
    assert calls == ["reservation"]


def test_update_waits_for_work_request_then_resource_when_response_data_is_none(monkeypatch):
    """Wait for update completion and fetch the resource when the body is empty."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_capacity_reservation")
    instance = make_reservation_module(module_obj, {"wait": True})
    events = []
    resource = FakeModel(id="reservation")
    instance.wait_for_work_request = lambda client, request_id: events.append(("work", request_id))
    instance.wait_for_resource_id = lambda resource_id, states: events.append(("resource", resource_id, states)) or resource
    response = FakeResponse(data=None, headers={"opc-work-request-id": "request-1"})

    result = instance.get_update_result(response, "reservation")

    assert result is resource
    assert events[0] == ("work", "request-1")
    assert events[1][0:2] == ("resource", "reservation")


def test_work_request_failure_stops_resource_wait(monkeypatch):
    """Propagate a failed work request without polling the reservation."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_capacity_reservation")
    instance = make_reservation_module(module_obj, {"wait": True})
    instance.wait_for_work_request = raising(RuntimeError("work request failed"))
    instance.wait_for_resource_id = raising(AssertionError("resource wait was not expected"))

    with pytest.raises(RuntimeError, match="work request failed"):
        instance.wait_for_reservation_work_request(
            FakeResponse(data=None, headers={"opc-work-request-id": "request-1"}),
            "reservation",
            ("ACTIVE",),
        )


def test_wait_false_skips_work_request_and_returns_get_result(monkeypatch):
    """Skip work request waits when wait is false and return the latest resource."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_capacity_reservation")
    expected = FakeModel(id="reservation", lifecycle_state="UPDATING")
    instance = make_reservation_module(
        module_obj,
        {"wait": False},
        client=types.SimpleNamespace(),
    )
    instance.get_resource_by_id = lambda resource_id: expected
    instance.wait_for_work_request = raising(AssertionError("unexpected wait"))

    result = instance.wait_for_reservation_work_request(
        FakeResponse(data=FakeModel(id="reservation"), headers={"opc-work-request-id": "request-1"}),
        "reservation",
        ("ACTIVE",),
    )

    assert result is expected


def test_check_mode_predicts_create_without_calling_sdk(monkeypatch):
    """Predict a create in check mode without calling the OCI client."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_capacity_reservation")
    instance = make_reservation_module(
        module_obj,
        {
            "state": "present",
            "compartment_id": "compartment",
            "availability_domain": "AD-1",
            "instance_reservation_configs": [
                {"instance_shape": "shape", "reserved_count": 1}
            ],
        },
        check_mode=True,
    )
    instance.client = types.SimpleNamespace(
        list_compute_capacity_reservations=raising(AssertionError("unexpected API call"))
    )
    instance.resolve_target_resource = lambda: None

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload["changed"] is True


@pytest.mark.parametrize("configs", [None, []], ids=["omitted", "empty"])
def test_check_mode_rejects_create_without_reservation_configs(monkeypatch, configs):
    """Reject an invalid create before check mode can predict a change."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_capacity_reservation")
    params = {
        "state": "present",
        "compartment_id": "compartment",
        "availability_domain": "AD-1",
    }
    if configs is not None:
        params["instance_reservation_configs"] = configs
    instance = make_reservation_module(module_obj, params, check_mode=True)
    instance.resolve_target_resource = lambda: None
    instance.create_resource = raising(
        AssertionError("create call was not expected")
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert "instance_reservation_configs" in exc_info.value.payload["msg"]


def test_check_mode_predicts_update_without_sdk_mutation(monkeypatch):
    """Predict an update without calling the OCI update operation."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_capacity_reservation")
    instance = make_reservation_module(
        module_obj,
        {"state": "present", "is_default_reservation": True},
        check_mode=True,
    )
    instance.resolve_target_resource = lambda: FakeModel(
        id="reservation", is_default_reservation=False
    )
    instance.update_resource = raising(
        AssertionError("update call was not expected")
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload["changed"] is True


def test_check_mode_predicts_delete_without_sdk_mutation(monkeypatch):
    """Predict a delete without calling the OCI delete operation."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_capacity_reservation")
    instance = make_reservation_module(
        module_obj,
        {"state": "absent", "capacity_reservation_id": "reservation"},
        check_mode=True,
    )
    resource = FakeModel(id="reservation", lifecycle_state="ACTIVE")
    instance.resolve_target_resource = lambda: resource
    instance.delete_resource = raising(
        AssertionError("delete call was not expected")
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload["changed"] is True


def test_matching_reservation_is_idempotent(monkeypatch):
    """Return unchanged when the current reservation matches the request."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_capacity_reservation")
    params = {
        "state": "present",
        "name": "reserved",
        "is_default_reservation": False,
        "instance_reservation_configs": [
            {"instance_shape": "shape", "reserved_count": 1}
        ],
    }
    instance = make_reservation_module(module_obj, params)
    resource = FakeModel(
        id="reservation",
        display_name="reserved",
        is_default_reservation=False,
        instance_reservation_configs=[
            FakeModel(instance_shape="shape", reserved_count=1, used_count=0)
        ],
    )
    instance.resolve_target_resource = lambda: resource

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload["changed"] is False


@pytest.mark.parametrize(
    "wait,headers,expected_events",
    [
        (True, {"opc-work-request-id": "request-1"}, ["delete", "work", "resource"]),
        (True, {}, ["delete", "resource"]),
        (False, {"opc-work-request-id": "request-1"}, ["delete"]),
    ],
)
def test_delete_preserves_wait_order_and_skips_reads_without_wait(
    monkeypatch, wait, headers, expected_events
):
    """Preserve delete wait order and avoid resource reads when waiting is disabled."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_capacity_reservation")
    events = []

    def delete_reservation(**kwargs):
        """Record the delete operation and return its response."""
        assert kwargs == {"capacity_reservation_id": "reservation"}
        events.append("delete")
        return FakeResponse(data=None, headers=headers)

    instance = make_reservation_module(
        module_obj,
        {"wait": wait},
        client=types.SimpleNamespace(delete_compute_capacity_reservation=delete_reservation),
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    instance.wait_for_work_request = lambda client, request_id: events.append("work")

    def wait_for_resource(resource_id, states):
        """Record the resource wait and check its target state."""
        assert resource_id == "reservation"
        assert tuple(states) == ("DELETED",)
        events.append("resource")

    instance.wait_for_resource_id = wait_for_resource
    instance.get_resource_by_id = lambda *args: pytest.fail("Unexpected resource read")

    assert instance.delete_resource(FakeModel(id="reservation")) is None
    assert events == expected_events


@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize("old_domain,new_domain", [("FD-1", None), (None, "FD-1"), ("FD-1", "FD-2")])
@pytest.mark.parametrize("count", [1, 2])
def test_fault_domain_replacement_fails_before_mutation(monkeypatch, check_mode, old_domain, new_domain, count):
    """Reject domain replacements even when the count changes or check mode is enabled."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_capacity_reservation")
    config = {"instance_shape": "shape", "reserved_count": count}
    if new_domain is not None:
        config["fault_domain"] = new_domain
    instance = make_reservation_module(
        module_obj, {"instance_reservation_configs": [config]}, check_mode=check_mode
    )
    resource = FakeModel(id="reservation", instance_reservation_configs=[
        FakeModel(instance_shape="shape", reserved_count=1, fault_domain=old_domain, used_count=0)
    ])
    instance.resolve_target_resource = lambda: resource
    instance.update_resource = raising(AssertionError("Unexpected mutation"))

    with pytest.raises(FailJsonCalled) as exc:
        instance.execute_resource_module()

    assert "deleting the reservation" in exc.value.payload["msg"]
    assert "creating a new reservation" in exc.value.payload["msg"]


@pytest.mark.parametrize("current_order", list(permutations(range(2))))
@pytest.mark.parametrize("desired_order", list(permutations(range(2))))
@pytest.mark.parametrize("check_mode", [False, True])
def test_mixed_fault_domains_are_idempotent(monkeypatch, current_order, desired_order, check_mode):
    """Keep matching specified and unspecified domains unchanged in every order."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_capacity_reservation")
    configs = [{"instance_shape": "shape", "reserved_count": 1},
               {"instance_shape": "shape", "reserved_count": 1, "fault_domain": "FD-1"}]
    desired = [dict(configs[index]) for index in desired_order]
    desired[0].setdefault("fault_domain", None)
    resource = FakeModel(id="reservation", instance_reservation_configs=[
        FakeModel(**configs[index], used_count=0) for index in current_order
    ])
    instance = make_reservation_module(module_obj, {"instance_reservation_configs": desired}, check_mode=check_mode)
    instance.resolve_target_resource = lambda: resource
    instance.update_resource = raising(AssertionError("Unexpected mutation"))

    with pytest.raises(ExitJsonCalled) as exc:
        instance.execute_resource_module()

    assert exc.value.payload["changed"] is False


@pytest.mark.parametrize("operation", ["add", "remove", "count"])
def test_configuration_changes_preserve_fault_domain_rules(monkeypatch, operation):
    """Permit adding, removing, and resizing configurations with retained placement."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_capacity_reservation")
    configs = [{"instance_shape": "shape", "reserved_count": 1, "fault_domain": "FD-1"},
               {"instance_shape": "shape", "reserved_count": 1}]
    current, desired = [dict(item) for item in configs], [dict(item) for item in configs]
    if operation == "add":
        current.pop()
    elif operation == "remove":
        desired.pop()
    else:
        desired[0]["reserved_count"] = 2
    instance = make_reservation_module(module_obj, {"instance_reservation_configs": desired})

    plan = instance.build_update_plan(FakeModel(instance_reservation_configs=current))

    assert plan["update_needed"] is True
    assert plan["update_model_fields"]["instance_reservation_configs"] == desired


def test_constructed_module_creates_reservation_and_waits(monkeypatch):
    """Construct both clients and execute creation with the expected payload and waits."""
    shared_install_fake_oci(monkeypatch, model_names=MODEL_NAMES, include_work_requests=True)
    module_obj = load_collection_module("oci_instance_capacity_reservation")
    from ansible_collections.ansible.oci.plugins.module_utils import oci_base
    events = []
    created = FakeModel(id="reservation")
    final = FakeModel(id="reservation", lifecycle_state="ACTIVE")

    def create(**kwargs):
        details = kwargs["create_compute_capacity_reservation_details"]
        assert details.compartment_id == "compartment"
        assert details.availability_domain == "AD-1"
        assert details.display_name == "reserved"
        assert details.is_default_reservation is False
        assert details.freeform_tags == {"phase": "create"}
        assert details.defined_tags == {"ns": {"key": "value"}}
        config = details.instance_reservation_configs[0]
        assert config.instance_shape == "shape"
        assert config.reserved_count == 1
        assert config.instance_shape_config.ocpus == 1.0
        events.append("create")
        return FakeResponse(created, {"opc-work-request-id": "work"})

    client = types.SimpleNamespace(create_compute_capacity_reservation=create)
    work_client = types.SimpleNamespace()
    monkeypatch.setattr(oci_base, "HAS_OCI_SDK", True)
    monkeypatch.setattr(oci_base, "create_service_client", lambda module, cls: client)
    monkeypatch.setattr(module_obj, "create_service_client", lambda module, cls: work_client)
    instance = module_obj.OciComputeCapacityReservationModule(DummyModule({
        "compartment_id": "compartment", "availability_domain": "AD-1", "name": "reserved",
        "is_default_reservation": False, "freeform_tags": {"phase": "create"},
        "defined_tags": {"ns": {"key": "value"}}, "wait": True,
        "instance_reservation_configs": [{"instance_shape": "shape", "reserved_count": 1,
                                          "instance_shape_config": {"ocpus": 1.0}}],
    }))
    assert instance.client is client
    assert instance.work_request_client is work_client
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)

    def wait_work(actual_client, request_id):
        assert actual_client is work_client
        assert request_id == "work"
        events.append("work")

    def wait_resource(resource_id, states):
        assert resource_id == "reservation"
        assert states == ("ACTIVE",)
        events.append("resource")
        return final

    instance.wait_for_work_request = wait_work
    instance.wait_for_resource_id = wait_resource

    assert instance.create_resource() is final
    assert events == ["create", "work", "resource"]
