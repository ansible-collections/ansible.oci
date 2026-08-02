from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

from conftest import (
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


def make_route_table_info_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciRouteTableInfoModule",
        params,
        client=client,
    )


def test_fetch_resources_prefers_id_lookup_using_rt_id_kwarg(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_route_table_info")
    get_calls = []

    def get_route_table(**kwargs):
        get_calls.append(kwargs)
        return FakeResponse(
            data=FakeModel(id=kwargs["rt_id"], display_name="example-route-table")
        )

    instance = make_route_table_info_module(
        info_module,
        {"route_table_id": "ocid1.routetable.oc1..example"},
        client=types.SimpleNamespace(get_route_table=get_route_table),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        raising(AssertionError("list_all_resources should not be called")),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    resources = instance.fetch_resources()

    assert len(resources) == 1
    assert resources[0].id == "ocid1.routetable.oc1..example"
    assert get_calls == [{"rt_id": "ocid1.routetable.oc1..example"}]


def test_fetch_resources_lists_by_compartment_and_vcn(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_route_table_info")
    paginate_calls = []
    instance = make_route_table_info_module(
        info_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "lifecycle_state": "AVAILABLE",
        },
        client=types.SimpleNamespace(list_route_tables="list_method"),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: paginate_calls.append((list_fn, kwargs)) or [],
    )

    resources = instance.fetch_resources()

    assert resources == []
    assert paginate_calls == [
        (
            "list_method",
            {
                "compartment_id": "ocid1.compartment.oc1..example",
                "vcn_id": "ocid1.vcn.oc1..example",
                "lifecycle_state": "AVAILABLE",
            },
        )
    ]


def test_run_returns_route_tables_key(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_route_table_info")
    resource = FakeModel(
        id="ocid1.routetable.oc1..example",
        display_name="example-route-table",
        lifecycle_state="AVAILABLE",
    )
    instance = make_route_table_info_module(
        info_module,
        {"compartment_id": "ocid1.compartment.oc1..example"},
    )
    monkeypatch.setattr(instance, "fetch_resources", lambda: [resource])

    try:
        instance.execute_info_module()
        raise AssertionError("execute_info_module should raise ExitJsonCalled")
    except ExitJsonCalled as exc_info:
        assert exc_info.payload == {
            "changed": False,
            "route_tables": [
                {
                    "id": "ocid1.routetable.oc1..example",
                    "name": "example-route-table",
                    "lifecycle_state": "AVAILABLE",
                }
            ],
        }
