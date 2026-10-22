from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from .conftest import (
    ExitJsonCalled,
    FakeModel,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)


SOURCE_ID = "ocid1.autonomousdatabase.oc1..source"
COMPARTMENT_ID = "ocid1.compartment.oc1..example"


def install_fake_oci(monkeypatch):
    oci_module, service_error = shared_install_fake_oci(monkeypatch)
    oci_module.database = types.SimpleNamespace(
        DatabaseClient=type("FakeDatabaseClient", (), {}),
        models=types.SimpleNamespace(),
    )
    return oci_module, service_error


def make_info_module(info_module, params):
    return make_module_instance(
        info_module,
        "OciAutonomousDatabaseCloneInfoModule",
        params,
        client=types.SimpleNamespace(
            list_autonomous_database_clones=lambda **kwargs: None
        ),
    )


def test_main_wires_argument_spec(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_autonomous_database_clone_info")
    captured = {}

    class FakeAnsibleModule:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(info_module, "AnsibleModule", FakeAnsibleModule)
    monkeypatch.setattr(
        info_module,
        "OciAutonomousDatabaseCloneInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )

    info_module.main()

    spec = captured["argument_spec"]
    assert captured["supports_check_mode"] is True
    assert spec["compartment_id"] == {"type": "str", "required": True}
    assert spec["source_id"] == {"type": "str", "required": True}
    assert spec["name"] == {"type": "str"}
    assert spec["lifecycle_state"] == {"type": "str"}
    assert spec["refreshable_only"] == {"type": "bool", "default": False}


@pytest.mark.parametrize(
    "extra_params, expected_extra_kwargs",
    [
        ({"refreshable_only": False}, {}),
        ({"refreshable_only": True}, {"clone_type": "REFRESHABLE_CLONE"}),
        (
            {"refreshable_only": False, "lifecycle_state": "AVAILABLE"},
            {"lifecycle_state": "AVAILABLE"},
        ),
    ],
)
def test_fetch_resources_maps_filters_to_list_clones(
    monkeypatch, extra_params, expected_extra_kwargs
):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_autonomous_database_clone_info")
    params = dict(compartment_id=COMPARTMENT_ID, source_id=SOURCE_ID, **extra_params)
    instance = make_info_module(info_module, params)
    list_calls = []

    def fake_list_all_resources(list_fn, **kwargs):
        list_calls.append((list_fn, kwargs))
        return []

    monkeypatch.setattr(instance, "list_all_resources", fake_list_all_resources)

    assert instance.fetch_resources() == []
    assert list_calls[0][0] == instance.client.list_autonomous_database_clones
    assert list_calls[0][1] == dict(
        compartment_id=COMPARTMENT_ID,
        autonomous_database_id=SOURCE_ID,
        **expected_extra_kwargs
    )


def test_fetch_resources_filters_by_exact_name(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_autonomous_database_clone_info")
    keep = FakeModel(id="ocid1.autonomousdatabase.oc1..keep", display_name="clone-a")
    drop = FakeModel(id="ocid1.autonomousdatabase.oc1..drop", display_name="clone-b")
    instance = make_info_module(
        info_module,
        {"compartment_id": COMPARTMENT_ID, "source_id": SOURCE_ID, "name": "clone-a"},
    )
    monkeypatch.setattr(instance, "list_all_resources", lambda list_fn, **kwargs: [keep, drop])

    assert instance.fetch_resources() == [keep]


def test_execute_info_module_serializes_and_renames_display_name(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_autonomous_database_clone_info")
    instance = make_info_module(
        info_module,
        {"compartment_id": COMPARTMENT_ID, "source_id": SOURCE_ID},
    )
    monkeypatch.setattr(
        instance,
        "fetch_resources",
        lambda: [
            FakeModel(
                id="ocid1.autonomousdatabase.oc1..clone",
                display_name="example-clone",
                source_id=SOURCE_ID,
            )
        ],
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()

    assert exc_info.value.payload == {
        "changed": False,
        "autonomous_databases": [
            {
                "id": "ocid1.autonomousdatabase.oc1..clone",
                "name": "example-clone",
                "source_id": SOURCE_ID,
            }
        ],
    }
