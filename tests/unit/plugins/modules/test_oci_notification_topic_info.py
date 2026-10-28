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
        NotificationControlPlaneClient=type("FakeNotificationClient", (), {}),
        models=types.SimpleNamespace(),
    )
    return oci_module, service_error


def load_topic_info_module(monkeypatch):
    """Load the topic info module with a fake OCI SDK."""
    install_fake_oci(monkeypatch)
    return load_collection_module("oci_notification_topic_info")


def make_topic_info(module_obj, params, client=None):
    """Create an info module instance without initializing OCI credentials."""
    return make_module_instance(
        module_obj,
        "OciNotificationTopicInfoModule",
        params,
        client=client,
    )


def test_main_argument_spec_contract(monkeypatch):
    """Expose topic filters, lowercase lifecycle choices, and required_one_of."""
    module_obj = load_topic_info_module(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        module_obj,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs)
        or DummyModule({"lifecycle_state": "active"}),
    )
    monkeypatch.setattr(
        module_obj,
        "OciNotificationTopicInfoModule",
        lambda module: captured.update(module=module)
        or types.SimpleNamespace(execute_info_module=lambda: None),
    )
    module_obj.main()
    assert captured["module"].params["lifecycle_state"] == "ACTIVE"
    assert captured["required_one_of"] == [["compartment_id", "topic_id"]]
    assert captured["supports_check_mode"] is True
    spec = captured["argument_spec"]
    assert spec["topic_id"] == {"type": "str"}
    assert spec["compartment_id"] == {"type": "str"}
    assert spec["name"] == {"type": "str"}
    assert spec["lifecycle_state"]["choices"] == ["active", "deleting", "creating"]


def test_class_metadata_and_client_class(monkeypatch):
    """Declare the Notifications client and get/list metadata."""
    module_obj = load_topic_info_module(monkeypatch)
    module_class = module_obj.OciNotificationTopicInfoModule
    assert module_class.results_key == "topics"
    assert module_class.resource_id_param == "topic_id"
    assert module_class.resource_get_method == "get_topic"
    assert module_class.list_resource_method == "list_topics"
    assert module_class.name_response_field == "name"
    assert module_class.list_filter_params == ["compartment_id", "lifecycle_state"]
    instance = make_topic_info(module_obj, {})
    assert instance.client_class is module_obj.oci.ons.NotificationControlPlaneClient


def test_get_by_topic_id_and_serialization(monkeypatch):
    """Fetch a topic by id and serialize its fields without an id key."""
    module_obj = load_topic_info_module(monkeypatch)
    topic = FakeModel(
        topic_id="topic1",
        name="alerts",
        compartment_id="compartment1",
        description="alerts topic",
        lifecycle_state="ACTIVE",
        freeform_tags={"team": "ops"},
        api_endpoint="https://notification.example",
    )
    client = types.SimpleNamespace(get_topic=object(), list_topics=object())
    instance = make_topic_info(module_obj, {"topic_id": "topic1"}, client)
    calls = []
    monkeypatch.setattr(
        instance,
        "get_resource_by_id",
        lambda resource_id, method, **kwargs: calls.append(
            (resource_id, method, kwargs)
        )
        or [topic],
    )
    assert instance.fetch_resources() == [topic]
    assert calls == [("topic1", client.get_topic, {"topic_id": "topic1"})]
    result = instance.serialize_result_resource(topic)
    assert result["topic_id"] == "topic1"
    assert result["name"] == "alerts"
    assert result["freeform_tags"] == {"team": "ops"}
    assert "id" not in result


def test_get_404_returns_empty_and_other_errors_propagate(monkeypatch):
    """Return no topics for a missing id and raise other OCI errors."""
    module_obj = load_topic_info_module(monkeypatch)
    instance = make_topic_info(
        module_obj, {"topic_id": "t"}, types.SimpleNamespace(get_topic=object())
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


def test_list_scoped_by_compartment_and_lifecycle_with_exact_name(monkeypatch):
    """Pass SDK-cased list filters to OCI and filter by exact topic name."""
    module_obj = load_topic_info_module(monkeypatch)
    client = types.SimpleNamespace(list_topics=object())
    instance = make_topic_info(
        module_obj,
        {
            "compartment_id": "compartment1",
            "lifecycle_state": "ACTIVE",
            "name": "alerts",
        },
        client,
    )
    matching = FakeModel(name="alerts", topic_id="t1")
    other = FakeModel(name="alerts-old", topic_id="t2")
    calls = []
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda method, **kwargs: calls.append((method, kwargs)) or [matching, other],
    )
    assert instance.fetch_resources() == [matching]
    assert calls == [
        (
            client.list_topics,
            {"compartment_id": "compartment1", "lifecycle_state": "ACTIVE"},
        )
    ]


def test_info_result_is_unchanged_and_reports_topics(monkeypatch):
    """Return serialized topics under topics with changed set to false."""
    module_obj = load_topic_info_module(monkeypatch)
    instance = make_topic_info(module_obj, {})
    monkeypatch.setattr(
        instance,
        "fetch_resources",
        lambda: [FakeModel(topic_id="t", name="alerts", lifecycle_state="ACTIVE")],
    )
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_info_module()
    assert result.value.payload["changed"] is False
    assert result.value.payload["topics"] == [
        {"topic_id": "t", "name": "alerts", "lifecycle_state": "ACTIVE"}
    ]
