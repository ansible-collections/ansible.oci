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


def load_api_key_info_module(monkeypatch):
    """Load the API key info module with the required SDK models.

    Args:
        monkeypatch: Pytest fixture for temporary SDK module installation.

    Returns:
        The imported API key info module.
    """
    install_fake_oci(
        monkeypatch,
        model_names=(
            "ApiKey",
            "ApiKeyUser",
            "ExtensionOCITags",
            "FreeformTags",
            "DefinedTags",
            "PatchOp",
            "Operations",
        ),
    )
    return load_collection_module("oci_identity_api_key_info")


def test_main_defines_info_contract(monkeypatch):
    """Verify domain, user, and optional fingerprint arguments.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
    """
    module_obj = load_api_key_info_module(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        module_obj,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule({}),
    )
    monkeypatch.setattr(
        module_obj,
        "OciIdentityApiKeyInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )

    module_obj.main()

    assert captured["required_one_of"] == [["domain_id", "domain_url"]]
    assert captured["mutually_exclusive"] == [["domain_id", "domain_url"]]
    assert captured["argument_spec"]["user_id"]["required"] is True
    assert captured["argument_spec"]["fingerprint"] == {"type": "str"}


def test_fetch_resources_uses_user_and_optional_fingerprint_filter(monkeypatch):
    """List API keys with the user filter and an optional fingerprint filter.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
    """
    module_obj = load_api_key_info_module(monkeypatch)
    listed = [FakeModel(id="key1")]
    calls = []
    instance = make_module_instance(
        module_obj,
        "OciIdentityApiKeyInfoModule",
        {"user_id": "user1", "fingerprint": "fp"},
        client=types.SimpleNamespace(list_api_keys=object()),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda method, **kwargs: calls.append((method, kwargs)) or listed,
    )

    assert instance.fetch_resources() == listed
    assert calls[0][0] is instance.client.list_api_keys
    assert calls[0][1] == {
        "filter": 'user.value eq "user1" and fingerprint eq "fp"'
    }


def test_fetch_resources_uses_user_filter_without_fingerprint(monkeypatch):
    """List all keys for one user when fingerprint is absent.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
    """
    module_obj = load_api_key_info_module(monkeypatch)
    calls = []
    instance = make_module_instance(
        module_obj,
        "OciIdentityApiKeyInfoModule",
        {"user_id": "user1"},
        client=types.SimpleNamespace(list_api_keys=object()),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda method, **kwargs: calls.append(kwargs) or [],
    )

    assert instance.fetch_resources() == []
    assert calls == [{"filter": 'user.value eq "user1"'}]


def test_execute_info_serializes_full_api_key_shape(monkeypatch):
    """Return serialized API keys in the documented result list.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
    """
    module_obj = load_api_key_info_module(monkeypatch)
    resource = FakeModel(
        id="key1",
        ocid="ocid1.key",
        domain_ocid="domain1",
        key="PUBLIC",
        fingerprint="fp",
        user=FakeModel(value="user1", ocid="ocid1.user"),
        meta=FakeModel(created="created", last_modified="modified"),
    )
    instance = make_module_instance(
        module_obj,
        "OciIdentityApiKeyInfoModule",
        {"user_id": "user1"},
    )
    monkeypatch.setattr(instance, "fetch_resources", lambda: [resource])

    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_info_module()

    assert result.value.payload == {
        "changed": False,
        "api_keys": [module_obj.serialize_api_key(resource)],
    }


def test_execute_info_returns_empty_list(monkeypatch):
    """Return an empty API key list when no key matches the filters.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
    """
    module_obj = load_api_key_info_module(monkeypatch)
    instance = make_module_instance(
        module_obj,
        "OciIdentityApiKeyInfoModule",
        {"user_id": "user1"},
    )
    monkeypatch.setattr(instance, "fetch_resources", lambda: [])

    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_info_module()

    assert result.value.payload == {"changed": False, "api_keys": []}


def test_list_all_resources_follows_scim_pagination(monkeypatch):
    """Collect API keys from all SCIM response pages.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
    """
    module_obj = load_api_key_info_module(monkeypatch)
    responses = iter(
        [
            FakeResponse(FakeModel(resources=["first"]), {"opc-next-page": "page2"}),
            FakeResponse(FakeModel(resources=["second"])),
        ]
    )
    calls = []
    instance = make_module_instance(module_obj, "OciIdentityApiKeyInfoModule", {})
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda method, **kwargs: calls.append(kwargs) or next(responses),
    )

    assert instance.list_all_resources(object()) == ["first", "second"]
    assert calls == [{}, {"page": "page2"}]


def test_fetch_resources_propagates_non_404_sdk_error(monkeypatch):
    """Propagate a non-404 SDK error from the API key list operation.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
    """
    module_obj = load_api_key_info_module(monkeypatch)
    service_error = __import__("oci").exceptions.ServiceError(500, "server error")
    instance = make_module_instance(
        module_obj,
        "OciIdentityApiKeyInfoModule",
        {"user_id": "user1"},
        client=types.SimpleNamespace(list_api_keys=object()),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        raising(service_error),
    )

    with pytest.raises(type(service_error)) as failure:
        instance.fetch_resources()

    assert failure.value.status == 500
