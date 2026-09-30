from __future__ import absolute_import, division, print_function

import base64
import gzip
import hashlib
import os
import sys
import types

import pytest

from .conftest import (
    ExitJsonCalled,
    FakeResponse,
    FailJsonCalled,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
)


def encoded_md5(content):
    return base64.b64encode(hashlib.md5(content).digest()).decode("ascii")


class ObjectClient:
    def __init__(self, service_error, exists=False, body=b"payload", headers=None):
        self.service_error = service_error
        self.exists = exists
        self.body = body
        self.headers = headers
        self.puts = []
        self.deletes = []
        self.gets = []
        self.heads = []
        self.objects = None
        self.versions = []

    def get_namespace(self, **kwargs):
        return FakeResponse("testns")

    def head_object(self, **kwargs):
        self.heads.append(kwargs)
        if not self.exists:
            raise self.service_error(404)
        return FakeResponse(
            None,
            self.headers if self.headers is not None else {
                "content-length": str(len(self.body)),
                "content-md5": encoded_md5(self.body),
                "etag": "etag",
            },
        )

    def put_object(self, **kwargs):
        self.puts.append(kwargs)
        self.exists = True
        return FakeResponse(None, {"etag": "new-etag"})

    def get_object(self, **kwargs):
        self.gets.append(kwargs)

        class Raw:
            def __init__(self, body):
                self.body = body

            def stream(self, chunk_size, decode_content=True):
                yield self.body

        class Body:
            def __init__(self, body):
                self.raw = Raw(body)
                self.closed = False

            def close(self):
                self.closed = True

        headers = self.headers if self.headers is not None else {"content-length": str(len(self.body))}
        return FakeResponse(Body(self.body), headers)

    def delete_object(self, **kwargs):
        self.deletes.append(kwargs)
        self.exists = False
        self.versions = [
            version
            for version in self.versions
            if version.version_id != kwargs.get("version_id")
        ]
        return FakeResponse()

    def list_objects(self, **kwargs):
        objects = self.objects
        if objects is None:
            fields = kwargs.get("fields", "name").split(",")
            objects = (
                [
                    types.SimpleNamespace(
                        name="object",
                        etag="etag" if "etag" in fields else None,
                        md5=encoded_md5(self.body) if "md5" in fields else None,
                    )
                ]
                if self.exists
                else []
            )
        return FakeResponse(types.SimpleNamespace(objects=objects))

    def list_object_versions(self, **kwargs):
        return FakeResponse(types.SimpleNamespace(items=self.versions))


class FakeUploadManager:
    def __init__(self, client, **kwargs):
        self.client = client

    def upload_file(self, file_path, **kwargs):
        if "metadata" in kwargs:
            kwargs["opc_meta"] = kwargs.pop("metadata")
        with open(file_path, "rb") as body:
            return self.client.put_object(put_object_body=body, **kwargs)


class FakeMultipartObjectAssembler:
    @staticmethod
    def calculate_md5(file_path, offset, chunk):
        with open(file_path, "rb") as source:
            source.seek(offset)
            return encoded_md5(source.read(chunk))


class FakeDownloadManager:
    def __init__(self, config, client):
        self.client = client

    def get_object_to_path(self, destination_path, **kwargs):
        response = self.client.get_object(**kwargs)
        size = 0
        try:
            with open(destination_path, "wb") as output:
                for chunk in response.data.raw.stream(
                    1024 * 1024,
                    decode_content=kwargs.get("http_response_content_encoding") != "identity",
                ):
                    output.write(chunk)
                    size += len(chunk)
        finally:
            response.data.close()
            response.data = None
        return size, response


def load_object(monkeypatch):
    fake_oci, service_error = install_fake_oci(monkeypatch)
    fake_oci.util = types.SimpleNamespace(
        to_dict=lambda resource: resource if isinstance(resource, dict) else vars(resource)
    )
    fake_oci.object_storage = types.SimpleNamespace(
        ObjectStorageClient=type("ObjectStorageClient", (), {}),
        UploadManager=FakeUploadManager,
        MultipartObjectAssembler=FakeMultipartObjectAssembler,
        DownloadManager=types.SimpleNamespace(DownloadManager=FakeDownloadManager),
    )
    config_module_name = "oci.object_storage.transfer.internal.download.DownloadConfiguration"
    config_module = types.ModuleType(config_module_name)
    config_module.DownloadConfiguration = types.SimpleNamespace
    monkeypatch.setitem(sys.modules, config_module_name, config_module)
    return load_collection_module("oci_object_storage_object"), service_error


def run(module_obj, monkeypatch, client, params, check_mode=False):
    instance = make_module_instance(
        module_obj,
        "OciObjectStorageObjectModule",
        params,
        client=client,
        check_mode=check_mode,
    )

    def list_resources(fn, *args, **kwargs):
        data = fn(*args, **kwargs).data
        return data.items if fn.__name__ == "list_object_versions" else data

    monkeypatch.setattr(instance, "list_all_resources", list_resources)
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    return result.value.payload


def base_params(**kwargs):
    params = {
        "bucket_name": "bucket",
        "object_name": "object",
        "namespace_name": "testns",
        "state": "present",
        "force": False,
    }
    params.update(kwargs)
    return params


def test_upload_check_mode_and_idempotency(monkeypatch, tmp_path):
    module_obj, service_error = load_object(monkeypatch)
    source = tmp_path / "source"
    source.write_bytes(b"hello")
    client = ObjectClient(service_error)
    checked = run(module_obj, monkeypatch, client, base_params(src=str(source)), check_mode=True)
    assert checked["changed"] is True
    assert not client.puts
    client.exists = True
    unchanged = run(module_obj, monkeypatch, client, base_params(src=str(source)))
    assert unchanged["changed"] is False
    assert not client.puts


def test_upload_creates_object_normally(monkeypatch, tmp_path):
    module_obj, service_error = load_object(monkeypatch)
    source = tmp_path / "source"
    source.write_bytes(b"hello")
    client = ObjectClient(service_error)
    result = run(module_obj, monkeypatch, client, base_params(src=str(source)))
    assert result["changed"] is True
    assert client.exists


def test_force_upload_overwrites_existing_object(monkeypatch, tmp_path):
    module_obj, service_error = load_object(monkeypatch)
    source = tmp_path / "source"
    source.write_bytes(b"hello")
    client = ObjectClient(service_error, exists=True)
    result = run(module_obj, monkeypatch, client, base_params(src=str(source), force=True))
    assert result["changed"] is True
    assert client.puts[0]["content_type"] == "application/octet-stream"


@pytest.mark.parametrize("check_mode", [False, True])
def test_force_upload_skips_matching_content(monkeypatch, tmp_path, check_mode):
    module_obj, service_error = load_object(monkeypatch)
    source = tmp_path / "source"
    source.write_bytes(b"matching content")
    client = ObjectClient(service_error, exists=True, body=source.read_bytes())

    result = run(
        module_obj,
        monkeypatch,
        client,
        base_params(src=str(source), force=True),
        check_mode=check_mode,
    )

    assert result["changed"] is False
    assert not client.puts


def test_empty_content_type_uses_upload_default(monkeypatch, tmp_path):
    module_obj, service_error = load_object(monkeypatch)
    source = tmp_path / "source"
    source.write_bytes(b"hello")
    client = ObjectClient(service_error)

    run(module_obj, monkeypatch, client, base_params(src=str(source), content_type=""))

    assert client.puts[0]["content_type"] == "application/octet-stream"


def test_upload_forwards_object_headers_and_encryption_options(monkeypatch, tmp_path):
    module_obj, service_error = load_object(monkeypatch)
    source = tmp_path / "source"
    source.write_bytes(b"hello")
    client = ObjectClient(service_error)
    options = {
        "content_md5": "XUFAKrxLKna5cZ2REBfFkg==",
        "content_language": "en",
        "content_encoding": "gzip",
        "content_disposition": "attachment",
        "cache_control": "no-cache",
        "storage_tier": "infrequent_access",
        "opc_meta": {"owner": "ansible"},
        "opc_sse_kms_key_id": "ocid1.key.oc1..example",
    }

    run(module_obj, monkeypatch, client, base_params(src=str(source), **options))

    expected = dict(options, storage_tier="InfrequentAccess")
    assert {name: client.puts[0].get(name) for name in options} == expected


@pytest.mark.parametrize("value,oci_value", [
    ("standard", "Standard"),
    ("infrequent_access", "InfrequentAccess"),
    ("archive", "Archive"),
])
def test_upload_maps_lowercase_storage_tier_to_oci_value(monkeypatch, tmp_path, value, oci_value):
    module_obj, service_error = load_object(monkeypatch)
    source = tmp_path / "source"
    source.write_bytes(b"hello")
    client = ObjectClient(service_error)

    run(module_obj, monkeypatch, client, base_params(src=str(source), storage_tier=value))

    assert client.puts[0]["storage_tier"] == oci_value


def test_upload_forwards_complete_customer_encryption_triplet(monkeypatch, tmp_path):
    module_obj, service_error = load_object(monkeypatch)
    source = tmp_path / "source"
    source.write_bytes(b"hello")
    client = ObjectClient(service_error)
    encryption = {
        "opc_sse_customer_algorithm": "aes256",
        "opc_sse_customer_key": "secret-key",
        "opc_sse_customer_key_sha256": "secret-key-hash",
    }

    run(module_obj, monkeypatch, client, base_params(src=str(source), **encryption))

    expected = dict(encryption, opc_sse_customer_algorithm="AES256")
    assert {name: client.puts[0].get(name) for name in encryption} == expected


def test_download_forwards_version_and_customer_encryption(monkeypatch, tmp_path):
    module_obj, service_error = load_object(monkeypatch)
    client = ObjectClient(service_error, exists=True)
    options = {
        "version_id": "version-1",
        "opc_sse_customer_algorithm": "aes256",
        "opc_sse_customer_key": "secret-key",
        "opc_sse_customer_key_sha256": "secret-key-hash",
    }

    run(
        module_obj,
        monkeypatch,
        client,
        base_params(dest=str(tmp_path / "download"), **options),
    )

    expected = dict(options, opc_sse_customer_algorithm="AES256")
    assert {name: client.heads[0].get(name) for name in options} == expected
    assert {name: client.gets[0].get(name) for name in options} == expected


def test_upload_does_not_overwrite_object_created_after_head(monkeypatch, tmp_path):
    module_obj, service_error = load_object(monkeypatch)
    source = tmp_path / "source"
    source.write_bytes(b"ours")
    client = ObjectClient(service_error)

    def concurrent_put(**kwargs):
        client.exists = True
        client.body = b"concurrent"
        if kwargs.get("if_none_match") == "*":
            raise service_error(412)
        client.body = kwargs["put_object_body"].read()
        return FakeResponse(None, {"etag": "ours"})

    client.put_object = concurrent_put
    result = run(module_obj, monkeypatch, client, base_params(src=str(source)))
    assert result["changed"] is False
    assert client.body == b"concurrent"


def test_download_is_atomic_and_check_mode_does_not_write(monkeypatch, tmp_path):
    module_obj, service_error = load_object(monkeypatch)
    destination = tmp_path / "download"
    client = ObjectClient(service_error, exists=True)
    checked = run(
        module_obj,
        monkeypatch,
        client,
        base_params(dest=str(destination)),
        check_mode=True,
    )
    assert checked["changed"] is True
    assert not destination.exists()

    result = run(module_obj, monkeypatch, client, base_params(dest=str(destination)))
    assert result["changed"] is True
    assert destination.read_bytes() == b"payload"
    rerun = run(module_obj, monkeypatch, client, base_params(dest=str(destination)))
    assert rerun["changed"] is False


def test_force_download_overwrites_existing_file(monkeypatch, tmp_path):
    module_obj, service_error = load_object(monkeypatch)
    destination = tmp_path / "download"
    destination.write_bytes(b"old")
    client = ObjectClient(service_error, exists=True)
    result = run(
        module_obj, monkeypatch, client, base_params(dest=str(destination), force=True)
    )
    assert result["changed"] is True
    assert destination.read_bytes() == b"payload"


@pytest.mark.parametrize("check_mode", [False, True])
def test_force_download_skips_matching_content(monkeypatch, tmp_path, check_mode):
    module_obj, service_error = load_object(monkeypatch)
    destination = tmp_path / "download"
    destination.write_bytes(b"matching content")
    client = ObjectClient(service_error, exists=True, body=destination.read_bytes())

    result = run(
        module_obj,
        monkeypatch,
        client,
        base_params(dest=str(destination), force=True),
        check_mode=check_mode,
    )

    assert result["changed"] is False
    assert destination.read_bytes() == b"matching content"
    assert not client.gets


@pytest.mark.parametrize("parts", [
    [b"multipart", b" object contents"],
    [b"m", b"ultipart object", b" contents"],
])
@pytest.mark.parametrize("destination_state", ["missing", "matching", "different"])
def test_force_multipart_download_is_idempotent(monkeypatch, tmp_path, parts, destination_state):
    module_obj, service_error = load_object(monkeypatch)
    content = b"".join(parts)
    part_hashes = b"".join(hashlib.md5(part).digest() for part in parts)
    headers = {
        "content-length": str(len(content)),
        "opc-multipart-md5": encoded_md5(part_hashes) + f"-{len(parts)}",
    }
    assert headers["opc-multipart-md5"] != encoded_md5(content)
    client = ObjectClient(service_error, exists=True, body=content, headers=headers)
    destination = tmp_path / "download"
    if destination_state != "missing":
        destination.write_bytes(content if destination_state == "matching" else b"x" * len(content))

    before = destination.stat() if destination.exists() else None
    checked = run(
        module_obj, monkeypatch, client,
        base_params(dest=str(destination), force=True), check_mode=True,
    )

    # Multipart headers alone cannot prove equality, and check mode must not fetch the content.
    assert checked["changed"] is True
    assert not client.gets
    assert destination.exists() is (destination_state != "missing")

    result = run(module_obj, monkeypatch, client, base_params(dest=str(destination), force=True))

    assert result["changed"] is (destination_state != "matching")
    assert destination.read_bytes() == content
    if destination_state == "matching":
        assert destination.stat().st_ino == before.st_ino
        assert destination.stat().st_mtime_ns == before.st_mtime_ns

    after = destination.stat()
    rerun = run(module_obj, monkeypatch, client, base_params(dest=str(destination), force=True))

    assert rerun["changed"] is False
    assert destination.stat().st_ino == after.st_ino
    assert destination.stat().st_mtime_ns == after.st_mtime_ns
    assert len(client.gets) == 2
    assert not list(tmp_path.glob(".ansible-oci-*"))


def test_force_download_preserves_existing_file_mode(monkeypatch, tmp_path):
    module_obj, service_error = load_object(monkeypatch)
    destination = tmp_path / "download"
    destination.write_bytes(b"old")
    destination.chmod(0o644)
    client = ObjectClient(service_error, exists=True)

    run(module_obj, monkeypatch, client, base_params(dest=str(destination), force=True))

    assert os.stat(destination).st_mode & 0o777 == 0o644


def test_download_creates_missing_parent(monkeypatch, tmp_path):
    module_obj, service_error = load_object(monkeypatch)
    destination = tmp_path / "nested" / "download"
    client = ObjectClient(service_error, exists=True)
    result = run(module_obj, monkeypatch, client, base_params(dest=str(destination)))
    assert result["changed"] is True
    assert destination.read_bytes() == b"payload"


def test_download_rejects_directory_destination(monkeypatch, tmp_path):
    module_obj, service_error = load_object(monkeypatch)
    destination = tmp_path / "directory"
    destination.mkdir()
    client = ObjectClient(service_error, exists=True)
    instance = make_module_instance(
        module_obj,
        "OciObjectStorageObjectModule",
        base_params(dest=str(destination)),
        client=client,
    )
    with pytest.raises(FailJsonCalled):
        instance.execute_resource_module()


def test_download_does_not_replace_file_created_during_stream(monkeypatch, tmp_path):
    module_obj, service_error = load_object(monkeypatch)
    destination = tmp_path / "download"
    client = ObjectClient(service_error, exists=True)
    original_link = module_obj.os.link

    def competing_link(source, target):
        destination.write_bytes(b"concurrent")
        return original_link(source, target)

    monkeypatch.setattr(module_obj.os, "link", competing_link)
    result = run(module_obj, monkeypatch, client, base_params(dest=str(destination)))
    assert result["changed"] is False
    assert destination.read_bytes() == b"concurrent"
    assert not list(tmp_path.glob(".ansible-oci-*"))


def test_download_does_not_fetch_object_when_temporary_file_creation_fails(monkeypatch, tmp_path):
    module_obj, service_error = load_object(monkeypatch)
    client = ObjectClient(service_error, exists=True)

    def fail_temporary_file(**kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(module_obj.tempfile, "NamedTemporaryFile", fail_temporary_file)
    instance = make_module_instance(
        module_obj,
        "OciObjectStorageObjectModule",
        base_params(dest=str(tmp_path / "download")),
        client=client,
    )
    with pytest.raises(FailJsonCalled):
        instance.execute_resource_module()
    assert not client.gets


def test_download_closes_response_when_temporary_cleanup_fails(monkeypatch, tmp_path):
    module_obj, service_error = load_object(monkeypatch)
    client = ObjectClient(service_error, exists=True)
    body = types.SimpleNamespace(
        closed=False,
        raw=types.SimpleNamespace(
            stream=lambda *args, **kwargs: iter([b"payload"])
        ),
    )

    def close_body():
        body.closed = True

    body.close = close_body
    client.get_object = lambda **kwargs: FakeResponse(body)
    original_unlink = module_obj.os.unlink

    def fail_temporary_unlink(path, *args, **kwargs):
        if os.path.basename(path).startswith(".ansible-oci-"):
            raise OSError("temporary cleanup failed")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(module_obj.os, "unlink", fail_temporary_unlink)
    with pytest.raises(OSError, match="temporary cleanup failed"):
        run(module_obj, monkeypatch, client, base_params(dest=str(tmp_path / "download")))
    assert body.closed


def test_download_stream_failure_removes_temporary_file(monkeypatch, tmp_path):
    module_obj, service_error = load_object(monkeypatch)
    destination = tmp_path / "nested" / "download"
    destination.parent.mkdir()
    client = ObjectClient(service_error, exists=True)

    class FailingRaw:
        def stream(self, *args, **kwargs):
            yield b"partial"
            raise RuntimeError("stream failed")

    class FailingBody:
        raw = FailingRaw()

        def close(self):
            pass

    client.get_object = lambda **kwargs: FakeResponse(FailingBody())
    instance = make_module_instance(
        module_obj,
        "OciObjectStorageObjectModule",
        base_params(dest=str(destination)),
        client=client,
    )
    with pytest.raises(RuntimeError):
        instance.execute_resource_module()
    assert not destination.exists()
    assert not list(destination.parent.glob(".ansible-oci-*"))


def test_download_preserves_encoded_object_bytes(monkeypatch, tmp_path):
    module_obj, service_error = load_object(monkeypatch)
    destination = tmp_path / "download"
    stored = gzip.compress(b"original compressed object bytes")
    client = ObjectClient(service_error, exists=True, body=stored)

    class EncodedRaw:
        def stream(self, chunk_size, decode_content=True):
            assert decode_content is False
            yield stored

    class EncodedBody:
        raw = EncodedRaw()

        def close(self):
            pass

    client.get_object = lambda **kwargs: FakeResponse(EncodedBody())
    run(module_obj, monkeypatch, client, base_params(dest=str(destination)))
    assert destination.read_bytes() == stored


def test_namespace_is_resolved_when_omitted(monkeypatch, tmp_path):
    module_obj, service_error = load_object(monkeypatch)
    source = tmp_path / "source"
    source.write_bytes(b"hello")
    client = ObjectClient(service_error)
    result = run(
        module_obj, monkeypatch, client, base_params(namespace_name=None, src=str(source))
    )
    assert result["changed"] is True


def test_download_missing_object_fails_even_in_check_mode(monkeypatch, tmp_path):
    module_obj, service_error = load_object(monkeypatch)
    client = ObjectClient(service_error)
    instance = make_module_instance(
        module_obj,
        "OciObjectStorageObjectModule",
        base_params(dest=str(tmp_path / "download")),
        client=client,
        check_mode=True,
    )
    with pytest.raises(FailJsonCalled):
        instance.execute_resource_module()


def test_existing_destination_is_unchanged_when_remote_object_is_missing(monkeypatch, tmp_path):
    module_obj, service_error = load_object(monkeypatch)
    destination = tmp_path / "download"
    destination.write_bytes(b"existing")
    client = ObjectClient(service_error)
    result = run(module_obj, monkeypatch, client, base_params(dest=str(destination)))
    assert result["changed"] is False


def test_existing_destination_needs_no_customer_key_when_not_forced(monkeypatch, tmp_path):
    module_obj, service_error = load_object(monkeypatch)
    destination = tmp_path / "download"
    destination.write_bytes(b"existing")
    client = ObjectClient(service_error, exists=True)

    def reject_head(**kwargs):
        raise service_error(400, "customer key required")

    client.head_object = reject_head

    result = run(module_obj, monkeypatch, client, base_params(dest=str(destination)))

    assert result == {"changed": False, "resource": {}}
    assert destination.read_bytes() == b"existing"


def test_large_upload_check_mode_defers_size_handling_to_sdk(monkeypatch, tmp_path):
    module_obj, service_error = load_object(monkeypatch)
    source = tmp_path / "source"
    source.write_bytes(b"hello")
    monkeypatch.setattr(
        module_obj.os.path,
        "getsize",
        lambda path: 50 * 1024 * 1024 * 1024 + 1,
    )
    instance = make_module_instance(
        module_obj,
        "OciObjectStorageObjectModule",
        base_params(src=str(source)),
        client=ObjectClient(service_error),
        check_mode=True,
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda fn, *args, **kwargs: fn(*args, **kwargs).data,
    )

    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()

    assert result.value.payload["changed"] is True
    assert not instance.client.puts


def test_delete_check_mode_and_idempotency(monkeypatch):
    module_obj, service_error = load_object(monkeypatch)
    client = ObjectClient(service_error, exists=True)
    params = base_params(state="absent")

    assert run(module_obj, monkeypatch, client, params, check_mode=True)["changed"] is True
    assert client.exists
    assert run(module_obj, monkeypatch, client, params)["changed"] is True
    assert run(module_obj, monkeypatch, client, params)["changed"] is False


def test_delete_exact_version_even_when_current_object_is_absent(monkeypatch):
    module_obj, service_error = load_object(monkeypatch)
    client = ObjectClient(service_error)
    client.versions = [
        types.SimpleNamespace(name="object-other", version_id="version-1"),
        types.SimpleNamespace(name="object", version_id="version-2"),
        types.SimpleNamespace(name="object", version_id="version-1"),
    ]
    params = base_params(state="absent", version_id="version-1")

    assert run(module_obj, monkeypatch, client, params, check_mode=True)["changed"] is True
    assert not client.deletes
    assert run(module_obj, monkeypatch, client, params)["changed"] is True
    assert client.deletes[0]["version_id"] == "version-1"
    assert run(module_obj, monkeypatch, client, params)["changed"] is False


def test_delete_customer_encrypted_object_without_key(monkeypatch):
    module_obj, service_error = load_object(monkeypatch)
    client = ObjectClient(service_error, exists=True)

    def reject_head(**kwargs):
        raise service_error(400, "customer key required")

    client.head_object = reject_head

    result = run(module_obj, monkeypatch, client, base_params(state="absent"))
    assert result["changed"] is True
    assert len(client.deletes) == 1


def test_existing_customer_encrypted_object_is_not_overwritten_without_force(monkeypatch, tmp_path):
    module_obj, service_error = load_object(monkeypatch)
    source = tmp_path / "source"
    source.write_bytes(b"new")
    client = ObjectClient(service_error, exists=True)

    def reject_head(**kwargs):
        raise service_error(400, "customer key required")

    client.head_object = reject_head

    result = run(module_obj, monkeypatch, client, base_params(src=str(source)))
    assert result["changed"] is False
    assert not client.puts


@pytest.mark.parametrize("operation", ["upload", "download"])
def test_customer_encryption_requires_complete_triplet(monkeypatch, tmp_path, operation):
    module_obj, service_error = load_object(monkeypatch)
    source = tmp_path / "source"
    source.write_bytes(b"hello")
    path_params = (
        {"src": str(source)}
        if operation == "upload"
        else {"dest": str(tmp_path / "download")}
    )
    params = base_params(opc_sse_customer_key="secret-key", **path_params)
    instance = make_module_instance(
        module_obj, "OciObjectStorageObjectModule", params, client=ObjectClient(service_error)
    )

    with pytest.raises(FailJsonCalled):
        instance.validate_arguments()


@pytest.mark.parametrize("algorithm", ["aes128", "AES256"])
def test_customer_encryption_rejects_unsupported_algorithm(monkeypatch, tmp_path, algorithm):
    module_obj, service_error = load_object(monkeypatch)
    source = tmp_path / "source"
    source.write_bytes(b"hello")
    params = base_params(
        src=str(source),
        opc_sse_customer_algorithm=algorithm,
        opc_sse_customer_key="secret-key",
        opc_sse_customer_key_sha256="secret-key-hash",
    )
    instance = make_module_instance(
        module_obj, "OciObjectStorageObjectModule", params, client=ObjectClient(service_error)
    )

    with pytest.raises(FailJsonCalled):
        instance.validate_arguments()


@pytest.mark.parametrize(
    "option,value",
    [
        ("content_type", "text/plain"),
        ("content_md5", "XUFAKrxLKna5cZ2REBfFkg=="),
        ("content_language", "en"),
        ("content_encoding", "gzip"),
        ("content_disposition", "attachment"),
        ("cache_control", "no-cache"),
        ("storage_tier", "archive"),
        ("opc_meta", {"owner": "ansible"}),
        ("opc_sse_kms_key_id", "ocid1.key.oc1..example"),
    ],
)
def test_upload_options_are_rejected_for_download(monkeypatch, tmp_path, option, value):
    module_obj, service_error = load_object(monkeypatch)
    params = base_params(dest=str(tmp_path / "download"), **{option: value})
    instance = make_module_instance(
        module_obj, "OciObjectStorageObjectModule", params, client=ObjectClient(service_error)
    )

    with pytest.raises(FailJsonCalled):
        instance.validate_arguments()


def test_upload_options_are_rejected_for_delete(monkeypatch):
    module_obj, service_error = load_object(monkeypatch)
    params = base_params(state="absent", opc_meta={"owner": "ansible"})
    instance = make_module_instance(
        module_obj, "OciObjectStorageObjectModule", params, client=ObjectClient(service_error)
    )

    with pytest.raises(FailJsonCalled):
        instance.validate_arguments()


def test_version_id_is_rejected_for_upload(monkeypatch, tmp_path):
    module_obj, service_error = load_object(monkeypatch)
    source = tmp_path / "source"
    source.write_bytes(b"hello")
    params = base_params(src=str(source), version_id="version-1")
    instance = make_module_instance(
        module_obj, "OciObjectStorageObjectModule", params, client=ObjectClient(service_error)
    )

    with pytest.raises(FailJsonCalled):
        instance.validate_arguments()


@pytest.mark.parametrize(
    "state,path_params",
    [
        ("absent", {}),
        ("present", {"dest": "/tmp/download"}),
    ],
)
def test_empty_version_id_is_rejected(monkeypatch, state, path_params):
    module_obj, service_error = load_object(monkeypatch)
    params = base_params(state=state, version_id="", **path_params)
    client = ObjectClient(service_error, exists=True)
    instance = make_module_instance(
        module_obj, "OciObjectStorageObjectModule", params, client=client
    )

    with pytest.raises(FailJsonCalled):
        instance.validate_arguments()
    assert not client.deletes


def test_delete_ignores_customer_encryption_credentials(monkeypatch):
    module_obj, service_error = load_object(monkeypatch)
    client = ObjectClient(service_error, exists=True)
    params = base_params(state="absent", opc_sse_customer_key="secret-key")

    assert run(module_obj, monkeypatch, client, params)["changed"] is True
    assert "opc_sse_customer_key" not in client.deletes[0]


def test_argument_spec_marks_customer_key_and_hash_secret(monkeypatch):
    module_obj, _service_error = load_object(monkeypatch)

    def capture_module(**kwargs):
        argument_spec = kwargs["argument_spec"]
        assert argument_spec["opc_sse_customer_key"]["no_log"] is True
        assert argument_spec["opc_sse_customer_key_sha256"]["no_log"] is True
        assert argument_spec["storage_tier"]["choices"] == [
            "standard",
            "infrequent_access",
            "archive",
        ]
        assert argument_spec["opc_sse_customer_algorithm"]["choices"] == ["aes256"]
        raise ExitJsonCalled({})

    monkeypatch.setattr(module_obj, "AnsibleModule", capture_module)
    with pytest.raises(ExitJsonCalled):
        module_obj.main()


@pytest.mark.parametrize(
    "params",
    [
        base_params(),
        base_params(src="a", dest="b"),
        base_params(state="absent", src="a"),
    ],
)
def test_validate_arguments(monkeypatch, params):
    module_obj = load_object(monkeypatch)[0]
    instance = make_module_instance(module_obj, "OciObjectStorageObjectModule", params)
    with pytest.raises(FailJsonCalled):
        instance.validate_arguments()
