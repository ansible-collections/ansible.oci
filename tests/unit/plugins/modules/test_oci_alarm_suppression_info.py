from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from .conftest import (
    ExitJsonCalled,
    FakeModel,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


SUPPRESSION_ID = "ocid1.alarmsuppression.oc1..example"
ALARM_ID = "ocid1.alarm.oc1..example"


def install_fake_oci(monkeypatch):
    oci_module, service_error = shared_install_fake_oci(monkeypatch)
    oci_module.monitoring = types.SimpleNamespace(
        MonitoringClient=type("FakeMonitoringClient", (), {}),
        models=types.SimpleNamespace(),
    )
    return oci_module, service_error


def test_main_wiring(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_alarm_suppression_info")
    captured = {}

    class FakeAnsibleModule:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.params = {
                "target_type": "compartment",
                "level": "dimension",
                "lifecycle_state": "deleted",
            }

    monkeypatch.setattr(info_module, "AnsibleModule", FakeAnsibleModule)
    monkeypatch.setattr(
        info_module,
        "OciAlarmSuppressionInfoModule",
        lambda module: captured.update(module=module)
        or types.SimpleNamespace(execute_info_module=lambda: None),
    )

    info_module.main()

    assert captured["module"].params == {
        "target_type": "COMPARTMENT",
        "level": "DIMENSION",
        "lifecycle_state": "DELETED",
    }
    spec = captured["argument_spec"]
    assert captured["required_one_of"] == [
        ["alarm_suppression_id", "alarm_id", "compartment_id"]
    ]
    assert captured["required_if"] == [
        ["target_type", "alarm", ["alarm_id"]],
        ["target_type", "compartment", ["compartment_id"]],
    ]
    assert captured["required_by"] == {
        "compartment_id_in_subtree": ["compartment_id"],
        "is_all_suppressions": ["alarm_id"],
    }
    assert captured["mutually_exclusive"] == [
        ["alarm_id", "compartment_id_in_subtree"]
    ]
    assert captured["supports_check_mode"] is True
    assert spec["alarm_suppression_id"] == {"type": "str"}
    assert spec["is_all_suppressions"] == {"type": "bool"}
    assert spec["target_type"]["choices"] == ["alarm", "compartment"]
    assert spec["lifecycle_state"]["choices"] == ["active", "deleted"]


def test_info_module_class_metadata(monkeypatch):
    install_fake_oci(monkeypatch)

    cls = load_collection_module("oci_alarm_suppression_info").OciAlarmSuppressionInfoModule

    assert cls.results_key == "alarm_suppressions"
    assert cls.resource_id_param == "alarm_suppression_id"
    assert cls.resource_get_method == "get_alarm_suppression"
    assert cls.list_resource_method == "list_alarm_suppressions"


def test_fetch_resources_prefers_get_by_id(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_alarm_suppression_info")
    get_calls = []
    suppression = FakeModel(id=SUPPRESSION_ID, display_name="maintenance")

    def get_alarm_suppression(alarm_suppression_id):
        get_calls.append(alarm_suppression_id)
        return types.SimpleNamespace(data=suppression)

    instance = make_module_instance(
        info_module,
        "OciAlarmSuppressionInfoModule",
        {"alarm_suppression_id": SUPPRESSION_ID},
        client=types.SimpleNamespace(get_alarm_suppression=get_alarm_suppression),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.fetch_resources() == [suppression]
    assert get_calls == [SUPPRESSION_ID]


def test_fetch_resources_returns_empty_on_404(monkeypatch):
    service_error = install_fake_oci(monkeypatch)[1]

    info_module = load_collection_module("oci_alarm_suppression_info")
    instance = make_module_instance(
        info_module,
        "OciAlarmSuppressionInfoModule",
        {"alarm_suppression_id": SUPPRESSION_ID},
        client=types.SimpleNamespace(get_alarm_suppression=None),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: raising(service_error(404))(),
    )

    assert instance.fetch_resources() == []


def test_fetch_resources_passes_filters_and_filters_by_name(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_alarm_suppression_info")
    list_calls = []
    wanted = FakeModel(id=SUPPRESSION_ID, display_name="wanted")
    other = FakeModel(id="ocid1.alarmsuppression.oc1..b", display_name="other")

    instance = make_module_instance(
        info_module,
        "OciAlarmSuppressionInfoModule",
        {
            "alarm_suppression_id": None,
            "alarm_id": ALARM_ID,
            "compartment_id": None,
            "is_all_suppressions": True,
            "level": "ALARM",
            "name": "wanted",
        },
        client=types.SimpleNamespace(list_alarm_suppressions=object()),
    )

    def fake_list_all(fn, **kwargs):
        list_calls.append(kwargs)
        return [wanted, other]

    monkeypatch.setattr(instance, "list_all_resources", fake_list_all)

    assert instance.fetch_resources() == [wanted]
    assert list_calls == [
        {"alarm_id": ALARM_ID, "is_all_suppressions": True, "level": "ALARM"}
    ]


def test_execute_info_module_exits_with_serialized_suppressions(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_alarm_suppression_info")
    instance = make_module_instance(
        info_module,
        "OciAlarmSuppressionInfoModule",
        {"alarm_id": ALARM_ID},
    )
    monkeypatch.setattr(
        instance,
        "fetch_resources",
        lambda: [FakeModel(id=SUPPRESSION_ID, display_name="maintenance")],
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()

    payload = exc_info.value.payload
    assert payload["changed"] is False
    assert payload["alarm_suppressions"] == [
        {"id": SUPPRESSION_ID, "name": "maintenance"}
    ]
