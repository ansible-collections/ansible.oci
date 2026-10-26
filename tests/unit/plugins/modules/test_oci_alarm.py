from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    FailJsonCalled,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)


ALARM_MODEL_NAMES = (
    "CreateAlarmDetails",
    "UpdateAlarmDetails",
    "AlarmOverride",
)
ALARM_ID = "ocid1.alarm.oc1..example"


def install_fake_oci(monkeypatch):
    oci_module, service_error = shared_install_fake_oci(monkeypatch)
    oci_module.monitoring = types.SimpleNamespace(
        MonitoringClient=type("FakeMonitoringClient", (), {}),
        models=types.SimpleNamespace(
            **{model_name: FakeModel for model_name in ALARM_MODEL_NAMES}
        ),
    )
    return oci_module, service_error


def make_alarm_module(module_obj, params, client=None, check_mode=False):
    instance = make_module_instance(
        module_obj,
        "OciAlarmModule",
        params,
        client=client,
        check_mode=check_mode,
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    return instance


def load_alarm_module(monkeypatch):
    install_fake_oci(monkeypatch)
    return load_collection_module("oci_alarm")


def test_main_wires_argument_spec_and_normalizes_choices(monkeypatch):
    module_obj = load_alarm_module(monkeypatch)
    captured = {}
    params = {
        "severity": "critical",
        "message_format": "pretty_json",
        "overrides": [{"rule_name": "r", "severity": "warning"}],
    }

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        captured["supports_check_mode"] = kwargs.get("supports_check_mode")
        return DummyModule(params)

    class FakeAlarmModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciAlarmModule", FakeAlarmModule)

    module_obj.main()

    spec = captured["argument_spec"]
    assert captured["run_called"] is True
    assert captured["supports_check_mode"] is True
    assert spec["alarm_id"] == {"type": "str"}
    assert spec["is_enabled"] == {"type": "bool"}
    assert spec["severity"]["choices"] == ["critical", "error", "warning", "info"]
    assert spec["message_format"]["choices"] == ["raw", "pretty_json", "ons_optimized"]
    assert spec["destinations"] == {"type": "list", "elements": "str"}
    assert spec["overrides"]["options"]["rule_name"] == {"type": "str", "required": True}
    assert spec["overrides"]["options"]["severity"]["choices"] == [
        "critical", "error", "warning", "info",
    ]
    assert "suppression" not in spec
    assert "display_name" not in spec
    assert params["severity"] == "CRITICAL"
    assert params["message_format"] == "PRETTY_JSON"
    assert params["overrides"][0]["severity"] == "WARNING"


def test_class_metadata(monkeypatch):
    cls = load_alarm_module(monkeypatch).OciAlarmModule

    assert cls.resource_id_param == "alarm_id"
    assert cls.list_resource_method == "list_alarms"
    assert cls.update_method_name == "update_alarm"
    assert cls.update_details_name == "update_alarm_details"
    assert cls.create_resource_name == "alarm"


def test_build_create_alarm_details_maps_fields_and_overrides(monkeypatch):
    alarm_module = load_alarm_module(monkeypatch)

    details = alarm_module.build_create_alarm_details(
        {
            "name": "high-cpu",
            "compartment_id": "ocid1.compartment.oc1..c",
            "metric_compartment_id": "ocid1.compartment.oc1..m",
            "namespace": "oci_computeagent",
            "query": "CpuUtilization[1m].mean() > 80",
            "severity": "CRITICAL",
            "destinations": ["ocid1.onstopic.oc1..t"],
            "is_enabled": True,
            "resolution": None,
            "freeform_tags": {"env": "dev"},
            "overrides": [
                {
                    "rule_name": "r1",
                    "severity": "WARNING",
                    "query": "q",
                    "body": None,
                    "pending_duration": None,
                }
            ],
        }
    )

    assert details.display_name == "high-cpu"
    assert not hasattr(details, "name")
    assert details.compartment_id == "ocid1.compartment.oc1..c"
    assert details.severity == "CRITICAL"
    assert details.destinations == ["ocid1.onstopic.oc1..t"]
    assert details.is_enabled is True
    assert details.freeform_tags == {"env": "dev"}
    assert not hasattr(details, "resolution")
    assert len(details.overrides) == 1
    override = details.overrides[0]
    assert isinstance(override, FakeModel)
    assert override.rule_name == "r1"
    assert override.severity == "WARNING"
    assert override.query == "q"
    assert not hasattr(override, "body")


def test_build_create_alarm_details_enables_alarm_by_default(monkeypatch):
    alarm_module = load_alarm_module(monkeypatch)

    details = alarm_module.build_create_alarm_details(
        {"name": "high-cpu", "is_enabled": None}
    )

    assert details.is_enabled is True


def test_build_create_alarm_details_keeps_disabled_alarm(monkeypatch):
    alarm_module = load_alarm_module(monkeypatch)

    details = alarm_module.build_create_alarm_details(
        {"name": "high-cpu", "is_enabled": False}
    )

    assert details.is_enabled is False


def test_create_resource_calls_create_alarm(monkeypatch):
    alarm_module = load_alarm_module(monkeypatch)
    create_calls = []

    def create_alarm(create_alarm_details):
        create_calls.append(create_alarm_details)
        return FakeResponse(data=FakeModel(id=ALARM_ID, lifecycle_state="ACTIVE"))

    instance = make_alarm_module(
        alarm_module,
        {"name": "high-cpu", "severity": "INFO", "wait": False},
        client=types.SimpleNamespace(create_alarm=create_alarm),
    )

    resource = instance.create_resource()

    assert create_calls[0].display_name == "high-cpu"
    assert create_calls[0].severity == "INFO"
    assert resource.id == ALARM_ID


def test_present_check_mode_creates_nothing(monkeypatch):
    alarm_module = load_alarm_module(monkeypatch)
    calls = []
    instance = make_alarm_module(
        alarm_module,
        {
            "state": "present",
            "name": "high-cpu",
            "compartment_id": "ocid1.compartment.oc1..c",
            "metric_compartment_id": "ocid1.compartment.oc1..m",
            "namespace": "ns",
            "query": "q",
            "severity": "INFO",
            "destinations": ["t"],
        },
        client=types.SimpleNamespace(create_alarm=lambda **kw: calls.append(kw)),
        check_mode=True,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload == {"changed": True}
    assert calls == []


def test_create_fails_without_required_fields(monkeypatch):
    alarm_module = load_alarm_module(monkeypatch)
    instance = make_alarm_module(
        alarm_module, {"state": "present", "name": "high-cpu"}
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert "namespace" in exc_info.value.payload["msg"]


def test_hydrate_named_resource_refetches_with_get_alarm(monkeypatch):
    alarm_module = load_alarm_module(monkeypatch)
    full = FakeModel(id=ALARM_ID, resolution="1m")
    get_calls = []

    def get_alarm(alarm_id):
        get_calls.append(alarm_id)
        return FakeResponse(data=full)

    instance = make_alarm_module(
        alarm_module, {}, client=types.SimpleNamespace(get_alarm=get_alarm)
    )

    assert instance.hydrate_named_resource(FakeModel(id=ALARM_ID)) is full
    assert get_calls == [ALARM_ID]


def matching_resource(**overrides):
    attrs = dict(
        id=ALARM_ID,
        display_name="high-cpu",
        compartment_id="ocid1.compartment.oc1..c",
        metric_compartment_id="ocid1.compartment.oc1..m",
        namespace="oci_computeagent",
        query="q",
        severity="CRITICAL",
        destinations=["b", "a"],
        is_enabled=True,
        pending_duration="PT5M",
        overrides=[
            {"rule_name": "r1", "severity": "WARNING", "query": "q1",
             "body": "default body", "pending_duration": "PT1M"},
            {"rule_name": "r2", "severity": "INFO", "query": "q2",
             "body": None, "pending_duration": None},
        ],
    )
    attrs.update(overrides)
    return FakeModel(**attrs)


MATCHING_PARAMS = {
    "name": "high-cpu",
    "compartment_id": "ocid1.compartment.oc1..c",
    "metric_compartment_id": "ocid1.compartment.oc1..m",
    "namespace": "oci_computeagent",
    "query": "q",
    "severity": "CRITICAL",
    "destinations": ["a", "b"],
    "is_enabled": True,
    "overrides": [
        {"rule_name": "r1", "severity": "WARNING", "query": "q1",
         "body": None, "pending_duration": None},
        {"rule_name": "r2", "severity": "INFO", "query": "q2",
         "body": None, "pending_duration": None},
    ],
}


def test_needs_update_false_when_resource_matches(monkeypatch):
    alarm_module = load_alarm_module(monkeypatch)
    instance = make_alarm_module(alarm_module, dict(MATCHING_PARAMS))

    assert instance.needs_update(matching_resource()) is False


def test_update_sends_only_changed_fields(monkeypatch):
    alarm_module = load_alarm_module(monkeypatch)
    update_calls = []

    def update_alarm(alarm_id, update_alarm_details):
        update_calls.append((alarm_id, update_alarm_details))
        return FakeResponse(data=FakeModel(id=alarm_id))

    params = dict(MATCHING_PARAMS, name="renamed", is_enabled=False, wait=False)
    instance = make_alarm_module(
        alarm_module,
        params,
        client=types.SimpleNamespace(update_alarm=update_alarm),
    )

    instance.update_resource(matching_resource())

    alarm_id, details = update_calls[0]
    assert alarm_id == ALARM_ID
    assert details.display_name == "renamed"
    assert details.is_enabled is False
    assert vars(details).keys() == {"display_name", "is_enabled"}


def test_needs_update_ignores_omitted_is_enabled(monkeypatch):
    alarm_module = load_alarm_module(monkeypatch)
    instance = make_alarm_module(
        alarm_module, dict(MATCHING_PARAMS, is_enabled=None)
    )

    assert instance.needs_update(matching_resource(is_enabled=False)) is False


def test_update_builds_override_models(monkeypatch):
    alarm_module = load_alarm_module(monkeypatch)
    update_calls = []

    def update_alarm(alarm_id, update_alarm_details):
        update_calls.append(update_alarm_details)
        return FakeResponse(data=FakeModel(id=alarm_id))

    params = dict(
        MATCHING_PARAMS,
        overrides=[{"rule_name": "r2", "severity": "ERROR", "query": None,
                    "body": None, "pending_duration": None}],
        wait=False,
    )
    instance = make_alarm_module(
        alarm_module,
        params,
        client=types.SimpleNamespace(update_alarm=update_alarm),
    )

    instance.update_resource(matching_resource())

    overrides = update_calls[0].overrides
    assert len(overrides) == 1
    assert isinstance(overrides[0], FakeModel)
    assert overrides[0].rule_name == "r2"
    assert overrides[0].severity == "ERROR"
    assert not hasattr(overrides[0], "query")


def test_overrides_order_change_triggers_update(monkeypatch):
    alarm_module = load_alarm_module(monkeypatch)
    params = dict(MATCHING_PARAMS, overrides=list(reversed(MATCHING_PARAMS["overrides"])))
    instance = make_alarm_module(alarm_module, params)

    assert instance.needs_update(matching_resource()) is True


def test_overrides_length_change_triggers_update(monkeypatch):
    alarm_module = load_alarm_module(monkeypatch)
    params = dict(MATCHING_PARAMS, overrides=MATCHING_PARAMS["overrides"][:1])
    instance = make_alarm_module(alarm_module, params)

    assert instance.needs_update(matching_resource()) is True


def test_compare_ordered_subset_list_handles_missing_current(monkeypatch):
    alarm_module = load_alarm_module(monkeypatch)
    instance = make_alarm_module(alarm_module, {})

    assert instance.compare_update_field_values(
        None, [{"rule_name": "r"}], compare="ordered_subset_list"
    ) is True
    assert instance.compare_update_field_values(
        [{"rule_name": "r", "body": "x"}], [{"rule_name": "r"}],
        compare="ordered_subset_list",
    ) is False
    assert instance.compare_update_field_values(
        ["b", "a"], ["a", "b"], compare="sorted_list"
    ) is False


def test_immutable_compartment_id_fails(monkeypatch):
    alarm_module = load_alarm_module(monkeypatch)
    params = dict(MATCHING_PARAMS, compartment_id="ocid1.compartment.oc1..other")
    instance = make_alarm_module(alarm_module, params)

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(matching_resource())

    assert "compartment_id" in exc_info.value.payload["msg"]


def test_delete_resource_calls_delete_alarm(monkeypatch):
    alarm_module = load_alarm_module(monkeypatch)
    delete_calls = []

    def delete_alarm(alarm_id):
        delete_calls.append(alarm_id)
        return FakeResponse(data=None)

    instance = make_alarm_module(
        alarm_module,
        {"wait": True},
        client=types.SimpleNamespace(delete_alarm=delete_alarm),
    )
    waits = []
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: waits.append(target_states),
    )

    instance.delete_resource(FakeModel(id=ALARM_ID))

    assert delete_calls == [ALARM_ID]
    assert waits and "DELETED" in waits[0]


def test_absent_check_mode_does_not_delete(monkeypatch):
    alarm_module = load_alarm_module(monkeypatch)
    instance = make_alarm_module(
        alarm_module, {"state": "absent", "alarm_id": ALARM_ID}, check_mode=True
    )
    monkeypatch.setattr(
        instance, "resolve_target_resource", lambda: FakeModel(id=ALARM_ID)
    )
    monkeypatch.setattr(
        instance,
        "delete_resource",
        lambda resource: pytest.fail("delete must not run in check mode"),
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload == {"changed": True}


def test_absent_when_missing_is_unchanged(monkeypatch):
    alarm_module = load_alarm_module(monkeypatch)
    instance = make_alarm_module(
        alarm_module, {"state": "absent", "alarm_id": ALARM_ID}
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload == {"changed": False}
