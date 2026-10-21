from __future__ import absolute_import, division, print_function

__metaclass__ = type

import types
from datetime import datetime, timedelta, timezone
from threading import Barrier, Event, Lock, get_ident

import pytest

from .conftest import (
    ExitJsonCalled,
    FailJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
)


class BucketClient:
    def __init__(self, service_error, bucket=None):
        self.service_error = service_error
        self.bucket = bucket
        self.created = 0
        self.updated = 0
        self.deleted = 0
        self.namespace_requests = []

    def get_namespace(self, **kwargs):
        self.namespace_requests.append(kwargs)
        return FakeResponse("testns")

    def get_bucket(self, namespace_name, bucket_name, fields):
        assert namespace_name == "testns"
        assert fields == ["autoTiering"]
        if self.bucket is None or self.bucket.name != bucket_name:
            raise self.service_error(404)
        return FakeResponse(self.bucket)

    def create_bucket(self, namespace_name, create_bucket_details):
        assert namespace_name == "testns"
        self.created += 1
        self.bucket = FakeModel(
            id="ocid1.bucket.oc1..test",
            namespace="testns",
            name=create_bucket_details.name,
            compartment_id=create_bucket_details.compartment_id,
            public_access_type=getattr(
                create_bucket_details, "public_access_type", None
            )
            or "NoPublicAccess",
            storage_tier=getattr(create_bucket_details, "storage_tier", None)
            or "Standard",
            versioning=getattr(create_bucket_details, "versioning", None) or "Disabled",
            metadata=getattr(create_bucket_details, "metadata", None) or {},
            object_events_enabled=getattr(
                create_bucket_details, "object_events_enabled", None
            )
            or False,
            auto_tiering=getattr(create_bucket_details, "auto_tiering", None)
            or "Disabled",
            kms_key_id=getattr(create_bucket_details, "kms_key_id", None),
            is_bucket_key_enabled=getattr(
                create_bucket_details, "is_bucket_key_enabled", None
            )
            or False,
            freeform_tags=getattr(create_bucket_details, "freeform_tags", None) or {},
            defined_tags=getattr(create_bucket_details, "defined_tags", None) or {},
        )
        return FakeResponse(self.bucket)

    def update_bucket(self, namespace_name, bucket_name, update_bucket_details):
        assert namespace_name == "testns"
        assert self.bucket.name == bucket_name
        self.updated += 1
        for name, value in vars(update_bucket_details).items():
            setattr(self.bucket, name, value)
        return FakeResponse(self.bucket)

    def delete_bucket(self, namespace_name, bucket_name):
        assert namespace_name == "testns"
        assert self.bucket.name == bucket_name
        self.deleted += 1
        self.bucket = None
        return FakeResponse()


class ForceBucketClient(BucketClient):
    def __init__(
        self,
        service_error,
        *,
        versioning="Disabled",
        objects=(),
        versions=(),
        uploads=(),
        requests=(),
        policies=(),
        retention_rules=(),
        read_only=False,
        page_size=2,
    ):
        super().__init__(
            service_error,
            FakeModel(name="logs", versioning=versioning, is_read_only=read_only),
        )
        self.objects = list(objects)
        self.versions = list(versions)
        self.uploads = list(uploads)
        self.requests = list(requests)
        self.policies = list(policies)
        self.retention_rules = list(retention_rules)
        self.calls = []
        self.listing_calls = []
        self.page_size = page_size
        self.lock = Lock()

    def _page(self, entries, page):
        offset = int(page or 0)
        next_page = str(offset + self.page_size) if offset + self.page_size < len(entries) else None
        return FakeResponse(
            entries[offset : offset + self.page_size],
            {"opc-next-page": next_page} if next_page else {},
        )

    def make_bucket_writable(self, **kwargs):
        self.calls.append("make_bucket_writable")
        self.bucket.is_read_only = False
        return FakeResponse()

    def list_replication_policies(self, page=None, **kwargs):
        self.listing_calls.append(("policies", page))
        return self._page(self.policies, page)

    def delete_replication_policy(self, replication_id, **kwargs):
        with self.lock:
            self.calls.append(("delete_replication_policy", replication_id))
            self.policies = [p for p in self.policies if p.id != replication_id]
        return FakeResponse()

    def list_retention_rules(self, page=None, **kwargs):
        self.listing_calls.append(("retention_rules", page))
        response = self._page(self.retention_rules, page)
        return FakeResponse(FakeModel(items=response.data), response.headers)

    def delete_retention_rule(self, retention_rule_id, **kwargs):
        with self.lock:
            self.calls.append(("delete_retention_rule", retention_rule_id))
            self.retention_rules = [
                rule for rule in self.retention_rules if rule.id != retention_rule_id
            ]
        return FakeResponse()

    def list_preauthenticated_requests(self, page=None, **kwargs):
        self.listing_calls.append(("requests", page))
        return self._page(self.requests, page)

    def delete_preauthenticated_request(self, par_id, **kwargs):
        with self.lock:
            self.calls.append(("delete_preauthenticated_request", par_id))
            self.requests = [request for request in self.requests if request.id != par_id]
        return FakeResponse()

    def list_multipart_uploads(self, page=None, **kwargs):
        self.listing_calls.append(("uploads", page))
        return self._page(self.uploads, page)

    def abort_multipart_upload(self, object_name, upload_id, **kwargs):
        with self.lock:
            self.calls.append(("abort_multipart_upload", upload_id))
            self.uploads = [
                upload for upload in self.uploads if upload.upload_id != upload_id
            ]
        return FakeResponse()

    def list_object_versions(self, page=None, **kwargs):
        self.listing_calls.append(("versions", page))
        response = self._page(self.versions, page)
        return FakeResponse(FakeModel(items=response.data), response.headers)

    def list_objects(self, start=None, **kwargs):
        self.listing_calls.append(("objects", start))
        response = self._page(self.objects, start)
        return FakeResponse(
            FakeModel(objects=response.data, next_start_with=response.headers.get("opc-next-page"))
        )

    def delete_object(self, object_name, version_id=None, **kwargs):
        with self.lock:
            if self.retention_rules:
                raise self.service_error(409, "object is protected by retention")
            self.calls.append(("delete_object", object_name, version_id))
            if version_id is None:
                self.objects = [obj for obj in self.objects if obj.name != object_name]
                self.versions = [
                    version
                    for version in self.versions
                    if version.name != object_name or version.version_id is not None
                ]
            else:
                self.versions = [
                    version
                    for version in self.versions
                    if (version.name, version.version_id) != (object_name, version_id)
                ]
        return FakeResponse()

    def delete_bucket(self, namespace_name, bucket_name):
        if (
            any(
                (
                    self.objects,
                    self.versions,
                    self.uploads,
                    self.requests,
                    self.policies,
                )
            )
            or self.bucket.is_read_only
        ):
            raise self.service_error(409, "bucket is not empty")
        self.calls.append("delete_bucket")
        return super().delete_bucket(namespace_name, bucket_name)


def load_bucket(monkeypatch):
    fake_oci, service_error = install_fake_oci(monkeypatch)
    fake_oci.object_storage = types.SimpleNamespace(
        ObjectStorageClient=type("ObjectStorageClient", (), {}),
        models=types.SimpleNamespace(
            CreateBucketDetails=FakeModel,
            UpdateBucketDetails=FakeModel,
        ),
    )
    fake_oci.pagination = types.SimpleNamespace(
        list_call_get_all_results_generator=iter_listing_responses,
    )
    return load_collection_module("oci_object_storage_bucket"), service_error


def iter_listing_responses(list_fn, yield_mode, **kwargs):
    assert yield_mode == "response"
    # The SDK retry strategy inspects the callable's name before requesting a page.
    assert list_fn.__name__
    while True:
        response = list_fn(**kwargs)
        yield response
        if hasattr(response.data, "objects"):
            token = response.data.next_start_with
            parameter = "start"
        else:
            token = response.headers.get("opc-next-page")
            parameter = "page"
        if token is None:
            return
        kwargs[parameter] = token


def run_bucket(module_obj, monkeypatch, client, params, check_mode=False):
    instance = make_module_instance(
        module_obj,
        "OciObjectStorageBucketModule",
        params,
        client=client,
        check_mode=check_mode,
    )
    monkeypatch.setattr(
        instance, "call_with_retry", lambda fn, *args, **kwargs: fn(*args, **kwargs)
    )
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    return result.value.payload


def test_create_uses_bucket_name_and_rerun_is_unchanged(monkeypatch):
    module_obj, service_error = load_bucket(monkeypatch)
    client = BucketClient(service_error)
    params = {
        "name": "logs",
        "compartment_id": "ocid1.compartment.oc1..test",
        "storage_tier": "Standard",
        "public_access_type": "NoPublicAccess",
        "versioning": "Enabled",
        "kms_key_id": "ocid1.key.oc1..test",
        "is_bucket_key_enabled": True,
        "metadata": {"owner": "automation"},
        "object_events_enabled": True,
        "auto_tiering": "InfrequentAccess",
        "freeform_tags": {"purpose": "logs"},
    }

    created = run_bucket(module_obj, monkeypatch, client, params)
    rerun = run_bucket(module_obj, monkeypatch, client, params)

    assert created["changed"] is True
    assert created["resource"]["name"] == "logs"
    assert created["resource"]["versioning"] == "Enabled"
    assert created["resource"]["kms_key_id"] == "ocid1.key.oc1..test"
    assert created["resource"]["metadata"] == {"owner": "automation"}
    assert created["resource"]["object_events_enabled"] is True
    assert created["resource"]["auto_tiering"] == "InfrequentAccess"
    assert rerun["changed"] is False
    assert client.created == 1
    assert client.updated == 0
    assert client.namespace_requests == [{}, {}]


def test_create_check_mode_does_not_create_bucket(monkeypatch):
    module_obj, service_error = load_bucket(monkeypatch)
    client = BucketClient(service_error)
    result = run_bucket(
        module_obj,
        monkeypatch,
        client,
        {"name": "logs", "compartment_id": "compartment"},
        check_mode=True,
    )
    assert result == {"changed": True}
    assert client.bucket is None
    assert client.created == 0


def test_update_check_mode_and_rerun_detect_only_supplied_drift(monkeypatch):
    module_obj, service_error = load_bucket(monkeypatch)
    client = BucketClient(
        service_error,
        bucket=FakeModel(
            id="ocid1.bucket.oc1..test",
            namespace="testns",
            name="logs",
            compartment_id="compartment",
            storage_tier="Standard",
            public_access_type="NoPublicAccess",
            versioning="Disabled",
            metadata={"old": "value"},
            object_events_enabled=True,
            auto_tiering="Disabled",
            kms_key_id=None,
            is_bucket_key_enabled=False,
            freeform_tags={"phase": "create"},
            defined_tags={},
        ),
    )
    params = {
        "name": "logs",
        "compartment_id": "compartment",
        "public_access_type": "ObjectReadWithoutList",
        "versioning": "Enabled",
        "metadata": {},
        "object_events_enabled": False,
        "auto_tiering": "InfrequentAccess",
        "freeform_tags": {"phase": "update"},
    }

    check_result = run_bucket(module_obj, monkeypatch, client, params, True)
    assert check_result == {"changed": True}
    assert client.bucket.versioning == "Disabled"
    assert client.bucket.freeform_tags == {"phase": "create"}
    assert client.bucket.metadata == {"old": "value"}
    assert client.updated == 0

    updated = run_bucket(module_obj, monkeypatch, client, params)
    rerun = run_bucket(module_obj, monkeypatch, client, params)
    assert updated["changed"] is True
    assert updated["resource"]["public_access_type"] == "ObjectReadWithoutList"
    assert updated["resource"]["versioning"] == "Enabled"
    assert updated["resource"]["freeform_tags"] == {"phase": "update"}
    assert updated["resource"]["metadata"] == {}
    assert updated["resource"]["object_events_enabled"] is False
    assert updated["resource"]["auto_tiering"] == "InfrequentAccess"
    assert rerun["changed"] is False
    assert client.updated == 1


def test_delete_check_mode_and_rerun_are_idempotent(monkeypatch):
    module_obj, service_error = load_bucket(monkeypatch)
    client = BucketClient(
        service_error,
        bucket=FakeModel(name="logs", compartment_id="compartment"),
    )
    params = {"state": "absent", "name": "logs", "namespace_name": "testns"}

    check_result = run_bucket(module_obj, monkeypatch, client, params, True)
    assert check_result == {"changed": True}
    assert client.bucket is not None
    assert client.deleted == 0

    deleted = run_bucket(module_obj, monkeypatch, client, params)
    rerun = run_bucket(module_obj, monkeypatch, client, params)
    assert deleted == {"changed": True}
    assert rerun == {"changed": False}
    assert client.deleted == 1
    assert client.namespace_requests == []


def test_force_deletes_all_blockers_and_is_idempotent(monkeypatch):
    module_obj, service_error = load_bucket(monkeypatch)
    client = ForceBucketClient(
        service_error,
        versioning="Enabled",
        read_only=True,
        versions=[
            FakeModel(name="record", version_id=f"v{n}", is_delete_marker=n == 2)
            for n in range(4)
        ],
        uploads=[FakeModel(object=f"pending-{n}", upload_id=f"u{n}") for n in range(3)],
        requests=[FakeModel(id=f"par-{n}") for n in range(3)],
        policies=[FakeModel(id="replication")],
        retention_rules=[FakeModel(id="retention", time_rule_locked=None)],
    )
    params = {
        "state": "absent",
        "name": "logs",
        "namespace_name": "testns",
        "force": True,
    }

    check_result = run_bucket(module_obj, monkeypatch, client, params, True)
    assert check_result == {"changed": True}
    assert client.calls == []

    deleted = run_bucket(module_obj, monkeypatch, client, params)
    rerun = run_bucket(module_obj, monkeypatch, client, params)

    assert deleted == {"changed": True}
    assert rerun == {"changed": False}
    assert client.calls[0] == "make_bucket_writable"
    assert ("delete_replication_policy", "replication") in client.calls
    assert ("delete_retention_rule", "retention") in client.calls
    assert {call[2] for call in client.calls if call[0] == "delete_object"} == {
        "v0",
        "v1",
        "v2",
        "v3",
    }
    assert client.calls[-1] == "delete_bucket"


def test_force_deletes_all_pages_of_unversioned_objects(monkeypatch):
    module_obj, service_error = load_bucket(monkeypatch)
    client = ForceBucketClient(
        service_error,
        objects=[FakeModel(name=f"object-{n}") for n in range(5)],
    )
    result = run_bucket(
        module_obj,
        monkeypatch,
        client,
        {"state": "absent", "name": "logs", "namespace_name": "testns", "force": True},
    )
    assert result == {"changed": True}
    assert len([call for call in client.calls if call[0] == "delete_object"]) == 5
    assert client.bucket is None


def test_nonempty_bucket_requires_force(monkeypatch):
    module_obj, service_error = load_bucket(monkeypatch)
    client = ForceBucketClient(service_error, objects=[FakeModel(name="object")])
    with pytest.raises(FailJsonCalled) as result:
        run_bucket(
            module_obj,
            monkeypatch,
            client,
            {"state": "absent", "name": "logs", "namespace_name": "testns"},
        )
    assert "delete_bucket" in result.value.payload["msg"]
    assert client.objects[0].name == "object"


@pytest.mark.parametrize("naive_lock_time", [False, True])
def test_force_reports_partial_cleanup_when_retention_blocks_objects(
    monkeypatch, naive_lock_time
):
    module_obj, service_error = load_bucket(monkeypatch)
    locked_at = datetime.now(timezone.utc) - timedelta(days=1)
    if naive_lock_time:
        locked_at = locked_at.replace(tzinfo=None)
    client = ForceBucketClient(
        service_error,
        objects=[FakeModel(name="protected")],
        requests=[FakeModel(id="par")],
        retention_rules=[
            FakeModel(
                id="locked",
                time_rule_locked=locked_at,
            )
        ],
    )
    with pytest.raises(FailJsonCalled) as result:
        run_bucket(
            module_obj,
            monkeypatch,
            client,
            {
                "state": "absent",
                "name": "logs",
                "namespace_name": "testns",
                "force": True,
            },
        )
    assert result.value.payload["changed"] is True
    assert "delete_object" in result.value.payload["msg"]
    assert client.requests == []
    assert client.bucket is not None


@pytest.mark.parametrize(
    "records", ["uploads", "versions", "objects", "policies", "retention_rules", "requests"]
)
def test_force_deletes_more_than_1000_listing_pages(monkeypatch, records):
    module_obj, service_error = load_bucket(monkeypatch)
    entries = [
        FakeModel(
            name=f"record-{n}", version_id=f"v{n}", object=f"record-{n}",
            upload_id=f"u{n}", id=f"id-{n}", time_rule_locked=None,
        )
        for n in range(1001)
    ]
    client = ForceBucketClient(
        service_error,
        versioning="Enabled" if records == "versions" else "Disabled",
        page_size=1,
        **{records: entries},
    )

    result = run_bucket(
        module_obj, monkeypatch, client,
        {"state": "absent", "name": "logs", "namespace_name": "testns", "force": True},
    )

    assert result == {"changed": True}
    assert getattr(client, records) == []
    assert len([call for call in client.listing_calls if call[0] == records]) == 1001
    assert client.bucket is None


@pytest.mark.parametrize(
    ("records", "list_method", "delete_method"),
    [
        ("uploads", "list_multipart_uploads", "abort_multipart_upload"),
        ("versions", "list_object_versions", "delete_object"),
        ("objects", "list_objects", "delete_object"),
    ],
)
def test_force_deletes_listed_entries_once_when_they_remain_visible(
    monkeypatch, records, list_method, delete_method
):
    module_obj, service_error = load_bucket(monkeypatch)
    client = ForceBucketClient(
        service_error,
        versioning="Enabled" if records == "versions" else "Disabled",
        **{
            records: [FakeModel(name="record", version_id="v1", object="record", upload_id="u1")]
        },
    )
    original_list = getattr(client, list_method)
    listing_calls = []
    deletion_calls = []

    def list_records(**kwargs):
        listing_calls.append(kwargs)
        assert len(listing_calls) == 1, "Cleanup relisted a completed deletion queue"
        return original_list(**kwargs)

    def keep_record(**kwargs):
        deletion_calls.append(kwargs)
        return FakeResponse()

    list_records.__name__ = list_method
    monkeypatch.setattr(client, list_method, list_records)
    monkeypatch.setattr(client, delete_method, keep_record)
    with pytest.raises(FailJsonCalled) as result:
        run_bucket(
            module_obj, monkeypatch, client,
            {"state": "absent", "name": "logs", "namespace_name": "testns", "force": True},
        )

    assert result.value.payload["changed"] is True
    assert "delete_bucket" in result.value.payload["msg"]
    assert len(deletion_calls) == 1
    assert client.deleted == 0


@pytest.mark.parametrize("parameter", ["page", "start"])
@pytest.mark.parametrize("tokens", [("same", "same"), ("first", "second", "first")])
@pytest.mark.parametrize("read_only", [False, True])
def test_force_rejects_pagination_cycles(monkeypatch, parameter, tokens, read_only):
    module_obj, service_error = load_bucket(monkeypatch)
    client = ForceBucketClient(service_error, read_only=read_only)
    requested = []

    def list_records(**kwargs):
        requested.append(kwargs.get(parameter))
        assert len(requested) <= len(tokens), "Cleanup followed a cyclic pagination marker"
        token = tokens[len(requested) - 1]
        if parameter == "start":
            return FakeResponse(FakeModel(objects=[FakeModel(name="record")], next_start_with=token))
        return FakeResponse([FakeModel(id="par")], {"opc-next-page": token})

    method_name = "list_objects" if parameter == "start" else "list_preauthenticated_requests"
    list_records.__name__ = method_name
    monkeypatch.setattr(client, method_name, list_records)
    with pytest.raises(FailJsonCalled) as result:
        run_bucket(
            module_obj, monkeypatch, client,
            {"state": "absent", "name": "logs", "namespace_name": "testns", "force": True},
        )

    assert result.value.payload["changed"] is read_only
    assert "logs" in result.value.payload["msg"]
    assert method_name in result.value.payload["msg"]
    assert "repeated pagination marker" in result.value.payload["msg"]
    assert requested == [None, *tokens[:-1]]
    assert client.calls == (["make_bucket_writable"] if read_only else [])
    assert client.deleted == 0


def test_force_collects_all_pages_before_deleting(monkeypatch):
    module_obj, service_error = load_bucket(monkeypatch)
    client = ForceBucketClient(
        service_error, objects=[FakeModel(name=f"record-{n}") for n in range(5)],
    )
    original_delete = client.delete_object

    def delete_object(**kwargs):
        assert [call for call in client.listing_calls if call[0] == "objects"] == [
            ("objects", None), ("objects", "2"), ("objects", "4"),
        ]
        return original_delete(**kwargs)

    monkeypatch.setattr(client, "delete_object", delete_object)
    result = run_bucket(
        module_obj, monkeypatch, client,
        {"state": "absent", "name": "logs", "namespace_name": "testns", "force": True},
    )

    assert result == {"changed": True}
    assert {call[1] for call in client.calls if call[0] == "delete_object"} == {
        "record-0", "record-1", "record-2", "record-3", "record-4",
    }


def test_force_leaves_concurrently_added_objects_for_bucket_delete_to_reject(monkeypatch):
    module_obj, service_error = load_bucket(monkeypatch)
    client = ForceBucketClient(service_error, objects=[FakeModel(name="old")])
    original_delete = client.delete_object

    def delete_object(**kwargs):
        response = original_delete(**kwargs)
        if kwargs["object_name"] == "old":
            with client.lock:
                client.objects.append(FakeModel(name="new"))
        return response

    monkeypatch.setattr(client, "delete_object", delete_object)
    with pytest.raises(FailJsonCalled) as result:
        run_bucket(
            module_obj, monkeypatch, client,
            {"state": "absent", "name": "logs", "namespace_name": "testns", "force": True},
        )

    assert result.value.payload["changed"] is True
    assert "delete_bucket" in result.value.payload["msg"]
    assert client.calls == [("delete_object", "old", None)]
    assert [obj.name for obj in client.objects] == ["new"]


@pytest.mark.parametrize("successful_deletion", [False, True])
def test_force_reports_worker_failure_on_main_thread_after_queue_finishes(
    monkeypatch, successful_deletion
):
    module_obj, service_error = load_bucket(monkeypatch)
    client = ForceBucketClient(
        service_error, requests=[FakeModel(id="bad"), FakeModel(id="good")],
        objects=[FakeModel(name="later-stage")],
    )
    barrier = Barrier(2, timeout=5)
    failed = Event()
    completed = []
    original_delete = client.delete_preauthenticated_request

    def delete_preauthenticated_request(par_id, **kwargs):
        barrier.wait()
        if par_id == "bad":
            with client.lock:
                completed.append(par_id)
            failed.set()
            raise service_error(403, "deletion forbidden")
        assert failed.wait(5)
        if successful_deletion:
            response = original_delete(par_id=par_id, **kwargs)
        else:
            response = None
        with client.lock:
            completed.append(par_id)
        if not successful_deletion:
            raise service_error(403, "deletion forbidden")
        return response

    monkeypatch.setattr(client, "delete_preauthenticated_request", delete_preauthenticated_request)
    instance = make_module_instance(
        module_obj, "OciObjectStorageBucketModule",
        {"state": "absent", "name": "logs", "namespace_name": "testns", "force": True},
        client=client,
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, *args, **kwargs: fn(*args, **kwargs))
    original_fail = instance.module.fail_json
    main_thread = get_ident()

    def fail_json(**kwargs):
        assert get_ident() == main_thread, "A worker attempted to write the Ansible failure"
        assert sorted(completed) == ["bad", "good"]
        original_fail(**kwargs)

    monkeypatch.setattr(instance.module, "fail_json", fail_json)
    with pytest.raises(FailJsonCalled) as result:
        instance.execute_resource_module()

    assert result.value.payload["changed"] is successful_deletion
    assert "delete_preauthenticated_request" in result.value.payload["msg"]
    assert "deletion forbidden" in result.value.payload["msg"]
    assert [obj.name for obj in client.objects] == ["later-stage"]
    assert not any(call[0] == "uploads" for call in client.listing_calls)
    assert client.deleted == 0


def test_force_deletes_suspended_versions_and_unversioned_objects(monkeypatch):
    module_obj, service_error = load_bucket(monkeypatch)
    client = ForceBucketClient(
        service_error,
        versioning="Suspended",
        versions=[FakeModel(name="old", version_id="v1"), FakeModel(name="legacy", version_id=None)],
        objects=[FakeModel(name="legacy"), FakeModel(name="current")],
    )

    result = run_bucket(
        module_obj,
        monkeypatch,
        client,
        {"state": "absent", "name": "logs", "namespace_name": "testns", "force": True},
    )

    assert result == {"changed": True}
    assert ("delete_object", "old", "v1") in client.calls
    assert ("delete_object", "legacy", None) in client.calls
    assert ("delete_object", "current", None) in client.calls
    assert client.bucket is None


def test_force_rejects_missing_version_id_when_versioning_is_enabled(monkeypatch):
    module_obj, service_error = load_bucket(monkeypatch)
    client = ForceBucketClient(
        service_error,
        versioning="Enabled",
        versions=[FakeModel(name="record", version_id=None)],
    )

    with pytest.raises(FailJsonCalled) as result:
        run_bucket(
            module_obj,
            monkeypatch,
            client,
            {"state": "absent", "name": "logs", "namespace_name": "testns", "force": True},
        )

    assert result.value.payload["changed"] is False
    assert "no version ID" in result.value.payload["msg"]
    assert client.calls == []
    assert client.bucket is not None


@pytest.mark.parametrize("naive_lock_time", [False, True])
def test_force_deletes_retention_rule_before_its_lock_time(monkeypatch, naive_lock_time):
    module_obj, service_error = load_bucket(monkeypatch)
    locked_at = datetime.now(timezone.utc) + timedelta(days=1)
    if naive_lock_time:
        locked_at = locked_at.replace(tzinfo=None)
    client = ForceBucketClient(
        service_error,
        retention_rules=[FakeModel(id="unlocked", time_rule_locked=locked_at)],
        objects=[FakeModel(name="record")],
    )

    result = run_bucket(
        module_obj,
        monkeypatch,
        client,
        {"state": "absent", "name": "logs", "namespace_name": "testns", "force": True},
    )

    assert result == {"changed": True}
    assert client.calls == [
        ("delete_retention_rule", "unlocked"),
        ("delete_object", "record", None),
        "delete_bucket",
    ]


@pytest.mark.parametrize(
    ("current", "desired", "field"),
    [
        ({"compartment_id": "first"}, {"compartment_id": "second"}, "compartment_id"),
        ({"storage_tier": "Standard"}, {"storage_tier": "Archive"}, "storage_tier"),
        ({"versioning": "Enabled"}, {"versioning": "Disabled"}, "versioning"),
    ],
)
def test_rejects_unsupported_existing_bucket_changes(
    monkeypatch, current, desired, field
):
    module_obj, service_error = load_bucket(monkeypatch)
    current_bucket = {
        "name": "logs",
        "compartment_id": "first",
        "storage_tier": "Standard",
        "versioning": "Disabled",
    }
    current_bucket.update(current)
    client = BucketClient(service_error, FakeModel(**current_bucket))
    with pytest.raises(FailJsonCalled) as result:
        run_bucket(
            module_obj,
            monkeypatch,
            client,
            {"name": "logs", "namespace_name": "testns", **desired},
            check_mode=True,
        )
    assert field in result.value.payload["msg"]
    assert client.updated == 0


def test_create_requires_compartment_and_rejects_suspended_versioning(monkeypatch):
    module_obj, service_error = load_bucket(monkeypatch)
    client = BucketClient(service_error)
    for params, expected in (
        ({"name": "logs"}, "compartment_id"),
        (
            {
                "name": "logs",
                "compartment_id": "compartment",
                "versioning": "Suspended",
            },
            "versioning",
        ),
    ):
        with pytest.raises(FailJsonCalled) as result:
            run_bucket(module_obj, monkeypatch, client, params, check_mode=True)
        assert expected in result.value.payload["msg"]
    assert client.created == 0


def test_empty_kms_key_is_rejected(monkeypatch):
    module_obj, service_error = load_bucket(monkeypatch)
    client = BucketClient(service_error)
    with pytest.raises(FailJsonCalled) as result:
        run_bucket(
            module_obj,
            monkeypatch,
            client,
            {"name": "logs", "compartment_id": "compartment", "kms_key_id": ""},
            check_mode=True,
        )
    assert "kms_key_id" in result.value.payload["msg"]
