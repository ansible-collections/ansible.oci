from __future__ import absolute_import, division, print_function

__metaclass__ = type

import types

import pytest

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


def make_info_module(module_obj, params, client):
    return make_module_instance(
        module_obj,
        "OciVolumeBackupPolicyInfoModule",
        params,
        client=client,
    )


def test_main_allows_unscoped_query_in_check_mode(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_volume_backup_policy_info")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule({})

    class FakeInfoModule:
        def __init__(self, module):
            pass

        def execute_info_module(self):
            captured["executed"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciVolumeBackupPolicyInfoModule", FakeInfoModule)

    module_obj.main()

    assert captured["executed"] is True
    assert captured["supports_check_mode"] is True
    assert "required_one_of" not in captured
    assert captured["argument_spec"]["volume_backup_policy_id"] == {"type": "str"}
    assert captured["argument_spec"]["compartment_id"] == {"type": "str"}
    assert captured["argument_spec"]["name"] == {"type": "str"}


def test_get_by_id_uses_policy_id_even_with_compartment(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_volume_backup_policy_info")
    get_calls = []

    def get_policy(**kwargs):
        get_calls.append(kwargs)
        return FakeResponse(data=FakeModel(id=kwargs["policy_id"]))

    instance = make_info_module(
        module_obj,
        {
            "volume_backup_policy_id": "ocid1.volumebackuppolicy.oc1..example",
            "compartment_id": "ocid1.compartment.oc1..example",
        },
        types.SimpleNamespace(get_volume_backup_policy=get_policy),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        raising(AssertionError("ID lookup must not list policies")),
    )

    resources = instance.fetch_resources()

    assert [resource.id for resource in resources] == [
        "ocid1.volumebackuppolicy.oc1..example"
    ]
    assert get_calls == [{"policy_id": "ocid1.volumebackuppolicy.oc1..example"}]


def test_list_without_compartment_omits_compartment_filter(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_volume_backup_policy_info")
    list_calls = []
    oracle_policy = FakeModel(id="oracle-policy", display_name="gold")
    instance = make_info_module(
        module_obj,
        {},
        types.SimpleNamespace(list_volume_backup_policies="list_method"),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda method, **kwargs: list_calls.append((method, kwargs)) or [oracle_policy],
    )

    assert instance.fetch_resources() == [oracle_policy]
    assert list_calls == [("list_method", {})]


def test_compartment_list_filters_name_locally(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_volume_backup_policy_info")
    list_calls = []
    matching = FakeModel(id="matching", display_name="daily")
    other = FakeModel(id="other", display_name="weekly")
    instance = make_info_module(
        module_obj,
        {"compartment_id": "ocid1.compartment.oc1..example", "name": "daily"},
        types.SimpleNamespace(list_volume_backup_policies="list_method"),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda method, **kwargs: list_calls.append((method, kwargs))
        or [other, matching],
    )

    assert instance.fetch_resources() == [matching]
    assert list_calls == [
        ("list_method", {"compartment_id": "ocid1.compartment.oc1..example"})
    ]


def test_info_result_serializes_policy_as_unchanged_list(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_volume_backup_policy_info")
    policy = FakeModel(
        id="ocid1.volumebackuppolicy.oc1..example",
        display_name="daily",
        compartment_id="ocid1.compartment.oc1..example",
        destination_region=None,
        schedules=[
            FakeModel(
                backup_type="INCREMENTAL",
                period="ONE_DAY",
                retention_seconds=604800,
            )
        ],
        freeform_tags={"phase": "create"},
        defined_tags={},
        time_created="2026-09-27T10:00:00Z",
    )
    instance = make_info_module(
        module_obj,
        {"volume_backup_policy_id": policy.id},
        types.SimpleNamespace(
            get_volume_backup_policy=lambda **kwargs: FakeResponse(data=policy)
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()

    assert exc_info.value.payload == {
        "changed": False,
        "volume_backup_policies": [
            {
                "id": "ocid1.volumebackuppolicy.oc1..example",
                "name": "daily",
                "compartment_id": "ocid1.compartment.oc1..example",
                "destination_region": None,
                "schedules": [
                    {
                        "backup_type": "INCREMENTAL",
                        "period": "ONE_DAY",
                        "retention_seconds": 604800,
                    }
                ],
                "freeform_tags": {"phase": "create"},
                "defined_tags": {},
                "time_created": "2026-09-27T10:00:00Z",
            }
        ],
    }


def test_missing_policy_returns_empty_list(monkeypatch):
    _oci_module, ServiceError = install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_volume_backup_policy_info")

    def missing_policy(**kwargs):
        raise ServiceError(404, "missing")

    instance = make_info_module(
        module_obj,
        {"volume_backup_policy_id": "ocid1.volumebackuppolicy.oc1..missing"},
        types.SimpleNamespace(get_volume_backup_policy=missing_policy),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()

    assert exc_info.value.payload == {"changed": False, "volume_backup_policies": []}
