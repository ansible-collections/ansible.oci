from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


def make_capacity_reservation_info_module(module_obj, params, client=None):
    """Create an info module instance without calling its constructor."""
    return make_module_instance(
        module_obj,
        "OciComputeCapacityReservationInfoModule",
        params,
        client=client,
    )


def test_main_requires_compartment_or_reservation_id_and_exposes_choices(monkeypatch):
    """Require a list scope or resource ID and expose lifecycle choices."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_capacity_reservation_info")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        captured["required_one_of"] = kwargs["required_one_of"]
        return DummyModule({"lifecycle_state": "active"})

    class FakeInfoModule:
        def __init__(self, module):
            self.module = module

        def execute_info_module(self):
            captured["run_called"] = True
            captured["params"] = self.module.params

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciComputeCapacityReservationInfoModule", FakeInfoModule)
    module_obj.main()

    assert captured["run_called"] is True
    assert captured["required_one_of"] == [["compartment_id", "capacity_reservation_id"]]
    assert captured["params"]["lifecycle_state"] == "ACTIVE"
    assert captured["argument_spec"]["lifecycle_state"]["choices"] == [
        "active", "creating", "updating", "moving", "deleted", "deleting"
    ]


def test_fetch_resources_prefers_id_lookup(monkeypatch):
    """Use the get operation when the caller gives a reservation ID."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_capacity_reservation_info")
    get_calls = []

    def get_reservation(**kwargs):
        get_calls.append(kwargs)
        return FakeResponse(data=FakeModel(id=kwargs["capacity_reservation_id"]))

    instance = make_capacity_reservation_info_module(
        module_obj,
        {"capacity_reservation_id": "reservation"},
        client=types.SimpleNamespace(get_compute_capacity_reservation=get_reservation),
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    instance.list_all_resources = raising(AssertionError("list call was not expected"))

    resources = instance.fetch_resources()

    assert [resource.id for resource in resources] == ["reservation"]
    assert get_calls == [{"capacity_reservation_id": "reservation"}]


def test_fetch_resources_returns_empty_list_when_get_returns_404(monkeypatch):
    """Return an empty result when the requested reservation does not exist."""
    _oci_module, service_error = install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_capacity_reservation_info")

    def get_missing_reservation(**kwargs):
        raise service_error(404, "missing")

    instance = make_capacity_reservation_info_module(
        module_obj,
        {"capacity_reservation_id": "missing"},
        client=types.SimpleNamespace(get_compute_capacity_reservation=get_missing_reservation),
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)

    assert instance.fetch_resources() == []


def test_fetch_resources_lists_with_filters_and_pagination(monkeypatch):
    """Pass supported filters to the paginated list operation."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_capacity_reservation_info")
    calls = []
    instance = make_capacity_reservation_info_module(
        module_obj,
        {
            "compartment_id": "compartment",
            "availability_domain": "AD-1",
            "lifecycle_state": "ACTIVE",
            "name": "reserved",
        },
        client=types.SimpleNamespace(list_compute_capacity_reservations="list_method"),
    )

    def list_all_resources(list_fn, **kwargs):
        calls.append((list_fn, kwargs))
        return [FakeModel(id="reservation", display_name="reserved")]

    instance.list_all_resources = list_all_resources
    resources = instance.fetch_resources()

    assert [resource.id for resource in resources] == ["reservation"]
    assert calls == [
        (
            "list_method",
            {
                "compartment_id": "compartment",
                "availability_domain": "AD-1",
                "lifecycle_state": "ACTIVE",
            },
        )
    ]


def test_run_returns_capacity_reservations_key(monkeypatch):
    """Return the documented capacity reservations result key."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_capacity_reservation_info")
    resource = FakeModel(id="reservation", display_name="reserved", lifecycle_state="ACTIVE")
    instance = make_capacity_reservation_info_module(module_obj, {"compartment_id": "compartment"})
    instance.fetch_resources = lambda: [resource]

    try:
        instance.execute_info_module()
    except ExitJsonCalled as result:
        assert result.payload == {
            "changed": False,
            "capacity_reservations": [
                {"id": "reservation", "name": "reserved", "lifecycle_state": "ACTIVE"}
            ],
        }
    else:
        raise AssertionError("execute_info_module did not return")
