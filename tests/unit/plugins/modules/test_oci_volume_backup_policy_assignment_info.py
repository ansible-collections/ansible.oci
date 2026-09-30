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
)


ASSET_ID = "ocid1.volume.oc1..example"
ASSIGNMENT_ID = "ocid1.volumebackuppolicyassignment.oc1..example"


def load_info_module(monkeypatch):
    fake_oci, ServiceError = install_fake_oci(monkeypatch)
    fake_oci.core.BlockstorageClient = type("BlockstorageClient", (), {})
    return load_collection_module("oci_volume_backup_policy_assignment_info"), ServiceError


def run_info(module_obj, client, params):
    instance = make_module_instance(
        module_obj,
        "OciVolumeBackupPolicyAssignmentInfoModule",
        params,
        client=client,
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_info_module()
    return result.value.payload


def assignment():
    return FakeModel(
        id=ASSIGNMENT_ID,
        asset_id=ASSET_ID,
        policy_id="ocid1.volumebackuppolicy.oc1..example",
        time_created="2026-09-27T00:00:00Z",
    )


def test_info_by_asset_returns_assignment_fields(monkeypatch):
    module_obj = load_info_module(monkeypatch)[0]
    requests = []

    def by_asset(asset_id):
        requests.append(asset_id)
        return FakeResponse([assignment()])

    client = types.SimpleNamespace(get_volume_backup_policy_asset_assignment=by_asset)

    result = run_info(module_obj, client, {"asset_id": ASSET_ID})

    assert result == {
        "changed": False,
        "volume_backup_policy_assignments": [
            {
                "id": ASSIGNMENT_ID,
                "asset_id": ASSET_ID,
                "policy_id": "ocid1.volumebackuppolicy.oc1..example",
                "time_created": "2026-09-27T00:00:00Z",
            }
        ],
    }
    assert requests == [ASSET_ID]


def test_info_by_assignment_id_returns_one_resource(monkeypatch):
    module_obj = load_info_module(monkeypatch)[0]
    requests = []

    def by_id(policy_assignment_id):
        requests.append(policy_assignment_id)
        return FakeResponse(assignment())

    client = types.SimpleNamespace(get_volume_backup_policy_assignment=by_id)

    result = run_info(
        module_obj, client, {"volume_backup_policy_assignment_id": ASSIGNMENT_ID}
    )

    assert result["changed"] is False
    assert result["volume_backup_policy_assignments"][0]["id"] == ASSIGNMENT_ID
    assert requests == [ASSIGNMENT_ID]


def test_info_returns_empty_list_when_asset_has_no_assignment(monkeypatch):
    module_obj = load_info_module(monkeypatch)[0]
    client = types.SimpleNamespace(
        get_volume_backup_policy_asset_assignment=lambda asset_id: FakeResponse([])
    )

    result = run_info(module_obj, client, {"asset_id": ASSET_ID})

    assert result == {"changed": False, "volume_backup_policy_assignments": []}


def test_info_returns_empty_list_for_missing_assignment_id(monkeypatch):
    module_obj, ServiceError = load_info_module(monkeypatch)

    def by_id(policy_assignment_id):
        raise ServiceError(404, "not found")

    client = types.SimpleNamespace(get_volume_backup_policy_assignment=by_id)

    result = run_info(
        module_obj, client, {"volume_backup_policy_assignment_id": ASSIGNMENT_ID}
    )

    assert result == {"changed": False, "volume_backup_policy_assignments": []}


def test_info_requires_exactly_one_lookup_identifier(monkeypatch):
    module_obj = load_info_module(monkeypatch)[0]
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule({})

    class FakeInfoModule:
        def __init__(self, module):
            pass

        def execute_info_module(self):
            pass

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciVolumeBackupPolicyAssignmentInfoModule", FakeInfoModule)

    module_obj.main()

    assert captured["required_one_of"] == [
        ["asset_id", "volume_backup_policy_assignment_id"]
    ]
    assert captured["mutually_exclusive"] == [
        ["asset_id", "volume_backup_policy_assignment_id"]
    ]
    assert captured["supports_check_mode"] is True
