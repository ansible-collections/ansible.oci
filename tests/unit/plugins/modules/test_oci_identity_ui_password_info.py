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


IDENTITY_DOMAINS_HELPER = (
    "ansible_collections.ansible.oci.plugins.module_utils.oci_identity_domains"
)


def get_identity_domains_helper():
    """Return the shared Identity Domains helper loaded by the module."""
    return sys.modules[IDENTITY_DOMAINS_HELPER]


def load_identity_domains_helper(monkeypatch):
    """Load the password module and return its shared helper."""
    load_password_info_module(monkeypatch)
    return get_identity_domains_helper()


def load_password_info_module(monkeypatch):
    """Load the password info module with a fake OCI SDK.

    Args:
        monkeypatch: Pytest fixture for temporary SDK installation.

    Returns:
        The imported password info module.
    """
    install_fake_oci(monkeypatch, model_names=("UserPasswordResetter",))
    helper_name = (
        "ansible_collections.ansible.oci.plugins.module_utils.oci_identity_domains"
    )
    monkeypatch.setitem(sys.modules, helper_name, sys.modules.get(helper_name))
    sys.modules.pop(helper_name, None)
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
    instance = make_module_instance(
        module_obj,
        "OciIdentityUiPasswordInfoModule",
        params,
        client=client,
        check_mode=check_mode,
    )
    instance.identity_domain_id = params.get("domain_id", "domain-id")
    instance.identity_domain_url = params.get("domain_url", "https://identity.example.com")
    return instance


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
        lambda **kwargs: captured.update(kwargs)
        or DummyModule({"user_id": "SCIM-ID", "domain_url": "https://idcs.example.com"}),
    )
    monkeypatch.setattr(
        module_obj,
        "OciIdentityUiPasswordInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
        raising=False,
    )

    module_obj.main()

    spec = captured["argument_spec"]
    for name in ("user_id", "user_ocid", "user_name"):
        assert spec[name]["type"] == "str"
    for name in ("domain_id", "domain_url", "domain_name", "compartment_id"):
        assert name in spec
    assert "aliases" not in spec["domain_id"]
    assert captured["supports_check_mode"] is True
    assert captured["required_one_of"] == [["user_id", "user_ocid", "user_name"]]
    validator = ModuleArgumentSpecValidator(
        spec,
        required_one_of=captured["required_one_of"],
        mutually_exclusive=captured["mutually_exclusive"],
    )
    for name, value in (("user_id", "SCIM-ID"), ("user_ocid", "ocid1.user.oc1..x"), ("user_name", "alice")):
        assert validator.validate({name: value}).errors.errors == []
    assert validator.validate({}).errors.errors
    assert validator.validate({"user_id": "SCIM-ID", "user_name": "alice"}).errors.errors
    assert validator.validate(
        {"user_id": "SCIM-ID", "domain_id": "d", "domain_url": "https://idcs"}
    ).errors.errors


def test_main_reads_password_state_in_check_mode(monkeypatch):
    """Run the info lookup in check mode."""
    module_obj = load_password_info_module(monkeypatch)
    module = DummyModule({"user_id": "SCIM-ID"}, check_mode=True)
    calls = []
    monkeypatch.setattr(module_obj, "AnsibleModule", lambda **kwargs: module)
    monkeypatch.setattr(
        module_obj,
        "OciIdentityUiPasswordInfoModule",
        lambda active: types.SimpleNamespace(
            execute_info_module=lambda: calls.append("read")
        ),
    )

    module_obj.main()

    assert calls == ["read"]


@pytest.mark.parametrize("error_kind", ["service", "generic", "constructor"])
def test_main_reports_safe_errors_without_active_exception(monkeypatch, error_kind):
    """Return safe error fields and clear exception context before failure."""
    module_obj = load_password_info_module(monkeypatch)
    module = DummyModule({"user_id": "SCIM-ID"})
    error = RuntimeError("request failed with generated-secret")
    service_error = module_obj.oci.exceptions.ServiceError(
        500, "request failed with generated-secret"
    )
    service_error.code = "InternalError"
    service_error.request_id = "request-123"
    service_error.body = {"message": "generated-secret"}
    captured_exception = []
    monkeypatch.setattr(module_obj, "AnsibleModule", lambda **kwargs: module)
    if error_kind == "service":
        monkeypatch.setattr(
            module_obj,
            "OciIdentityUiPasswordInfoModule",
            lambda active: types.SimpleNamespace(execute_info_module=raising(service_error)),
        )
    elif error_kind == "generic":
        monkeypatch.setattr(
            module_obj,
            "OciIdentityUiPasswordInfoModule",
            lambda active: types.SimpleNamespace(execute_info_module=raising(error)),
        )
    else:
        monkeypatch.setattr(
            module_obj, "OciIdentityUiPasswordInfoModule", raising(error)
        )

    def fail_json(**kwargs):
        """Capture the failure payload and active exception."""
        captured_exception.append(sys.exc_info()[1])
        raise FailJsonCalled(kwargs)

    monkeypatch.setattr(module, "fail_json", fail_json)

    with pytest.raises(FailJsonCalled) as failure:
        module_obj.main()

    assert captured_exception == [None]
    if error_kind == "service":
        assert failure.value.payload == {
            "msg": "Failed to get identity-domain password information",
            "status": 500,
            "code": "InternalError",
            "request_id": "request-123",
        }
    else:
        assert failure.value.payload == {
            "msg": "Failed to get identity-domain password information"
        }
    assert "generated-secret" not in str(failure.value.payload)


def test_fetch_uses_user_getter_and_serializes_metadata(monkeypatch):
    """Get one SCIM user and serialize selected password state.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
    """
    module_obj = load_password_info_module(monkeypatch)
    resource = FakeModel(
        id="SCIM-ID",
        ocid="user.ocid",
        user_name="alice",
        domain_ocid="domain-id",
        urn_ietf_params_scim_schemas_oracle_idcs_extension_password_state_user=FakeModel(
            cant_change=False,
            cant_expire=False,
            must_change=True,
            expired=False,
            last_successful_set_date="2026-01-02T03:04:05Z",
        ),
    )
    calls = []

    def get_user(**kwargs):
        """Record a SCIM user request and return one user."""
        calls.append(kwargs)
        return FakeResponse(resource)

    client = types.SimpleNamespace(get_user=get_user)
    instance = make_password_info(module_obj, {"user_id": "SCIM-ID"}, client=client)

    assert instance.fetch_resources() == [resource]
    assert calls == [{
        "user_id": "SCIM-ID",
        "attributes": "id,ocid,userName,domainOcid,urn:ietf:params:scim:schemas:oracle:idcs:extension:passwordState:User",
        "attribute_sets": ["default"],
    }]
    assert instance.serialize_result_resource(resource) == {
        "user_id": "SCIM-ID",
        "user_ocid": "user.ocid",
        "user_name": "alice",
        "domain_id": "domain-id",
        "password_state": {
            "cant_change": False,
            "cant_expire": False,
            "must_change": True,
            "expired": False,
            "last_successful_set_date": "2026-01-02T03:04:05Z",
        },
    }


@pytest.mark.parametrize("check_mode", [False, True])
def test_execute_info_serializes_password_information(monkeypatch, check_mode):
    """Return the user's password information fields.

    Args:
        monkeypatch: Pytest fixture for temporary changes.
        check_mode: Whether the module runs in check mode.
    """
    module_obj = load_password_info_module(monkeypatch)
    resource = FakeModel(id="SCIM-ID", ocid="user.ocid", user_name="alice")
    instance = make_password_info(
        module_obj, {"user_id": "SCIM-ID"}, check_mode=check_mode
    )
    monkeypatch.setattr(instance, "fetch_resources", lambda: [resource])

    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_info_module()

    assert result.value.payload == {
        "changed": False,
        "ui_passwords": [
            {
                "user_id": "SCIM-ID",
                "user_ocid": "user.ocid",
                "user_name": "alice",
                "domain_id": "domain-id",
                "password_state": {},
            }
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
        {"user_id": "SCIM-ID"},
        client=types.SimpleNamespace(get_user=raising(error)),
    )

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
        {"user_id": "SCIM-ID"},
        client=types.SimpleNamespace(get_user=raising(error)),
    )

    with pytest.raises(type(error)):
        instance.fetch_resources()


def test_resolve_domain_id_and_domain_url(monkeypatch):
    """Resolve a domain OCID and use a supplied domain URL."""
    helper = load_identity_domains_helper(monkeypatch)
    calls = []
    identity_client = types.SimpleNamespace(
        get_domain=lambda **kwargs: calls.append(kwargs)
        or FakeResponse(FakeModel(id="domain-id", url="https://identity.example.com/"))
    )
    monkeypatch.setattr(
        helper, "create_service_client", lambda module, client_class: identity_client
    )

    assert helper.resolve_identity_domain(DummyModule({"domain_id": "domain-id"})) == (
        "domain-id",
        "https://identity.example.com",
    )
    assert calls == [{"domain_id": "domain-id"}]
    assert helper.resolve_identity_domain(
        DummyModule({"domain_url": "https://direct.example.com/"})
    ) == (None, "https://direct.example.com")
    assert calls == [{"domain_id": "domain-id"}]


def test_resolve_default_domain_uses_compartment_and_pages(monkeypatch):
    """Resolve the Default domain by name in the selected compartment."""
    helper = load_identity_domains_helper(monkeypatch)
    calls = []
    domain = FakeModel(
        id="default-domain-id", display_name="Default", url="https://identity.example.com/"
    )
    identity_client = types.SimpleNamespace(list_domains=object())
    monkeypatch.setattr(
        helper.oci,
        "pagination",
        types.SimpleNamespace(
            list_call_get_all_results=lambda method, **kwargs: calls.append(
                (method, kwargs)
            ) or FakeResponse([domain])
        ),
        raising=False,
    )
    monkeypatch.setattr(
        helper, "create_service_client", lambda module, client_class: identity_client
    )

    assert helper.resolve_identity_domain(
        DummyModule({"domain_name": "Default", "compartment_id": "compartment-id"})
    ) == ("default-domain-id", "https://identity.example.com")
    assert calls == [
        (
            identity_client.list_domains,
            {
                "compartment_id": "compartment-id",
                "name": "Default",
                "limit": 1000,
                "retry_strategy": helper.oci.retry.DEFAULT_RETRY_STRATEGY,
            },
        )
    ]


def test_resolve_default_domain_uses_configured_tenancy(monkeypatch):
    """Use the configured tenancy when no compartment is set."""
    helper = load_identity_domains_helper(monkeypatch)
    calls = []
    domain = FakeModel(id="default-domain-id", display_name="Default", url="https://idcs")
    identity_client = types.SimpleNamespace(list_domains=object())
    monkeypatch.setattr(
        helper.oci,
        "pagination",
        types.SimpleNamespace(
            list_call_get_all_results=lambda method, **kwargs: calls.append(kwargs)
            or FakeResponse([domain])
        ),
        raising=False,
    )
    monkeypatch.setattr(
        helper, "create_service_client", lambda module, client_class: identity_client
    )
    monkeypatch.setattr(helper, "get_oci_config", lambda module: {"tenancy": "tenancy-id"})

    assert helper.resolve_identity_domain(DummyModule({"domain_name": "Default"})) == (
        "default-domain-id",
        "https://idcs",
    )
    assert calls[0]["compartment_id"] == "tenancy-id"
    assert calls[0]["name"] == "Default"


def test_default_domain_requires_compartment_or_configured_tenancy(monkeypatch):
    """Fail when the default domain lookup has no compartment."""
    helper = load_identity_domains_helper(monkeypatch)
    monkeypatch.setattr(
        helper, "create_service_client", lambda module, client_class: types.SimpleNamespace()
    )
    monkeypatch.setattr(helper, "get_oci_config", lambda module: {})

    with pytest.raises(helper.IdentityDomainConfigurationError, match="compartment_id"):
        helper.resolve_identity_domain(DummyModule({"domain_name": ""}))


def test_domain_name_lookup_rejects_ambiguous_names(monkeypatch):
    """Fail when multiple domains have the same exact name."""
    helper = load_identity_domains_helper(monkeypatch)
    identity_client = types.SimpleNamespace(list_domains=object())
    domains = [
        FakeModel(id="one", display_name="Finance", url="https://one"),
        FakeModel(id="two", display_name="Finance", url="https://two"),
    ]
    monkeypatch.setattr(
        helper.oci,
        "pagination",
        types.SimpleNamespace(
            list_call_get_all_results=lambda method, **kwargs: FakeResponse(domains)
        ),
        raising=False,
    )
    monkeypatch.setattr(
        helper, "create_service_client", lambda module, client_class: identity_client
    )

    with pytest.raises(helper.IdentityDomainConfigurationError, match="exactly one"):
        helper.resolve_identity_domain(
            DummyModule({"domain_name": "Finance", "compartment_id": "compartment-id"})
        )


@pytest.mark.parametrize(
    ("selector", "value", "filter_text"),
    [
        pytest.param("user_ocid", "ocid1.user.oc1..abc", 'ocid eq "ocid1.user.oc1..abc"', id="ocid"),
    ],
)
def test_find_user_by_ocid_or_name_uses_paged_scim_filter(
    monkeypatch, selector, value, filter_text
):
    """Find an OCID or login with an escaped SCIM filter across pages."""
    helper = load_identity_domains_helper(monkeypatch)
    user = FakeModel(id="scim-id", ocid="ocid1.user.oc1..abc", user_name='Alice"Ops')
    calls = []

    def list_users(**kwargs):
        """Return two partial pages with the selected user on the second page."""
        calls.append(kwargs)
        page_user = (
            user
            if kwargs.get("start_index") == 2
            else FakeModel(id="other", ocid="other-ocid", user_name="other")
        )
        return FakeResponse(
            FakeModel(
                resources=[page_user],
                start_index=kwargs.get("start_index"),
                items_per_page=1,
                total_results=2,
            )
        )

    client = types.SimpleNamespace(list_users=list_users)
    result = helper.find_identity_domain_user(
        DummyModule({selector: value}), client, attributes="id,ocid,userName"
    )

    assert result is user
    assert len(calls) == 2
    assert calls[0] == {
        "filter": filter_text,
        "count": 1000,
        "retry_strategy": helper.oci.retry.DEFAULT_RETRY_STRATEGY,
        "attributes": "id,ocid,userName",
        "attribute_sets": ["default"],
        "start_index": 1,
    }
    assert calls[1]["start_index"] == 2


def test_find_user_name_uses_escaped_filter(monkeypatch):
    """Escape a quote in a user name SCIM filter."""
    helper = load_identity_domains_helper(monkeypatch)
    user = FakeModel(id="SCIM-ID", user_name='Alice"Ops')
    calls = []
    client = types.SimpleNamespace(
        list_users=lambda **kwargs: calls.append(kwargs)
        or FakeResponse(FakeModel(resources=[user], start_index=1, items_per_page=1, total_results=1))
    )

    assert helper.find_identity_domain_user(
        DummyModule({"user_name": 'Alice"Ops'}), client
    ) is user
    assert calls[0]["filter"] == 'userName eq "Alice\\"Ops"'


def test_find_user_name_accepts_canonical_case_from_service(monkeypatch):
    """Accept a canonical user name with different letter case."""
    helper = load_identity_domains_helper(monkeypatch)
    user = FakeModel(id="SCIM-ID", user_name="alice@example.com")
    client = types.SimpleNamespace(
        list_users=lambda **kwargs: FakeResponse(
            FakeModel(resources=[user], start_index=1, items_per_page=1, total_results=1)
        )
    )

    assert helper.find_identity_domain_user(
        DummyModule({"user_name": "Alice@Example.com"}), client
    ) is user


def test_find_user_by_scim_id_calls_get_user(monkeypatch):
    """Fetch a SCIM user by ID with the requested attributes."""
    helper = load_identity_domains_helper(monkeypatch)
    user = FakeModel(id="SCIM-ID")
    calls = []
    client = types.SimpleNamespace(
        get_user=lambda **kwargs: calls.append(kwargs) or FakeResponse(user)
    )

    assert helper.find_identity_domain_user(
        DummyModule({"user_id": "SCIM-ID"}), client, attributes="id,passwordState"
    ) is user
    assert calls == [
        {
            "user_id": "SCIM-ID",
            "attributes": "id,passwordState",
            "attribute_sets": ["default"],
        }
    ]


def test_find_user_rejects_ocid_in_scim_selector(monkeypatch):
    """Reject an OCID in the SCIM user selector."""
    helper = load_identity_domains_helper(monkeypatch)

    with pytest.raises(helper.IdentityDomainUserError, match="SCIM ID"):
        helper.find_identity_domain_user(
            DummyModule({"user_id": "ocid1.user.oc1..abc"}), types.SimpleNamespace()
        )


def test_find_user_returns_none_for_missing_user_and_rejects_ambiguity(monkeypatch):
    """Return no user for 404 and fail when a filter matches multiple users."""
    module_obj = load_password_info_module(monkeypatch)
    helper = get_identity_domains_helper()
    error = module_obj.oci.exceptions.ServiceError(404, "missing")
    client = types.SimpleNamespace(get_user=raising(error))
    assert helper.find_identity_domain_user(
        DummyModule({"user_id": "missing"}), client
    ) is None

    users = [FakeModel(id="one", user_name="alice"), FakeModel(id="two", user_name="alice")]
    list_client = types.SimpleNamespace(
        list_users=lambda **kwargs: FakeResponse(FakeModel(resources=users))
    )
    with pytest.raises(helper.IdentityDomainUserError, match="multiple"):
        helper.find_identity_domain_user(DummyModule({"user_name": "alice"}), list_client)


def test_serialize_password_state_omits_other_user_fields(monkeypatch):
    """Return user identifiers and password state without profile or secrets."""
    helper = load_identity_domains_helper(monkeypatch)
    user = FakeModel(
        id="SCIM-ID",
        ocid="user-ocid",
        user_name="alice",
        domain_ocid="domain-id",
        password="secret",
        profile=FakeModel(email="private@example.com"),
        urn_ietf_params_scim_schemas_oracle_idcs_extension_password_state_user=FakeModel(
            cant_change=False,
            cant_expire=False,
            must_change=True,
            expired=False,
            last_successful_set_date="2026-01-02T03:04:05Z",
        ),
    )

    assert helper.serialize_identity_domain_password_user(user) == {
        "user_id": "SCIM-ID",
        "user_ocid": "user-ocid",
        "user_name": "alice",
        "domain_id": "domain-id",
        "password_state": {
            "cant_change": False,
            "cant_expire": False,
            "must_change": True,
            "expired": False,
            "last_successful_set_date": "2026-01-02T03:04:05Z",
        },
    }
    empty_state = helper.serialize_identity_domain_password_user(FakeModel(id="SCIM-ID"))
    assert empty_state["password_state"] == {}
    assert "password" not in empty_state
    assert "profile" not in empty_state
