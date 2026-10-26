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


def install_fake_oci(monkeypatch):
    oci_module, service_error = shared_install_fake_oci(monkeypatch)
    oci_module.monitoring = types.SimpleNamespace(
        MonitoringClient=type("FakeMonitoringClient", (), {}),
        models=types.SimpleNamespace(),
    )
    return oci_module, service_error


def test_main_wiring(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_alarm_info")
    captured = {}

    class FakeAnsibleModule:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(info_module, "AnsibleModule", FakeAnsibleModule)
    monkeypatch.setattr(
        info_module,
        "OciAlarmInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )

    info_module.main()

    spec = captured["argument_spec"]
    assert captured["required_one_of"] == [["compartment_id", "alarm_id"]]
    assert captured["supports_check_mode"] is True
    assert spec["alarm_id"] == {"type": "str"}
    assert spec["name"] == {"type": "str"}
    assert spec["compartment_id"] == {"type": "str"}
    assert spec["compartment_id_in_subtree"] == {"type": "bool"}
    assert spec["include_details"] == {"type": "bool", "default": False}
    assert spec["lifecycle_state"] == {
        "type": "str",
        "choices": ["active", "deleting", "deleted"],
    }


def test_info_module_class_metadata(monkeypatch):
    install_fake_oci(monkeypatch)

    cls = load_collection_module("oci_alarm_info").OciAlarmInfoModule

    assert cls.results_key == "alarms"
    assert cls.resource_id_param == "alarm_id"
    assert cls.resource_get_method == "get_alarm"
    assert cls.list_resource_method == "list_alarms"
    assert tuple(cls.list_filter_params) == (
        "compartment_id",
        "lifecycle_state",
        "compartment_id_in_subtree",
    )
    assert cls.name_filter_param == "name"
    assert cls.name_response_field == "display_name"


def test_fetch_resources_prefers_get_by_id(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_alarm_info")
    get_calls = []
    alarm = FakeModel(id="ocid1.alarm.oc1..example", display_name="example-alarm")

    def get_alarm(alarm_id):
        get_calls.append(alarm_id)
        return types.SimpleNamespace(data=alarm)

    instance = make_module_instance(
        info_module,
        "OciAlarmInfoModule",
        {"alarm_id": "ocid1.alarm.oc1..example"},
        client=types.SimpleNamespace(get_alarm=get_alarm),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.fetch_resources() == [alarm]
    assert get_calls == ["ocid1.alarm.oc1..example"]


def test_fetch_resources_returns_empty_on_404(monkeypatch):
    service_error = install_fake_oci(monkeypatch)[1]

    info_module = load_collection_module("oci_alarm_info")
    instance = make_module_instance(
        info_module,
        "OciAlarmInfoModule",
        {"alarm_id": "ocid1.alarm.oc1..missing"},
        client=types.SimpleNamespace(get_alarm=lambda alarm_id: None),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: raising(service_error(404))(),
    )

    assert instance.fetch_resources() == []


def test_fetch_resources_passes_filters_and_filters_by_name(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_alarm_info")
    list_calls = []
    wanted = FakeModel(id="ocid1.alarm.oc1..a", display_name="wanted")
    other = FakeModel(id="ocid1.alarm.oc1..b", display_name="other")

    instance = make_module_instance(
        info_module,
        "OciAlarmInfoModule",
        {
            "compartment_id": "ocid1.tenancy.oc1..example",
            "alarm_id": None,
            "name": "wanted",
            "lifecycle_state": "deleted",
            "compartment_id_in_subtree": True,
        },
        client=types.SimpleNamespace(list_alarms=object()),
    )

    def fake_list_all(fn, **kwargs):
        list_calls.append(kwargs)
        return [wanted, other]

    monkeypatch.setattr(instance, "list_all_resources", fake_list_all)

    assert instance.fetch_resources() == [wanted]
    assert list_calls == [
        {
            "compartment_id": "ocid1.tenancy.oc1..example",
            "lifecycle_state": "DELETED",
            "compartment_id_in_subtree": True,
        }
    ]


def test_fetch_resources_fetches_details_for_listed_alarms(monkeypatch):
    service_error = install_fake_oci(monkeypatch)[1]

    info_module = load_collection_module("oci_alarm_info")
    summaries = [
        FakeModel(id="ocid1.alarm.oc1..a", display_name="first"),
        FakeModel(id="ocid1.alarm.oc1..gone", display_name="second"),
    ]
    detailed = FakeModel(id="ocid1.alarm.oc1..a", display_name="first", body="CPU is high")
    get_calls = []

    def get_alarm(alarm_id):
        get_calls.append(alarm_id)
        if alarm_id == "ocid1.alarm.oc1..gone":
            raise service_error(404)
        return types.SimpleNamespace(data=detailed)

    instance = make_module_instance(
        info_module,
        "OciAlarmInfoModule",
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "alarm_id": None,
            "include_details": True,
        },
        client=types.SimpleNamespace(list_alarms=object(), get_alarm=get_alarm),
    )
    monkeypatch.setattr(instance, "list_all_resources", lambda fn, **kwargs: summaries)
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.fetch_resources() == [detailed]
    assert get_calls == ["ocid1.alarm.oc1..a", "ocid1.alarm.oc1..gone"]


def test_fetch_resources_skips_details_by_default(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_alarm_info")
    summary = FakeModel(id="ocid1.alarm.oc1..a", display_name="first")

    instance = make_module_instance(
        info_module,
        "OciAlarmInfoModule",
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "alarm_id": None,
            "include_details": False,
        },
        client=types.SimpleNamespace(list_alarms=object(), get_alarm=raising(AssertionError())),
    )
    monkeypatch.setattr(instance, "list_all_resources", lambda fn, **kwargs: [summary])

    assert instance.fetch_resources() == [summary]


def test_execute_info_module_exits_with_serialized_alarms(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_alarm_info")
    instance = make_module_instance(
        info_module,
        "OciAlarmInfoModule",
        {"compartment_id": "ocid1.compartment.oc1..example"},
    )
    monkeypatch.setattr(
        instance,
        "fetch_resources",
        lambda: [
            FakeModel(id="ocid1.alarm.oc1..example", display_name="example-alarm")
        ],
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()

    payload = exc_info.value.payload
    assert payload["changed"] is False
    assert payload["alarms"] == [
        {"id": "ocid1.alarm.oc1..example", "name": "example-alarm"}
    ]
