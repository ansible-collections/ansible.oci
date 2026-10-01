from __future__ import absolute_import, division, print_function

__metaclass__ = type

import types

import pytest

from .conftest import (
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
)


class BucketInfoClient:
    def __init__(self, service_error):
        self.service_error = service_error
        self.namespace_requests = []
        self.list_requests = []

    def get_namespace(self, **kwargs):
        self.namespace_requests.append(kwargs)
        return FakeResponse("testns")

    def get_bucket(self, namespace_name, bucket_name, fields):
        assert namespace_name == "testns"
        assert fields == ["autoTiering"]
        if bucket_name == "missing":
            raise self.service_error(404)
        return FakeResponse(
            FakeModel(
                id="ocid1.bucket.oc1..test",
                namespace="testns",
                name=bucket_name,
                compartment_id="compartment",
                versioning="Enabled",
                storage_tier="Standard",
                auto_tiering="Disabled",
            )
        )

    def list_buckets(self, namespace_name, compartment_id):
        self.list_requests.append((namespace_name, compartment_id))
        return FakeResponse(
            [
                FakeModel(name="logs", compartment_id=compartment_id),
                FakeModel(name="other", compartment_id=compartment_id),
            ]
        )


def load_info(monkeypatch):
    fake_oci, service_error = install_fake_oci(monkeypatch)
    fake_oci.object_storage = types.SimpleNamespace(
        ObjectStorageClient=type("ObjectStorageClient", (), {})
    )
    return load_collection_module("oci_object_storage_bucket_info"), service_error


def run_info(module_obj, monkeypatch, client, params, check_mode=False):
    instance = make_module_instance(
        module_obj,
        "OciObjectStorageBucketInfoModule",
        params,
        client=client,
        check_mode=check_mode,
    )
    monkeypatch.setattr(
        instance, "call_with_retry", lambda fn, *args, **kwargs: fn(*args, **kwargs)
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda fn, *args, **kwargs: fn(*args, **kwargs).data,
    )
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_info_module()
    return result.value.payload


def test_bucket_name_returns_full_bucket_and_missing_returns_empty(monkeypatch):
    module_obj, service_error = load_info(monkeypatch)
    client = BucketInfoClient(service_error)
    found = run_info(
        module_obj,
        monkeypatch,
        client,
        {"bucket_name": "logs", "namespace_name": "testns"},
        check_mode=True,
    )
    missing = run_info(
        module_obj,
        monkeypatch,
        client,
        {"bucket_name": "missing", "namespace_name": "testns"},
    )
    assert found["changed"] is False
    assert found["buckets"][0]["name"] == "logs"
    assert found["buckets"][0]["versioning"] == "Enabled"
    assert found["buckets"][0]["auto_tiering"] == "Disabled"
    assert missing == {"changed": False, "buckets": []}
    assert client.namespace_requests == []


def test_compartment_list_filters_by_bucket_name(monkeypatch):
    module_obj, service_error = load_info(monkeypatch)
    client = BucketInfoClient(service_error)
    result = run_info(
        module_obj,
        monkeypatch,
        client,
        {"compartment_id": "compartment", "name": "logs"},
    )
    assert result == {
        "changed": False,
        "buckets": [{"name": "logs", "compartment_id": "compartment"}],
    }
    assert client.namespace_requests == [{"compartment_id": "compartment"}]
    assert client.list_requests == [("testns", "compartment")]
