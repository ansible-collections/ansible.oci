from __future__ import absolute_import, division, print_function
__metaclass__ = type

import json
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


SUBSCRIPTION_MODEL_NAMES = (
    "CreateSubscriptionDetails",
    "UpdateSubscriptionDetails",
    "DeliveryPolicy",
    "BackoffRetryPolicy",
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
        NotificationDataPlaneClient=type("FakeNotificationDataPlaneClient", (), {}),
        models=types.SimpleNamespace(
            **{model_name: FakeModel for model_name in SUBSCRIPTION_MODEL_NAMES}
        ),
    )
    return oci_module, service_error


def load_subscription_module(monkeypatch):
    """Load the subscription module with fake OCI types.

    Args:
        monkeypatch: Pytest fixture for replacing OCI modules.

    Returns:
        The loaded subscription module.
    """
    install_fake_oci(monkeypatch)
    return load_collection_module("oci_notification_subscription")


def make_subscription(module_obj, params, client=None, check_mode=False):
    """Create a subscription module instance without OCI credentials.

    Args:
        module_obj: The loaded subscription module.
        params: The parameters for the module instance.
        client: An optional fake client.
        check_mode: Whether Ansible check mode is enabled.

    Returns:
        The subscription module instance.
    """
    return make_module_instance(
        module_obj,
        "OciNotificationSubscriptionModule",
        params,
        client=client,
        check_mode=check_mode,
    )


def passthrough_retry(monkeypatch, instance):
    """Make call_with_retry call the method directly."""
    monkeypatch.setattr(instance, "call_with_retry", lambda method, **kwargs: method(**kwargs))


def deliver_policy(max_retry_duration):
    """Build the deliver_policy JSON string returned by get_subscription."""
    return json.dumps(
        {"backoffRetryPolicy": {"maxRetryDuration": max_retry_duration, "policyType": "EXPONENTIAL"}}
    )


def make_current(**overrides):
    """Build a current subscription model as returned by get_subscription."""
    fields = {
        "id": "s1",
        "topic_id": "t1",
        "compartment_id": "c1",
        "protocol": "EMAIL",
        "endpoint": "ops@example.com",
        "lifecycle_state": "ACTIVE",
        "deliver_policy": deliver_policy(7200000),
        "freeform_tags": {},
        "defined_tags": {},
    }
    fields.update(overrides)
    return FakeModel(**fields)


def test_main_argument_contract(monkeypatch):
    """Expose the subscription options and normalize the protocol to OCI values."""
    module_obj = load_subscription_module(monkeypatch)
    captured = {}
    params = {"protocol": "custom_https"}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule(params)

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(
        module_obj,
        "OciNotificationSubscriptionModule",
        lambda module: types.SimpleNamespace(execute_resource_module=lambda: captured.update(ran=True)),
    )
    module_obj.main()
    spec = captured["argument_spec"]
    for name in ("subscription_id", "compartment_id", "topic_id", "metadata"):
        assert spec[name] == {"type": "str"}
    assert spec["endpoint"] == {"type": "str", "no_log": True}
    assert spec["max_retry_duration"] == {"type": "int"}
    assert spec["protocol"] == {
        "type": "str",
        "choices": ["custom_https", "email", "https", "oracle_functions", "pagerduty", "slack", "sms"],
    }
    assert spec["state"]["choices"] == ["present", "absent"]
    assert spec["state"]["default"] == "present"
    assert spec["freeform_tags"]["type"] == "dict"
    assert spec["defined_tags"]["type"] == "dict"
    assert captured["supports_check_mode"] is True
    assert captured["required_together"] == [["protocol", "endpoint"]]
    assert params["protocol"] == "CUSTOM_HTTPS"
    assert captured["ran"] is True


def test_class_metadata(monkeypatch):
    """Declare subscription-specific identifier, lookup, and update metadata."""
    module_obj = load_subscription_module(monkeypatch)
    cls = module_obj.OciNotificationSubscriptionModule
    assert cls.resource_id_param == "subscription_id"
    assert cls.resource_id_field == "id"
    assert cls.list_resource_method == "list_subscriptions"
    assert cls.common_list_filter_params == ("compartment_id",)
    assert cls.list_filter_params == ("topic_id",)
    assert cls.name_lookup_param == "endpoint"
    assert cls.name_response_field == "endpoint"
    assert cls.create_required_fields == ("compartment_id", "topic_id", "protocol", "endpoint")
    assert cls.create_resource_name == "notification subscription"
    assert cls.update_method_name == "update_subscription"
    assert cls.update_details_name == "update_subscription_details"
    assert cls.update_wait_states == ("PENDING", "ACTIVE")
    assert cls.client_class.fget(object()).__name__ == "FakeNotificationDataPlaneClient"


@pytest.mark.parametrize("missing", ["compartment_id", "topic_id", "protocol", "endpoint"])
def test_create_requires_scope_protocol_and_endpoint(monkeypatch, missing):
    """Fail create validation when a required value is absent."""
    module_obj = load_subscription_module(monkeypatch)
    params = {"compartment_id": "c", "topic_id": "t", "protocol": "EMAIL", "endpoint": "a@example.com"}
    del params[missing]
    instance = make_subscription(module_obj, params)
    with pytest.raises(FailJsonCalled) as failure:
        instance.validate_create_request()
    assert missing in failure.value.payload["msg"]


def test_create_builds_details_and_waits_for_pending_or_active(monkeypatch):
    """Create with CreateSubscriptionDetails and wait using the subscription id."""
    module_obj = load_subscription_module(monkeypatch)
    calls = []
    client = types.SimpleNamespace(
        create_subscription=lambda **kwargs: calls.append(kwargs) or FakeResponse(FakeModel(id="s1"))
    )
    instance = make_subscription(
        module_obj,
        {
            "wait": True,
            "compartment_id": "c1",
            "topic_id": "t1",
            "protocol": "EMAIL",
            "endpoint": "ops@example.com",
            "metadata": "meta",
            "max_retry_duration": 3600000,
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
        lambda resource_id, states: waited.append((resource_id, states)) or FakeModel(id=resource_id),
    )
    assert instance.create_resource().id == "s1"
    assert waited == [("s1", ("PENDING", "ACTIVE"))]
    assert set(calls[0]) == {"create_subscription_details"}
    assert vars(calls[0]["create_subscription_details"]) == {
        "topic_id": "t1",
        "compartment_id": "c1",
        "protocol": "EMAIL",
        "endpoint": "ops@example.com",
        "metadata": "meta",
        "freeform_tags": {"team": "ops"},
        "defined_tags": {"Ops": {"Cost": "1"}},
    }


def test_create_omits_unset_optional_fields(monkeypatch):
    """Do not send unset metadata or tags to create_subscription."""
    module_obj = load_subscription_module(monkeypatch)
    calls = []
    client = types.SimpleNamespace(
        create_subscription=lambda **kwargs: calls.append(kwargs) or FakeResponse(FakeModel(id="s1"))
    )
    instance = make_subscription(
        module_obj,
        {"wait": False, "compartment_id": "c1", "topic_id": "t1", "protocol": "SMS", "endpoint": "+15555550100"},
        client,
    )
    passthrough_retry(monkeypatch, instance)
    instance.create_resource()
    assert vars(calls[0]["create_subscription_details"]) == {
        "topic_id": "t1",
        "compartment_id": "c1",
        "protocol": "SMS",
        "endpoint": "+15555550100",
    }


def test_create_without_wait_does_not_poll(monkeypatch):
    """Return the create response directly when wait is disabled."""
    module_obj = load_subscription_module(monkeypatch)
    client = types.SimpleNamespace(
        create_subscription=lambda **kwargs: FakeResponse(FakeModel(id="s1"))
    )
    instance = make_subscription(module_obj, {"wait": False}, client)
    passthrough_retry(monkeypatch, instance)
    monkeypatch.setattr(instance, "wait_for_resource_id", raising(AssertionError("polled")))
    assert instance.create_resource().id == "s1"


def test_finalize_created_resource_applies_max_retry_duration(monkeypatch):
    """Apply a requested retry duration with a follow-up update after create."""
    module_obj = load_subscription_module(monkeypatch)
    updates = []
    updated = make_current(deliver_policy=deliver_policy(3600000))
    client = types.SimpleNamespace(
        update_subscription=lambda **kwargs: updates.append(kwargs) or FakeResponse(FakeModel()),
        get_subscription=lambda **kwargs: FakeResponse(updated),
    )
    instance = make_subscription(
        module_obj,
        {
            "wait": False,
            "compartment_id": "c1",
            "topic_id": "t1",
            "protocol": "EMAIL",
            "endpoint": "ops@example.com",
            "max_retry_duration": 3600000,
        },
        client,
    )
    passthrough_retry(monkeypatch, instance)
    assert instance.finalize_created_resource(make_current()) is updated
    assert updates[0]["subscription_id"] == "s1"
    assert "max_retry_duration" not in vars(updates[0]["update_subscription_details"])


def test_finalize_created_resource_without_max_retry_duration_does_not_update(monkeypatch):
    """Skip the follow-up update when no delivery policy change is requested."""
    module_obj = load_subscription_module(monkeypatch)
    instance = make_subscription(
        module_obj,
        {"compartment_id": "c1", "topic_id": "t1", "protocol": "EMAIL", "endpoint": "ops@example.com"},
        types.SimpleNamespace(update_subscription=raising(AssertionError("unexpected update"))),
    )
    created = make_current()
    assert instance.finalize_created_resource(created) is created


def test_create_in_check_mode_does_not_call_api(monkeypatch):
    """Report a change for a new subscription without calling create."""
    module_obj = load_subscription_module(monkeypatch)
    instance = make_subscription(
        module_obj,
        {"compartment_id": "c", "topic_id": "t", "protocol": "EMAIL", "endpoint": "a@example.com"},
        types.SimpleNamespace(create_subscription=raising(AssertionError("create in check mode"))),
        check_mode=True,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload["changed"] is True


@pytest.mark.parametrize("max_retry_duration", [7200000, None])
def test_idempotent_present_does_not_update(monkeypatch, max_retry_duration):
    """Leave a matching subscription unchanged, with or without a retry duration."""
    module_obj = load_subscription_module(monkeypatch)
    instance = make_subscription(
        module_obj,
        {
            "subscription_id": "s1",
            "compartment_id": "c1",
            "topic_id": "t1",
            "protocol": "EMAIL",
            "endpoint": "ops@example.com",
            "max_retry_duration": max_retry_duration,
        },
        types.SimpleNamespace(update_subscription=raising(AssertionError("unexpected update"))),
    )
    monkeypatch.setattr(instance, "resolve_target_resource", make_current)
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    payload = result.value.payload
    assert payload["changed"] is False
    assert "deliver_policy" not in payload["resource"]
    assert payload["resource"]["delivery_policy"]["backoff_retry_policy"]["max_retry_duration"] == 7200000


@pytest.mark.parametrize("policy", [None, "", "{}", deliver_policy(7200000)])
def test_max_retry_duration_drift_is_detected(monkeypatch, policy):
    """Report drift when the current policy lacks the requested duration."""
    module_obj = load_subscription_module(monkeypatch)
    instance = make_subscription(module_obj, {"max_retry_duration": 3600000})
    assert instance.needs_update(make_current(deliver_policy=policy)) is True


def test_compare_delegates_other_modes(monkeypatch):
    """Use inherited comparison for modes other than max_retry_duration."""
    module_obj = load_subscription_module(monkeypatch)
    instance = make_subscription(module_obj, {})
    assert instance.compare_update_field_values("a", "a") is False
    assert instance.compare_update_field_values("a", "b") is True
    assert instance.compare_update_field_values(deliver_policy(1), 1, compare="max_retry_duration") is False
    assert instance.compare_update_field_values(deliver_policy(1), 2, compare="max_retry_duration") is True
    assert instance.compare_update_field_values(None, 2, compare="max_retry_duration") is True
    assert instance.compare_update_field_values(None, None, compare="max_retry_duration") is False


def test_max_retry_duration_update_builds_delivery_policy(monkeypatch):
    """Send an exponential backoff delivery policy when the duration drifts."""
    module_obj = load_subscription_module(monkeypatch)
    calls = []
    client = types.SimpleNamespace(
        update_subscription=lambda **kwargs: calls.append(kwargs) or FakeResponse(FakeModel()),
        get_subscription=lambda **kwargs: FakeResponse(make_current(deliver_policy=deliver_policy(3600000))),
    )
    instance = make_subscription(
        module_obj, {"wait": False, "subscription_id": "s1", "max_retry_duration": 3600000}, client
    )
    passthrough_retry(monkeypatch, instance)
    instance.update_resource(make_current())
    assert calls[0]["subscription_id"] == "s1"
    details = vars(calls[0]["update_subscription_details"])
    assert set(details) == {"delivery_policy"}
    backoff = vars(details["delivery_policy"].backoff_retry_policy)
    assert backoff == {"max_retry_duration": 3600000, "policy_type": "EXPONENTIAL"}


def test_tags_only_update_sends_no_delivery_policy(monkeypatch):
    """Send only tags when the delivery policy is not part of the change."""
    module_obj = load_subscription_module(monkeypatch)
    calls = []
    client = types.SimpleNamespace(
        update_subscription=lambda **kwargs: calls.append(kwargs) or FakeResponse(FakeModel()),
        get_subscription=lambda **kwargs: FakeResponse(make_current()),
    )
    instance = make_subscription(
        module_obj,
        {"wait": False, "subscription_id": "s1", "freeform_tags": {"team": "new"}},
        client,
    )
    passthrough_retry(monkeypatch, instance)
    instance.update_resource(make_current(freeform_tags={"team": "old"}))
    assert vars(calls[0]["update_subscription_details"]) == {"freeform_tags": {"team": "new"}}


def test_get_update_result_refetches_even_without_wait(monkeypatch):
    """Return the fetched subscription because update returns update details."""
    module_obj = load_subscription_module(monkeypatch)
    fetched = make_current()
    calls = []
    client = types.SimpleNamespace(
        get_subscription=lambda **kwargs: calls.append(kwargs) or FakeResponse(fetched)
    )
    instance = make_subscription(module_obj, {"wait": False}, client)
    passthrough_retry(monkeypatch, instance)
    result = instance.get_update_result(FakeResponse(FakeModel(freeform_tags={})), "s1")
    assert result is fetched
    assert calls == [{"subscription_id": "s1"}]


def test_update_waits_for_pending_or_active(monkeypatch):
    """Poll the updated subscription for PENDING or ACTIVE when waiting."""
    module_obj = load_subscription_module(monkeypatch)
    instance = make_subscription(module_obj, {"wait": True})
    waited = []
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, states: waited.append((resource_id, states)) or FakeModel(id=resource_id),
    )
    instance.get_update_result(FakeResponse(FakeModel()), "s1")
    assert waited == [("s1", ("PENDING", "ACTIVE"))]


@pytest.mark.parametrize(
    "params, current, field",
    [
        ({"topic_id": "other"}, make_current(), "topic_id"),
        ({"protocol": "SMS"}, make_current(), "protocol"),
        ({"endpoint": "other@example.com"}, make_current(), "endpoint"),
        ({"compartment_id": "other"}, make_current(), "compartment_id"),
    ],
)
def test_immutable_fields_fail(monkeypatch, params, current, field):
    """Fail when an immutable subscription field would change."""
    module_obj = load_subscription_module(monkeypatch)
    instance = make_subscription(module_obj, params)
    with pytest.raises(FailJsonCalled) as failure:
        instance.needs_update(current)
    assert field in failure.value.payload["msg"]


def test_get_by_subscription_id_404_is_missing(monkeypatch):
    """Treat a 404 from get_subscription as a missing subscription."""
    module_obj = load_subscription_module(monkeypatch)
    missing = RuntimeError("missing")
    missing.status = 404
    client = types.SimpleNamespace(get_subscription=raising(missing))
    instance = make_subscription(module_obj, {"subscription_id": "s1"}, client)
    passthrough_retry(monkeypatch, instance)
    assert instance.resolve_target_resource() is None


def test_get_resource_response_uses_subscription_id(monkeypatch):
    """Call get_subscription with the subscription_id keyword."""
    module_obj = load_subscription_module(monkeypatch)
    calls = []
    client = types.SimpleNamespace(get_subscription=lambda **kwargs: calls.append(kwargs) or "response")
    instance = make_subscription(module_obj, {}, client)
    passthrough_retry(monkeypatch, instance)
    assert instance.get_resource_response("s1") == "response"
    assert calls == [{"subscription_id": "s1"}]


LOOKUP_PARAMS = {
    "compartment_id": "c1",
    "topic_id": "t1",
    "protocol": "EMAIL",
    "endpoint": "ops@example.com",
}


def make_lookup_instance(module_obj, monkeypatch, summaries, params=None):
    """Create a lookup instance whose list call returns ``summaries``."""
    client = types.SimpleNamespace(list_subscriptions=object())
    instance = make_subscription(module_obj, dict(LOOKUP_PARAMS, **(params or {})), client)
    calls = []
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda method, **kwargs: calls.append((method, kwargs)) or summaries,
    )
    return instance, client, calls


def test_lookup_lists_with_scope_and_filters_by_protocol_and_endpoint(monkeypatch):
    """Pass only compartment_id and topic_id to the list call and filter locally."""
    module_obj = load_subscription_module(monkeypatch)
    summaries = [
        FakeModel(id="s0", endpoint="other@example.com", protocol="EMAIL", lifecycle_state="ACTIVE"),
        FakeModel(id="s1", endpoint="ops@example.com", protocol="EMAIL", lifecycle_state="ACTIVE"),
        FakeModel(id="s2", endpoint="ops@example.com", protocol="SLACK", lifecycle_state="ACTIVE"),
    ]
    instance, client, calls = make_lookup_instance(module_obj, monkeypatch, summaries)
    matches = instance.find_resources_by_name()
    assert [match.id for match in matches] == ["s1"]
    assert calls == [(client.list_subscriptions, {"compartment_id": "c1", "topic_id": "t1"})]


def test_lookup_hydrates_match_by_id(monkeypatch):
    """Replace the list summary with the full subscription from get_subscription."""
    module_obj = load_subscription_module(monkeypatch)
    summary = FakeModel(
        id="s1",
        endpoint="ops@example.com",
        protocol="EMAIL",
        lifecycle_state="ACTIVE",
        delivery_policy=FakeModel(),
    )
    instance = make_lookup_instance(module_obj, monkeypatch, [summary])[0]
    full = make_current()
    fetched = []
    monkeypatch.setattr(
        instance, "get_resource_by_id", lambda resource_id: fetched.append(resource_id) or full
    )
    assert instance.resolve_target_resource() is full
    assert fetched == ["s1"]


def test_lookup_ambiguous_match_fails(monkeypatch):
    """Fail when more than one subscription matches the lookup."""
    module_obj = load_subscription_module(monkeypatch)
    summaries = [
        FakeModel(id="s1", endpoint="ops@example.com", protocol="EMAIL", lifecycle_state="ACTIVE"),
        FakeModel(id="s2", endpoint="ops@example.com", protocol="EMAIL", lifecycle_state="PENDING"),
    ]
    instance = make_lookup_instance(module_obj, monkeypatch, summaries)[0]
    with pytest.raises(FailJsonCalled) as failure:
        instance.resolve_target_resource()
    assert "subscription_id" in failure.value.payload["msg"]
    assert "2 matches" in failure.value.payload["msg"]


@pytest.mark.parametrize("missing", ["compartment_id", "topic_id"])
def test_lookup_missing_scope_fails(monkeypatch, missing):
    """Require compartment_id and topic_id for lookup by endpoint."""
    module_obj = load_subscription_module(monkeypatch)
    params = dict(LOOKUP_PARAMS)
    del params[missing]
    instance = make_subscription(module_obj, params, types.SimpleNamespace(list_subscriptions=object()))
    with pytest.raises(FailJsonCalled) as failure:
        instance.resolve_target_resource()
    assert missing in failure.value.payload["msg"]


def test_lookup_deleted_match_is_missing(monkeypatch):
    """Ignore a DELETED subscription during lookup."""
    module_obj = load_subscription_module(monkeypatch)
    summaries = [
        FakeModel(id="s1", endpoint="ops@example.com", protocol="EMAIL", lifecycle_state="DELETED"),
    ]
    instance = make_lookup_instance(module_obj, monkeypatch, summaries)[0]
    monkeypatch.setattr(instance, "get_resource_by_id", raising(AssertionError("hydrated")))
    assert instance.resolve_target_resource() is None


def test_hydrated_deleted_subscription_is_missing(monkeypatch):
    """Treat a subscription that is DELETED when fetched by id as missing."""
    module_obj = load_subscription_module(monkeypatch)
    summaries = [
        FakeModel(id="s1", endpoint="ops@example.com", protocol="EMAIL", lifecycle_state="ACTIVE"),
    ]
    instance = make_lookup_instance(module_obj, monkeypatch, summaries)[0]
    monkeypatch.setattr(
        instance, "get_resource_by_id", lambda resource_id: make_current(lifecycle_state="DELETED")
    )
    assert instance.resolve_target_resource() is None


def test_delete_calls_delete_subscription_and_waits_for_dead_state(monkeypatch):
    """Delete by subscription id and wait for the subscription to disappear."""
    module_obj = load_subscription_module(monkeypatch)
    calls = []
    client = types.SimpleNamespace(
        delete_subscription=lambda **kwargs: calls.append(kwargs) or FakeResponse(None)
    )
    instance = make_subscription(module_obj, {"wait": True}, client)
    passthrough_retry(monkeypatch, instance)
    waited = []
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, states: waited.append((resource_id, states)) or None,
    )
    instance.delete_resource(FakeModel(id="s1"))
    assert calls == [{"subscription_id": "s1"}]
    assert len(waited) == 1
    assert waited[0][0] == "s1"
    assert "DELETED" in waited[0][1]


def test_absent_when_missing_is_unchanged(monkeypatch):
    """Report no change when the subscription does not exist."""
    module_obj = load_subscription_module(monkeypatch)
    instance = make_subscription(
        module_obj,
        {"state": "absent", "subscription_id": "s1"},
        types.SimpleNamespace(delete_subscription=raising(AssertionError("unexpected delete"))),
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload["changed"] is False


def test_absent_in_check_mode_does_not_delete(monkeypatch):
    """Report a change in check mode without calling delete."""
    module_obj = load_subscription_module(monkeypatch)
    instance = make_subscription(
        module_obj,
        {"state": "absent", "subscription_id": "s1"},
        types.SimpleNamespace(delete_subscription=raising(AssertionError("delete in check mode"))),
        check_mode=True,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: FakeModel(id="s1"))
    monkeypatch.setattr(instance, "delete_resource", raising(AssertionError("delete in check mode")))
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload["changed"] is True


def test_serialize_result_resource_converts_deliver_policy(monkeypatch):
    """Expose delivery_policy as a dict instead of the deliver_policy JSON string."""
    module_obj = load_subscription_module(monkeypatch)
    instance = make_subscription(module_obj, {})
    result = instance.serialize_result_resource(make_current())
    assert "deliver_policy" not in result
    assert result["endpoint"] is None
    assert result["id"] == "s1"
    assert result["delivery_policy"] == {
        "backoff_retry_policy": {"max_retry_duration": 7200000, "policy_type": "EXPONENTIAL"}
    }


def test_present_result_summarizes_endpoint(monkeypatch):
    """Return only the endpoint scheme, hostname, and port while still matching on the full endpoint."""
    module_obj = load_subscription_module(monkeypatch)
    endpoint = "https://hooks.slack.com/services/T000/B000/secret"
    instance = make_subscription(
        module_obj, dict(LOOKUP_PARAMS, protocol="SLACK", endpoint=endpoint)
    )
    monkeypatch.setattr(
        instance,
        "resolve_target_resource",
        lambda: make_current(protocol="SLACK", endpoint=endpoint),
    )
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload["changed"] is False
    assert result.value.payload["resource"]["id"] == "s1"
    assert result.value.payload["resource"]["endpoint"] == "https://hooks.slack.com"
