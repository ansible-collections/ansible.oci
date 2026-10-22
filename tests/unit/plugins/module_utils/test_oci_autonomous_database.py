from __future__ import absolute_import, division, print_function

__metaclass__ = type

import types

from .conftest import load_collection_module


class FakeDatabaseClient:
    pass


class FakeUpdateDetails:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def load_adb_util(monkeypatch):
    fake_oci = types.SimpleNamespace(
        database=types.SimpleNamespace(
            DatabaseClient=FakeDatabaseClient,
            models=types.SimpleNamespace(
                UpdateAutonomousDatabaseDetails=FakeUpdateDetails,
            ),
        )
    )
    oci_common = load_collection_module("oci_common")
    monkeypatch.setattr(oci_common, "import_oci_sdk", lambda: (fake_oci, True))
    return load_collection_module("oci_autonomous_database")


def make_adb_base(util, client=None):
    class ConcreteADB(util.OciADBBase):
        update_field_specs = ()

        def create_resource(self):
            raise NotImplementedError

    instance = object.__new__(ConcreteADB)
    instance.client = client or types.SimpleNamespace()
    return instance


def test_class_metadata(monkeypatch):
    util = load_adb_util(monkeypatch)
    cls = util.OciADBBase

    assert cls.client_class.fget(None) is FakeDatabaseClient
    assert cls.resource_id_param == "autonomous_database_id"
    assert cls.list_resource_method == "list_autonomous_databases"
    assert cls.update_method_name == "update_autonomous_database"
    assert cls.update_details_name == "update_autonomous_database_details"


def test_get_resource_response_calls_get_autonomous_database(monkeypatch):
    util = load_adb_util(monkeypatch)
    calls = []
    response = object()

    def get_autonomous_database(autonomous_database_id):
        calls.append(autonomous_database_id)
        return response

    client = types.SimpleNamespace(get_autonomous_database=get_autonomous_database)
    instance = make_adb_base(util, client)
    monkeypatch.setattr(
        instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs), raising=False
    )

    assert instance.get_resource_response("ocid1.adb") is response
    assert calls == ["ocid1.adb"]


def test_build_update_details_builds_update_model(monkeypatch):
    util = load_adb_util(monkeypatch)
    instance = make_adb_base(util)

    details = instance.build_update_details(
        {"compute_count": 4.0, "display_name": "adb"}
    )

    assert isinstance(details, FakeUpdateDetails)
    assert details.compute_count == 4.0
    assert details.display_name == "adb"


def test_delete_resource_deletes_by_resource_id_and_waits(monkeypatch):
    util = load_adb_util(monkeypatch)
    delete_fn = object()
    client = types.SimpleNamespace(delete_autonomous_database=delete_fn)
    instance = make_adb_base(util, client)
    resource = types.SimpleNamespace(id="ocid1.adb")
    captured = {}
    terminated = object()

    def delete_resource_and_wait(res, fn, **kwargs):
        captured.update(resource=res, fn=fn, kwargs=kwargs)
        return terminated

    monkeypatch.setattr(
        instance, "delete_resource_and_wait", delete_resource_and_wait, raising=False
    )

    assert instance.delete_resource(resource) is terminated
    assert captured["resource"] is resource
    assert captured["fn"] is delete_fn
    assert captured["kwargs"] == {"autonomous_database_id": "ocid1.adb"}
