from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types
from datetime import datetime, timezone

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


SUPPRESSION_MODEL_NAMES = (
    "CreateAlarmSuppressionDetails",
    "AlarmSuppressionAlarmTarget",
    "AlarmSuppressionCompartmentTarget",
    "Recurrence",
)
SUPPRESSION_ID = "ocid1.alarmsuppression.oc1..example"
ALARM_ID = "ocid1.alarm.oc1..example"
COMPARTMENT_ID = "ocid1.compartment.oc1..example"
TIME_FROM = datetime(2026, 11, 3, 1, 0, tzinfo=timezone.utc)
TIME_UNTIL = datetime(2026, 11, 3, 5, 0, tzinfo=timezone.utc)


def install_fake_oci(monkeypatch):
    oci_module, service_error = shared_install_fake_oci(monkeypatch)
    oci_module.monitoring = types.SimpleNamespace(
        MonitoringClient=type("FakeMonitoringClient", (), {}),
        models=types.SimpleNamespace(
            **{model_name: FakeModel for model_name in SUPPRESSION_MODEL_NAMES}
        ),
    )
    return oci_module, service_error


def load_suppression_module(monkeypatch):
    install_fake_oci(monkeypatch)
    return load_collection_module("oci_alarm_suppression")


def make_suppression_module(module_obj, params, client=None, check_mode=False):
    instance = make_module_instance(
        module_obj,
        "OciAlarmSuppressionModule",
        params,
        client=client,
        check_mode=check_mode,
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    return instance


def matching_resource(**overrides):
    attrs = dict(
        id=SUPPRESSION_ID,
        display_name="maintenance",
        compartment_id=COMPARTMENT_ID,
        alarm_suppression_target={"target_type": "ALARM", "alarm_id": ALARM_ID},
        level="ALARM",
        description="planned",
        dimensions={},
        time_suppress_from=TIME_FROM,
        time_suppress_until=TIME_UNTIL,
        suppression_conditions=[
            {
                "condition_type": "RECURRENCE",
                "suppression_recurrence": "FREQ=DAILY;BYHOUR=2",
                "suppression_duration": "PT2H",
            }
        ],
        freeform_tags={"env": "dev"},
        lifecycle_state="ACTIVE",
    )
    attrs.update(overrides)
    return FakeModel(**attrs)


MATCHING_PARAMS = {
    "name": "maintenance",
    "alarm_id": ALARM_ID,
    "level": "ALARM",
    "description": "planned",
    "time_suppress_from": TIME_FROM,
    "time_suppress_until": TIME_UNTIL,
    "suppression_conditions": [
        {
            "condition_type": "RECURRENCE",
            "suppression_recurrence": "FREQ=DAILY;BYHOUR=2",
            "suppression_duration": "PT2H",
        }
    ],
    "freeform_tags": {"env": "dev"},
}


def test_main_wires_argument_spec_and_normalizes_inputs(monkeypatch):
    module_obj = load_suppression_module(monkeypatch)
    captured = {}
    params = {
        "level": "alarm",
        "time_suppress_from": "2026-11-03T01:00:00Z",
        "time_suppress_until": "2026-11-03T05:00:00.000+00:00",
        "suppression_conditions": [{"condition_type": "recurrence"}],
    }

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule(params)

    class FakeSuppressionModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciAlarmSuppressionModule", FakeSuppressionModule)

    module_obj.main()

    spec = captured["argument_spec"]
    assert captured["run_called"] is True
    assert captured["supports_check_mode"] is True
    assert captured["mutually_exclusive"] == [
        ["alarm_id", "compartment_id"],
        ["alarm_id", "compartment_id_in_subtree"],
    ]
    assert captured["required_by"] == {
        "compartment_id_in_subtree": ["compartment_id"]
    }
    assert spec["alarm_suppression_id"] == {"type": "str"}
    assert spec["level"]["choices"] == ["alarm", "dimension"]
    conditions = spec["suppression_conditions"]["options"]
    assert conditions["condition_type"]["default"] == "recurrence"
    assert conditions["suppression_recurrence"] == {"type": "str", "required": True}
    assert params["level"] == "ALARM"
    assert params["suppression_conditions"][0]["condition_type"] == "RECURRENCE"
    assert params["time_suppress_from"] == TIME_FROM
    assert params["time_suppress_until"] == TIME_UNTIL


@pytest.mark.parametrize(
    "value",
    ["2026-11-03T01:00:00", "2026-11-03", "tomorrow"],
)
def test_normalize_time_parameters_rejects_invalid_values(monkeypatch, value):
    module_obj = load_suppression_module(monkeypatch)
    module = DummyModule({"time_suppress_from": value, "time_suppress_until": None})

    with pytest.raises(FailJsonCalled) as exc_info:
        module_obj.normalize_time_parameters(module)

    assert "time_suppress_from" in exc_info.value.payload["msg"]


def test_class_metadata(monkeypatch):
    cls = load_suppression_module(monkeypatch).OciAlarmSuppressionModule

    assert cls.resource_id_param == "alarm_suppression_id"
    assert cls.list_resource_method == "list_alarm_suppressions"
    assert cls.common_list_filter_params == ()
    assert cls.update_method_name is None
    assert all(spec.is_mutable is False for spec in cls.common_update_field_specs)
    assert all(spec.is_mutable is False for spec in cls.update_field_specs)


def test_build_create_details_for_alarm_target(monkeypatch):
    module_obj = load_suppression_module(monkeypatch)

    details = module_obj.build_create_alarm_suppression_details(
        dict(MATCHING_PARAMS, dimensions=None, defined_tags=None)
    )

    assert details.display_name == "maintenance"
    assert details.alarm_suppression_target.alarm_id == ALARM_ID
    assert details.level == "ALARM"
    assert details.time_suppress_from == TIME_FROM
    assert details.freeform_tags == {"env": "dev"}
    assert not hasattr(details, "dimensions")
    assert not hasattr(details, "defined_tags")
    condition = details.suppression_conditions[0]
    assert isinstance(condition, FakeModel)
    assert vars(condition) == {
        "suppression_recurrence": "FREQ=DAILY;BYHOUR=2",
        "suppression_duration": "PT2H",
    }


def test_build_create_details_for_compartment_target(monkeypatch):
    module_obj = load_suppression_module(monkeypatch)

    details = module_obj.build_create_alarm_suppression_details(
        {
            "name": "nightly",
            "compartment_id": COMPARTMENT_ID,
            "compartment_id_in_subtree": True,
            "time_suppress_from": TIME_FROM,
            "time_suppress_until": TIME_UNTIL,
        }
    )

    assert vars(details.alarm_suppression_target) == {
        "compartment_id": COMPARTMENT_ID,
        "compartment_id_in_subtree": True,
    }
    assert not hasattr(details, "suppression_conditions")


@pytest.mark.parametrize(
    "params, expected_filters",
    [
        ({"alarm_id": ALARM_ID, "name": "n"}, {"alarm_id": ALARM_ID}),
        (
            {"compartment_id": COMPARTMENT_ID, "name": "n"},
            {"compartment_id": COMPARTMENT_ID},
        ),
    ],
)
def test_name_lookup_is_scoped_to_target(monkeypatch, params, expected_filters):
    module_obj = load_suppression_module(monkeypatch)
    list_calls = []
    instance = make_suppression_module(module_obj, params)
    match = FakeModel(
        id=SUPPRESSION_ID,
        display_name="n",
        lifecycle_state="ACTIVE",
        alarm_suppression_target={"target_type": instance.target_type},
    )
    other = FakeModel(id="other", display_name="x", lifecycle_state="ACTIVE")

    def fake_list_all(list_fn, **kwargs):
        list_calls.append(kwargs)
        return [match, other]

    instance.client = types.SimpleNamespace(list_alarm_suppressions=None)
    monkeypatch.setattr(instance, "list_all_resources", fake_list_all)

    assert instance.resolve_resource_by_name() is match
    assert list_calls == [expected_filters]


def test_compartment_name_lookup_skips_alarm_targeted_match(monkeypatch):
    module_obj = load_suppression_module(monkeypatch)
    instance = make_suppression_module(
        module_obj, {"compartment_id": COMPARTMENT_ID, "name": "n"}
    )
    alarm_targeted = FakeModel(
        id="alarm-targeted",
        display_name="n",
        lifecycle_state="ACTIVE",
        alarm_suppression_target={"target_type": "ALARM", "alarm_id": ALARM_ID},
    )

    def fake_list_all(list_fn, **kwargs):
        return [alarm_targeted]

    instance.client = types.SimpleNamespace(list_alarm_suppressions=None)
    monkeypatch.setattr(instance, "list_all_resources", fake_list_all)

    assert instance.resolve_resource_by_name() is None


def test_name_lookup_requires_target_scope(monkeypatch):
    module_obj = load_suppression_module(monkeypatch)
    instance = make_suppression_module(module_obj, {"name": "n"})

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.find_resources_by_name()

    msg = exc_info.value.payload["msg"]
    assert "one of" in msg
    assert "alarm_id" in msg
    assert "compartment_id" in msg


def test_needs_update_false_when_resource_matches(monkeypatch):
    module_obj = load_suppression_module(monkeypatch)
    instance = make_suppression_module(module_obj, dict(MATCHING_PARAMS))

    assert instance.needs_update(matching_resource()) is False


def test_needs_update_ignores_omitted_options(monkeypatch):
    module_obj = load_suppression_module(monkeypatch)
    instance = make_suppression_module(
        module_obj, {"name": "maintenance", "alarm_id": ALARM_ID}
    )

    assert instance.needs_update(matching_resource()) is False


@pytest.mark.parametrize(
    "param_name, value",
    [
        ("name", "renamed"),
        ("description", "changed"),
        ("level", "DIMENSION"),
        ("time_suppress_until", datetime(2026, 11, 3, 6, 0, tzinfo=timezone.utc)),
        ("suppression_conditions", []),
        ("freeform_tags", {"env": "prod"}),
        ("alarm_id", "ocid1.alarm.oc1..other"),
    ],
)
def test_changed_option_fails_as_immutable(monkeypatch, param_name, value):
    module_obj = load_suppression_module(monkeypatch)
    instance = make_suppression_module(
        module_obj, dict(MATCHING_PARAMS, **{param_name: value})
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(matching_resource())

    msg = exc_info.value.payload["msg"]
    assert param_name in msg
    assert "OCI does not support updating alarm suppressions" in msg


@pytest.mark.parametrize(
    "returned_rule",
    [
        "FREQ=DAILY;BYHOUR=2",
        "RRULE:FREQ=DAILY;BYHOUR=2",
        "BYHOUR=2;FREQ=DAILY",
        "FREQ=DAILY;BYHOUR=2;BYMINUTE=0;BYSECOND=0",
        # The exact form OCI returned in integration testing.
        "FREQ=DAILY;BYHOUR=02;BYMINUTE=00;BYSECOND=00",
        "freq=daily;byhour=2",
    ],
)
def test_equivalent_recurrence_rule_is_unchanged(monkeypatch, returned_rule):
    module_obj = load_suppression_module(monkeypatch)
    instance = make_suppression_module(module_obj, dict(MATCHING_PARAMS))
    resource = matching_resource(
        suppression_conditions=[
            {
                "condition_type": "RECURRENCE",
                "suppression_recurrence": returned_rule,
                "suppression_duration": "PT2H",
            }
        ]
    )

    assert instance.needs_update(resource) is False


def test_unreported_suppression_conditions_are_not_drift(monkeypatch):
    module_obj = load_suppression_module(monkeypatch)
    instance = make_suppression_module(module_obj, dict(MATCHING_PARAMS))
    resource = matching_resource(suppression_conditions=None)

    assert instance.needs_update(resource) is False


def test_changed_recurrence_rule_fails_with_values(monkeypatch):
    module_obj = load_suppression_module(monkeypatch)
    instance = make_suppression_module(module_obj, dict(MATCHING_PARAMS))
    resource = matching_resource(
        suppression_conditions=[
            {
                "condition_type": "RECURRENCE",
                "suppression_recurrence": "FREQ=WEEKLY;BYDAY=MO",
                "suppression_duration": "PT2H",
            }
        ]
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    msg = exc_info.value.payload["msg"]
    assert "FREQ=WEEKLY;BYDAY=MO" in msg
    assert "FREQ=DAILY;BYHOUR=2" in msg


def test_compartment_target_mismatch_fails(monkeypatch):
    module_obj = load_suppression_module(monkeypatch)
    instance = make_suppression_module(
        module_obj, {"compartment_id": COMPARTMENT_ID, "compartment_id_in_subtree": True}
    )
    resource = matching_resource(
        alarm_suppression_target={
            "target_type": "COMPARTMENT",
            "compartment_id": COMPARTMENT_ID,
            "compartment_id_in_subtree": False,
        }
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "compartment_id_in_subtree" in exc_info.value.payload["msg"]


def test_present_existing_resource_is_unchanged(monkeypatch):
    module_obj = load_suppression_module(monkeypatch)
    instance = make_suppression_module(module_obj, dict(MATCHING_PARAMS, state="present"))
    monkeypatch.setattr(instance, "resolve_target_resource", matching_resource)

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload["changed"] is False
    assert exc_info.value.payload["resource"]["id"] == SUPPRESSION_ID
    assert exc_info.value.payload["resource"]["name"] == "maintenance"


def test_hydrate_named_resource_refetches_with_get_alarm_suppression(monkeypatch):
    module_obj = load_suppression_module(monkeypatch)
    full = FakeModel(
        id=SUPPRESSION_ID,
        suppression_conditions=[{"condition_type": "RECURRENCE"}],
    )
    get_calls = []

    def get_alarm_suppression(alarm_suppression_id):
        get_calls.append(alarm_suppression_id)
        return FakeResponse(data=full)

    instance = make_suppression_module(
        module_obj,
        {},
        client=types.SimpleNamespace(get_alarm_suppression=get_alarm_suppression),
    )

    summary = FakeModel(id=SUPPRESSION_ID)
    assert instance.hydrate_named_resource(summary) is full
    assert get_calls == [SUPPRESSION_ID]


def test_create_resource_calls_create_alarm_suppression(monkeypatch):
    module_obj = load_suppression_module(monkeypatch)
    create_calls = []

    def create_alarm_suppression(create_alarm_suppression_details):
        create_calls.append(create_alarm_suppression_details)
        return FakeResponse(data=FakeModel(id=SUPPRESSION_ID))

    instance = make_suppression_module(
        module_obj,
        dict(MATCHING_PARAMS, wait=False),
        client=types.SimpleNamespace(create_alarm_suppression=create_alarm_suppression),
    )

    resource = instance.create_resource()

    assert create_calls[0].display_name == "maintenance"
    assert resource.id == SUPPRESSION_ID


def test_present_check_mode_creates_nothing(monkeypatch):
    module_obj = load_suppression_module(monkeypatch)
    calls = []
    instance = make_suppression_module(
        module_obj,
        dict(MATCHING_PARAMS, state="present"),
        client=types.SimpleNamespace(create_alarm_suppression=lambda **kw: calls.append(kw)),
        check_mode=True,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload == {"changed": True}
    assert calls == []


def test_create_fails_without_required_fields(monkeypatch):
    module_obj = load_suppression_module(monkeypatch)
    instance = make_suppression_module(
        module_obj, {"state": "present", "name": "n", "alarm_id": ALARM_ID}
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert "time_suppress_from" in exc_info.value.payload["msg"]


def test_create_fails_without_target(monkeypatch):
    module_obj = load_suppression_module(monkeypatch)
    instance = make_suppression_module(
        module_obj,
        {
            "state": "present",
            "name": "n",
            "time_suppress_from": TIME_FROM,
            "time_suppress_until": TIME_UNTIL,
        },
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.execute_resource_module()

    msg = exc_info.value.payload["msg"]
    assert "one of" in msg
    assert "alarm_id" in msg
    assert "compartment_id" in msg


def test_delete_resource_calls_delete_alarm_suppression(monkeypatch):
    module_obj = load_suppression_module(monkeypatch)
    delete_calls = []

    def delete_alarm_suppression(alarm_suppression_id):
        delete_calls.append(alarm_suppression_id)
        return FakeResponse(data=None)

    instance = make_suppression_module(
        module_obj,
        {"wait": True},
        client=types.SimpleNamespace(delete_alarm_suppression=delete_alarm_suppression),
    )
    waits = []
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: waits.append(target_states),
    )

    instance.delete_resource(FakeModel(id=SUPPRESSION_ID))

    assert delete_calls == [SUPPRESSION_ID]
    assert waits and "DELETED" in waits[0]


def test_absent_check_mode_does_not_delete(monkeypatch):
    module_obj = load_suppression_module(monkeypatch)
    instance = make_suppression_module(
        module_obj,
        {"state": "absent", "alarm_suppression_id": SUPPRESSION_ID},
        check_mode=True,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", matching_resource)
    monkeypatch.setattr(
        instance,
        "delete_resource",
        lambda resource: pytest.fail("delete must not run in check mode"),
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload == {"changed": True}


def test_absent_when_missing_is_unchanged(monkeypatch):
    module_obj = load_suppression_module(monkeypatch)
    instance = make_suppression_module(
        module_obj, {"state": "absent", "alarm_suppression_id": SUPPRESSION_ID}
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload == {"changed": False}
