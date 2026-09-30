from __future__ import absolute_import, division, print_function

__metaclass__ = type

import types

import pytest

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    FailJsonCalled,
    load_collection_module,
    make_module_instance,
    raising,
)


def items(**overrides):
    rule = {
        "name": "archive-old-objects",
        "action": "archive",
        "time_amount": 30,
        "time_unit": "days",
        "is_enabled": True,
    }
    rule.update(overrides)
    return [rule]


def make_policy_module(module_obj, params, client=None, check_mode=False):
    instance = make_module_instance(
        module_obj,
        "OciObjectLifecyclePolicyModule",
        params,
        client=client,
        check_mode=check_mode,
        _namespace_name=None,
    )
    instance.call_with_retry = lambda fn, *args, **kwargs: fn(*args, **kwargs)
    return instance


class ServiceError(Exception):
    def __init__(self, status):
        super(ServiceError, self).__init__("service error")
        self.status = status


def test_main_exposes_bucket_policy_arguments_and_auth_only(monkeypatch):
    module_obj = load_collection_module("oci_object_lifecycle_policy")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        captured["required_if"] = kwargs.get("required_if")
        captured["supports_check_mode"] = kwargs["supports_check_mode"]
        return DummyModule({})

    class FakePolicyModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(
        module_obj, "OciObjectLifecyclePolicyModule", FakePolicyModule
    )

    module_obj.main()

    spec = captured["argument_spec"]
    assert captured["run_called"] is True
    assert captured["supports_check_mode"] is True
    assert spec["bucket_name"] == {"type": "str", "required": True}
    assert spec["namespace_name"] == {"type": "str"}
    assert spec["items"]["type"] == "list"
    assert spec["items"]["options"]["target"]["default"] == "objects"
    assert spec["items"]["options"]["action"]["choices"] == [
        "archive",
        "infrequent_access",
        "delete",
        "abort",
    ]
    assert spec["items"]["options"]["time_unit"]["choices"] == [
        "days",
        "years",
    ]
    assert "freeform_tags" not in spec
    assert "defined_tags" not in spec
    assert "wait" not in spec
    assert captured["required_if"] == [("state", "present", ["items"])]


def test_build_policy_details_converts_rules_and_optional_filter(monkeypatch):
    module_obj = load_collection_module("oci_object_lifecycle_policy")

    details = module_obj.build_policy_details(
        [
            dict(
                items()[0],
                target="previous-object-versions",
                object_name_filter={
                    "inclusion_prefixes": ["logs/", "archive/"],
                    "inclusion_patterns": ["*.log"],
                    "exclusion_patterns": ["keep-*"],
                },
            )
        ]
    )

    rule = details.items[0]
    assert rule.name == "archive-old-objects"
    assert rule.action == "ARCHIVE"
    assert rule.target == "previous-object-versions"
    assert rule.time_amount == 30
    assert rule.time_unit == "DAYS"
    assert rule.is_enabled is True
    assert rule.object_name_filter.inclusion_prefixes == ["logs/", "archive/"]
    assert rule.object_name_filter.inclusion_patterns == ["*.log"]
    assert rule.object_name_filter.exclusion_patterns == ["keep-*"]


def test_build_policy_details_filters_none_values_from_optional_filter():
    module_obj = load_collection_module("oci_object_lifecycle_policy")

    details = module_obj.build_policy_details(
        [
            dict(
                items()[0],
                object_name_filter={
                    "inclusion_prefixes": ["logs/"],
                    "inclusion_patterns": None,
                    "exclusion_patterns": None,
                },
            ),
            dict(
                items()[0],
                name="no-filter-fields",
                object_name_filter={
                    "inclusion_prefixes": None,
                    "inclusion_patterns": None,
                    "exclusion_patterns": None,
                },
            ),
        ]
    )

    assert details.items[0].object_name_filter.inclusion_prefixes == ["logs/"]
    assert details.items[0].object_name_filter.inclusion_patterns is None
    assert details.items[0].object_name_filter.exclusion_patterns is None
    assert details.items[1].object_name_filter is None


def test_build_policy_details_applies_objects_target_default():
    module_obj = load_collection_module("oci_object_lifecycle_policy")

    details = module_obj.build_policy_details(items())

    assert details.items[0].target == "objects"


def test_namespace_mixin_uses_explicit_value_and_caches_automatic_lookup():
    module_obj = load_collection_module("oci_object_lifecycle_policy")
    explicit_client = types.SimpleNamespace(
        get_namespace=lambda: pytest.fail("explicit namespace must skip lookup")
    )
    explicit = make_policy_module(
        module_obj,
        {"namespace_name": "explicit-ns"},
        client=explicit_client,
    )
    assert explicit.namespace_name == "explicit-ns"
    assert explicit.namespace_name == "explicit-ns"

    calls = []
    automatic = make_policy_module(
        module_obj,
        {},
        client=types.SimpleNamespace(
            get_namespace=lambda: calls.append(True) or FakeResponse("auto-ns")
        ),
    )
    assert automatic.namespace_name == "auto-ns"
    assert automatic.namespace_name == "auto-ns"
    assert calls == [True]


def test_check_mode_predicts_create_without_put():
    module_obj = load_collection_module("oci_object_lifecycle_policy")
    client = types.SimpleNamespace(
        get_object_lifecycle_policy=raising(ServiceError(404)),
        put_object_lifecycle_policy=lambda **kwargs: pytest.fail(
            "check mode must not write"
        ),
    )
    instance = make_policy_module(
        module_obj,
        {"bucket_name": "logs", "namespace_name": "ns", "items": items()},
        client=client,
        check_mode=True,
    )

    with pytest.raises(ExitJsonCalled) as exc:
        instance.execute_resource_module()

    assert exc.value.payload == {"changed": True}


def test_check_mode_predicts_update_without_put():
    module_obj = load_collection_module("oci_object_lifecycle_policy")
    current = FakeModel(items=[FakeModel(**dict(items()[0], target="objects"))])
    client = types.SimpleNamespace(
        get_object_lifecycle_policy=lambda **kwargs: FakeResponse(current),
        put_object_lifecycle_policy=lambda **kwargs: pytest.fail(
            "check mode must not write"
        ),
    )
    instance = make_policy_module(
        module_obj,
        {
            "bucket_name": "logs",
            "namespace_name": "ns",
            "items": items(time_amount=45),
        },
        client=client,
        check_mode=True,
    )

    with pytest.raises(ExitJsonCalled) as exc:
        instance.execute_resource_module()

    assert exc.value.payload == {"changed": True}


def test_check_mode_predicts_delete_without_delete_call():
    module_obj = load_collection_module("oci_object_lifecycle_policy")
    client = types.SimpleNamespace(
        get_object_lifecycle_policy=lambda **kwargs: FakeResponse(FakeModel(items=[])),
        delete_object_lifecycle_policy=lambda **kwargs: pytest.fail(
            "check mode must not delete"
        ),
    )
    instance = make_policy_module(
        module_obj,
        {"state": "absent", "bucket_name": "logs", "namespace_name": "ns"},
        client=client,
        check_mode=True,
    )

    with pytest.raises(ExitJsonCalled) as exc:
        instance.execute_resource_module()

    assert exc.value.payload == {"changed": True}


def test_policy_rule_order_and_defaults_are_idempotent():
    module_obj = load_collection_module("oci_object_lifecycle_policy")
    current = FakeModel(
        time_created="ignored",
        items=[
            FakeModel(
                name="delete-multipart",
                action="ABORT",
                target="multipart-uploads",
                time_amount=7,
                time_unit="DAYS",
                is_enabled=True,
                object_name_filter=FakeModel(
                    inclusion_prefixes=["b/", "a/"],
                    inclusion_patterns=["*.z", "*.a"],
                    exclusion_patterns=["keep-*", "skip-*"],
                ),
            ),
            FakeModel(
                name="archive-old-objects",
                action="ARCHIVE",
                target="objects",
                time_amount=30,
                time_unit="DAYS",
                is_enabled=True,
                object_name_filter=FakeModel(
                    inclusion_prefixes=[],
                    inclusion_patterns=[],
                    exclusion_patterns=[],
                ),
            ),
        ],
    )
    desired = [
        dict(items()[0], object_name_filter={}),
        {
            "name": "delete-multipart",
            "action": "abort",
            "target": "multipart-uploads",
            "time_amount": 7,
            "time_unit": "days",
            "is_enabled": True,
            "object_name_filter": {
                "inclusion_prefixes": ["a/", "b/"],
                "inclusion_patterns": ["*.a", "*.z"],
                "exclusion_patterns": ["skip-*", "keep-*"],
            },
        },
    ]
    instance = make_policy_module(
        module_obj,
        {"bucket_name": "logs", "namespace_name": "ns", "items": desired},
    )

    assert instance.needs_update(current) is False


def test_policy_sorting_handles_same_rule_fields_with_different_filters():
    module_obj = load_collection_module("oci_object_lifecycle_policy")
    unfiltered = items()[0]
    filtered = dict(unfiltered, object_name_filter={"inclusion_prefixes": ["logs/"]})

    normalized = module_obj.normalized_policy_items([filtered, unfiltered])

    assert len(normalized) == 2
    assert normalized != module_obj.normalized_policy_items([unfiltered])


def test_rule_field_change_requires_update():
    module_obj = load_collection_module("oci_object_lifecycle_policy")
    current = FakeModel(items=[FakeModel(**dict(items()[0], target="objects"))])
    instance = make_policy_module(
        module_obj,
        {"bucket_name": "logs", "namespace_name": "ns", "items": items(is_enabled=False)},
    )

    assert instance.needs_update(current) is True


def test_get_policy_treats_only_404_as_missing():
    module_obj = load_collection_module("oci_object_lifecycle_policy")
    calls = []

    def get_policy(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise ServiceError(404)
        return FakeResponse(FakeModel(items=[]))

    client = types.SimpleNamespace(get_object_lifecycle_policy=get_policy)
    instance = make_policy_module(
        module_obj,
        {"bucket_name": "logs", "namespace_name": "ns", "items": items()},
        client=client,
    )
    assert instance.resolve_target_resource() is None
    assert calls[0] == {"namespace_name": "ns", "bucket_name": "logs"}

    requested_ids = []
    original_get_resource_by_id = instance.get_resource_by_id

    def capture_lookup_key(resource_id):
        requested_ids.append(resource_id)
        return original_get_resource_by_id(resource_id)

    instance.get_resource_by_id = capture_lookup_key
    instance.resolve_target_resource()
    assert requested_ids == ["logs"]

    instance.get_resource_response("another-bucket")
    assert calls[-1] == {"namespace_name": "ns", "bucket_name": "another-bucket"}

    def raise_forbidden(**kwargs):
        raise ServiceError(403)

    instance.client.get_object_lifecycle_policy = raise_forbidden
    with pytest.raises(ServiceError) as exc:
        instance.resolve_target_resource()
    assert exc.value.status == 403


def test_create_update_and_delete_use_bucket_scoped_policy_api():
    module_obj = load_collection_module("oci_object_lifecycle_policy")
    calls = []
    current = FakeModel(items=[FakeModel(**dict(items()[0], target="objects"))])

    def get_policy(**kwargs):
        calls.append(("get", kwargs))
        return FakeResponse(current)

    def put_policy(**kwargs):
        calls.append(("put", kwargs))
        return FakeResponse(FakeModel(items=kwargs["put_object_lifecycle_policy_details"].items))

    def delete_policy(**kwargs):
        calls.append(("delete", kwargs))
        return FakeResponse()

    client = types.SimpleNamespace(
        get_object_lifecycle_policy=get_policy,
        put_object_lifecycle_policy=put_policy,
        delete_object_lifecycle_policy=delete_policy,
    )
    params = {"bucket_name": "logs", "namespace_name": "ns", "items": items(time_amount=45)}
    update = make_policy_module(module_obj, params, client=client)
    updated = update.update_resource(current)
    assert updated.items[0].time_amount == 45
    assert calls[-1][0] == "put"
    assert calls[-1][1]["namespace_name"] == "ns"
    assert calls[-1][1]["bucket_name"] == "logs"

    absent = make_policy_module(
        module_obj,
        {"state": "absent", "bucket_name": "logs", "namespace_name": "ns"},
        client=client,
    )
    absent.delete_resource(current)
    assert calls[-1] == (
        "delete",
        {"namespace_name": "ns", "bucket_name": "logs"},
    )

    create_client = types.SimpleNamespace(
        put_object_lifecycle_policy=put_policy,
    )
    create = make_policy_module(module_obj, params, client=create_client)
    created = create.create_resource()
    assert created.items[0].time_amount == 45


def test_absent_without_policy_is_unchanged_and_present_requires_items():
    module_obj = load_collection_module("oci_object_lifecycle_policy")
    client = types.SimpleNamespace(
        get_object_lifecycle_policy=raising(ServiceError(404))
    )
    absent = make_policy_module(
        module_obj,
        {"state": "absent", "bucket_name": "logs", "namespace_name": "ns"},
        client=client,
    )
    with pytest.raises(ExitJsonCalled) as exc:
        absent.execute_resource_module()
    assert exc.value.payload == {"changed": False}

    present = make_policy_module(
        module_obj,
        {"bucket_name": "logs", "namespace_name": "ns"},
        client=client,
    )
    with pytest.raises(FailJsonCalled):
        present.validate_create_request()
