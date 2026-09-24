from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types
import sys

import pytest

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FailJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


MODELS = (
    "Group",
    "ExtensionOCITags",
    "FreeformTags",
    "DefinedTags",
    "PatchOp",
    "Operations",
)


def load_group_module(monkeypatch):
    install_fake_oci(monkeypatch, model_names=MODELS)
    return load_collection_module("oci_group")


def make_group(module_obj, params, client=None, check_mode=False):
    return make_module_instance(
        module_obj, "OciGroupModule", params, client=client, check_mode=check_mode
    )


def test_main_exposes_domain_scim_contract(monkeypatch):
    module_obj = load_group_module(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        module_obj,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule({}),
    )
    monkeypatch.setattr(
        module_obj,
        "OciGroupModule",
        lambda module: types.SimpleNamespace(execute_resource_module=lambda: None),
    )
    module_obj.main()
    assert captured["required_one_of"] == [["domain_id", "domain_url"]]
    assert captured["mutually_exclusive"] == [["domain_id", "domain_url"]]
    assert captured["argument_spec"]["group_id"] == {"type": "str"}
    assert captured["argument_spec"]["display_name"] == {"type": "str"}
    assert "compartment_id" not in captured["argument_spec"]
    assert "description" not in captured["argument_spec"]


def test_create_uses_identity_domains_group_model(monkeypatch):
    module_obj = load_group_module(monkeypatch)
    created = FakeModel(id="group1", display_name="admins")
    calls = []
    instance = make_group(
        module_obj,
        {
            "display_name": "admins",
            "freeform_tags": {"team": "iam"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        },
        types.SimpleNamespace(
            create_group=lambda **kwargs: calls.append(kwargs) or FakeResponse(created)
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    assert instance.create_resource() is created
    group = calls[0]["group"]
    assert group.display_name == "admins"
    assert module_obj.CORE_GROUP_SCHEMA in group.schemas
    helper = sys.modules[module_obj.OciIdentityDomainResourceBase.__module__]
    assert helper.OCI_TAGS_SCHEMA in group.schemas


@pytest.mark.parametrize("display_name", [None, "", "   "])
def test_create_requires_nonempty_display_name(monkeypatch, display_name):
    module_obj = load_group_module(monkeypatch)
    instance = make_group(module_obj, {"display_name": display_name})
    with pytest.raises(FailJsonCalled) as result:
        instance.validate_create_request()
    assert "display_name" in result.value.payload["msg"]


def test_identity_domains_helper_preserves_user_contract(monkeypatch):
    module_obj = load_group_module(monkeypatch)
    helper = sys.modules[module_obj.OciIdentityDomainResourceBase.__module__]
    user = FakeModel(
        display_name="Application User",
        emails=[
            FakeModel(type="home", value="home@example.com", primary=True),
            FakeModel(type="work", value="work@example.com"),
        ],
    )
    result = helper.serialize_user(user)
    assert result["name"] == "Application User"
    assert result["email"] == "work@example.com"

    monkeypatch.setattr(helper, "HAS_OCI_SDK", False)
    with pytest.raises(FailJsonCalled) as failure:
        module_obj.OciGroupModule(DummyModule({"domain_id": "domain1"}))
    assert "oci" in failure.value.payload["msg"]


def test_domain_id_resolution_and_identity_domains_client(monkeypatch):
    module_obj = load_group_module(monkeypatch)
    helper = sys.modules[module_obj.OciIdentityDomainResourceBase.__module__]
    client = types.SimpleNamespace(
        get_domain=lambda **kwargs: FakeResponse(
            FakeModel(url="https://identity.example.com/")
        )
    )
    monkeypatch.setattr(helper, "create_service_client", lambda module, cls: client)
    assert helper.resolve_domain_url(DummyModule({"domain_id": "domain1"})) == (
        "https://identity.example.com"
    )
    instance = make_group(module_obj, {})
    instance.identity_domain_url = "https://identity.example.com"
    assert (
        instance.client_class.func
        is module_obj.oci.identity_domains.IdentityDomainsClient
    )


def test_exact_display_name_lookup_escapes_scim_filter(monkeypatch):
    module_obj = load_group_module(monkeypatch)
    list_groups = object()
    instance = make_group(
        module_obj,
        {"display_name": 'admin"ops'},
        types.SimpleNamespace(list_groups=list_groups),
    )
    calls = []
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda method, **kwargs: calls.append((method, kwargs)) or [],
    )
    assert instance.find_resources_by_name() == []
    assert calls == [
        (list_groups, {"filter": 'displayName eq "admin\\"ops"'})
    ]


def test_update_builds_patch_for_display_name_and_tags(monkeypatch):
    module_obj = load_group_module(monkeypatch)
    calls = []
    updated = FakeModel(id="group1", display_name="operators")
    instance = make_group(
        module_obj,
        {
            "display_name": "operators",
            "freeform_tags": {"phase": "updated"},
        },
        types.SimpleNamespace(
            patch_group=lambda **kwargs: calls.append(kwargs) or FakeResponse(updated)
        ),
    )
    current = FakeModel(
        id="group1",
        display_name="admins",
        urn_ietf_params_scim_schemas_oracle_idcs_extension_oci_tags=None,
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    assert instance.needs_update(current) is True
    assert instance.update_resource(current) is updated
    helper = sys.modules[module_obj.OciIdentityDomainResourceBase.__module__]
    assert len(calls) == 1
    assert set(calls[0]) == {"group_id", "patch_op"}
    assert calls[0]["group_id"] == "group1"
    assert [operation.path for operation in calls[0]["patch_op"].operations] == [
        "displayName",
        helper.OCI_TAGS_SCHEMA + ":freeformTags",
    ]


def test_defined_tags_preserve_oci_tags_and_converge(monkeypatch):
    module_obj = load_group_module(monkeypatch)
    current = FakeModel(
        display_name="admins",
        urn_ietf_params_scim_schemas_oracle_idcs_extension_oci_tags=FakeModel(
            defined_tags=[
                FakeModel(namespace="Oracle-Tags", key="CreatedBy", value="admin"),
                FakeModel(namespace="Operations", key="CostCenter", value="42"),
            ]
        ),
    )
    unchanged = make_group(
        module_obj, {"defined_tags": {"Operations": {"CostCenter": "42"}}}
    )
    assert unchanged.needs_update(current) is False

    changed = make_group(
        module_obj, {"defined_tags": {"Operations": {"CostCenter": "43"}}}
    )
    operations = changed.build_update_plan(current)["operations"]
    assert len(operations) == 1
    helper = sys.modules[module_obj.OciIdentityDomainResourceBase.__module__]
    assert operations[0].path == helper.OCI_TAGS_SCHEMA + ":definedTags"
    assert {
        (tag.namespace, tag.key): tag.value for tag in operations[0].value
    } == {
        ("Oracle-Tags", "CreatedBy"): "admin",
        ("Operations", "CostCenter"): "43",
    }


def test_empty_tags_clear_user_tags_but_keep_oracle_tags(monkeypatch):
    module_obj = load_group_module(monkeypatch)
    current = FakeModel(
        urn_ietf_params_scim_schemas_oracle_idcs_extension_oci_tags=FakeModel(
            freeform_tags=[FakeModel(key="phase", value="old")],
            defined_tags=[
                FakeModel(namespace="Oracle-Tags", key="CreatedBy", value="admin"),
                FakeModel(namespace="Operations", key="CostCenter", value="42"),
            ],
        )
    )
    instance = make_group(module_obj, {"freeform_tags": {}, "defined_tags": {}})

    operations = instance.build_update_plan(current)["operations"]
    helper = sys.modules[module_obj.OciIdentityDomainResourceBase.__module__]
    assert [operation.path for operation in operations] == [
        helper.OCI_TAGS_SCHEMA + ":freeformTags",
        helper.OCI_TAGS_SCHEMA + ":definedTags",
    ]
    assert operations[0].value == []
    assert [(tag.namespace, tag.key, tag.value) for tag in operations[1].value] == [
        ("Oracle-Tags", "CreatedBy", "admin")
    ]
    assert instance.module.params["defined_tags"] == {}

    converged = FakeModel(
        urn_ietf_params_scim_schemas_oracle_idcs_extension_oci_tags=FakeModel(
            freeform_tags=[],
            defined_tags=[
                FakeModel(namespace="Oracle-Tags", key="CreatedBy", value="admin")
            ],
        )
    )
    assert instance.needs_update(converged) is False


def test_unchanged_group_does_not_send_empty_patch(monkeypatch):
    module_obj = load_group_module(monkeypatch)
    current = FakeModel(id="group1", display_name="admins")
    instance = make_group(
        module_obj,
        {"display_name": "admins"},
        types.SimpleNamespace(
            patch_group=lambda **kwargs: pytest.fail("unexpected patch")
        ),
    )

    assert instance.needs_update(current) is False
    assert instance.update_resource(current) is current


def test_404_check_mode_idempotency_delete_and_serialization(monkeypatch):
    module_obj = load_group_module(monkeypatch)
    instance = make_group(module_obj, {"display_name": "admins"}, check_mode=True)
    error = RuntimeError("missing")
    error.status = 404
    monkeypatch.setattr(
        instance,
        "get_resource_response",
        raising(error),
    )
    assert instance.get_resource_by_id("missing") is None
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload == {"changed": True}

    existing = FakeModel(id="group1", ocid="ocid1.group.example", display_name="admins")
    instance.check_mode = False
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: existing)
    monkeypatch.setattr(instance, "needs_update", lambda resource: False)
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload["changed"] is False
    assert result.value.payload["resource"]["id"] == "group1"

    calls = []
    instance.client = types.SimpleNamespace(delete_group=object())
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda method, **kwargs: calls.append((method, kwargs)),
    )
    instance.delete_resource(existing)
    assert calls == [(instance.client.delete_group, {"group_id": "group1"})]
