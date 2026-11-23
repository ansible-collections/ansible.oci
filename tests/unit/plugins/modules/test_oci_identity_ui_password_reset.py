from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types
import sys

import pytest
from ansible.module_utils.common.arg_spec import ModuleArgumentSpecValidator

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


def load_password_module(monkeypatch):
    """Load the password module with a fake OCI SDK.

    Args:
        monkeypatch: Pytest fixture for temporary SDK installation.

    Returns:
        The imported password module.
    """
    install_fake_oci(monkeypatch)
    return load_collection_module("oci_identity_ui_password_reset")


def make_password(module_obj, params, client=None, check_mode=False):
    """Create a password module instance for a focused test.

    Args:
        module_obj: Imported password module.
        params: Module parameters for the test case.
        client: Optional fake OCI client.
        check_mode: Whether the module runs in check mode.

    Returns:
        A password resource module instance.
    """
    return make_module_instance(
        module_obj,
        "OciIdentityUiPasswordResetModule",
        params,
        client=client,
        check_mode=check_mode,
    )


def test_main_defines_reset_contract(monkeypatch):
    """Verify the required user argument and check mode support.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
    """
    module_obj = load_password_module(monkeypatch)
    captured = {}
    module = DummyModule({"user_id": "user.ocid"})
    module.no_log = True
    monkeypatch.setattr(
        module_obj,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or module,
    )
    monkeypatch.setattr(
        module_obj,
        "OciIdentityUiPasswordResetModule",
        lambda active_module: types.SimpleNamespace(
            reset_password=lambda: FakeResponse(FakeModel(password="generated")),
            serialize_result_resource=lambda resource: resource.__dict__,
        ),
    )

    with pytest.raises(ExitJsonCalled):
        module_obj.main()

    spec = captured["argument_spec"]
    assert spec["user_id"]["required"] is True
    assert captured["supports_check_mode"] is True
    assert "state" not in spec
    assert "action" not in spec
    validator = ModuleArgumentSpecValidator(spec)
    assert validator.validate({"user_id": "user.ocid"}).errors.errors == []
    assert validator.validate({"user_id": "user.ocid", "action": "reset"}).errors.errors
    assert validator.validate({}).errors.errors


@pytest.mark.parametrize("no_log", [False, True])
@pytest.mark.parametrize("password", ["generated-secret", None])
def test_reset_calls_sdk_directly_and_preserves_password(monkeypatch, password, no_log):
    """Call the SDK once per reset and return its password field.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
        password: Password value returned by the fake SDK.
        no_log: Whether task output is protected.
    """
    module_obj = load_password_module(monkeypatch)
    calls = []

    def reset(**kwargs):
        """Record the SDK request and return a password response.

        Args:
            **kwargs: SDK request arguments.

        Returns:
            A fake OCI response with a generated password.
        """
        calls.append(kwargs)
        return FakeResponse(FakeModel(password=password))

    client = types.SimpleNamespace(create_or_reset_ui_password=reset)
    module = DummyModule({"user_id": "user.ocid"})
    module.no_log = no_log
    monkeypatch.setattr(module_obj, "AnsibleModule", lambda **kwargs: module)

    instance = make_password(module_obj, module.params, client=client)
    instance.module = module
    monkeypatch.setattr(module_obj, "OciIdentityUiPasswordResetModule", lambda active: instance)

    for _attempt in range(2):
        with pytest.raises(ExitJsonCalled) as result:
            module_obj.main()
        assert result.value.payload["changed"] is True
        assert result.value.payload["action"] == "reset"
        assert result.value.payload["resource"]["password"] == password

    assert calls == [
        {
            "user_id": "user.ocid",
            "retry_strategy": module_obj.oci.retry.DEFAULT_RETRY_STRATEGY,
        },
        {
            "user_id": "user.ocid",
            "retry_strategy": module_obj.oci.retry.DEFAULT_RETRY_STRATEGY,
        },
    ]


@pytest.mark.parametrize("no_log", [False, True])
def test_check_mode_does_not_call_sdk_and_returns_changed(monkeypatch, no_log):
    """Report a reset in check mode without an SDK call.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
        no_log: Whether task output is protected.
    """
    module_obj = load_password_module(monkeypatch)
    module = DummyModule({"user_id": "user.ocid"}, check_mode=True)
    module.no_log = no_log
    monkeypatch.setattr(module_obj, "AnsibleModule", lambda **kwargs: module)

    with pytest.raises(ExitJsonCalled) as result:
        module_obj.main()

    assert result.value.payload == {"changed": True, "action": "reset"}


@pytest.mark.parametrize(
    ("status", "code"),
    [
        pytest.param(400, "InvalidParameter", id="400-invalid-parameter"),
        pytest.param(403, "NotAuthorized", id="403-not-authorized"),
        pytest.param(404, "NotAuthorizedOrNotFound", id="404-not-found"),
        pytest.param(500, "InternalError", id="500-internal-error"),
    ],
)
def test_service_error_includes_safe_diagnostics_only(monkeypatch, status, code):
    """Return safe OCI diagnostics without secret response data.

    Args:
        monkeypatch: Pytest fixture for temporary SDK installation.
        status: OCI HTTP status code.
        code: OCI service error code.
    """
    module_obj = load_password_module(monkeypatch)
    module = DummyModule({"user_id": "user.ocid"})
    module.no_log = False
    monkeypatch.setattr(module_obj, "AnsibleModule", lambda **kwargs: module)
    service_error = module_obj.oci.exceptions.ServiceError(
        status, "request failed with generated-secret"
    )
    service_error.message = "failed with generated-secret"
    service_error.code = code
    service_error.request_id = "request-123"
    service_error.body = {"message": "body generated-secret"}
    service_error.headers = {"opc-request-id": "header generated-secret"}
    client = types.SimpleNamespace(create_or_reset_ui_password=raising(service_error))

    instance = make_password(module_obj, module.params, client=client)
    instance.module = module
    monkeypatch.setattr(module_obj, "OciIdentityUiPasswordResetModule", lambda active: instance)

    active_exception = []

    def fail_json(**kwargs):
        """Capture the safe error payload and active exception state.

        Args:
            **kwargs: Error payload fields.

        Raises:
            FailJsonCalled: Always, with the error payload.
        """
        active_exception.append(sys.exc_info()[1])
        raise FailJsonCalled(kwargs)

    monkeypatch.setattr(module, "fail_json", fail_json)

    with pytest.raises(FailJsonCalled) as failure:
        module_obj.main()

    assert failure.value.payload == {
        "msg": "Failed to reset the user's console password",
        "status": status,
        "code": code,
        "request_id": "request-123",
    }
    assert active_exception == [None]
    assert "generated-secret" not in str(failure.value.payload)
    assert "headers" not in failure.value.payload
    assert "body" not in failure.value.payload


def test_generic_error_returns_fixed_message_only(monkeypatch):
    """Return a fixed failure message for a generic SDK error.

    Args:
        monkeypatch: Pytest fixture for temporary SDK installation.
    """
    module_obj = load_password_module(monkeypatch)
    module = DummyModule({"user_id": "user.ocid"})
    module.no_log = False
    monkeypatch.setattr(module_obj, "AnsibleModule", lambda **kwargs: module)
    error = RuntimeError("request failed with generated-secret")
    client = types.SimpleNamespace(create_or_reset_ui_password=raising(error))
    instance = make_password(module_obj, module.params, client=client)
    instance.module = module
    monkeypatch.setattr(module_obj, "OciIdentityUiPasswordResetModule", lambda active: instance)

    active_exception = []

    def fail_json(**kwargs):
        """Capture the generic error payload and active exception state.

        Args:
            **kwargs: Error payload fields.

        Raises:
            FailJsonCalled: Always, with the error payload.
        """
        active_exception.append(sys.exc_info()[1])
        raise FailJsonCalled(kwargs)

    monkeypatch.setattr(module, "fail_json", fail_json)

    with pytest.raises(FailJsonCalled) as failure:
        module_obj.main()

    assert failure.value.payload == {
        "msg": "Failed to reset the user's console password"
    }
    assert active_exception == [None]
    assert "generated-secret" not in str(failure.value.payload)
