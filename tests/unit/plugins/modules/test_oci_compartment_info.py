from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

from .conftest import (
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
)


def test_main_requires_compartment_id_or_parent_compartment_id(monkeypatch):
    install_fake_oci(monkeypatch)
    info_module = load_collection_module("oci_compartment_info")
    captured = {}

    class FakeAnsibleModule:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(info_module, "AnsibleModule", FakeAnsibleModule)
    monkeypatch.setattr(
        info_module,
        "OciCompartmentInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )

    info_module.main()

    assert captured["required_one_of"] == [["compartment_id", "parent_compartment_id"]]
    assert captured["argument_spec"]["compartment_id"] == {"type": "str"}
    assert captured["argument_spec"]["parent_compartment_id"] == {"type": "str"}
    assert captured["argument_spec"]["name"] == {"type": "str"}
    assert captured["argument_spec"]["lifecycle_state"] == {"type": "str"}


def test_info_module_class_metadata(monkeypatch):
    install_fake_oci(monkeypatch)
    info_module = load_collection_module("oci_compartment_info")

    assert info_module.OciCompartmentInfoModule.results_key == "compartments"
    assert info_module.OciCompartmentInfoModule.resource_id_param == "compartment_id"
    assert info_module.OciCompartmentInfoModule.resource_get_method == "get_compartment"
    assert info_module.OciCompartmentInfoModule.list_resource_method == "list_compartments"
    assert info_module.OciCompartmentInfoModule.name_response_field == "name"


def test_fetch_resources_prefers_get_by_id(monkeypatch):
    install_fake_oci(monkeypatch)
    info_module = load_collection_module("oci_compartment_info")
    get_calls = []
    compartment = FakeModel(id="ocid1.compartment.oc1..child", name="development")

    def get_compartment(compartment_id):
        get_calls.append(compartment_id)
        return FakeResponse(data=compartment)

    instance = make_module_instance(
        info_module,
        "OciCompartmentInfoModule",
        {"compartment_id": "ocid1.compartment.oc1..child"},
        client=types.SimpleNamespace(get_compartment=get_compartment),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.fetch_resources() == [compartment]
    assert get_calls == ["ocid1.compartment.oc1..child"]


def test_fetch_resources_lists_children_and_filters_name(monkeypatch):
    install_fake_oci(monkeypatch)
    info_module = load_collection_module("oci_compartment_info")
    calls = []
    expected = FakeModel(id="ocid1.compartment.oc1..child", name="development")
    instance = make_module_instance(
        info_module,
        "OciCompartmentInfoModule",
        {
            "parent_compartment_id": "ocid1.compartment.oc1..parent",
            "name": "development",
            "lifecycle_state": "ACTIVE",
        },
        client=types.SimpleNamespace(list_compartments="list_compartments_method"),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: calls.append((list_fn, kwargs))
        or [expected, FakeModel(id="ocid1.compartment.oc1..other", name="other")],
    )

    assert instance.fetch_resources() == [expected]
    assert calls == [
        (
            "list_compartments_method",
            {
                "compartment_id": "ocid1.compartment.oc1..parent",
                "lifecycle_state": "ACTIVE",
            },
        )
    ]


def test_execute_info_module_returns_serialized_compartments(monkeypatch):
    install_fake_oci(monkeypatch)
    info_module = load_collection_module("oci_compartment_info")
    instance = make_module_instance(
        info_module,
        "OciCompartmentInfoModule",
        {"parent_compartment_id": "ocid1.compartment.oc1..parent"},
    )
    monkeypatch.setattr(
        instance,
        "fetch_resources",
        lambda: [
            FakeModel(
                id="ocid1.compartment.oc1..child",
                compartment_id="ocid1.compartment.oc1..parent",
                name="development",
            )
        ],
    )

    try:
        instance.execute_info_module()
    except ExitJsonCalled as exc_info:
        payload = exc_info.payload
    else:
        raise AssertionError("execute_info_module did not call exit_json")

    assert payload == {
        "changed": False,
        "compartments": [
            {
                "id": "ocid1.compartment.oc1..child",
                "compartment_id": "ocid1.compartment.oc1..parent",
                "name": "development",
            }
        ],
    }
