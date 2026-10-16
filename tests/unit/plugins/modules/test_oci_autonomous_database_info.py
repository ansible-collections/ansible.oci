from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

from .conftest import (
    ExitJsonCalled,
    FakeModel,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)


def install_fake_oci(monkeypatch):
    oci_module, service_error = shared_install_fake_oci(monkeypatch)
    oci_module.database = types.SimpleNamespace(
        DatabaseClient=type("FakeDatabaseClient", (), {}),
        models=types.SimpleNamespace(),
    )
    return oci_module, service_error


def test_main_requires_compartment_id_or_autonomous_database_id(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_autonomous_database_info")
    captured = {}

    class FakeAnsibleModule:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(info_module, "AnsibleModule", FakeAnsibleModule)
    monkeypatch.setattr(
        info_module,
        "OciAutonomousDatabaseInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )

    info_module.main()

    assert captured["required_one_of"] == [
        ["compartment_id", "autonomous_database_id"]
    ]
    assert captured["argument_spec"]["autonomous_database_id"] == {"type": "str"}
    assert captured["argument_spec"]["name"] == {"type": "str"}
    assert captured["argument_spec"]["lifecycle_state"] == {"type": "str"}
    assert captured["argument_spec"]["db_workload"] == {"type": "str"}
    assert captured["argument_spec"]["compartment_id"] == {"type": "str"}


def test_info_module_class_metadata(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_autonomous_database_info")
    cls = info_module.OciAutonomousDatabaseInfoModule

    assert cls.results_key == "autonomous_databases"
    assert cls.resource_id_param == "autonomous_database_id"
    assert cls.resource_get_method == "get_autonomous_database"
    assert cls.list_resource_method == "list_autonomous_databases"
    assert cls.list_filter_params == [
        "compartment_id",
        "lifecycle_state",
        "db_workload",
    ]
    # Standard display_name resource: name filtering uses the base defaults.
    assert cls.name_filter_param == "name"
    assert cls.name_response_field == "display_name"


def test_fetch_resources_prefers_get_by_id(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_autonomous_database_info")
    get_calls = []
    database = FakeModel(
        id="ocid1.autonomousdatabase.oc1..example",
        display_name="example-adb",
    )

    def get_autonomous_database(autonomous_database_id):
        get_calls.append(autonomous_database_id)
        return types.SimpleNamespace(data=database)

    instance = make_module_instance(
        info_module,
        "OciAutonomousDatabaseInfoModule",
        {"autonomous_database_id": "ocid1.autonomousdatabase.oc1..example"},
        client=types.SimpleNamespace(
            get_autonomous_database=get_autonomous_database
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    resources = instance.fetch_resources()

    assert get_calls == ["ocid1.autonomousdatabase.oc1..example"]
    assert resources == [database]


def test_execute_info_module_serializes_and_renames_display_name(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_autonomous_database_info")
    instance = make_module_instance(
        info_module,
        "OciAutonomousDatabaseInfoModule",
        {"compartment_id": "ocid1.compartment.oc1..example"},
    )
    monkeypatch.setattr(
        instance,
        "fetch_resources",
        lambda: [
            FakeModel(
                id="ocid1.autonomousdatabase.oc1..example",
                display_name="example-adb",
            )
        ],
    )

    payload = None
    try:
        instance.execute_info_module()
    except ExitJsonCalled as exc_info:
        payload = exc_info.payload
    else:
        raise AssertionError("execute_info_module did not call exit_json")

    assert payload["changed"] is False
    # The shared serializer renames display_name -> name in results.
    assert payload["autonomous_databases"] == [
        {"id": "ocid1.autonomousdatabase.oc1..example", "name": "example-adb"}
    ]
