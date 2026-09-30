from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from .conftest import (
    ExitJsonCalled,
    FailJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
)

ASSET_ID = "ocid1.volume.oc1..example"
POLICY_ID = "ocid1.volumebackuppolicy.oc1..first"
OTHER_POLICY_ID = "ocid1.volumebackuppolicy.oc1..second"


def assignment(policy_id=POLICY_ID, asset_id=ASSET_ID):
    return FakeModel(
        id="ocid1.volumebackuppolicyassignment.oc1..old",
        asset_id=asset_id,
        policy_id=policy_id,
        time_created="2026-09-26T00:00:00Z",
    )


class AssignmentClient:
    def __init__(self, assignment=None):
        self.assignment = assignment
        self.create_calls = []
        self.delete_calls = []
        self.next_id = 1
        self.create_error = None

    def get_volume_backup_policy_asset_assignment(self, asset_id):
        if self.assignment and self.assignment.asset_id == asset_id:
            return FakeResponse([self.assignment])
        return FakeResponse([])

    def create_volume_backup_policy_assignment(
        self, create_volume_backup_policy_assignment_details
    ):
        details = create_volume_backup_policy_assignment_details
        self.create_calls.append(details)
        if self.create_error:
            raise self.create_error
        self.assignment = FakeModel(
            id=f"ocid1.volumebackuppolicyassignment.oc1..{self.next_id}",
            asset_id=details.asset_id,
            policy_id=details.policy_id,
            time_created="2026-09-27T00:00:00Z",
        )
        self.next_id += 1
        return FakeResponse(self.assignment)

    def delete_volume_backup_policy_assignment(self, policy_assignment_id):
        self.delete_calls.append(policy_assignment_id)
        assert self.assignment.id == policy_assignment_id
        self.assignment = None
        return FakeResponse(None)


def load_assignment_module(monkeypatch):
    fake_oci, ServiceError = install_fake_oci(
        monkeypatch,
        model_names=("CreateVolumeBackupPolicyAssignmentDetails",),
    )
    fake_oci.core.BlockstorageClient = type("BlockstorageClient", (), {})
    return load_collection_module("oci_volume_backup_policy_assignment"), ServiceError


def run_assignment(module_obj, client, params, check_mode=False):
    instance = make_module_instance(
        module_obj,
        "OciVolumeBackupPolicyAssignmentModule",
        params,
        client=client,
        check_mode=check_mode,
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    return result.value.payload


def test_replacing_policy_and_repeat_is_idempotent(monkeypatch):
    module_obj = load_assignment_module(monkeypatch)[0]
    client = AssignmentClient(assignment())
    params = {"state": "present", "asset_id": ASSET_ID, "policy_id": OTHER_POLICY_ID}

    replaced = run_assignment(module_obj, client, params)
    repeated = run_assignment(module_obj, client, params)

    assert replaced["changed"] is True
    assert replaced["resource"]["policy_id"] == OTHER_POLICY_ID
    assert repeated["changed"] is False
    assert len(client.create_calls) == 1
    assert client.create_calls[0].asset_id == ASSET_ID
    assert client.create_calls[0].policy_id == OTHER_POLICY_ID
    assert client.delete_calls == []


@pytest.mark.parametrize("asset_type", ["volume", "bootvolume", "volumegroup"])
def test_create_assignment_and_repeat_is_idempotent(monkeypatch, asset_type):
    module_obj = load_assignment_module(monkeypatch)[0]
    client = AssignmentClient()
    asset_id = f"ocid1.{asset_type}.oc1..example"
    params = {"state": "present", "asset_id": asset_id, "policy_id": POLICY_ID}

    created = run_assignment(module_obj, client, params)
    repeated = run_assignment(module_obj, client, params)

    assert created["changed"] is True
    assert created["resource"] == {
        "id": "ocid1.volumebackuppolicyassignment.oc1..1",
        "asset_id": asset_id,
        "policy_id": POLICY_ID,
        "time_created": "2026-09-27T00:00:00Z",
    }
    assert repeated == {"changed": False, "resource": created["resource"]}
    assert len(client.create_calls) == 1
    assert client.delete_calls == []


def test_delete_assignment_and_repeat_is_idempotent(monkeypatch):
    module_obj = load_assignment_module(monkeypatch)[0]
    current = assignment()
    client = AssignmentClient(current)
    params = {"state": "absent", "asset_id": ASSET_ID}

    deleted = run_assignment(module_obj, client, params)
    repeated = run_assignment(module_obj, client, params)

    assert deleted == {"changed": True}
    assert repeated == {"changed": False}
    assert client.delete_calls == [current.id]


@pytest.mark.parametrize(
    "initial,params",
    [
        (None, {"state": "present", "asset_id": ASSET_ID, "policy_id": POLICY_ID}),
        (
            assignment(),
            {"state": "present", "asset_id": ASSET_ID, "policy_id": OTHER_POLICY_ID},
        ),
        (assignment(), {"state": "absent", "asset_id": ASSET_ID}),
    ],
)
def test_check_mode_reports_change_without_mutation(monkeypatch, initial, params):
    module_obj = load_assignment_module(monkeypatch)[0]
    client = AssignmentClient(initial)

    result = run_assignment(module_obj, client, params, check_mode=True)

    assert result == {"changed": True}
    assert client.assignment is initial
    assert client.create_calls == []
    assert client.delete_calls == []


def test_group_owned_assignment_is_not_deleted_from_member_volume(monkeypatch):
    module_obj = load_assignment_module(monkeypatch)[0]
    current = assignment(asset_id="ocid1.volumegroup.oc1..example")
    client = AssignmentClient(current)
    client.get_volume_backup_policy_asset_assignment = lambda asset_id: FakeResponse(
        [current]
    )

    with pytest.raises(FailJsonCalled) as result:
        run_assignment(module_obj, client, {"state": "absent", "asset_id": ASSET_ID})

    assert "volume group" in result.value.payload["msg"].lower()
    assert client.assignment is current
    assert client.delete_calls == []


def test_oci_rejection_includes_asset_and_group_guidance(monkeypatch):
    module_obj, ServiceError = load_assignment_module(monkeypatch)
    client = AssignmentClient()
    client.create_error = ServiceError(409, "assignment controlled by volume group")

    with pytest.raises(FailJsonCalled) as result:
        run_assignment(
            module_obj,
            client,
            {"state": "present", "asset_id": ASSET_ID, "policy_id": POLICY_ID},
        )

    assert ASSET_ID in result.value.payload["msg"]
    assert "assignment controlled by volume group" in result.value.payload["msg"]
    assert "volume group" in result.value.payload["msg"].lower()
