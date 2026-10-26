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
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


TOPIC_MODEL_NAMES = (
    "CreateTopicDetails",
    "TopicAttributesDetails",
)


def install_fake_oci(monkeypatch):
    """Install fake OCI modules including the Notifications namespace.

    Args:
        monkeypatch: Pytest fixture for replacing OCI modules.

    Returns:
        The fake oci module and ServiceError class.
    """
    oci_module, service_error = shared_install_fake_oci(monkeypatch)
    oci_module.ons = types.SimpleNamespace(
        NotificationControlPlaneClient=type("FakeNotificationClient", (), {}),
        models=types.SimpleNamespace(
            **{model_name: FakeModel for model_name in TOPIC_MODEL_NAMES}
        ),
    )
    return oci_module, service_error


def load_topic_module(monkeypatch):
    """Load the topic module with fake OCI types.

    Args:
        monkeypatch: Pytest fixture for replacing OCI modules.

    Returns:
        The loaded topic module.
    """
    install_fake_oci(monkeypatch)
    return load_collection_module("oci_notification_topic")


def make_topic(module_obj, params, client=None, check_mode=False):
    """Create a topic module instance without OCI credentials.

    Args:
        module_obj: The loaded topic module.
        params: The parameters for the module instance.
        client: An optional fake client.
        check_mode: Whether Ansible check mode is enabled.

    Returns:
        The topic module instance.
    """
    return make_module_instance(
        module_obj,
        "OciNotificationTopicModule",
        params,
        client=client,
        check_mode=check_mode,
    )


def passthrough_retry(monkeypatch, instance):
    """Make call_with_retry call the method directly."""
    monkeypatch.setattr(instance, "call_with_retry", lambda method, **kwargs: method(**kwargs))


def test_main_argument_contract(monkeypatch):
    """Expose the topic options and run the module with check mode support."""
    module_obj = load_topic_module(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        module_obj,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule({}),
    )
    monkeypatch.setattr(
        module_obj,
        "OciNotificationTopicModule",
        lambda module: types.SimpleNamespace(execute_resource_module=lambda: captured.update(ran=True)),
    )
    module_obj.main()
    spec = captured["argument_spec"]
    assert spec["topic_id"] == {"type": "str"}
    assert spec["name"] == {"type": "str"}
    assert spec["compartment_id"] == {"type": "str"}
    assert spec["description"] == {"type": "str"}
    assert spec["state"]["choices"] == ["present", "absent"]
    assert spec["state"]["default"] == "present"
    assert spec["freeform_tags"]["type"] == "dict"
    assert spec["defined_tags"]["type"] == "dict"
    assert "allow_duplicate_name" not in spec
    assert captured["supports_check_mode"] is True
    assert captured["ran"] is True


def test_class_metadata(monkeypatch):
    """Declare topic-specific identifier, lookup, and update metadata."""
    module_obj = load_topic_module(monkeypatch)
    cls = module_obj.OciNotificationTopicModule
    assert cls.resource_id_param == "topic_id"
    assert cls.resource_id_field == "topic_id"
    assert cls.list_resource_method == "list_topics"
    assert cls.name_response_field == "name"
    assert cls.create_required_fields == ("compartment_id", "name")
    assert cls.create_resource_name == "notification topic"
    assert cls.update_method_name == "update_topic"
    assert cls.update_details_name == "topic_attributes_details"
    assert cls.update_wait_states == ("ACTIVE",)
    assert cls.client_class.fget(object()).__name__ == "FakeNotificationClient"


@pytest.mark.parametrize("missing", ["compartment_id", "name"])
def test_create_requires_compartment_and_name(monkeypatch, missing):
    """Fail create validation when a required value is absent."""
    module_obj = load_topic_module(monkeypatch)
    params = {"compartment_id": "c", "name": "topic"}
    del params[missing]
    instance = make_topic(module_obj, params)
    with pytest.raises(FailJsonCalled) as failure:
        instance.validate_create_request()
    assert missing in failure.value.payload["msg"]


def test_create_builds_details_and_waits_on_topic_id(monkeypatch):
    """Create with CreateTopicDetails and wait using the topic_id."""
    module_obj = load_topic_module(monkeypatch)
    calls = []
    client = types.SimpleNamespace(
        create_topic=lambda **kwargs: calls.append(kwargs) or FakeResponse(FakeModel(topic_id="t1"))
    )
    instance = make_topic(
        module_obj,
        {
            "wait": True,
            "compartment_id": "c1",
            "name": "alerts",
            "description": "desc",
            "freeform_tags": {"team": "ops"},
            "defined_tags": {"Ops": {"Cost": "1"}},
        },
        client,
    )
    passthrough_retry(monkeypatch, instance)
    waited = []
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, states: waited.append((resource_id, states)) or FakeModel(topic_id=resource_id),
    )
    result = instance.create_resource()
    assert result.topic_id == "t1"
    assert waited == [("t1", ("ACTIVE",))]
    assert set(calls[0]) == {"create_topic_details"}
    details = calls[0]["create_topic_details"]
    assert vars(details) == {
        "compartment_id": "c1",
        "name": "alerts",
        "description": "desc",
        "freeform_tags": {"team": "ops"},
        "defined_tags": {"Ops": {"Cost": "1"}},
    }


def test_create_without_wait_does_not_poll(monkeypatch):
    """Return the create response directly when wait is disabled."""
    module_obj = load_topic_module(monkeypatch)
    client = types.SimpleNamespace(
        create_topic=lambda **kwargs: FakeResponse(FakeModel(topic_id="t1"))
    )
    instance = make_topic(module_obj, {"wait": False, "compartment_id": "c", "name": "n"}, client)
    passthrough_retry(monkeypatch, instance)
    monkeypatch.setattr(instance, "wait_for_resource_id", raising(AssertionError("polled")))
    assert instance.create_resource().topic_id == "t1"


def test_create_in_check_mode_does_not_call_api(monkeypatch):
    """Report a change for a new topic without calling create."""
    module_obj = load_topic_module(monkeypatch)
    instance = make_topic(
        module_obj,
        {"compartment_id": "c", "name": "n"},
        types.SimpleNamespace(create_topic=raising(AssertionError("create in check mode"))),
        check_mode=True,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload["changed"] is True


@pytest.mark.parametrize("current_description", ["same", None])
def test_idempotent_present_does_not_update(monkeypatch, current_description):
    """Leave a matching topic unchanged, treating None and empty as equal."""
    module_obj = load_topic_module(monkeypatch)
    desired = "same" if current_description else ""
    instance = make_topic(
        module_obj,
        {"topic_id": "t1", "name": "n", "compartment_id": "c", "description": desired},
        types.SimpleNamespace(update_topic=raising(AssertionError("unexpected update"))),
    )
    current = FakeModel(
        topic_id="t1",
        name="n",
        compartment_id="c",
        description=current_description,
        freeform_tags={},
        defined_tags={},
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: current)
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload["changed"] is False


def test_description_comparison_delegates_other_modes(monkeypatch):
    """Use inherited comparison for modes other than empty_as_none."""
    module_obj = load_topic_module(monkeypatch)
    instance = make_topic(module_obj, {})
    assert instance.compare_update_field_values("a", "a") is False
    assert instance.compare_update_field_values("a", "b") is True
    assert instance.compare_update_field_values(None, "", compare="empty_as_none") is False
    assert instance.compare_update_field_values("", None, compare="empty_as_none") is False
    assert instance.compare_update_field_values("a", "", compare="empty_as_none") is True


def test_description_update_sends_topic_id_and_details(monkeypatch):
    """Update the description by topic_id and wait on it."""
    module_obj = load_topic_module(monkeypatch)
    calls = []
    updated = FakeModel(topic_id="t1", description="new")
    client = types.SimpleNamespace(
        update_topic=lambda **kwargs: calls.append(kwargs) or FakeResponse(updated)
    )
    instance = make_topic(module_obj, {"wait": False, "topic_id": "t1", "description": "new"}, client)
    passthrough_retry(monkeypatch, instance)
    result = instance.update_resource(FakeModel(topic_id="t1", description="old"))
    assert result is updated
    assert calls[0]["topic_id"] == "t1"
    assert vars(calls[0]["topic_attributes_details"]) == {"description": "new"}


def test_update_waits_on_topic_id(monkeypatch):
    """Poll the updated topic by topic_id when wait is enabled."""
    module_obj = load_topic_module(monkeypatch)
    client = types.SimpleNamespace(
        update_topic=lambda **kwargs: FakeResponse(FakeModel(topic_id="t1"))
    )
    instance = make_topic(module_obj, {"wait": True, "description": "new"}, client)
    passthrough_retry(monkeypatch, instance)
    waited = []
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, states: waited.append((resource_id, states)) or FakeModel(topic_id=resource_id),
    )
    instance.update_resource(FakeModel(topic_id="t1", description="old"))
    assert waited == [("t1", ("ACTIVE",))]


@pytest.mark.parametrize("current_description, expected", [("keep me", "keep me"), (None, "")])
def test_tags_only_update_includes_current_description(monkeypatch, current_description, expected):
    """Send the current description (or empty) because OCI requires it."""
    module_obj = load_topic_module(monkeypatch)
    calls = []
    client = types.SimpleNamespace(
        update_topic=lambda **kwargs: calls.append(kwargs) or FakeResponse(FakeModel(topic_id="t1"))
    )
    instance = make_topic(
        module_obj,
        {"wait": False, "topic_id": "t1", "freeform_tags": {"team": "new"}},
        client,
    )
    passthrough_retry(monkeypatch, instance)
    current = FakeModel(topic_id="t1", description=current_description, freeform_tags={"team": "old"})
    instance.update_resource(current)
    assert vars(calls[0]["topic_attributes_details"]) == {
        "freeform_tags": {"team": "new"},
        "description": expected,
    }


def test_no_change_plan_has_no_description_injected(monkeypatch):
    """Do not add a description to the plan when nothing changes."""
    module_obj = load_topic_module(monkeypatch)
    instance = make_topic(module_obj, {"freeform_tags": {"a": "b"}})
    plan = instance.build_update_plan(FakeModel(topic_id="t1", description="d", freeform_tags={"a": "b"}))
    assert plan["update_model_fields"] == {}
    assert plan["update_needed"] is False


@pytest.mark.parametrize(
    "params, current, field",
    [
        ({"name": "new"}, FakeModel(name="old"), "name"),
        ({"compartment_id": "other"}, FakeModel(compartment_id="c1"), "compartment_id"),
    ],
)
def test_immutable_fields_fail(monkeypatch, params, current, field):
    """Fail when the name or compartment would change."""
    module_obj = load_topic_module(monkeypatch)
    instance = make_topic(module_obj, params)
    with pytest.raises(FailJsonCalled) as failure:
        instance.needs_update(current)
    assert field in failure.value.payload["msg"]


def test_get_by_topic_id_404_is_missing(monkeypatch):
    """Treat a 404 from get_topic as a missing topic."""
    module_obj = load_topic_module(monkeypatch)
    missing = RuntimeError("missing")
    missing.status = 404
    client = types.SimpleNamespace(get_topic=raising(missing))
    instance = make_topic(module_obj, {"topic_id": "t1"}, client)
    passthrough_retry(monkeypatch, instance)
    assert instance.resolve_target_resource() is None


def test_get_resource_response_uses_topic_id(monkeypatch):
    """Call get_topic with the topic_id keyword."""
    module_obj = load_topic_module(monkeypatch)
    calls = []
    client = types.SimpleNamespace(get_topic=lambda **kwargs: calls.append(kwargs) or "response")
    instance = make_topic(module_obj, {}, client)
    passthrough_retry(monkeypatch, instance)
    assert instance.get_resource_response("t1") == "response"
    assert calls == [{"topic_id": "t1"}]


def test_name_lookup_is_scoped_by_compartment(monkeypatch):
    """Scope name lookup to list_topics in the requested compartment."""
    module_obj = load_topic_module(monkeypatch)
    client = types.SimpleNamespace(list_topics=object())
    instance = make_topic(module_obj, {"name": "alerts", "compartment_id": "c1"}, client)
    calls = []
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda method, **kwargs: calls.append((method, kwargs)) or [],
    )
    assert instance.find_resources_by_name() == []
    assert calls == [(client.list_topics, {"compartment_id": "c1"})]


def test_name_lookup_matches_name_field(monkeypatch):
    """Resolve a topic by its name response field."""
    module_obj = load_topic_module(monkeypatch)
    client = types.SimpleNamespace(list_topics=object())
    instance = make_topic(module_obj, {"name": "alerts", "compartment_id": "c1"}, client)
    topics = [FakeModel(topic_id="t0", name="other"), FakeModel(topic_id="t1", name="alerts")]
    monkeypatch.setattr(instance, "list_all_resources", lambda method, **kwargs: topics)
    monkeypatch.setattr(
        instance, "get_resource_by_id", lambda resource_id: FakeModel(topic_id=resource_id, name="alerts")
    )
    assert instance.resolve_target_resource().topic_id == "t1"


def test_delete_calls_delete_topic_and_waits_on_topic_id(monkeypatch):
    """Delete by topic_id and wait for the topic to disappear."""
    module_obj = load_topic_module(monkeypatch)
    calls = []
    client = types.SimpleNamespace(
        delete_topic=lambda **kwargs: calls.append(kwargs) or FakeResponse(None)
    )
    instance = make_topic(module_obj, {"wait": True}, client)
    passthrough_retry(monkeypatch, instance)
    waited = []
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, states: waited.append((resource_id, states)) or None,
    )
    instance.delete_resource(FakeModel(topic_id="t1"))
    assert calls == [{"topic_id": "t1"}]
    assert len(waited) == 1
    assert waited[0][0] == "t1"
    assert "DELETED" in waited[0][1] or "TERMINATED" in waited[0][1]


def test_absent_when_missing_is_unchanged(monkeypatch):
    """Report no change when the topic does not exist."""
    module_obj = load_topic_module(monkeypatch)
    instance = make_topic(
        module_obj,
        {"state": "absent", "topic_id": "t1"},
        types.SimpleNamespace(delete_topic=raising(AssertionError("unexpected delete"))),
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload["changed"] is False


def test_absent_in_check_mode_does_not_delete(monkeypatch):
    """Report a change in check mode without calling delete."""
    module_obj = load_topic_module(monkeypatch)
    instance = make_topic(
        module_obj,
        {"state": "absent", "topic_id": "t1"},
        types.SimpleNamespace(delete_topic=raising(AssertionError("delete in check mode"))),
        check_mode=True,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: FakeModel(topic_id="t1"))
    monkeypatch.setattr(instance, "delete_resource", raising(AssertionError("delete in check mode")))
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload["changed"] is True
