from __future__ import absolute_import, division, print_function

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


class InfoClient:
    def __init__(self, service_error, expected_prefix=None, headers=None):
        self.service_error = service_error
        self.expected_prefix = expected_prefix
        self.headers = headers if headers is not None else {"etag": "abc", "content-length": "4"}
        self.namespace_requests = []
        self.namespace_error = None
        self.head_requests = []
        self.list_requests = []

    def get_namespace(self, **kwargs):
        self.namespace_requests.append(kwargs)
        if self.namespace_error is not None:
            raise self.namespace_error
        return FakeResponse("testns")

    def head_object(self, **kwargs):
        self.head_requests.append(kwargs)
        if kwargs["object_name"] == "missing":
            raise self.service_error(404)
        return FakeResponse(None, self.headers)

    def list_objects(self, **kwargs):
        self.list_requests.append(kwargs)
        assert set(kwargs["fields"].split(",")) == {
            "name",
            "size",
            "etag",
            "md5",
            "timeCreated",
            "timeModified",
            "storageTier",
            "archivalState",
        }
        assert kwargs["prefix"] == self.expected_prefix
        return FakeResponse(
            FakeModel(
                objects=[
                    FakeModel(name="a-other", size=1),
                    FakeModel(name="a", size=4, etag="abc"),
                ]
            )
        )


def load_info(monkeypatch):
    fake_oci, service_error = install_fake_oci(monkeypatch)
    fake_oci.util = types.SimpleNamespace(
        to_dict=lambda resource: resource if isinstance(resource, dict) else vars(resource)
    )
    fake_oci.object_storage = types.SimpleNamespace(
        ObjectStorageClient=type("ObjectStorageClient", (), {}),
        models=types.SimpleNamespace(
            ObjectSummary=lambda: FakeModel(
                attribute_map={
                    "name": "name",
                    "size": "size",
                    "md5": "md5",
                    "time_created": "timeCreated",
                    "time_modified": "timeModified",
                    "etag": "etag",
                    "storage_tier": "storageTier",
                    "archival_state": "archivalState",
                },
            ),
        ),
    )
    return load_collection_module("oci_object_storage_object_info"), service_error


def run(module_obj, monkeypatch, client, params):
    instance = make_module_instance(
        module_obj, "OciObjectStorageObjectInfoModule", params, client=client
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, *args, **kwargs: fn(*args, **kwargs),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda fn, *args, **kwargs: fn(*args, **kwargs).data,
    )

    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_info_module()

    return result.value.payload


@pytest.mark.parametrize(
    "headers",
    [
        {"etag": "abc", "content-length": "4"},
        {"ETag": "abc", "Content-Length": "4"},
    ],
)
@pytest.mark.parametrize("namespace_name", ["ns", None])
def test_exact_lookup_returns_sdk_summary_and_headers(
    monkeypatch, headers, namespace_name
):
    module_obj, service_error = load_info(monkeypatch)
    client = InfoClient(service_error, expected_prefix="a", headers=headers)
    found = run(
        module_obj,
        monkeypatch,
        client,
        {
            "bucket_name": "bucket",
            "namespace_name": namespace_name,
            "object_name": "a",
        },
    )
    assert found["objects"][0]["name"] == "a"
    assert found["objects"][0]["etag"] == "abc"
    assert found["objects"][0]["size"] == 4
    assert found["objects"][0]["headers"] == {"etag": "abc", "content-length": "4"}
    expected_namespace = namespace_name or "testns"
    assert client.list_requests[0]["namespace_name"] == expected_namespace
    assert client.head_requests[0]["namespace_name"] == expected_namespace
    assert client.namespace_requests == ([{}] if namespace_name is None else [])


def test_namespace_uses_supplied_name_without_lookup(monkeypatch):
    module_obj, service_error = load_info(monkeypatch)
    client = InfoClient(service_error)
    instance = make_module_instance(
        module_obj,
        "OciObjectStorageObjectInfoModule",
        {"namespace_name": "customns"},
        client=client,
    )
    retry_calls = []
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, *args, **kwargs: retry_calls.append(fn.__name__),
    )

    assert instance.namespace_name == "customns"
    assert instance.namespace_name == "customns"
    assert client.namespace_requests == []
    assert retry_calls == []


@pytest.mark.parametrize("namespace_name", [None, ""])
def test_namespace_is_resolved_once_through_retry(monkeypatch, namespace_name):
    module_obj, service_error = load_info(monkeypatch)
    client = InfoClient(service_error)
    instance = make_module_instance(
        module_obj,
        "OciObjectStorageObjectInfoModule",
        {"namespace_name": namespace_name},
        client=client,
    )
    retry_calls = []

    def call_with_retry(fn, *args, **kwargs):
        retry_calls.append((fn.__name__, args, kwargs))
        return fn(*args, **kwargs)

    monkeypatch.setattr(instance, "call_with_retry", call_with_retry)

    assert instance.namespace_name == "testns"
    assert instance.namespace_name == "testns"
    assert client.namespace_requests == [{}]
    assert retry_calls == [("get_namespace", (), {})]


def test_namespace_lookup_failure_is_not_cached(monkeypatch):
    module_obj, service_error = load_info(monkeypatch)
    client = InfoClient(service_error)
    client.namespace_error = service_error(403, "forbidden")
    instance = make_module_instance(
        module_obj,
        "OciObjectStorageObjectInfoModule",
        {"namespace_name": None},
        client=client,
    )
    monkeypatch.setattr(
        instance, "call_with_retry", lambda fn, *args, **kwargs: fn(*args, **kwargs)
    )

    with pytest.raises(service_error) as result:
        instance.namespace_name

    assert result.value is client.namespace_error
    assert getattr(instance, "_namespace_name", None) is None
    client.namespace_error = None
    assert instance.namespace_name == "testns"
    assert client.namespace_requests == [{}, {}]


def test_missing_exact_object_returns_empty_list(monkeypatch):
    module_obj, service_error = load_info(monkeypatch)
    client = InfoClient(service_error, expected_prefix="missing")

    missing = run(
        module_obj,
        monkeypatch,
        client,
        {"bucket_name": "bucket", "namespace_name": "ns", "object_name": "missing"},
    )
    assert missing["objects"] == []


def test_list_uses_prefix_and_unwraps_object_summaries(monkeypatch):
    module_obj, service_error = load_info(monkeypatch)
    client = InfoClient(service_error, expected_prefix="a")
    result = run(
        module_obj,
        monkeypatch,
        client,
        {"bucket_name": "bucket", "namespace_name": None, "prefix": "a"},
    )
    assert [obj["name"] for obj in result["objects"]] == ["a-other", "a"]
    assert client.namespace_requests == [{}]
    assert client.list_requests[0]["namespace_name"] == "testns"
