from __future__ import absolute_import, division, print_function

__metaclass__ = type

import types

import pytest

from conftest import (
    DummyModule,
    FakeModel,
    FakeResponse,
    FailJsonCalled,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)

VOLUME_BACKUP_POLICY_MODEL_NAMES = (
    "CreateVolumeBackupPolicyDetails",
    "UpdateVolumeBackupPolicyDetails",
    "VolumeBackupSchedule",
    "RetentionDuration",
)


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(
        monkeypatch,
        model_names=VOLUME_BACKUP_POLICY_MODEL_NAMES,
    )


def make_policy_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciVolumeBackupPolicyModule",
        params,
        client=client,
    )


def daily_schedule(**overrides):
    schedule = {
        "backup_type": "incremental",
        "period": "one_day",
        "offset_type": "structured",
        "hour_of_day": 2,
        "retention_seconds": 604800,
        "time_zone": "utc",
    }
    schedule.update(overrides)
    return schedule


def test_main_exposes_expected_arguments_without_waiters(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_backup_policy")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        return DummyModule({})

    class FakePolicyModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciVolumeBackupPolicyModule", FakePolicyModule)

    module_obj.main()

    argument_spec = captured["argument_spec"]
    schedule_options = argument_spec["schedules"]["options"]
    assert captured["run_called"] is True
    assert argument_spec["volume_backup_policy_id"] == {"type": "str"}
    assert argument_spec["name"] == {"type": "str"}
    assert argument_spec["destination_region"] == {"type": "str"}
    assert "wait" not in argument_spec
    assert schedule_options["backup_type"] == {
        "type": "str",
        "choices": ["full", "incremental"],
        "required": True,
    }
    assert schedule_options["period"]["required"] is True
    assert schedule_options["retention_seconds"] == {
        "type": "int",
        "required": True,
    }
    assert schedule_options["retention_period"]["options"]["retention_time_unit"][
        "choices"
    ] == ["days", "years"]
    assert "is_prevent_deletion_enabled" not in schedule_options
    assert "is_retention_lock_enabled" not in schedule_options


def test_build_create_details_normalizes_schedule_and_retention(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_backup_policy")
    details = module_obj.build_create_volume_backup_policy_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "daily-policy",
            "destination_region": "us-ashburn-1",
            "schedules": [
                daily_schedule(
                    retention_period={
                        "retention_time_amount": 7,
                        "retention_time_unit": "days",
                    },
                    prevent_deletion_enabled=True,
                    retention_lock_enabled=False,
                )
            ],
            "freeform_tags": {"phase": "create"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        }
    )

    schedule = details.schedules[0]
    assert details.compartment_id == "ocid1.compartment.oc1..example"
    assert details.display_name == "daily-policy"
    assert details.destination_region == "us-ashburn-1"
    assert schedule.backup_type == "INCREMENTAL"
    assert schedule.period == "ONE_DAY"
    assert schedule.offset_type == "STRUCTURED"
    assert schedule.time_zone == "UTC"
    assert schedule.retention_period.retention_time_amount == 7
    assert schedule.retention_period.retention_time_unit == "DAYS"
    assert schedule.is_prevent_deletion_enabled is True
    assert schedule.is_retention_lock_enabled is False
    assert details.freeform_tags == {"phase": "create"}


def test_build_create_details_omits_unset_optional_fields(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_backup_policy")
    details = module_obj.build_create_volume_backup_policy_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "empty-policy",
        }
    )

    assert details.compartment_id == "ocid1.compartment.oc1..example"
    assert details.display_name == "empty-policy"
    assert not hasattr(details, "destination_region")
    assert not hasattr(details, "schedules")
    assert not hasattr(details, "freeform_tags")


def test_build_schedules_preserves_explicit_empty_list(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_backup_policy")

    assert module_obj.build_schedules(None) is None
    assert module_obj.build_schedules([]) == []


def test_schedule_comparison_is_normalized_and_order_insensitive(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_backup_policy")
    desired = [
        daily_schedule(),
        daily_schedule(
            backup_type="full",
            period="one_week",
            day_of_week="sunday",
            retention_seconds=1209600,
        ),
    ]
    current = [
        {
            "backup_type": "FULL",
            "period": "ONE_WEEK",
            "offset_type": "STRUCTURED",
            "hour_of_day": 2,
            "day_of_week": "SUNDAY",
            "retention_seconds": 1209600,
            "time_zone": "UTC",
            "month": None,
            "offset_seconds": 3600,
        },
        {
            "backup_type": "INCREMENTAL",
            "period": "ONE_DAY",
            "offset_type": "STRUCTURED",
            "hour_of_day": 2,
            "retention_seconds": 604800,
            "time_zone": "UTC",
        },
    ]

    assert module_obj.schedules_match(current, desired) is True


def test_build_update_plan_detects_schedule_change(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_backup_policy")
    desired = [daily_schedule(hour_of_day=4)]
    instance = make_policy_module(module_obj, {"schedules": desired})
    resource = FakeModel(
        id="ocid1.volumebackuppolicy.oc1..example",
        schedules=[FakeModel(**daily_schedule(hour_of_day=2))],
    )

    update_plan = instance.build_update_plan(resource)

    assert update_plan["update_needed"] is True
    assert update_plan["update_model_fields"]["schedules"] == desired


def test_build_update_plan_preserves_empty_schedule_update(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_backup_policy")
    instance = make_policy_module(module_obj, {"schedules": []})
    resource = FakeModel(
        id="ocid1.volumebackuppolicy.oc1..example",
        schedules=[FakeModel(**daily_schedule())],
    )

    update_plan = instance.build_update_plan(resource)

    assert update_plan["update_needed"] is True
    assert update_plan["update_model_fields"]["schedules"] == []


def test_destination_region_none_is_idempotent_after_reset(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_backup_policy")
    instance = make_policy_module(
        module_obj,
        {"destination_region": "none"},
    )
    resource = FakeModel(
        id="ocid1.volumebackuppolicy.oc1..example",
        destination_region=None,
    )

    assert instance.needs_update(resource) is False


def test_build_update_details_wraps_schedule_models(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_backup_policy")
    instance = make_policy_module(module_obj, {})
    details = instance.build_update_details(
        {
            "display_name": "updated-policy",
            "schedules": [daily_schedule()],
        }
    )

    assert details.display_name == "updated-policy"
    assert len(details.schedules) == 1
    assert details.schedules[0].backup_type == "INCREMENTAL"
    assert details.schedules[0].period == "ONE_DAY"


def test_create_resource_uses_synchronous_policy_api(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_backup_policy")
    create_calls = []

    def create_volume_backup_policy(create_volume_backup_policy_details):
        create_calls.append(create_volume_backup_policy_details)
        return FakeResponse(data=FakeModel(id="ocid1.volumebackuppolicy.oc1..example"))

    instance = make_policy_module(
        module_obj,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "daily-policy",
        },
        client=types.SimpleNamespace(
            create_volume_backup_policy=create_volume_backup_policy
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    resource = instance.create_resource()

    assert resource.id == "ocid1.volumebackuppolicy.oc1..example"
    assert create_calls[0].display_name == "daily-policy"


def test_update_resource_uses_synchronous_policy_api(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_backup_policy")
    update_calls = []

    def update_volume_backup_policy(policy_id, update_volume_backup_policy_details):
        update_calls.append((policy_id, update_volume_backup_policy_details))
        return FakeResponse(data=FakeModel(id=policy_id, display_name="updated-policy"))

    instance = make_policy_module(
        module_obj,
        {
            "name": "updated-policy",
            "destination_region": "none",
        },
        client=types.SimpleNamespace(
            update_volume_backup_policy=update_volume_backup_policy
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    resource = FakeModel(
        id="ocid1.volumebackuppolicy.oc1..example",
        display_name="current-policy",
        destination_region="us-ashburn-1",
    )

    updated = instance.update_resource(resource)

    assert updated.display_name == "updated-policy"
    assert update_calls[0][0] == resource.id
    assert update_calls[0][1].display_name == "updated-policy"
    assert update_calls[0][1].destination_region == "none"


def test_get_resource_uses_synchronous_policy_api(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_backup_policy")
    get_calls = []

    def get_volume_backup_policy(policy_id):
        get_calls.append(policy_id)
        return FakeResponse(data=FakeModel(id=policy_id))

    instance = make_policy_module(
        module_obj,
        {},
        client=types.SimpleNamespace(get_volume_backup_policy=get_volume_backup_policy),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    response = instance.get_resource_response("ocid1.volumebackuppolicy.oc1..example")

    assert response.data.id == "ocid1.volumebackuppolicy.oc1..example"
    assert get_calls == ["ocid1.volumebackuppolicy.oc1..example"]


def test_delete_resource_uses_synchronous_policy_api(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_backup_policy")
    delete_calls = []

    def delete_volume_backup_policy(policy_id):
        delete_calls.append(policy_id)
        return FakeResponse(data=None)

    instance = make_policy_module(
        module_obj,
        {},
        client=types.SimpleNamespace(
            delete_volume_backup_policy=delete_volume_backup_policy
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    resource = FakeModel(id="ocid1.volumebackuppolicy.oc1..example")

    assert instance.delete_resource(resource) is None
    assert delete_calls == [resource.id]


def test_create_required_fields_are_enforced(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_backup_policy")
    instance = make_policy_module(
        module_obj,
        {"compartment_id": "ocid1.compartment.oc1..example"},
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "name" in exc_info.value.payload["msg"]


def test_name_lookup_requires_compartment_id(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_backup_policy")
    instance = make_policy_module(module_obj, {"name": "daily-policy"})

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.find_resources_by_name()

    assert "compartment_id" in exc_info.value.payload["msg"]


def test_name_lookup_lists_only_the_requested_compartment(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_backup_policy")
    requested_filters = []
    list_method = object()
    instance = make_policy_module(
        module_obj,
        {
            "name": "daily-policy",
            "compartment_id": "ocid1.compartment.oc1..example",
        },
        client=types.SimpleNamespace(list_volume_backup_policies=list_method),
    )

    def list_all_resources(method, **kwargs):
        requested_filters.append((method, kwargs))
        return [
            FakeModel(id="matching-policy", display_name="daily-policy"),
            FakeModel(id="other-policy", display_name="other-policy"),
        ]

    monkeypatch.setattr(instance, "list_all_resources", list_all_resources)

    matches = instance.find_resources_by_name()

    assert [resource.id for resource in matches] == ["matching-policy"]
    assert requested_filters == [
        (
            list_method,
            {"compartment_id": "ocid1.compartment.oc1..example"},
        )
    ]


def test_compartment_change_is_rejected(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_backup_policy")
    instance = make_policy_module(
        module_obj,
        {"compartment_id": "ocid1.compartment.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.volumebackuppolicy.oc1..example",
        compartment_id="ocid1.compartment.oc1..current",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "compartment_id" in exc_info.value.payload["msg"]
