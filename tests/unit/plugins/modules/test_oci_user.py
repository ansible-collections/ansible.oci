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
)


MODELS = (
    "User",
    "UserName",
    "UserEmails",
    "ExtensionOCITags",
    "FreeformTags",
    "DefinedTags",
    "PatchOp",
    "Operations",
)


def load_user_module(monkeypatch):
    install_fake_oci(monkeypatch, model_names=MODELS)
    return load_collection_module("oci_user")


def make_user(module_obj, params, client=None, check_mode=False):
    return make_module_instance(
        module_obj, "OciUserModule", params, client=client, check_mode=check_mode
    )


def test_main_exposes_scim_arguments_and_domain_choice(monkeypatch):
    module_obj = load_user_module(monkeypatch)
    captured = {}

    monkeypatch.setattr(
        module_obj,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule({}),
    )
    monkeypatch.setattr(
        module_obj,
        "OciUserModule",
        lambda module: types.SimpleNamespace(execute_resource_module=lambda: None),
    )
    module_obj.main()

    assert captured["supports_check_mode"] is True
    assert captured["required_one_of"] == [["domain_id", "domain_url"]]
    assert captured["mutually_exclusive"] == [["domain_id", "domain_url"]]
    for name in (
        "user_id",
        "user_name",
        "name",
        "given_name",
        "family_name",
        "email",
        "description",
    ):
        assert captured["argument_spec"][name] == {"type": "str"}
    assert "compartment_id" not in captured["argument_spec"]


def test_identity_domains_client_is_bound_to_domain_endpoint(monkeypatch):
    module_obj = load_user_module(monkeypatch)
    instance = make_user(module_obj, {})
    instance.identity_domain_url = "https://identity.example.com"
    client_factory = instance.client_class
    assert client_factory.func is module_obj.oci.identity_domains.IdentityDomainsClient
    assert client_factory.keywords == {
        "service_endpoint": "https://identity.example.com"
    }


def test_domain_id_is_resolved_through_control_plane(monkeypatch):
    module_obj = load_user_module(monkeypatch)
    helper = sys.modules[module_obj.OciIdentityDomainResourceBase.__module__]
    calls = []
    identity_client = types.SimpleNamespace(
        get_domain=lambda **kwargs: calls.append(kwargs)
        or FakeResponse(FakeModel(url="https://identity.example.com/"))
    )
    monkeypatch.setattr(
        helper, "create_service_client", lambda module, client_class: identity_client
    )
    assert helper.resolve_domain_url(DummyModule({"domain_id": "domain1"})) == (
        "https://identity.example.com"
    )
    assert calls == [{"domain_id": "domain1"}]


def test_missing_sdk_fails_before_domain_id_resolution(monkeypatch):
    module_obj = load_user_module(monkeypatch)
    helper = sys.modules[module_obj.OciIdentityDomainResourceBase.__module__]
    monkeypatch.setattr(helper, "HAS_OCI_SDK", False)
    monkeypatch.setattr(
        helper,
        "resolve_domain_url",
        lambda module: pytest.fail("domain lookup must not run without OCI SDK"),
    )

    with pytest.raises(FailJsonCalled, match="oci"):
        module_obj.OciUserModule(DummyModule({"domain_id": "domain1"}))


@pytest.mark.parametrize(
    "params",
    [
        {"user_name": "alice@example.com"},
        {"user_name": "alice@example.com", "family_name": ""},
        {"user_name": "", "family_name": "Example"},
        {"user_name": "alice@example.com", "family_name": "Example", "email": ""},
    ],
)
def test_create_rejects_missing_or_empty_required_values(monkeypatch, params):
    module_obj = load_user_module(monkeypatch)
    instance = make_user(module_obj, params)

    with pytest.raises(FailJsonCalled):
        instance.validate_create_request()


def test_create_builds_scim_user_and_calls_identity_domains_api(monkeypatch):
    module_obj = load_user_module(monkeypatch)
    created = FakeModel(id="user1", user_name="alice@example.com")
    calls = []
    client = types.SimpleNamespace(
        create_user=lambda **kwargs: calls.append(kwargs) or FakeResponse(created)
    )
    instance = make_user(
        module_obj,
        {
            "user_name": "alice@example.com",
            "name": "Alice",
            "given_name": "Alice",
            "family_name": "Example",
            "email": "alice@example.com",
            "active": True,
            "freeform_tags": {"team": "iam"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        },
        client,
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.create_resource() is created
    user = calls[0]["user"]
    assert user.user_name == "alice@example.com"
    assert user.display_name == "Alice"
    assert user.name.given_name == "Alice"
    assert user.emails[0].value == "alice@example.com"
    assert user.active is True
    assert module_obj.CORE_USER_SCHEMA in user.schemas
    helper = sys.modules[module_obj.OciIdentityDomainResourceBase.__module__]
    assert helper.OCI_TAGS_SCHEMA in user.schemas


def test_serialized_user_matches_create_and_info_result_shape(monkeypatch):
    module_obj = load_user_module(monkeypatch)
    user = FakeModel(
        id="scim-user-1",
        ocid="ocid1.user.oc1..example",
        domain_ocid="ocid1.domain.oc1..example",
        user_name="alice@example.com",
        display_name="Alice Example",
        name=FakeModel(given_name="Alice", family_name="Example"),
        emails=[FakeModel(value="alice@example.com", type="work")],
        description="Example user",
        active=True,
        urn_ietf_params_scim_schemas_oracle_idcs_extension_oci_tags=FakeModel(
            freeform_tags=[FakeModel(key="phase", value="create")],
            defined_tags=[
                FakeModel(namespace="Oracle-Tags", key="CreatedBy", value="admin")
            ],
        ),
        meta=FakeModel(
            created="2026-09-23T12:03:35.786Z",
            last_modified="2026-09-23T12:03:35.786Z",
        ),
    )

    assert module_obj.serialize_user(user) == {
        "id": "scim-user-1",
        "ocid": "ocid1.user.oc1..example",
        "domain_id": "ocid1.domain.oc1..example",
        "user_name": "alice@example.com",
        "name": "Alice Example",
        "given_name": "Alice",
        "family_name": "Example",
        "email": "alice@example.com",
        "description": "Example user",
        "active": True,
        "freeform_tags": {"phase": "create"},
        "defined_tags": {"Oracle-Tags": {"CreatedBy": "admin"}},
        "time_created": "2026-09-23T12:03:35.786Z",
        "time_modified": "2026-09-23T12:03:35.786Z",
    }


def test_exact_user_name_lookup_uses_escaped_scim_filter(monkeypatch):
    module_obj = load_user_module(monkeypatch)
    list_users = object()
    instance = make_user(
        module_obj,
        {"user_name": 'alice"ops'},
        types.SimpleNamespace(list_users=list_users),
    )
    calls = []
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda method, **kwargs: calls.append((method, kwargs)) or [],
    )

    assert instance.find_resources_by_name() == []
    assert calls == [
        (list_users, {"filter": 'userName eq "alice\\"ops"'})
    ]


def test_update_builds_scim_patch_for_fields_email_and_tags(monkeypatch):
    module_obj = load_user_module(monkeypatch)
    updated = FakeModel(id="user1", user_name="alice@example.com")
    calls = []
    client = types.SimpleNamespace(
        patch_user=lambda **kwargs: calls.append(kwargs) or FakeResponse(updated)
    )
    instance = make_user(
        module_obj,
        {
            "name": "Alice Updated",
            "given_name": "Alicia",
            "email": "new@example.com",
            "active": False,
            "freeform_tags": {"phase": "update"},
        },
        client,
    )
    current = FakeModel(
        id="user1",
        user_name="alice@example.com",
        display_name="Alice",
        name=FakeModel(given_name="Alice", family_name="Example"),
        emails=[
            FakeModel(value="old@example.com", type="work", primary=False),
            FakeModel(value="home@example.com", type="home", primary=True),
        ],
        active=True,
        urn_ietf_params_scim_schemas_oracle_idcs_extension_oci_tags=None,
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.needs_update(current) is True
    assert instance.update_resource(current) is updated
    assert len(calls) == 1
    assert set(calls[0]) == {"user_id", "patch_op"}
    assert calls[0]["user_id"] == "user1"
    patch_op = calls[0]["patch_op"]
    helper = sys.modules[module_obj.OciIdentityDomainResourceBase.__module__]
    assert patch_op.schemas == [helper.PATCH_SCHEMA]
    assert [operation.path for operation in patch_op.operations] == [
        "displayName",
        "name.givenName",
        "active",
        'emails[type eq "work"].value',
        helper.OCI_TAGS_SCHEMA + ":freeformTags",
    ]
    assert patch_op.operations[2].value is False
    email_op = next(op for op in patch_op.operations if op.path.startswith("emails"))
    assert email_op.value == "new@example.com"
    assert email_op.op == "REPLACE"


def test_defined_tags_preserve_oci_tags_and_converge(monkeypatch):
    module_obj = load_user_module(monkeypatch)
    current = FakeModel(
        urn_ietf_params_scim_schemas_oracle_idcs_extension_oci_tags=FakeModel(
            defined_tags=[
                FakeModel(namespace="Oracle-Tags", key="CreatedBy", value="admin"),
                FakeModel(namespace="Oracle-Tags", key="CreatedOn", value="2026-09-23"),
                FakeModel(namespace="Operations", key="CostCenter", value="42"),
            ]
        )
    )
    unchanged = make_user(
        module_obj, {"defined_tags": {"Operations": {"CostCenter": "42"}}}
    )
    assert unchanged.needs_update(current) is False

    changed = make_user(
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
        ("Oracle-Tags", "CreatedOn"): "2026-09-23",
        ("Operations", "CostCenter"): "43",
    }


def test_add_work_email_preserves_existing_primary_email(monkeypatch):
    module_obj = load_user_module(monkeypatch)
    instance = make_user(module_obj, {"email": "work@example.com"})
    current = FakeModel(
        emails=[FakeModel(value="home@example.com", type="home", primary=True)]
    )

    plan = instance.build_update_plan(current)
    assert len(plan["operations"]) == 1
    email_op = plan["operations"][0]
    assert email_op.op == "ADD"
    assert email_op.path == "emails"
    assert email_op.value[0].value == "work@example.com"
    assert email_op.value[0].primary is False
    assert module_obj.serialize_user(current)["email"] is None


def test_unchanged_user_email_and_fields_do_not_send_patch(monkeypatch):
    module_obj = load_user_module(monkeypatch)
    current = FakeModel(
        id="user1",
        active=False,
        emails=[FakeModel(type="work", value="work@example.com", primary=True)],
        urn_ietf_params_scim_schemas_oracle_idcs_extension_oci_tags=FakeModel(
            freeform_tags=[FakeModel(key="phase", value="update")]
        ),
    )
    instance = make_user(
        module_obj,
        {
            "active": False,
            "email": "work@example.com",
            "freeform_tags": {"phase": "update"},
        },
        types.SimpleNamespace(
            patch_user=lambda **kwargs: pytest.fail("unexpected patch")
        ),
    )

    assert instance.needs_update(current) is False
    assert instance.update_resource(current) is current


def test_get_404_check_mode_idempotency_delete_and_serialization(monkeypatch):
    module_obj = load_user_module(monkeypatch)
    instance = make_user(
        module_obj,
        {"user_name": "alice@example.com", "family_name": "Example"},
        check_mode=True,
    )
    error = RuntimeError("missing")
    error.status = 404

    def raise_not_found(resource_id):
        assert resource_id == "missing"
        raise error

    monkeypatch.setattr(
        instance,
        "get_resource_response",
        raise_not_found,
    )
    assert instance.get_resource_by_id("missing") is None

    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload == {"changed": True}

    existing = FakeModel(
        id="user1",
        ocid="ocid1.user.example",
        user_name="alice@example.com",
        name=None,
        emails=[],
    )
    instance.check_mode = False
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: existing)
    monkeypatch.setattr(instance, "needs_update", lambda resource: False)
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload["changed"] is False
    assert result.value.payload["resource"]["id"] == "user1"

    calls = []
    instance.client = types.SimpleNamespace(delete_user=object())
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda method, **kwargs: calls.append((method, kwargs)),
    )
    instance.delete_resource(existing)
    assert calls == [(instance.client.delete_user, {"user_id": "user1"})]
