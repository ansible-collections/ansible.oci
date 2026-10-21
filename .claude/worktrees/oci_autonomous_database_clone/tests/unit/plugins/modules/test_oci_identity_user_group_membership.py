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
    "GroupMembers",
    "PatchOp",
    "Operations",
    "ExtensionOCITags",
    "FreeformTags",
    "DefinedTags",
)


def load_membership_module(monkeypatch):
    install_fake_oci(monkeypatch, model_names=MODELS)
    return load_collection_module("oci_identity_user_group_membership")


def make_membership(module_obj, params, client=None, check_mode=False):
    return make_module_instance(
        module_obj,
        "OciIdentityUserGroupMembershipModule",
        params,
        client=client,
        check_mode=check_mode,
    )


def test_main_requires_domain_user_and_group(monkeypatch):
    module_obj = load_membership_module(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        module_obj,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule({}),
    )
    monkeypatch.setattr(
        module_obj,
        "OciIdentityUserGroupMembershipModule",
        lambda module: types.SimpleNamespace(execute_resource_module=lambda: None),
    )
    module_obj.main()
    assert captured["required_one_of"] == [["domain_id", "domain_url"]]
    assert captured["mutually_exclusive"] == [["domain_id", "domain_url"]]
    assert captured["argument_spec"]["user_id"]["required"] is True
    assert captured["argument_spec"]["group_id"]["required"] is True
    assert "user_group_membership_id" not in captured["argument_spec"]
    assert "compartment_id" not in captured["argument_spec"]


def test_domain_id_resolution_and_identity_domains_client(monkeypatch):
    module_obj = load_membership_module(monkeypatch)
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
    instance = make_membership(module_obj, {})
    instance.identity_domain_url = "https://identity.example.com"
    assert instance.client_class.func is module_obj.oci.identity_domains.IdentityDomainsClient


def test_missing_oci_sdk_fails_before_domain_lookup(monkeypatch):
    module_obj = load_membership_module(monkeypatch)
    helper = sys.modules[module_obj.OciIdentityDomainResourceBase.__module__]
    monkeypatch.setattr(helper, "HAS_OCI_SDK", False)
    monkeypatch.setattr(
        helper, "resolve_domain_url", lambda module: pytest.fail("unexpected lookup")
    )
    with pytest.raises(FailJsonCalled) as failure:
        module_obj.OciIdentityUserGroupMembershipModule(DummyModule({"domain_id": "domain1"}))
    assert "oci" in failure.value.payload["msg"]


def test_shared_identity_domain_user_and_tag_contract(monkeypatch):
    module_obj = load_membership_module(monkeypatch)
    helper = sys.modules[module_obj.OciIdentityDomainResourceBase.__module__]
    user = FakeModel(
        display_name="Application User",
        emails=[
            FakeModel(type="home", value="home@example.com", primary=True),
            FakeModel(type="work", value="work@example.com"),
        ],
    )
    serialized = helper.serialize_user(user)
    assert serialized["name"] == "Application User"
    assert serialized["email"] == "work@example.com"

    current = {
        "freeform_tags": {},
        "defined_tags": {
            "Oracle-Tags": {"CreatedBy": "admin"},
            "Operations": {"CostCenter": "42"},
        },
    }
    operations = helper.build_tag_patch_operations(
        {"defined_tags": {"Operations": {"CostCenter": "43"}}}, current
    )
    assert [operation.path for operation in operations] == [
        helper.OCI_TAGS_SCHEMA + ":definedTags"
    ]
    assert {
        (tag.namespace, tag.key): tag.value for tag in operations[0].value
    } == {
        ("Oracle-Tags", "CreatedBy"): "admin",
        ("Operations", "CostCenter"): "43",
    }


def test_composite_lookup_is_idempotent_and_handles_group_404(monkeypatch):
    module_obj = load_membership_module(monkeypatch)
    member = FakeModel(value="user1", membership_ocid="membership1", type="User")
    group = FakeModel(id="group1", members=[member])
    calls = []
    client = types.SimpleNamespace(
        get_group=lambda **kwargs: calls.append(kwargs) or FakeResponse(group)
    )
    instance = make_membership(
        module_obj, {"group_id": "group1", "user_id": "user1"}, client
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    assert instance.resolve_target_resource() is member
    assert calls == [{"group_id": "group1", "attributes": "members"}]

    error = RuntimeError("missing")
    error.status = 404
    client.get_group = raising(error)
    assert instance.resolve_target_resource() is None


def test_existing_membership_has_no_update_operations(monkeypatch):
    module_obj = load_membership_module(monkeypatch)
    member = FakeModel(value="user1")
    instance = make_membership(
        module_obj,
        {"group_id": "group1", "user_id": "user1"},
        types.SimpleNamespace(patch_group=lambda **kwargs: pytest.fail("unexpected patch")),
    )
    assert instance.needs_update(member) is False
    assert instance.update_resource(member) is member


def test_add_and_remove_use_group_scim_patch(monkeypatch):
    module_obj = load_membership_module(monkeypatch)
    calls = []
    member = FakeModel(value="user1", membership_ocid="membership1", type="User")
    client = types.SimpleNamespace(
        patch_group=lambda **kwargs: calls.append(kwargs)
        or FakeResponse(FakeModel(id="group1", members=[member]))
    )
    instance = make_membership(
        module_obj, {"group_id": "group1", "user_id": "user1"}, client
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.create_resource() is member
    add = calls[0]["patch_op"].operations[0]
    assert add.op == "ADD"
    assert add.path == "members"
    assert add.value[0].value == "user1"
    assert add.value[0].type == "User"
    assert calls[0]["patch_op"].schemas == [
        sys.modules[module_obj.OciIdentityDomainResourceBase.__module__].PATCH_SCHEMA
    ]
    assert calls[0]["attributes"] == "members"

    instance.delete_resource(member)
    remove = calls[1]["patch_op"].operations[0]
    assert remove.op == "REMOVE"
    assert remove.path == "members"
    assert remove.value[0].value == "user1"
    assert remove.value[0].type == "User"


def test_check_mode_present_absent_and_output_serialization(monkeypatch):
    module_obj = load_membership_module(monkeypatch)
    instance = make_membership(
        module_obj,
        {"group_id": "group1", "user_id": "user1"},
        check_mode=True,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload == {"changed": True}

    member = FakeModel(
        value="user1",
        membership_ocid="membership1",
        ocid="ocid1.user.example",
        display="Alice",
        type="User",
    )
    instance.check_mode = False
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: member)
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload["changed"] is False
    assert result.value.payload["resource"] == {
        "group_id": "group1",
        "user_id": "user1",
        "membership_ocid": "membership1",
        "user_ocid": "ocid1.user.example",
        "display_name": "Alice",
        "type": "User",
        "date_added": None,
    }

    instance.module.params["state"] = "absent"
    instance.check_mode = True
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload == {"changed": True}

    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)
    instance.check_mode = False
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload == {"changed": False}
