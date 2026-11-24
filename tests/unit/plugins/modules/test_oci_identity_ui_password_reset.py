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
    install_fake_oci(monkeypatch, model_names=("UserPasswordResetter",))
    helper_name = (
        "ansible_collections.ansible.oci.plugins.module_utils.oci_identity_domains"
    )
    monkeypatch.setitem(sys.modules, helper_name, sys.modules.get(helper_name))
    sys.modules.pop(helper_name, None)
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
        "OciIdentityDomainUiPasswordResetModule",
        params,
        client=client,
        check_mode=check_mode,
        identity_domain_id=params.get("domain_id"),
    )


def make_domain_password(module_obj, params, client):
    """Create a domain reset helper without client construction."""
    instance = object.__new__(module_obj.OciIdentityDomainUiPasswordResetModule)
    instance.module = DummyModule(params)
    instance.client = client
    instance.identity_domain_id = params.get("domain_id", "domain-id")
    instance.identity_domain_url = params.get("domain_url", "https://identity.example.com")
    return instance


def test_main_defines_reset_contract(monkeypatch):
    """Verify the required user argument and check mode support.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
    """
    module_obj = load_password_module(monkeypatch)
    captured = {}
    module = DummyModule({"user_id": "SCIM-ID", "domain_url": "https://idcs.example.com"})
    module.no_log = True
    monkeypatch.setattr(
        module_obj,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or module,
    )
    user = FakeModel(
        id="SCIM-ID", ocid="user-ocid", user_name="alice", domain_ocid="domain-id"
    )
    monkeypatch.setattr(
        module_obj,
        "OciIdentityDomainUiPasswordResetModule",
        lambda active_module: types.SimpleNamespace(
            identity_domain_id="domain-id",
            find_user=lambda: user,
            reset_password=lambda active_user: FakeResponse(
                FakeModel(one_time_password="generated")
            ),
        ),
    )

    with pytest.raises(ExitJsonCalled) as result:
        module_obj.main()
    assert result.value.payload["changed"] is True
    assert result.value.payload["resource"]["user_id"] == "SCIM-ID"
    assert result.value.payload["resource"]["password"] == "generated"

    spec = captured["argument_spec"]
    for name in ("user_id", "user_ocid", "user_name"):
        assert spec[name]["type"] == "str"
    for name in ("domain_id", "domain_url", "domain_name", "compartment_id"):
        assert name in spec
    assert "aliases" not in spec["domain_id"]
    assert captured["supports_check_mode"] is True
    assert "state" not in spec
    assert "action" not in spec
    validator = ModuleArgumentSpecValidator(
        spec,
        required_one_of=captured["required_one_of"],
        mutually_exclusive=captured["mutually_exclusive"],
    )
    assert captured["required_one_of"] == [["user_id", "user_ocid", "user_name"]]
    for name, value in (("user_id", "SCIM-ID"), ("user_ocid", "ocid1.user.oc1..x"), ("user_name", "alice")):
        assert validator.validate({name: value}).errors.errors == []
    assert validator.validate({}).errors.errors
    assert validator.validate({"user_id": "SCIM-ID", "user_name": "alice"}).errors.errors
    assert validator.validate(
        {"user_id": "SCIM-ID", "domain_id": "d", "domain_url": "https://idcs"}
    ).errors.errors
    assert validator.validate({"user_id": "user.ocid", "action": "reset"}).errors.errors
    assert validator.validate({}).errors.errors


@pytest.mark.parametrize("no_log", [False, True])
@pytest.mark.parametrize("password", ["generated-secret", None])
def test_reset_calls_sdk_directly_and_preserves_password(monkeypatch, password, no_log):
    """Submit two domain resets and return a supplied temporary password.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
        password: Password value returned by the fake SDK.
        no_log: Whether task output is protected.
    """
    module_obj = load_password_module(monkeypatch)
    calls = []

    def get_user(**kwargs):
        """Return the selected SCIM user."""
        calls.append(("get_user", kwargs))
        return FakeResponse(
            FakeModel(
                id="SCIM-ID",
                ocid="user-ocid",
                user_name="alice",
                domain_ocid="domain-id",
            )
        )

    def reset(**kwargs):
        """Record the SCIM reset request and return a password response.

        Args:
            **kwargs: SDK request arguments.

        Returns:
            A fake OCI response with a generated password.
        """
        calls.append(("reset", kwargs))
        return FakeResponse(FakeModel(one_time_password=password))

    client = types.SimpleNamespace(get_user=get_user, put_user_password_resetter=reset)
    module = DummyModule({"user_id": "SCIM-ID", "domain_id": "domain-id"})
    module.no_log = no_log
    monkeypatch.setattr(module_obj, "AnsibleModule", lambda **kwargs: module)

    instance = make_password(module_obj, module.params, client=client)
    instance.module = module
    monkeypatch.setattr(
        module_obj, "OciIdentityDomainUiPasswordResetModule", lambda active: instance
    )

    for _attempt in range(2):
        with pytest.raises(ExitJsonCalled) as result:
            module_obj.main()
        assert result.value.payload["changed"] is True
        assert result.value.payload["action"] == "reset"
        if password is None:
            assert "password" not in result.value.payload["resource"]
        else:
            assert result.value.payload["resource"]["password"] == password

    assert [name for name, kwargs in calls] == ["get_user", "reset", "get_user", "reset"]
    reset_calls = [kwargs for name, kwargs in calls if name == "reset"]
    assert len(reset_calls) == 2
    for request in reset_calls:
        assert request["user_password_resetter_id"] == "SCIM-ID"
        assert request["retry_strategy"] is module_obj.oci.retry.DEFAULT_RETRY_STRATEGY
        assert request["user_password_resetter"].schemas == [
            "urn:ietf:params:scim:schemas:oracle:idcs:UserPasswordResetter"
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
    module = DummyModule({"user_id": "SCIM-ID"})
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
    instance = types.SimpleNamespace(
        identity_domain_id="domain-id",
        find_user=lambda: FakeModel(id="SCIM-ID"),
        reset_password=raising(service_error),
    )
    monkeypatch.setattr(
        module_obj, "OciIdentityDomainUiPasswordResetModule", lambda active: instance
    )

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
        "msg": "Failed to reset the identity-domain user's password",
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
    module = DummyModule({"user_id": "SCIM-ID"})
    module.no_log = False
    monkeypatch.setattr(module_obj, "AnsibleModule", lambda **kwargs: module)
    error = RuntimeError("request failed with generated-secret")
    instance = types.SimpleNamespace(
        find_user=lambda: FakeModel(id="SCIM-ID"),
        reset_password=raising(error),
    )
    monkeypatch.setattr(
        module_obj, "OciIdentityDomainUiPasswordResetModule", lambda active: instance
    )

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
        "msg": "Failed to reset the identity-domain user's password"
    }
    assert active_exception == [None]
    assert "generated-secret" not in str(failure.value.payload)


@pytest.mark.parametrize(
    ("password", "include_password"),
    [
        pytest.param("temporary-secret", True, id="password-present"),
        pytest.param(None, True, id="password-null"),
        pytest.param(None, False, id="password-omitted"),
    ],
)
def test_domain_reset_serializer_returns_selected_ids_and_optional_password(
    monkeypatch, password, include_password
):
    """Return selected user IDs and include only a supplied password."""
    load_password_module(monkeypatch)
    helper = sys.modules[
        "ansible_collections.ansible.oci.plugins.module_utils.oci_identity_domains"
    ]
    user = FakeModel(
        id="SCIM-ID",
        ocid="user-ocid",
        user_name="alice",
        domain_ocid="domain-id",
        profile=FakeModel(email="private@example.com"),
        password="private-password",
    )
    response = FakeModel(user_token="private-token")
    if include_password:
        response.one_time_password = password

    result = helper.serialize_identity_domain_password_reset(user, response)

    expected = {
        "user_id": "SCIM-ID",
        "user_ocid": "user-ocid",
        "user_name": "alice",
        "domain_id": "domain-id",
    }
    if password is not None:
        expected["password"] = password
    assert result == expected
    assert "private" not in str(result)
