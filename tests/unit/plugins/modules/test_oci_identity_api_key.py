from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import oci.identity_domains
import pytest
from oci.base_client import BaseClient

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


def load_api_key_module(monkeypatch):
    """Load the API key module with the SDK models required by tests.

    Args:
        monkeypatch: Pytest fixture for temporary SDK module installation.

    Returns:
        The imported API key module.
    """
    install_fake_oci(
        monkeypatch,
        model_names=(
            "ApiKey",
            "ApiKeyUser",
            "ExtensionSelfChangeUser",
            "ExtensionOCITags",
            "FreeformTags",
            "DefinedTags",
            "PatchOp",
            "Operations",
        ),
    )
    return load_collection_module("oci_identity_api_key")


def make_api_key(module_obj, params, client=None, check_mode=False):
    """Create an API key module instance for a focused unit test.

    Args:
        module_obj: Imported API key module.
        params: Module parameters for the test case.
        client: Optional fake Identity Domains client.
        check_mode: Whether the module runs in check mode.

    Returns:
        An API key resource module instance.
    """
    return make_module_instance(
        module_obj,
        "OciIdentityApiKeyModule",
        params,
        client=client,
        check_mode=check_mode,
    )


def test_main_defines_api_key_contract(monkeypatch):
    """Verify required domain, user, state, and key arguments.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
    """
    module_obj = load_api_key_module(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        module_obj,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule({}),
    )
    monkeypatch.setattr(
        module_obj,
        "OciIdentityApiKeyModule",
        lambda module: types.SimpleNamespace(execute_resource_module=lambda: None),
    )

    module_obj.main()

    assert captured["required_one_of"] == [["domain_id", "domain_url"]]
    assert captured["mutually_exclusive"] == [["domain_id", "domain_url"]]
    assert captured["supports_check_mode"] is True
    assert captured["argument_spec"]["user_id"]["required"] is True
    assert captured["required_if"] == [
        ["state", "present", ["key"]],
        ["state", "absent", ["fingerprint"]],
    ]
    assert captured["argument_spec"]["key"]["no_log"] is True
    assert captured["argument_spec"]["fingerprint"] == {"type": "str"}
    assert captured["argument_spec"]["state"]["default"] == "present"
    assert "allow_self_change" not in captured["argument_spec"]


def test_create_validates_key_and_user(monkeypatch):
    """Reject a create request when required SCIM inputs are absent.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
    """
    module_obj = load_api_key_module(monkeypatch)
    instance = make_api_key(module_obj, {"user_id": "user1"})

    with pytest.raises(FailJsonCalled) as failure:
        instance.validate_create_request()

    assert "key" in failure.value.payload["msg"]


def test_delete_validates_fingerprint(monkeypatch):
    """Reject an absent-state request when fingerprint is empty.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
    """
    module_obj = load_api_key_module(monkeypatch)
    instance = make_api_key(module_obj, {"user_id": "user1", "fingerprint": " "})

    with pytest.raises(FailJsonCalled) as failure:
        instance.validate_delete_request()

    assert "fingerprint" in failure.value.payload["msg"]


def test_build_filter_escapes_user_and_fingerprint(monkeypatch):
    """Escape quoted SCIM filter values and preserve both filter predicates.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
    """
    module_obj = load_api_key_module(monkeypatch)

    assert module_obj.build_api_key_filter('user"\\1', 'fp"\\2') == (
        'user.value eq "user\\"\\\\1" and fingerprint eq "fp\\"\\\\2"'
    )
    assert module_obj.build_api_key_filter("user1") == 'user.value eq "user1"'


def test_existing_key_matches_public_key_and_user(monkeypatch):
    """Use the public key and user identifiers for idempotent lookup.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
    """
    module_obj = load_api_key_module(monkeypatch)
    key = FakeModel(id="key1", key="PUBLIC", user=FakeModel(value="user1"))
    instance = make_api_key(
        module_obj,
        {"user_id": "user1", "key": "PUBLIC"},
        client=types.SimpleNamespace(list_api_keys=object()),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda method, **kwargs: [key]
        if 'user.value eq "user1"' in kwargs["filter"]
        else [],
    )

    assert instance.resolve_target_resource() is key

    instance.module.params["user_id"] = "other-user"
    assert instance.resolve_target_resource() is None


def test_create_uses_api_key_schema_and_user_model(monkeypatch):
    """Create an API key with the public key and SCIM user model.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
    """
    module_obj = load_api_key_module(monkeypatch)
    calls = []

    def create_api_key(**kwargs):
        """Return a fake create response and record the request.

        Args:
            **kwargs: SDK request arguments.

        Returns:
            A fake OCI response with the created API key.
        """
        calls.append(kwargs)
        return FakeResponse(FakeModel(id="key1", key="PUBLIC"))

    instance = make_api_key(
        module_obj,
        {"user_id": "user1", "key": "PUBLIC"},
        client=types.SimpleNamespace(create_api_key=create_api_key),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    created = instance.create_resource()

    assert created.id == "key1"
    api_key = calls[0]["api_key"]
    assert api_key.schemas == [module_obj.API_KEY_SCHEMA, module_obj.SELF_CHANGE_SCHEMA]
    assert api_key.key == "PUBLIC"
    assert api_key.user.value == "user1"
    extension = api_key.urn_ietf_params_scim_schemas_oracle_idcs_extension_self_change_user
    assert extension.allow_self_change is True
    assert not hasattr(api_key, "fingerprint")


@pytest.mark.parametrize("user_id", ["self-user", "other-user"])
def test_create_serializes_self_change_with_real_sdk(monkeypatch, user_id):
    """Check the SDK payload without changing the requested user."""
    module_obj = load_api_key_module(monkeypatch)
    monkeypatch.setattr(module_obj, "oci", oci)
    calls = []
    instance = make_api_key(
        module_obj,
        {"user_id": user_id, "key": "PUBLIC"},
        client=types.SimpleNamespace(
            create_api_key=lambda **kwargs: calls.append(kwargs) or FakeResponse()
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    instance.create_resource()

    serializer = object.__new__(BaseClient)
    serializer.complex_type_mappings = oci.identity_domains.models.identity_domains_type_mapping
    payload = serializer.sanitize_for_serialization(calls[0]["api_key"])
    assert payload["user"] == {"value": user_id}
    assert payload["key"] == "PUBLIC"
    assert payload[module_obj.SELF_CHANGE_SCHEMA] == {"allowSelfChange": True}
    assert module_obj.SELF_CHANGE_SCHEMA in payload["schemas"]


def test_delete_uses_resource_scim_id(monkeypatch):
    """Delete the selected key with its SCIM identifier.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
    """
    module_obj = load_api_key_module(monkeypatch)
    calls = []
    instance = make_api_key(
        module_obj,
        {"user_id": "user1", "key": "PUBLIC"},
        client=types.SimpleNamespace(
            base_client=types.SimpleNamespace(
                call_api=lambda **kwargs: calls.append(kwargs) or FakeResponse()
            ),
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    instance.delete_resource(FakeModel(id="scim-key-id"))

    assert len(calls) == 1
    request = calls[0]
    assert request["resource_path"] == "/admin/v1/ApiKeys/{apiKeyId}"
    assert request["method"] == "DELETE"
    assert request["path_params"] == {"apiKeyId": "scim-key-id"}
    assert request["query_params"] == {"allowSelfChange": True}
    assert request["operation_name"] == "delete_api_key"
    serializer = object.__new__(BaseClient)
    serializer.complex_type_mappings = oci.identity_domains.models.identity_domains_type_mapping
    assert serializer.process_query_params(request["query_params"]) == {"allowSelfChange": "true"}


@pytest.mark.parametrize("operation", ["create", "delete"])
@pytest.mark.parametrize("status", [401, 403])
def test_self_change_preserves_access_denied_errors(monkeypatch, operation, status):
    """Return access errors without a fallback request."""
    module_obj = load_api_key_module(monkeypatch)
    error = module_obj.oci.exceptions.ServiceError(status, "access denied")
    calls = []

    def deny_access(**kwargs):
        calls.append(kwargs)
        raise error

    instance = make_api_key(
        module_obj,
        {"user_id": "other-user", "key": "PUBLIC"},
        client=types.SimpleNamespace(
            create_api_key=deny_access,
            base_client=types.SimpleNamespace(call_api=deny_access),
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    with pytest.raises(type(error)) as failure:
        if operation == "create":
            instance.create_resource()
        else:
            instance.delete_resource(FakeModel(id="other-user-key"))

    assert failure.value is error
    assert len(calls) == 1


def test_execute_present_check_mode_reports_change_without_create(monkeypatch):
    """Report a missing key as changed in check mode without calling create.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
    """
    module_obj = load_api_key_module(monkeypatch)
    instance = make_api_key(
        module_obj,
        {"user_id": "user1", "key": "PUBLIC", "state": "present"},
        check_mode=True,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)
    instance.create_resource = lambda: pytest.fail("create must not run in check mode")

    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()

    assert result.value.payload["changed"] is True


def test_execute_absent_existing_and_missing_states(monkeypatch):
    """Report deletion only when an API key exists.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
    """
    module_obj = load_api_key_module(monkeypatch)
    params = {"user_id": "user1", "fingerprint": "fp", "state": "absent"}
    instance = make_api_key(module_obj, params)
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: FakeModel(id="key1"))
    monkeypatch.setattr(instance, "delete_resource", lambda resource: None)

    with pytest.raises(ExitJsonCalled) as existing:
        instance.execute_resource_module()
    assert existing.value.payload["changed"] is True

    instance = make_api_key(module_obj, params)
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)
    with pytest.raises(ExitJsonCalled) as missing:
        instance.execute_resource_module()
    assert missing.value.payload["changed"] is False


@pytest.mark.parametrize("state", ["present", "absent"])
@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize("matches", [False, True])
def test_resource_lifecycle_uses_scoped_paginated_lookup(
    monkeypatch, state, check_mode, matches
):
    """Exercise lookup and lifecycle behavior for state and check-mode combinations.

    Args:
        monkeypatch: Pytest fixture for temporary SDK behavior.
        state: Desired API key state.
        check_mode: Whether the lifecycle runs in check mode.
        matches: Whether the selected key exists.
    """
    module_obj = load_api_key_module(monkeypatch)
    target = FakeModel(
        id="target-id",
        key="PUBLIC",
        fingerprint="target-fp",
        user=FakeModel(value="user1"),
    )
    unrelated = FakeModel(
        id="other-id",
        key="OTHER",
        fingerprint="other-fp",
        user=FakeModel(value="user1"),
    )
    first_page = [unrelated]
    second_page = [target] if matches else []
    list_calls = []
    create_calls = []
    delete_calls = []

    def list_api_keys(**kwargs):
        """Return one fake SCIM page for the requested filter.

        Args:
            **kwargs: SCIM list request arguments, including an optional page.

        Returns:
            A fake OCI response containing API-key resources.
        """
        list_calls.append(kwargs)
        if kwargs.get("page"):
            return FakeResponse(FakeModel(resources=second_page))
        return FakeResponse(
            FakeModel(resources=first_page), {"opc-next-page": "page-2"}
        )

    def create_api_key(**kwargs):
        """Record a fake API-key create request.

        Args:
            **kwargs: SDK request arguments.

        Returns:
            A fake OCI response containing the created API key.
        """
        create_calls.append(kwargs)
        return FakeResponse(target)

    def delete_api_key(**kwargs):
        """Record a fake API-key delete request.

        Args:
            **kwargs: SDK request arguments.

        Returns:
            An empty fake OCI response.
        """
        delete_calls.append(kwargs)
        return FakeResponse()

    params = {
        "user_id": "user1",
        "state": state,
        "key": "PUBLIC",
        "fingerprint": "target-fp",
    }
    instance = make_api_key(
        module_obj,
        params,
        client=types.SimpleNamespace(
            list_api_keys=list_api_keys,
            create_api_key=create_api_key,
            base_client=types.SimpleNamespace(call_api=delete_api_key),
        ),
        check_mode=check_mode,
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    expected_changed = (
        (state == "present" and not matches)
        or (state == "absent" and matches)
    )
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()

    assert result.value.payload["changed"] is expected_changed
    assert len(list_calls) == 2
    assert 'user.value eq "user1"' in list_calls[0]["filter"]
    if state == "absent":
        assert 'fingerprint eq "target-fp"' in list_calls[0]["filter"]
    else:
        assert "fingerprint" not in list_calls[0]["filter"]
    if check_mode or not expected_changed:
        assert create_calls == []
        assert delete_calls == []
    elif state == "present":
        assert len(create_calls) == 1
        assert create_calls[0]["api_key"].key == "PUBLIC"
    else:
        assert len(delete_calls) == 1
        assert delete_calls[0]["path_params"] == {"apiKeyId": "target-id"}
        assert delete_calls[0]["query_params"] == {"allowSelfChange": True}


def test_serialize_api_key_result_shape(monkeypatch):
    """Serialize API key fields with SCIM metadata and user identifiers.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
    """
    module_obj = load_api_key_module(monkeypatch)
    resource = FakeModel(
        id="key1",
        ocid="ocid1.key",
        domain_ocid="domain1",
        key="PUBLIC",
        fingerprint="fp",
        user=FakeModel(value="user1", ocid="ocid1.user"),
        meta=FakeModel(created="created", last_modified="modified"),
    )

    assert module_obj.serialize_api_key(resource) == {
        "id": "key1",
        "ocid": "ocid1.key",
        "domain_id": "domain1",
        "user_id": "user1",
        "user_ocid": "ocid1.user",
        "key": "PUBLIC",
        "fingerprint": "fp",
        "time_created": "created",
        "time_modified": "modified",
    }
