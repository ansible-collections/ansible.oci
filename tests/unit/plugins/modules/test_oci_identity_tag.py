from __future__ import absolute_import, division, print_function
__metaclass__ = type

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
)


MODELS = (
    "CreateTagDetails",
    "UpdateTagDetails",
    "EnumTagDefinitionValidator",
    "DefaultTagDefinitionValidator",
)


def load_tag_module(monkeypatch):
    """Load the tag module with fake OCI SDK models.

    Args:
        monkeypatch: Pytest fixture for temporary SDK module setup.

    Returns:
        The imported tag module.
    """
    install_fake_oci(monkeypatch, model_names=MODELS)
    return load_collection_module("oci_identity_tag")


def make_tag(module_obj, params, client=None, check_mode=False):
    """Create a tag module instance for one test case.

    Args:
        module_obj: Imported tag module.
        params: Module parameters for the test.
        client: Optional fake OCI client.
        check_mode: Whether to enable check mode.

    Returns:
        A tag module instance.
    """
    return make_module_instance(
        module_obj, "OciIdentityTagModule", params, client=client, check_mode=check_mode
    )


def test_main_declares_tag_contract(monkeypatch):
    """Test main declares tag contract behavior."""
    module_obj = load_tag_module(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        module_obj,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule({}),
    )
    monkeypatch.setattr(
        module_obj,
        "OciIdentityTagModule",
        lambda module: types.SimpleNamespace(
            validate_validator=lambda: None, execute_resource_module=lambda: None
        ),
    )
    module_obj.main()
    spec = captured["argument_spec"]
    assert spec["tag_namespace_id"] == {"type": "str", "required": True}
    assert spec["name"] == {"type": "str", "required": True}
    assert spec["state"]["choices"] == ["present", "absent"]
    assert spec["state"]["default"] == "present"
    assert spec["validator"]["options"]["validator_type"]["choices"] == ["enum", "default"]
    assert "tag_id" not in spec


def test_create_sends_sdk_model_and_namespace(monkeypatch):
    """Test create sends sdk model and namespace behavior."""
    module_obj = load_tag_module(monkeypatch)
    calls = []
    created = FakeModel(name="Environment", lifecycle_state="ACTIVE")
    client = types.SimpleNamespace(
        create_tag=lambda **kwargs: calls.append(kwargs) or FakeResponse(created)
    )
    instance = make_tag(
        module_obj,
        {
            "tag_namespace_id": "ns1",
            "name": "Environment",
            "description": "Deployment environment",
            "is_cost_tracking": True,
            "validator": {"validator_type": "enum", "values": ["Dev", "Prod"]},
        },
        client,
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    instance.get_mutation_result = lambda data, *args: data
    assert instance.create_resource() is created
    assert calls[0]["tag_namespace_id"] == "ns1"
    details = calls[0]["create_tag_details"]
    assert isinstance(details, module_obj.oci.identity.models.CreateTagDetails)
    assert details.name == "Environment"
    assert isinstance(details.validator, module_obj.oci.identity.models.EnumTagDefinitionValidator)
    assert details.validator.values == ["Dev", "Prod"]


def test_validator_creation_normalizes_type_and_default(monkeypatch):
    """Test validator creation normalizes type and default behavior."""
    module_obj = load_tag_module(monkeypatch)
    enum = module_obj.build_tag_validator({"validator_type": "enum", "values": ["A"]})
    default = module_obj.build_tag_validator({"validator_type": "default"})
    assert isinstance(enum, module_obj.oci.identity.models.EnumTagDefinitionValidator)
    assert enum.validator_type == "ENUM"
    assert isinstance(default, module_obj.oci.identity.models.DefaultTagDefinitionValidator)
    assert default.validator_type == "DEFAULT"
    assert module_obj.build_tag_validator(None) is None


def test_default_validator_accepts_ansible_null_values(monkeypatch):
    """Test default validator accepts ansible null values behavior."""
    module_obj = load_tag_module(monkeypatch)
    instance = make_tag(
        module_obj,
        {"validator": {"validator_type": "default", "values": None}},
    )
    instance.validate_validator()
    validator = module_obj.build_tag_validator(instance.module.params["validator"])
    assert isinstance(validator, module_obj.oci.identity.models.DefaultTagDefinitionValidator)


@pytest.mark.parametrize(
    "validator",
    [
        {"validator_type": "enum", "values": []},
        {"validator_type": "enum", "values": [""]},
        {"validator_type": "enum", "values": ["A", "A"]},
        {"validator_type": "default", "values": ["A"]},
    ],
)
def test_rejects_invalid_validator(monkeypatch, validator):
    """Test rejects invalid validator behavior."""
    module_obj = load_tag_module(monkeypatch)
    instance = make_tag(module_obj, {"validator": validator})
    with pytest.raises(FailJsonCalled):
        instance.validate_validator()


def test_validate_create_requires_description(monkeypatch):
    """Test validate create requires description behavior."""
    module_obj = load_tag_module(monkeypatch)
    instance = make_tag(module_obj, {"name": "Environment"})
    with pytest.raises(FailJsonCalled) as failure:
        instance.validate_create_request()
    assert "description" in failure.value.payload["msg"]


def test_enum_order_does_not_cause_update(monkeypatch):
    """Test enum order does not cause update behavior."""
    module_obj = load_tag_module(monkeypatch)
    instance = make_tag(module_obj, {"validator": {"validator_type": "enum", "values": ["B", "A"]}})
    current = FakeModel(validator={"validator_type": "ENUM", "values": ["A", "B"]})
    assert instance.plan_validator_update(current, {"validator": current.validator}, None, instance.module.params["validator"]) == []


def test_default_validator_canonicalizes_missing_api_validator(monkeypatch):
    """Test default validator canonicalizes missing api validator behavior."""
    module_obj = load_tag_module(monkeypatch)
    instance = make_tag(module_obj, {"validator": {"validator_type": "default"}})
    current = FakeModel()
    assert instance.plan_validator_update(current, {"validator": None}, None, instance.module.params["validator"]) == []


def test_sparse_update_preserves_omitted_fields_and_casing(monkeypatch):
    """Test sparse update preserves omitted fields and casing behavior."""
    module_obj = load_tag_module(monkeypatch)
    calls = []
    updated = FakeModel(name="Environment", lifecycle_state="ACTIVE")
    client = types.SimpleNamespace(
        update_tag=lambda **kwargs: calls.append(kwargs) or FakeResponse(updated)
    )
    params = {
        "tag_namespace_id": "ns1",
        "name": "Environment",
        "description": "New description",
        "defined_tags": {"validator_type": {"CamelKey": "Value"}},
    }
    instance = make_tag(module_obj, params, client)
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    instance.get_mutation_result = lambda data, *args: data
    current = FakeModel(
        name="Environment",
        description="Old description",
        is_retired=False,
        is_cost_tracking=False,
        freeform_tags={},
        defined_tags={"validator_type": {"CamelKey": "Value"}},
        validator=None,
        lifecycle_state="ACTIVE",
    )
    assert instance.needs_update(current) is True
    assert instance.update_resource(current) is updated
    assert calls[0]["tag_namespace_id"] == "ns1"
    assert calls[0]["tag_name"] == "Environment"
    assert calls[0]["update_tag_details"].description == "New description"


def test_update_validator_uses_model_and_keeps_arbitrary_key_case(monkeypatch):
    """Test update validator uses model and keeps arbitrary key case behavior."""
    module_obj = load_tag_module(monkeypatch)
    instance = make_tag(module_obj, {"tag_namespace_id": "ns1", "name": "T"})
    details = instance.build_update_details(
        {"validator": {"validator_type": "enum", "values": ["X"]},
         "defined_tags": {"validator_type": {"MixedCase": "v"}}}
    )
    assert isinstance(details.validator, module_obj.oci.identity.models.EnumTagDefinitionValidator)
    assert details.defined_tags == {"validator_type": {"MixedCase": "v"}}


def test_absent_delete_retires_before_delete(monkeypatch):
    """Test absent delete retires before delete behavior."""
    module_obj = load_tag_module(monkeypatch)
    calls = []
    client = types.SimpleNamespace(
        update_tag=lambda **kwargs: calls.append(("update", kwargs)) or FakeResponse(FakeModel(lifecycle_state="INACTIVE")),
        delete_tag=lambda **kwargs: calls.append(("delete", kwargs)) or FakeResponse(FakeModel(lifecycle_state="DELETED")),
    )
    instance = make_tag(module_obj, {"tag_namespace_id": "ns1", "name": "Environment"}, client)
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    instance.get_mutation_result = lambda data, *args: data
    instance.delete_resource(FakeModel(name="Environment", is_retired=False, lifecycle_state="ACTIVE"))
    assert [call[0] for call in calls] == ["update", "delete"]
    assert calls[0][1]["update_tag_details"].is_retired is True
    assert calls[1][1]["tag_namespace_id"] == "ns1"
    assert calls[1][1]["tag_name"] == "Environment"


def test_deleting_tag_fails_present_request(monkeypatch):
    """Fail a present request while OCI deletes the tag."""
    module_obj = load_tag_module(monkeypatch)
    client = types.SimpleNamespace(
        get_tag=lambda **kwargs: FakeResponse(
            FakeModel(name="Environment", lifecycle_state="DELETING")
        )
    )
    instance = make_tag(
        module_obj,
        {"tag_namespace_id": "ns1", "name": "Environment", "wait": False},
        client,
    )
    with pytest.raises(FailJsonCalled):
        instance.call_with_retry = lambda fn, *args, **kwargs: fn(*args, **kwargs)
        instance.execute_resource_module()


def execute_tag(instance):
    """Run the resource flow and return its exit payload.

    Args:
        instance: Tag module instance to execute.

    Returns:
        The arguments passed to ``exit_json``.
    """
    instance.call_with_retry = lambda fn, *args, **kwargs: fn(*args, **kwargs)
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    return result.value.payload


def test_create_lifecycle_check_mode_and_reruns(monkeypatch):
    """Test create prediction, creation, and unchanged normal and check runs."""
    module_obj, service_error = install_fake_oci(monkeypatch, model_names=MODELS)
    module_obj = load_collection_module("oci_identity_tag")
    current = {"tag": None}
    calls = []

    def get_tag(**kwargs):
        """Return the current tag or raise a fake 404."""
        if current["tag"] is None:
            raise service_error(404)
        return FakeResponse(current["tag"])

    def create_tag(**kwargs):
        """Store the tag created by the fake client."""
        calls.append(kwargs)
        current["tag"] = FakeModel(
            name="Environment",
            description="Deployment environment",
            lifecycle_state="ACTIVE",
            is_retired=False,
            is_cost_tracking=False,
            freeform_tags=None,
            defined_tags=None,
            validator=None,
        )
        return FakeResponse(current["tag"])

    client = types.SimpleNamespace(get_tag=get_tag, create_tag=create_tag)
    params = {
        "tag_namespace_id": "ns1",
        "name": "Environment",
        "description": "Deployment environment",
        "wait": False,
    }
    check = make_tag(module_obj, params, client, check_mode=True)
    assert execute_tag(check)["changed"] is True
    assert calls == []
    assert current["tag"] is None

    create = make_tag(module_obj, params, client)
    assert execute_tag(create)["changed"] is True
    assert calls[0]["tag_namespace_id"] == "ns1"
    assert calls[0]["create_tag_details"].name == "Environment"
    assert execute_tag(make_tag(module_obj, params, client))["changed"] is False
    assert execute_tag(make_tag(module_obj, params, client, check_mode=True))["changed"] is False
    assert len(calls) == 1


def test_create_with_retirement_waits_for_inactive(monkeypatch):
    """Test a requested retired state after tag creation."""
    module_obj = load_tag_module(monkeypatch)
    calls = []
    created = FakeModel(name="Environment", lifecycle_state="ACTIVE", is_retired=False)
    retired = FakeModel(name="Environment", lifecycle_state="INACTIVE", is_retired=True)
    client = types.SimpleNamespace(
        create_tag=lambda **kwargs: calls.append(("create", kwargs)) or FakeResponse(created),
        update_tag=lambda **kwargs: calls.append(("update", kwargs)) or FakeResponse(retired),
    )
    instance = make_tag(
        module_obj,
        {
            "tag_namespace_id": "ns1",
            "name": "Environment",
            "description": "Environment",
            "is_retired": True,
        },
        client,
    )
    waits = []
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    instance.get_mutation_result = lambda data, name, states: waits.append(states) or data
    assert instance.create_resource() is retired
    assert [call[0] for call in calls] == ["create", "update"]
    assert waits == [("ACTIVE",), ("INACTIVE",)]


def test_delete_lifecycle_check_mode_and_repeat(monkeypatch):
    """Test delete prediction, retire-before-delete, and absent reruns."""
    module_obj, service_error = install_fake_oci(monkeypatch, model_names=MODELS)
    module_obj = load_collection_module("oci_identity_tag")
    current = {"tag": FakeModel(
        name="Environment", lifecycle_state="ACTIVE", is_retired=False,
        description="Environment", is_cost_tracking=False,
        freeform_tags=None, defined_tags=None, validator=None,
    )}
    calls = []

    def get_tag(**kwargs):
        """Return the current tag or raise a fake 404."""
        if current["tag"] is None:
            raise service_error(404)
        return FakeResponse(current["tag"])

    def update_tag(**kwargs):
        """Apply the retirement update in the fake client."""
        calls.append(("update", kwargs))
        current["tag"].is_retired = True
        current["tag"].lifecycle_state = "INACTIVE"
        return FakeResponse(current["tag"])

    def delete_tag(**kwargs):
        """Remove the tag in the fake client."""
        calls.append(("delete", kwargs))
        current["tag"].lifecycle_state = "DELETED"
        current["tag"] = None
        return FakeResponse(FakeModel(name="Environment", lifecycle_state="DELETED"))

    client = types.SimpleNamespace(get_tag=get_tag, update_tag=update_tag, delete_tag=delete_tag)
    params = {"tag_namespace_id": "ns1", "name": "Environment", "state": "absent", "wait": False}
    predicted = execute_tag(make_tag(module_obj, params, client, check_mode=True))
    assert predicted["changed"] is True
    assert current["tag"].is_retired is False
    assert calls == []

    actual = make_tag(module_obj, params, client)
    actual.get_mutation_result = lambda data, *args: data
    actual.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    assert execute_tag(actual)["changed"] is True
    assert [call[0] for call in calls] == ["update", "delete"]
    assert calls[0][1]["update_tag_details"].is_retired is True
    assert calls[1][1]["tag_namespace_id"] == "ns1"
    assert calls[1][1]["tag_name"] == "Environment"
    assert execute_tag(make_tag(module_obj, params, client))["changed"] is False
    assert execute_tag(make_tag(module_obj, params, client, check_mode=True))["changed"] is False


def test_deleted_tombstone_and_get_404_are_missing(monkeypatch):
    """Test deleted tags and 404 responses as absent resources."""
    module_obj, service_error = install_fake_oci(monkeypatch, model_names=MODELS)
    module_obj = load_collection_module("oci_identity_tag")
    instance = make_tag(
        module_obj,
        {"tag_namespace_id": "ns1", "name": "Environment", "state": "absent"},
        types.SimpleNamespace(
            get_tag=lambda **kwargs: FakeResponse(
                FakeModel(name="Environment", lifecycle_state="DELETED")
            )
        ),
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    assert execute_tag(instance)["changed"] is False

    missing = make_tag(
        module_obj,
        {"tag_namespace_id": "ns1", "name": "Environment", "state": "absent"},
        types.SimpleNamespace(
            get_tag=lambda **kwargs: (item for item in ()).throw(service_error(404))
        ),
    )
    assert execute_tag(missing)["changed"] is False


def test_deleting_tag_absent_check_mode_uses_lifecycle_flow(monkeypatch):
    """Test an in-progress deletion as unchanged during an absent check run."""
    module_obj = load_tag_module(monkeypatch)
    client = types.SimpleNamespace(
        get_tag=lambda **kwargs: FakeResponse(
            FakeModel(name="Environment", lifecycle_state="DELETING")
        )
    )
    instance = make_tag(
        module_obj,
        {
            "tag_namespace_id": "ns1",
            "name": "Environment",
            "state": "absent",
            "wait": True,
        },
        client,
        check_mode=True,
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    assert execute_tag(instance)["changed"] is False


def test_update_lifecycle_check_mode_and_reruns(monkeypatch):
    """Test retirement prediction, update, and unchanged normal and check runs."""
    module_obj = load_tag_module(monkeypatch)
    current = {"tag": FakeModel(
        name="Environment", description="Environment", lifecycle_state="ACTIVE",
        is_retired=False, is_cost_tracking=False, freeform_tags=None,
        defined_tags=None, validator=None,
    )}
    calls = []

    def get_tag(**kwargs):
        """Return the current tag or raise a fake 404."""
        return FakeResponse(current["tag"])

    def update_tag(**kwargs):
        """Apply the retirement update in the fake client."""
        calls.append(kwargs)
        current["tag"].is_retired = kwargs["update_tag_details"].is_retired
        current["tag"].lifecycle_state = "INACTIVE"
        return FakeResponse(current["tag"])

    client = types.SimpleNamespace(get_tag=get_tag, update_tag=update_tag)
    params = {
        "tag_namespace_id": "ns1", "name": "Environment",
        "is_retired": True, "wait": False,
    }
    assert execute_tag(make_tag(module_obj, params, client, check_mode=True))["changed"] is True
    assert calls == []
    assert current["tag"].is_retired is False
    assert execute_tag(make_tag(module_obj, params, client))["changed"] is True
    assert len(calls) == 1
    assert execute_tag(make_tag(module_obj, params, client))["changed"] is False
    assert execute_tag(make_tag(module_obj, params, client, check_mode=True))["changed"] is False
    assert len(calls) == 1


def test_serialization_keeps_null_validator_result(monkeypatch):
    """Preserve the API response when the validator is absent."""
    module_obj = load_tag_module(monkeypatch)
    instance = make_tag(module_obj, {})
    result = instance.serialize_result_resource(
        FakeModel(name="Environment", validator=None)
    )
    assert result["validator"] is None


def test_retirement_and_reactivation_wait_for_target_state(monkeypatch):
    """Test the wait target when a tag changes retired state."""
    module_obj = load_tag_module(monkeypatch)
    for desired, current_retired, response_state, expected_wait in [
        (True, False, "INACTIVE", ("INACTIVE",)),
        (False, True, "ACTIVE", ("ACTIVE",)),
    ]:
        calls = []
        response = FakeModel(name="Environment", is_retired=desired, lifecycle_state=response_state)
        client = types.SimpleNamespace(
            update_tag=lambda **kwargs: calls.append(kwargs) or FakeResponse(response)
        )
        instance = make_tag(
            module_obj,
            {"tag_namespace_id": "ns1", "name": "Environment", "is_retired": desired},
            client,
        )
        instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
        waits = []
        instance.get_mutation_result = lambda data, name, states: waits.append(states) or data
        instance.get_update_plan = lambda resource: {
            "update_model_fields": {"is_retired": desired},
            "strategy_operations": [],
        }
        assert instance.update_resource(
            FakeModel(name="Environment", is_retired=current_retired)
        ) is response
        assert waits == [expected_wait]
