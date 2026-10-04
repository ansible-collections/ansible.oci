from __future__ import absolute_import, division, print_function

__metaclass__ = type

import types

import pytest

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


def load_info_module(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_object_lifecycle_policy_info")
    module_obj.oci.object_storage = types.SimpleNamespace(ObjectStorageClient=object)
    return module_obj


def make_info_module(module_obj, params, client):
    return make_module_instance(
        module_obj,
        "OciObjectLifecyclePolicyInfoModule",
        params,
        client=client,
    )


def test_main_requires_bucket_and_supports_check_mode(monkeypatch):
    module_obj = load_info_module(monkeypatch)
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule({})

    class FakeInfoModule:
        def __init__(self, module):
            pass

        def execute_info_module(self):
            captured["executed"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciObjectLifecyclePolicyInfoModule", FakeInfoModule)

    module_obj.main()

    assert captured["executed"] is True
    assert captured["supports_check_mode"] is True
    assert captured["argument_spec"]["bucket_name"] == {"type": "str", "required": True}
    assert captured["argument_spec"]["namespace_name"] == {"type": "str"}


def test_fetch_uses_explicit_namespace_for_bucket_policy(monkeypatch):
    module_obj = load_info_module(monkeypatch)
    get_calls = []
    policy = FakeModel(time_created="2026-09-20T12:00:00Z", items=[])

    def get_policy(**kwargs):
        get_calls.append(kwargs)
        return FakeResponse(data=policy)

    instance = make_info_module(
        module_obj,
        {"bucket_name": "application-logs", "namespace_name": "tenant-ns"},
        types.SimpleNamespace(
            get_object_lifecycle_policy=get_policy,
            get_namespace=raising(AssertionError("explicit namespace must be used")),
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.fetch_resources() == [policy]
    assert get_calls == [
        {"namespace_name": "tenant-ns", "bucket_name": "application-logs"}
    ]


def test_fetch_resolves_and_caches_namespace_when_omitted(monkeypatch):
    module_obj = load_info_module(monkeypatch)
    namespace_calls = []
    policy = FakeModel(time_created="2026-09-20T12:00:00Z", items=[])

    def get_namespace():
        namespace_calls.append(True)
        return FakeResponse(data="resolved-ns")

    get_calls = []

    def get_policy(**kwargs):
        get_calls.append(kwargs)
        return FakeResponse(data=policy)

    instance = make_info_module(
        module_obj,
        {"bucket_name": "application-logs"},
        types.SimpleNamespace(
            get_namespace=get_namespace,
            get_object_lifecycle_policy=get_policy,
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.fetch_resources() == [policy]
    assert instance.namespace_name == "resolved-ns"
    assert namespace_calls == [True]
    assert get_calls == [
        {"namespace_name": "resolved-ns", "bucket_name": "application-logs"}
    ]


@pytest.mark.parametrize("check_mode", [False, True])
def test_info_serializes_policy_and_items_as_unchanged_list(monkeypatch, check_mode):
    module_obj = load_info_module(monkeypatch)
    policy = FakeModel(
        time_created="2026-09-20T12:00:00Z",
        items=[
            FakeModel(
                action="DELETE",
                is_enabled=True,
                name="expire-logs",
                object_name_filter=FakeModel(inclusion_patterns=["logs/*"]),
            )
        ],
    )
    instance = make_info_module(
        module_obj,
        {"bucket_name": "application-logs", "namespace_name": "tenant-ns"},
        types.SimpleNamespace(
            get_object_lifecycle_policy=lambda **kwargs: FakeResponse(data=policy)
        ),
    )
    instance.module.check_mode = check_mode
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()

    assert exc_info.value.payload == {
        "changed": False,
        "object_lifecycle_policies": [
            {
                "time_created": "2026-09-20T12:00:00Z",
                "items": [
                    {
                        "action": "DELETE",
                        "is_enabled": True,
                        "name": "expire-logs",
                        "object_name_filter": {"inclusion_patterns": ["logs/*"]},
                    }
                ],
            }
        ],
    }


def test_missing_policy_returns_empty_list(monkeypatch):
    _oci_module, ServiceError = install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_object_lifecycle_policy_info")
    module_obj.oci.object_storage = types.SimpleNamespace(ObjectStorageClient=object)

    def missing_policy(**kwargs):
        raise ServiceError(404, "missing")

    instance = make_info_module(
        module_obj,
        {"bucket_name": "missing-bucket", "namespace_name": "tenant-ns"},
        types.SimpleNamespace(get_object_lifecycle_policy=missing_policy),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()

    assert exc_info.value.payload == {"changed": False, "object_lifecycle_policies": []}


def test_non_404_get_error_propagates(monkeypatch):
    _oci_module, ServiceError = install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_object_lifecycle_policy_info")
    module_obj.oci.object_storage = types.SimpleNamespace(ObjectStorageClient=object)
    error = ServiceError(500, "service unavailable")
    instance = make_info_module(
        module_obj,
        {"bucket_name": "application-logs", "namespace_name": "tenant-ns"},
        types.SimpleNamespace(
            get_object_lifecycle_policy=raising(error),
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    with pytest.raises(ServiceError) as exc_info:
        instance.fetch_resources()

    assert exc_info.value is error
