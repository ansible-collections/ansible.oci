from __future__ import absolute_import, division, print_function
__metaclass__ = type

import datetime
import types

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
    "CreatePolicyDetails",
    "UpdatePolicyDetails",
    "Policy",
)
NONE_SENTINEL = object()


def load_policy_module(monkeypatch):
    """Load the policy module with fake OCI model types.

    Args:
        monkeypatch: Pytest fixture for replacing OCI modules.

    Returns:
        The loaded policy module.
    """
    install_fake_oci(monkeypatch, model_names=MODELS)
    module_obj = load_collection_module("oci_identity_policy")
    monkeypatch.setattr(
        module_obj.oci,
        "util",
        types.SimpleNamespace(NONE_SENTINEL=NONE_SENTINEL),
        raising=False,
    )
    return module_obj


def make_policy(module_obj, params, client=None, check_mode=False):
    """Create a policy module instance without OCI credentials.

    Args:
        module_obj: The loaded policy module.
        params: The parameters for the module instance.
        client: An optional fake IdentityClient.
        check_mode: Whether Ansible check mode is enabled.

    Returns:
        The policy module instance.
    """
    return make_module_instance(
        module_obj,
        "OciIdentityPolicyModule",
        params,
        client=client,
        check_mode=check_mode,
    )


def test_main_argument_contract(monkeypatch):
    """Expose the required policy options."""
    module_obj = load_policy_module(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        module_obj,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule({}),
    )
    monkeypatch.setattr(
        module_obj,
        "OciIdentityPolicyModule",
        lambda module: types.SimpleNamespace(execute_resource_module=lambda: None),
    )
    module_obj.main()
    spec = captured["argument_spec"]
    assert spec["policy_id"] == {"type": "str"}
    assert spec["name"] == {"type": "str"}
    assert spec["compartment_id"] == {"type": "str"}
    assert spec["description"] == {"type": "str"}
    assert spec["statements"] == {"type": "list", "elements": "str"}
    assert spec["version_date"] == {"type": "str"}
    assert spec["state"]["choices"] == ["present", "absent"]
    assert spec["freeform_tags"]["type"] == "dict"
    assert spec["defined_tags"]["type"] == "dict"
    assert "allow_duplicate_name" not in spec
    assert captured["supports_check_mode"] is True


def test_create_maps_inputs_to_sdk_model_and_create_call(monkeypatch):
    """Map policy values into the SDK create model and IdentityClient call."""
    module_obj = load_policy_module(monkeypatch)
    calls = []
    response = FakeResponse(FakeModel(id="policy1"))
    client = types.SimpleNamespace(
        create_policy=lambda **kwargs: calls.append(kwargs) or response
    )
    instance = make_policy(
        module_obj,
        {
            "compartment_id": "compartment1",
            "name": "audit",
            "description": "",
            "statements": ["Allow any-user to inspect vcns"],
            "version_date": "2020-01-17",
            "freeform_tags": {"team": "security"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        },
        client,
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda method, **kwargs: method(**kwargs))
    monkeypatch.setattr(instance, "get_mutation_result", lambda resource, *args: resource)
    assert instance.create_resource() is response.data
    assert set(calls[0]) == {"create_policy_details"}
    details = calls[0]["create_policy_details"]
    assert details.compartment_id == "compartment1"
    assert details.name == "audit"
    assert details.description == ""
    assert details.statements == ["Allow any-user to inspect vcns"]
    assert details.version_date == "2020-01-17"
    assert details.freeform_tags == {"team": "security"}
    assert details.defined_tags == {"Operations": {"CostCenter": "42"}}


@pytest.mark.parametrize(
    "params, missing",
    [
        ({"name": "audit", "description": "", "statements": ["x"]}, "compartment_id"),
        ({"compartment_id": "c", "description": "", "statements": ["x"]}, "name"),
        ({"compartment_id": "c", "name": "audit", "statements": ["x"]}, "description"),
        ({"compartment_id": "c", "name": "audit", "description": ""}, "statements"),
    ],
)
def test_create_requires_all_fields(monkeypatch, params, missing):
    """Fail create validation when a required policy value is absent."""
    module_obj = load_policy_module(monkeypatch)
    instance = make_policy(module_obj, params)
    with pytest.raises(FailJsonCalled) as failure:
        instance.validate_create_request()
    assert missing in failure.value.payload["msg"]


@pytest.mark.parametrize(
    "params, text",
    [
        ({"name": "", "statements": ["x"]}, "name"),
        ({"name": "   ", "statements": ["x"]}, "name"),
        ({"name": "audit", "statements": []}, "statements"),
        ({"name": "audit", "statements": [" "]}, "statements"),
        ({"name": "audit", "statements": ["x"], "version_date": "2020-1-17"}, "YYYY-MM-DD"),
        ({"name": "audit", "statements": ["x"], "version_date": "2020-02-30"}, "YYYY-MM-DD"),
    ],
)
def test_invalid_name_statements_or_date_fail_main_validation(monkeypatch, params, text):
    """Reject empty values and malformed policy dates."""
    module_obj = load_policy_module(monkeypatch)
    with pytest.raises(FailJsonCalled) as failure:
        module_obj.validate_policy_parameters(DummyModule(params))
    assert text in failure.value.payload["msg"]


def test_empty_description_is_valid(monkeypatch):
    """Accept an empty policy description."""
    module_obj = load_policy_module(monkeypatch)
    module_obj.validate_policy_parameters(
        DummyModule({"description": "", "name": "audit", "statements": ["x"]})
    )


def test_empty_version_date_is_valid_for_create(monkeypatch):
    """Allow an empty version date in a policy create request."""
    module_obj = load_policy_module(monkeypatch)
    module_obj.validate_policy_parameters(
        DummyModule(
            {
                "name": "audit",
                "statements": ["allow"],
                "version_date": "",
            }
        )
    )
    details = module_obj.build_create_policy_details(
        {
            "compartment_id": "c",
            "name": "audit",
            "description": "",
            "statements": ["allow"],
            "version_date": "",
        }
    )
    assert "version_date" not in vars(details)


def test_resource_contract(monkeypatch):
    """Use policy id, name lookup, and immutable identity fields."""
    module_obj = load_policy_module(monkeypatch)
    instance = make_policy(module_obj, {"policy_id": "p", "name": "audit"})
    assert instance.resource_id_param == "policy_id"
    assert instance.name_response_field == "name"
    assert instance.create_required_fields == ("compartment_id", "name", "description", "statements")
    with pytest.raises(FailJsonCalled) as name_error:
        make_policy(module_obj, {"name": "new-name"}).needs_update(
            FakeModel(name="audit")
        )
    assert "name" in name_error.value.payload["msg"]
    with pytest.raises(FailJsonCalled) as compartment_error:
        make_policy(module_obj, {"compartment_id": "other"}).needs_update(
            FakeModel(compartment_id="compartment1")
        )
    assert "compartment_id" in compartment_error.value.payload["msg"]


def test_name_lookup_is_scoped_by_compartment(monkeypatch):
    """Scope name lookup to the requested compartment and exact name."""
    module_obj = load_policy_module(monkeypatch)
    client = types.SimpleNamespace(list_policies=object())
    instance = make_policy(
        module_obj, {"name": "audit", "compartment_id": "compartment1"}, client
    )
    calls = []
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda method, **kwargs: calls.append((method, kwargs)) or [],
    )
    assert instance.find_resources_by_name() == []
    assert calls == [(client.list_policies, {"compartment_id": "compartment1"})]


def test_reordered_statements_compare_unchanged(monkeypatch):
    """Treat policy statement order as irrelevant for updates."""
    module_obj = load_policy_module(monkeypatch)
    instance = make_policy(
        module_obj,
        {"statements": ["second", "first"], "version_date": "2020-01-17"},
    )
    current = FakeModel(
        statements=["first", "second"],
        version_date=datetime.datetime(2020, 1, 17),
    )
    assert instance.needs_update(current) is False


def test_version_date_compares_sdk_datetime_and_empty_values(monkeypatch):
    """Compare SDK dates and accept an empty value when no date exists."""
    module_obj = load_policy_module(monkeypatch)
    same = make_policy(module_obj, {"version_date": "2020-01-17"})
    same_current = FakeModel(
        version_date=datetime.datetime(2020, 1, 17), statements=["current"]
    )
    assert same.needs_update(same_current) is False
    empty = make_policy(module_obj, {"version_date": ""})
    unset_date = FakeModel(version_date=None)
    assert empty.needs_update(unset_date) is False
    changed = make_policy(module_obj, {"version_date": "2021-01-17"})
    pinned_date = FakeModel(
        version_date=datetime.datetime(2020, 1, 17), statements=["current"]
    )
    assert changed.needs_update(pinned_date) is True


def test_policy_date_comparison_does_not_normalize_other_fields(monkeypatch):
    """Use the inherited exact comparison for fields other than the policy date."""
    module_obj = load_policy_module(monkeypatch)
    instance = make_policy(module_obj, {})
    assert instance.compare_update_field_values("same", "same") is False
    assert instance.compare_update_field_values("old", "new") is True


def test_omitted_version_date_does_not_update(monkeypatch):
    """Leave the current policy version date unchanged when omitted."""
    module_obj = load_policy_module(monkeypatch)
    instance = make_policy(module_obj, {"description": "same"})
    assert instance.needs_update(
        FakeModel(
            description="same",
            version_date=datetime.datetime(2021, 1, 17),
        )
    ) is False


def test_check_mode_clear_predicts_change_without_update(monkeypatch):
    """Predict a date clear without sending an OCI update in check mode."""
    module_obj = load_policy_module(monkeypatch)
    instance = make_policy(
        module_obj,
        {"policy_id": "p", "version_date": ""},
        check_mode=True,
    )
    current = FakeModel(id="p", version_date=datetime.datetime(2020, 1, 17))
    current.statements = ["current"]
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: current)
    monkeypatch.setattr(
        instance,
        "update_resource",
        lambda resource: pytest.fail("check mode called update_resource"),
    )
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload["changed"] is True


def _capture_update_payload(monkeypatch, module_obj, params, current):
    """Run one policy update and return its SDK details model.

    Args:
        monkeypatch: Pytest fixture for replacing OCI behavior.
        module_obj: The loaded policy module.
        params: Requested policy update values.
        current: The current policy model.

    Returns:
        The update details model sent to OCI.
    """
    calls = []
    client = types.SimpleNamespace(
        update_policy=lambda **kwargs: calls.append(kwargs)
        or FakeResponse(FakeModel(id="p"))
    )
    instance = make_policy(module_obj, params, client)
    monkeypatch.setattr(instance, "call_with_retry", lambda method, **kwargs: method(**kwargs))
    monkeypatch.setattr(instance, "get_mutation_result", lambda resource, *args: resource)
    instance.update_resource(current)
    return calls[0]["update_policy_details"]


def test_clear_date_payload_uses_none_sentinel_and_current_statements(monkeypatch):
    """Clear the API date with its sentinel and include current statements."""
    module_obj = load_policy_module(monkeypatch)
    current_statements = ["Allow any-user to inspect vcns"]
    details = _capture_update_payload(
        monkeypatch,
        module_obj,
        {"policy_id": "p", "version_date": ""},
        FakeModel(
            id="p",
            version_date=datetime.datetime(2020, 1, 17),
            statements=current_statements,
        ),
    )
    assert details.version_date is NONE_SENTINEL
    assert details.statements == current_statements


def test_date_only_update_preserves_current_statements(monkeypatch):
    """Include current statements when the request changes only the date."""
    module_obj = load_policy_module(monkeypatch)
    current_statements = ["Allow any-user to inspect vcns"]
    details = _capture_update_payload(
        monkeypatch,
        module_obj,
        {"policy_id": "p", "version_date": "2021-01-17"},
        FakeModel(
            id="p",
            version_date=datetime.datetime(2020, 1, 17),
            statements=current_statements,
        ),
    )
    assert details.statements == current_statements
    assert details.version_date == "2021-01-17"


@pytest.mark.parametrize("include_same_date", [False, True])
def test_statement_update_preserves_current_date(monkeypatch, include_same_date):
    """Keep the pinned date when a statement update omits or repeats it."""
    module_obj = load_policy_module(monkeypatch)
    current_date = datetime.datetime(2021, 1, 17)
    params = {"policy_id": "p", "statements": ["new statement"]}
    if include_same_date:
        params["version_date"] = "2021-01-17"
    details = _capture_update_payload(
        monkeypatch,
        module_obj,
        params,
        FakeModel(id="p", version_date=current_date, statements=["old statement"]),
    )
    assert details.statements == ["new statement"]
    assert details.version_date == "2021-01-17"


def test_unrelated_updates_do_not_add_date_or_statements(monkeypatch):
    """Keep statements and date out of unrelated updates."""
    module_obj = load_policy_module(monkeypatch)
    details = _capture_update_payload(
        monkeypatch,
        module_obj,
        {"policy_id": "p", "description": "new"},
        FakeModel(
            id="p",
            description="old",
            version_date=datetime.datetime(2021, 1, 17),
            statements=["current"],
        ),
    )
    assert vars(details) == {"description": "new"}


def test_update_payload_contains_only_changed_fields_and_tags(monkeypatch):
    """Build an update model with changed fields and requested tag changes only."""
    module_obj = load_policy_module(monkeypatch)
    instance = make_policy(
        module_obj,
        {
            "description": "new",
            "freeform_tags": {"team": "network"},
            "defined_tags": {"Operations": {"CostCenter": "43"}},
        },
    )
    current = FakeModel(
        description="old",
        freeform_tags={"team": "security"},
        defined_tags={"Operations": {"CostCenter": "42"}},
        statements=["current"],
        version_date=datetime.datetime(2020, 1, 17),
    )
    changes = instance.build_update_plan(current)["update_model_fields"]
    assert set(changes) == {"description", "freeform_tags", "defined_tags"}
    assert changes["description"] == "new"


def test_update_calls_sdk_with_changed_values(monkeypatch):
    """Send only changed update fields through the IdentityClient wrapper."""
    module_obj = load_policy_module(monkeypatch)
    calls = []
    updated = FakeModel(id="p", description="new")
    client = types.SimpleNamespace(
        update_policy=lambda **kwargs: calls.append(kwargs) or FakeResponse(updated)
    )
    instance = make_policy(module_obj, {"policy_id": "p", "description": "new"}, client)
    current = FakeModel(id="p", description="old", statements=["s"])
    monkeypatch.setattr(instance, "call_with_retry", lambda method, **kwargs: method(**kwargs))
    monkeypatch.setattr(instance, "get_mutation_result", lambda resource, *args: resource)
    result = instance.update_resource(current)
    assert result is updated
    assert calls[0]["policy_id"] == "p"
    assert vars(calls[0]["update_policy_details"]) == {"description": "new"}


def test_unchanged_resource_does_not_send_update(monkeypatch):
    """Return the current resource when no update field changed."""
    module_obj = load_policy_module(monkeypatch)
    instance = make_policy(
        module_obj,
        {"name": "audit", "description": "same", "statements": ["a", "b"]},
        types.SimpleNamespace(update_policy=lambda **kwargs: pytest.fail("unexpected update")),
    )
    current = FakeModel(
        name="audit",
        description="same",
        statements=["b", "a"],
        version_date=datetime.datetime(2020, 1, 17),
    )
    assert instance.needs_update(current) is False
    assert instance.update_resource(current) is current


def test_check_mode_predicts_change_without_mutation(monkeypatch):
    """Report planned changes in check mode without calling mutation methods."""
    module_obj = load_policy_module(monkeypatch)
    instance = make_policy(module_obj, {"name": "audit"}, check_mode=True)
    existing = FakeModel(id="p", name="audit", description="old")
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: existing)
    monkeypatch.setattr(instance, "needs_update", lambda resource: True)
    monkeypatch.setattr(instance, "update_resource", lambda resource: pytest.fail("mutation in check mode"))
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload["changed"] is True


def test_check_mode_create_and_delete_do_not_mutate(monkeypatch):
    """Predict create and delete changes without calling OCI mutations."""
    module_obj = load_policy_module(monkeypatch)
    create = make_policy(
        module_obj,
        {
            "compartment_id": "c",
            "name": "audit",
            "description": "",
            "statements": ["allow"],
        },
        check_mode=True,
    )
    monkeypatch.setattr(create, "resolve_target_resource", lambda: None)
    create.client = types.SimpleNamespace(
        create_policy=raising(AssertionError("create mutation in check mode"))
    )
    with pytest.raises(ExitJsonCalled) as result:
        create.execute_resource_module()
    assert result.value.payload["changed"] is True

    delete = make_policy(
        module_obj,
        {"policy_id": "p", "state": "absent"},
        check_mode=True,
    )
    current = FakeModel(id="p")
    monkeypatch.setattr(delete, "resolve_target_resource", lambda: current)
    delete.client = types.SimpleNamespace(
        delete_policy=raising(AssertionError("delete mutation in check mode"))
    )
    monkeypatch.setattr(
        delete,
        "delete_resource",
        raising(AssertionError("delete mutation in check mode")),
    )
    with pytest.raises(ExitJsonCalled) as result:
        delete.execute_resource_module()
    assert result.value.payload["changed"] is True


def test_get_404_is_absent_and_other_errors_raise(monkeypatch):
    """Return no resource for 404 and propagate other OCI errors."""
    module_obj = load_policy_module(monkeypatch)
    instance = make_policy(module_obj, {})
    missing = RuntimeError("missing")
    missing.status = 404
    monkeypatch.setattr(instance, "get_resource_response", raising(missing))
    assert instance.get_resource_by_id("missing") is None
    forbidden = RuntimeError("forbidden")
    forbidden.status = 403
    monkeypatch.setattr(instance, "get_resource_response", raising(forbidden))
    with pytest.raises(RuntimeError, match="forbidden"):
        instance.get_resource_by_id("blocked")


def test_delete_uses_identity_client_and_retry_wrapper(monkeypatch):
    """Delete a policy by id through the shared retry and wait helper."""
    module_obj = load_policy_module(monkeypatch)
    calls = []
    client = types.SimpleNamespace(delete_policy=object())
    instance = make_policy(module_obj, {}, client)
    monkeypatch.setattr(
        instance,
        "delete_resource_and_wait",
        lambda resource, method, **kwargs: calls.append((resource, method, kwargs)),
    )
    resource = FakeModel(id="policy1")
    instance.delete_resource(resource)
    assert calls == [(resource, client.delete_policy, {"policy_id": "policy1"})]


@pytest.mark.parametrize("wait", [False, True])
def test_create_wait_setting_controls_resource_polling(monkeypatch, wait):
    """Poll the created policy only when wait is enabled."""
    module_obj = load_policy_module(monkeypatch)
    instance = make_policy(
        module_obj,
        {
            "wait": wait,
            "compartment_id": "c",
            "name": "audit",
            "description": "",
            "statements": ["allow"],
        },
        types.SimpleNamespace(create_policy=lambda **kwargs: FakeResponse(FakeModel(id="p"))),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda method, **kwargs: method(**kwargs))
    monkeypatch.setattr(instance, "get_resource_response", lambda resource_id: FakeResponse(FakeModel(id=resource_id)))
    waited = []
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, states: waited.append((resource_id, states)) or FakeModel(id=resource_id),
    )
    result = instance.create_resource()
    if wait:
        assert result.id == "p"
        assert waited == [("p", ("ACTIVE",))]
    else:
        assert result.id == "p"
        assert waited == []


@pytest.mark.parametrize("wait", [False, True])
def test_update_wait_setting_controls_resource_polling(monkeypatch, wait):
    """Poll the updated policy only when wait is enabled."""
    module_obj = load_policy_module(monkeypatch)
    client = types.SimpleNamespace(
        update_policy=lambda **kwargs: FakeResponse(FakeModel(id="p", description="new"))
    )
    instance = make_policy(module_obj, {"wait": wait, "description": "new"}, client)
    monkeypatch.setattr(instance, "call_with_retry", lambda method, **kwargs: method(**kwargs))
    monkeypatch.setattr(instance, "get_resource_response", lambda resource_id: FakeResponse(FakeModel(id=resource_id)))
    waited = []
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, states: waited.append((resource_id, states)) or FakeModel(id=resource_id),
    )
    result = instance.update_resource(FakeModel(id="p", description="old"))
    if wait:
        assert result.id == "p"
        assert waited == [("p", ("ACTIVE",))]
    else:
        assert result.description == "new"
        assert waited == []
