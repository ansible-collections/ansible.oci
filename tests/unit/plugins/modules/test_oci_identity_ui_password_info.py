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


def load_password_info_module(monkeypatch):
    """Load the password info module with a fake OCI SDK.

    Args:
        monkeypatch: Pytest fixture for temporary SDK installation.

    Returns:
        The imported password info module.
    """
    install_fake_oci(monkeypatch)
    return load_collection_module("oci_identity_ui_password_info")


def make_password_info(module_obj, params, client=None, check_mode=False):
    """Create a password info instance for a focused test.

    Args:
        module_obj: Imported password info module.
        params: Module parameters for the test case.
        client: Optional fake OCI client.
        check_mode: Whether the module runs in check mode.

    Returns:
        A password info module instance.
    """
    return make_module_instance(
        module_obj,
        "OciIdentityUiPasswordInfoModule",
        params,
        client=client,
        check_mode=check_mode,
    )


def test_main_defines_info_contract(monkeypatch):
    """Verify the required user identifier and check mode support.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
    """
    module_obj = load_password_info_module(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        module_obj,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule({}),
    )
    monkeypatch.setattr(
        module_obj,
        "OciIdentityUiPasswordInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )

    module_obj.main()

    assert captured["argument_spec"]["user_id"]["required"] is True
    assert captured["supports_check_mode"] is True


def test_fetch_uses_user_getter_and_serializes_metadata(monkeypatch):
    """Get one password record by the user's OCID.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
    """
    module_obj = load_password_info_module(monkeypatch)
    resource = FakeModel(
        user_id="user.ocid", time_created="2026-01-02T03:04:05Z", lifecycle_state="ACTIVE"
    )
    calls = []
    client = types.SimpleNamespace(
        get_user_ui_password_information=object(),
    )
    instance = make_password_info(
        module_obj, {"user_id": "user.ocid"}, client=client
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda method, **kwargs: calls.append((method, kwargs))
        or FakeResponse(resource),
    )

    assert instance.fetch_resources() == [resource]
    assert calls == [
        (client.get_user_ui_password_information, {"user_id": "user.ocid"})
    ]
    assert instance.serialize_result_resource(resource) == {
        "user_id": "user.ocid",
        "time_created": "2026-01-02T03:04:05Z",
        "lifecycle_state": "ACTIVE",
    }


@pytest.mark.parametrize("check_mode", [False, True])
def test_execute_info_serializes_password_information(monkeypatch, check_mode):
    """Return the user's password information fields.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
        check_mode: Whether the module runs in check mode.
    """
    module_obj = load_password_info_module(monkeypatch)
    resource = FakeModel(user_id="user.ocid", time_created=None, lifecycle_state="ACTIVE")
    instance = make_password_info(
        module_obj, {"user_id": "user.ocid"}, check_mode=check_mode
    )
    monkeypatch.setattr(instance, "fetch_resources", lambda: [resource])

    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_info_module()

    assert result.value.payload == {
        "changed": False,
        "ui_passwords": [
            {"user_id": "user.ocid", "time_created": None, "lifecycle_state": "ACTIVE"}
        ],
    }


def test_fetch_returns_empty_list_for_404(monkeypatch):
    """Return an empty list when OCI has no password record for the user.

    Args:
        monkeypatch: Pytest fixture for temporary SDK installation.
    """
    module_obj = load_password_info_module(monkeypatch)
    error = module_obj.oci.exceptions.ServiceError(404, "missing")
    instance = make_password_info(
        module_obj,
        {"user_id": "user.ocid"},
        client=types.SimpleNamespace(get_user_ui_password_information=object()),
    )
    monkeypatch.setattr(instance, "call_with_retry", raising(error))

    assert instance.fetch_resources() == []


def test_fetch_propagates_non_404_errors(monkeypatch):
    """Propagate an OCI error when the status is not 404.

    Args:
        monkeypatch: Pytest fixture for temporary SDK installation.
    """
    module_obj = load_password_info_module(monkeypatch)
    error = module_obj.oci.exceptions.ServiceError(500, "server error")
    instance = make_password_info(
        module_obj,
        {"user_id": "user.ocid"},
        client=types.SimpleNamespace(get_user_ui_password_information=object()),
    )
    monkeypatch.setattr(instance, "call_with_retry", raising(error))

    with pytest.raises(type(error)):
        instance.fetch_resources()
