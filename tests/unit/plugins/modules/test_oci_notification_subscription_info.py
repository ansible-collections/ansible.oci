from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FakeModel,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


def install_fake_oci(monkeypatch):
    """Install the shared fake OCI SDK with a Notifications namespace."""
    oci_module, service_error = shared_install_fake_oci(monkeypatch)
    oci_module.ons = types.SimpleNamespace(
        NotificationDataPlaneClient=type("FakeNotificationDataPlaneClient", (), {}),
        models=types.SimpleNamespace(),
    )
    return oci_module, service_error


def load_subscription_info_module(monkeypatch):
    """Load the subscription info module with a fake OCI SDK."""
    install_fake_oci(monkeypatch)
    return load_collection_module("oci_notification_subscription_info")


def make_subscription_info(module_obj, params, client=None):
    """Create an info module instance without initializing OCI credentials."""
    return make_module_instance(
        module_obj,
        "OciNotificationSubscriptionInfoModule",
        params,
        client=client,
    )


def test_main_argument_spec_contract(monkeypatch):
    """Expose subscription filters without name or lifecycle_state options."""
    module_obj = load_subscription_info_module(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        module_obj,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule({}),
    )
    monkeypatch.setattr(
        module_obj,
        "OciNotificationSubscriptionInfoModule",
        lambda module: captured.update(module=module)
        or types.SimpleNamespace(execute_info_module=lambda: None),
    )
    module_obj.main()
    assert captured["required_one_of"] == [["compartment_id", "subscription_id"]]
    assert captured["supports_check_mode"] is True
    spec = captured["argument_spec"]
    assert spec["subscription_id"] == {"type": "str"}
    assert spec["compartment_id"] == {"type": "str"}
    assert spec["topic_id"] == {"type": "str"}
    assert "name" not in spec
    assert "lifecycle_state" not in spec
    assert set(module_obj.OCI_AUTH_ARGS) <= set(spec)


def test_class_metadata_and_client_class(monkeypatch):
    """Declare the Notifications data plane client and get/list metadata."""
    module_obj = load_subscription_info_module(monkeypatch)
    module_class = module_obj.OciNotificationSubscriptionInfoModule
    assert module_class.results_key == "subscriptions"
    assert module_class.resource_id_param == "subscription_id"
    assert module_class.resource_get_method == "get_subscription"
    assert module_class.list_resource_method == "list_subscriptions"
    assert module_class.list_filter_params == ["compartment_id", "topic_id"]
    instance = make_subscription_info(module_obj, {})
    assert instance.client_class is module_obj.oci.ons.NotificationDataPlaneClient


def test_get_by_subscription_id(monkeypatch):
    """Fetch a subscription by id through get_subscription."""
    module_obj = load_subscription_info_module(monkeypatch)
    subscription = FakeModel(id="sub1", topic_id="topic1")
    client = types.SimpleNamespace(
        get_subscription=object(), list_subscriptions=object()
    )
    instance = make_subscription_info(module_obj, {"subscription_id": "sub1"}, client)
    calls = []
    monkeypatch.setattr(
        instance,
        "get_resource_by_id",
        lambda resource_id, method, **kwargs: calls.append(
            (resource_id, method, kwargs)
        )
        or [subscription],
    )
    assert instance.fetch_resources() == [subscription]
    assert calls == [("sub1", client.get_subscription, {"subscription_id": "sub1"})]


def test_get_404_returns_empty_and_other_errors_propagate(monkeypatch):
    """Return no subscriptions for a missing id and raise other OCI errors."""
    module_obj = load_subscription_info_module(monkeypatch)
    instance = make_subscription_info(
        module_obj,
        {"subscription_id": "s"},
        types.SimpleNamespace(get_subscription=object()),
    )
    missing = RuntimeError("missing")
    missing.status = 404
    monkeypatch.setattr(instance, "call_with_retry", raising(missing))
    assert instance.fetch_resources() == []
    forbidden = RuntimeError("forbidden")
    forbidden.status = 403
    monkeypatch.setattr(instance, "call_with_retry", raising(forbidden))
    with pytest.raises(RuntimeError, match="forbidden"):
        instance.fetch_resources()


def test_list_scoped_by_compartment_and_topic(monkeypatch):
    """Pass compartment_id and topic_id to list_subscriptions."""
    module_obj = load_subscription_info_module(monkeypatch)
    client = types.SimpleNamespace(list_subscriptions=object())
    instance = make_subscription_info(
        module_obj,
        {"compartment_id": "compartment1", "topic_id": "topic1"},
        client,
    )
    subscriptions = [FakeModel(id="s1"), FakeModel(id="s2")]
    calls = []
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda method, **kwargs: calls.append((method, kwargs)) or subscriptions,
    )
    assert instance.fetch_resources() == subscriptions
    assert calls == [
        (
            client.list_subscriptions,
            {"compartment_id": "compartment1", "topic_id": "topic1"},
        )
    ]


def test_list_without_topic_omits_topic_filter(monkeypatch):
    """Only send compartment_id when no topic filter is given."""
    module_obj = load_subscription_info_module(monkeypatch)
    client = types.SimpleNamespace(list_subscriptions=object())
    instance = make_subscription_info(
        module_obj, {"compartment_id": "compartment1", "topic_id": None}, client
    )
    calls = []
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda method, **kwargs: calls.append(kwargs) or [],
    )
    assert instance.fetch_resources() == []
    assert calls == [{"compartment_id": "compartment1"}]


def test_serialize_converts_deliver_policy_json_to_delivery_policy(monkeypatch):
    """Turn the get_subscription JSON string into a delivery_policy dict."""
    module_obj = load_subscription_info_module(monkeypatch)
    instance = make_subscription_info(module_obj, {})
    subscription = FakeModel(
        id="sub1",
        topic_id="topic1",
        protocol="CUSTOM_HTTPS",
        endpoint="https://hooks.example.com/secret",
        deliver_policy='{"backoffRetryPolicy": {"maxRetryDuration": 3600000, '
        '"policyType": "EXPONENTIAL"}}',
    )
    result = instance.serialize_result_resource(subscription)
    assert result["id"] == "sub1"
    assert result["delivery_policy"] == {
        "backoff_retry_policy": {
            "max_retry_duration": 3600000,
            "policy_type": "EXPONENTIAL",
        }
    }
    assert "deliver_policy" not in result
    assert result["endpoint"] == "https://hooks.example.com"


def test_serialize_leaves_list_delivery_policy_alone(monkeypatch):
    """Keep the delivery_policy that list_subscriptions already returns."""
    module_obj = load_subscription_info_module(monkeypatch)
    instance = make_subscription_info(module_obj, {})
    policy = {"backoff_retry_policy": {"max_retry_duration": 7200000}}
    summary = FakeModel(id="sub1", endpoint="https://hooks.example.com/secret", delivery_policy=policy)
    result = instance.serialize_result_resource(summary)
    assert result == {"id": "sub1", "endpoint": "https://hooks.example.com", "delivery_policy": policy}


def test_info_result_is_unchanged_and_reports_subscriptions(monkeypatch):
    """Return serialized subscriptions under subscriptions with changed false."""
    module_obj = load_subscription_info_module(monkeypatch)
    instance = make_subscription_info(module_obj, {})
    monkeypatch.setattr(
        instance,
        "fetch_resources",
        lambda: [FakeModel(id="s", topic_id="t", lifecycle_state="ACTIVE")],
    )
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_info_module()
    assert result.value.payload["changed"] is False
    assert result.value.payload["subscriptions"] == [
        {"id": "s", "topic_id": "t", "lifecycle_state": "ACTIVE"}
    ]
