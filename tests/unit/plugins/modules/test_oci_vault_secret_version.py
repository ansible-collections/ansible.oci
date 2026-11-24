from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types
from datetime import datetime, timedelta, timezone

import pytest

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FailJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)

SECRET_ID = "ocid1.vaultsecret.oc1..example"
SCHEDULED_AT = datetime(2026, 2, 1, tzinfo=timezone.utc)


class NotFound(Exception):
    status = 404


def install_fake_oci(monkeypatch):
    oci_module, service_error = shared_install_fake_oci(monkeypatch)
    oci_module.vault = types.SimpleNamespace(
        VaultsClient=type("FakeVaultsClient", (), {}),
        models=types.SimpleNamespace(ScheduleSecretVersionDeletionDetails=FakeModel),
    )
    oci_module.wait_calls = []

    def fake_wait_until(wait_client, response, *args, **kwargs):
        oci_module.wait_calls.append(kwargs)
        evaluate_response = kwargs["evaluate_response"]
        fetch_func = kwargs["fetch_func"]
        polls = 0
        while not evaluate_response(response):
            polls += 1
            if polls > 10:
                raise AssertionError("fake wait_until: condition never met")
            response = fetch_func(response=response)
        return response

    oci_module.wait_until = fake_wait_until
    return oci_module, service_error


def load_module():
    return load_collection_module("oci_vault_secret_version")


def make_version(version_number=1, stages=("DEPRECATED",), name=None, deletion=None):
    return FakeModel(
        secret_id=SECRET_ID,
        version_number=version_number,
        name=name,
        stages=list(stages) if stages is not None else None,
        time_of_deletion=deletion,
    )


class FakeVaultsClient:
    """Serve secret versions and apply deletion changes after ``lag`` polls.

    Like OCI, each deletion change keeps the owning secret ``UPDATING`` for
    ``secret_lag`` polls of ``get_secret``.
    """

    def __init__(self, versions, lag=0, secret_lag=0):
        self.versions = {version.version_number: version for version in versions}
        self.lag = lag
        self.secret_lag = secret_lag
        self.secret_updating_polls = 0
        self.pending = {}
        self.calls = []
        self.get_count = 0
        self.secret_get_count = 0

    def get_secret(self, secret_id):
        self.secret_get_count += 1
        assert secret_id == SECRET_ID
        state = "ACTIVE"
        if self.secret_updating_polls > 0:
            self.secret_updating_polls -= 1
            state = "UPDATING"
        return FakeResponse(FakeModel(id=SECRET_ID, lifecycle_state=state))

    def get_secret_version(self, secret_id, secret_version_number):
        self.get_count += 1
        assert secret_id == SECRET_ID
        change = self.pending.get(secret_version_number)
        if change is not None:
            if change["lag"] > 0:
                change["lag"] -= 1
            else:
                self.versions[secret_version_number].time_of_deletion = change["value"]
                del self.pending[secret_version_number]
        if secret_version_number not in self.versions:
            raise NotFound()
        return FakeResponse(self.versions[secret_version_number])

    def list_secret_versions(self, secret_id):
        self.calls.append(("list_secret_versions", secret_id))
        return list(self.versions.values())

    def schedule_secret_version_deletion(
        self,
        secret_id,
        secret_version_number,
        schedule_secret_version_deletion_details,
    ):
        self.calls.append(
            (
                "schedule_secret_version_deletion",
                secret_id,
                secret_version_number,
                schedule_secret_version_deletion_details,
            )
        )
        value = getattr(
            schedule_secret_version_deletion_details,
            "time_of_deletion",
            SCHEDULED_AT,
        )
        self.pending[secret_version_number] = {"value": value, "lag": self.lag}
        self.secret_updating_polls = self.secret_lag
        return FakeResponse(None)

    def cancel_secret_version_deletion(self, secret_id, secret_version_number):
        self.calls.append(
            ("cancel_secret_version_deletion", secret_id, secret_version_number)
        )
        self.pending[secret_version_number] = {"value": None, "lag": self.lag}
        self.secret_updating_polls = self.secret_lag
        return FakeResponse(None)

    def mutating_calls(self):
        return [
            call
            for call in self.calls
            if call[0]
            in ("schedule_secret_version_deletion", "cancel_secret_version_deletion")
        ]


def build_instance(module_obj, params, client, check_mode=False):
    full_params = {
        "state": "present",
        "secret_id": SECRET_ID,
        "version_number": 1,
        "version_name": None,
        "deletion_days": None,
        "wait": False,
        "wait_timeout": 60,
        "wait_interval": 5,
    }
    full_params.update(params)
    instance = make_module_instance(
        module_obj,
        "OciVaultSecretVersionModule",
        full_params,
        client=client,
        check_mode=check_mode,
    )
    instance.call_with_retry = lambda fn, *args, **kwargs: fn(*args, **kwargs)
    instance.list_all_resources = lambda fn, **kwargs: fn(**kwargs)
    return instance


def run_module(module_obj, params, client, check_mode=False):
    instance = build_instance(module_obj, params, client, check_mode)
    with pytest.raises(ExitJsonCalled) as excinfo:
        instance.execute_resource_module()
    return excinfo.value.payload


def run_failing_module(module_obj, params, client, check_mode=False):
    instance = build_instance(module_obj, params, client, check_mode)
    with pytest.raises(FailJsonCalled) as excinfo:
        instance.execute_resource_module()
    return excinfo.value.payload["msg"]


def test_main_wires_argument_spec_and_runs_module(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule({})

    class FakeVersionModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciVaultSecretVersionModule", FakeVersionModule)

    module_obj.main()

    spec = captured["argument_spec"]
    assert captured["run_called"] is True
    assert captured["supports_check_mode"] is True
    assert captured["required_one_of"] == [["version_number", "version_name"]]
    assert captured["mutually_exclusive"] == [["version_number", "version_name"]]
    assert spec["state"] == {
        "type": "str",
        "choices": ["present", "absent"],
        "default": "present",
    }
    assert spec["secret_id"] == {"type": "str", "required": True}
    assert spec["version_number"] == {"type": "int"}
    assert spec["version_name"] == {"type": "str"}
    assert spec["deletion_days"] == {"type": "int"}
    assert spec["wait"] == {"type": "bool", "default": True}
    assert "freeform_tags" not in spec
    assert "name" not in spec
    assert "compartment_id" not in spec


def test_class_metadata(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    cls = module_obj.OciVaultSecretVersionModule

    assert cls.client_class.fget(None) is module_obj.oci.vault.VaultsClient
    assert cls.resource_id_param == "version_number"
    assert cls.resource_id_field == "version_number"
    assert cls.list_resource_method == "list_secret_versions"
    assert cls.common_list_filter_params == ("secret_id",)
    assert cls.name_lookup_param == "version_name"
    assert cls.name_response_field == "name"
    assert cls.create_resource_name == "secret version"
    assert cls.update_field_specs == ()
    assert cls.common_update_field_specs == ()


def test_create_resource_is_not_supported(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    instance = build_instance(module_obj, {}, FakeVaultsClient([]))

    with pytest.raises(NotImplementedError):
        instance.create_resource()


@pytest.mark.parametrize("check_mode", [False, True])
def test_present_unscheduled_version_is_unchanged(monkeypatch, check_mode):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeVaultsClient([make_version(1)])

    payload = run_module(module_obj, {}, client, check_mode=check_mode)

    assert payload["changed"] is False
    assert payload["resource"]["version_number"] == 1
    assert payload["resource"]["time_of_deletion"] is None
    assert client.mutating_calls() == []


def test_present_scheduled_version_check_mode_reports_change_only(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeVaultsClient([make_version(1, deletion=SCHEDULED_AT)])

    payload = run_module(module_obj, {}, client, check_mode=True)

    assert payload == {"changed": True}
    assert client.mutating_calls() == []


def test_present_scheduled_version_is_cancelled_without_waiting(monkeypatch):
    oci_module = install_fake_oci(monkeypatch)[0]
    module_obj = load_module()
    client = FakeVaultsClient([make_version(1, deletion=SCHEDULED_AT)])

    payload = run_module(module_obj, {"wait": False}, client)

    assert payload["changed"] is True
    assert payload["resource"]["time_of_deletion"] is None
    assert client.mutating_calls() == [
        ("cancel_secret_version_deletion", SECRET_ID, 1)
    ]
    assert oci_module.wait_calls == []


def test_present_waits_until_the_deletion_is_cancelled(monkeypatch):
    oci_module = install_fake_oci(monkeypatch)[0]
    module_obj = load_module()
    client = FakeVaultsClient([make_version(1, deletion=SCHEDULED_AT)], lag=2)

    payload = run_module(module_obj, {"wait": True}, client)

    assert payload["changed"] is True
    assert payload["resource"]["time_of_deletion"] is None
    assert client.versions[1].time_of_deletion is None
    assert client.get_count > 3
    assert len(oci_module.wait_calls) == 2
    for wait_call in oci_module.wait_calls:
        assert wait_call["max_wait_seconds"] == 60
        assert wait_call["max_interval_seconds"] == 5


def test_present_rerun_after_cancel_is_unchanged(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeVaultsClient([make_version(1, deletion=SCHEDULED_AT)])

    run_module(module_obj, {}, client)
    payload = run_module(module_obj, {}, client)

    assert payload["changed"] is False
    assert len(client.mutating_calls()) == 1


def test_present_missing_version_number_fails_in_every_mode(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()

    for check_mode in (False, True):
        client = FakeVaultsClient([make_version(1)])
        message = run_failing_module(
            module_obj, {"version_number": 7}, client, check_mode=check_mode
        )

        assert "version_number=7" in message
        assert SECRET_ID in message
        assert "ansible.oci.oci_vault_secret" in message
        assert client.mutating_calls() == []


def test_present_missing_version_name_fails(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeVaultsClient([make_version(1, name="other")])

    message = run_failing_module(
        module_obj,
        {"version_number": None, "version_name": "wanted"},
        client,
        check_mode=True,
    )

    assert "version_name=wanted" in message
    assert "ansible.oci.oci_vault_secret" in message


def test_present_finds_version_by_name_and_refetches_it(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeVaultsClient(
        [make_version(1, name="first"), make_version(2, name="second", deletion=SCHEDULED_AT)]
    )

    payload = run_module(
        module_obj, {"version_number": None, "version_name": "second"}, client
    )

    assert payload["changed"] is True
    assert client.mutating_calls() == [
        ("cancel_secret_version_deletion", SECRET_ID, 2)
    ]
    assert payload["resource"]["version_number"] == 2
    assert payload["resource"]["name"] == "second"


def test_present_ambiguous_version_name_fails(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeVaultsClient(
        [make_version(1, name="same"), make_version(2, name="same")]
    )

    message = run_failing_module(
        module_obj, {"version_number": None, "version_name": "same"}, client
    )

    assert "version_number" in message
    assert "2 matches" in message


@pytest.mark.parametrize("missing", ["number", "name"])
def test_absent_missing_version_is_unchanged(monkeypatch, missing):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeVaultsClient([make_version(1, name="other")])
    params = {"state": "absent"}
    if missing == "number":
        params["version_number"] = 7
    else:
        params.update(version_number=None, version_name="wanted")

    payload = run_module(module_obj, params, client)

    assert payload == {"changed": False}
    assert client.mutating_calls() == []


@pytest.mark.parametrize("check_mode", [False, True])
def test_absent_already_scheduled_version_is_unchanged(monkeypatch, check_mode):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeVaultsClient([make_version(1, deletion=SCHEDULED_AT)])

    payload = run_module(
        module_obj, {"state": "absent"}, client, check_mode=check_mode
    )

    assert payload == {"changed": False}
    assert client.mutating_calls() == []


def test_absent_already_scheduled_current_version_is_unchanged(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeVaultsClient(
        [make_version(1, stages=("CURRENT", "LATEST"), deletion=SCHEDULED_AT)]
    )

    payload = run_module(module_obj, {"state": "absent"}, client)

    assert payload == {"changed": False}


@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize("stages", [("CURRENT", "LATEST"), ("PREVIOUS",), None])
def test_absent_fails_for_a_version_that_is_not_deprecated(
    monkeypatch, check_mode, stages
):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeVaultsClient([make_version(1, stages=stages)])

    message = run_failing_module(
        module_obj, {"state": "absent"}, client, check_mode=check_mode
    )

    assert "Secret version 1 cannot be scheduled for deletion" in message
    assert "DEPRECATED" in message
    assert client.mutating_calls() == []


def test_absent_deprecated_version_check_mode_reports_change_only(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeVaultsClient([make_version(1)])

    payload = run_module(module_obj, {"state": "absent"}, client, check_mode=True)

    assert payload == {"changed": True}
    assert client.mutating_calls() == []
    assert client.versions[1].time_of_deletion is None


def test_absent_schedules_deletion_with_deletion_days(monkeypatch):
    oci_module = install_fake_oci(monkeypatch)[0]
    module_obj = load_module()
    client = FakeVaultsClient([make_version(1)])
    before = datetime.now(timezone.utc)

    payload = run_module(
        module_obj, {"state": "absent", "deletion_days": 7, "wait": False}, client
    )

    assert payload == {"changed": True}
    (call,) = client.mutating_calls()
    assert call[:3] == ("schedule_secret_version_deletion", SECRET_ID, 1)
    time_of_deletion = call[3].time_of_deletion
    window = timedelta(days=7, minutes=10)
    assert before + window <= time_of_deletion <= datetime.now(timezone.utc) + window
    assert oci_module.wait_calls == []


def test_absent_without_deletion_days_lets_oci_choose_the_window(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeVaultsClient([make_version(1)])

    run_module(module_obj, {"state": "absent"}, client)

    (call,) = client.mutating_calls()
    assert not hasattr(call[3], "time_of_deletion")


def test_absent_by_name_schedules_the_matching_version(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeVaultsClient([make_version(1, name="old"), make_version(2, name="new", stages=("CURRENT",))])

    payload = run_module(
        module_obj,
        {"state": "absent", "version_number": None, "version_name": "old"},
        client,
    )

    assert payload == {"changed": True}
    (call,) = client.mutating_calls()
    assert call[:3] == ("schedule_secret_version_deletion", SECRET_ID, 1)


def test_absent_waits_until_the_deletion_is_scheduled(monkeypatch):
    oci_module = install_fake_oci(monkeypatch)[0]
    module_obj = load_module()
    client = FakeVaultsClient([make_version(1)], lag=2)

    payload = run_module(
        module_obj, {"state": "absent", "deletion_days": 3, "wait": True}, client
    )

    assert payload == {"changed": True}
    assert client.versions[1].time_of_deletion is not None
    assert client.get_count > 3
    assert len(oci_module.wait_calls) == 2
    for wait_call in oci_module.wait_calls:
        assert wait_call["max_wait_seconds"] == 60
        assert wait_call["max_interval_seconds"] == 5


def test_absent_rerun_after_scheduling_is_unchanged(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeVaultsClient([make_version(1)])

    run_module(module_obj, {"state": "absent", "deletion_days": 3}, client)
    payload = run_module(module_obj, {"state": "absent", "deletion_days": 3}, client)

    assert payload == {"changed": False}
    assert len(client.mutating_calls()) == 1


def test_absent_translates_dependency_conflict(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeVaultsClient([make_version(1)])

    class Conflict(Exception):
        status = 409

    def conflicting(*args, **kwargs):
        raise Conflict("in use")

    client.schedule_secret_version_deletion = conflicting

    message = run_failing_module(module_obj, {"state": "absent"}, client)

    assert "Cannot schedule deletion of secret version 1" in message


@pytest.mark.parametrize("deletion_days", [0, 31, -1])
def test_absent_rejects_deletion_days_outside_the_window(monkeypatch, deletion_days):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeVaultsClient([make_version(1)])

    message = run_failing_module(
        module_obj, {"state": "absent", "deletion_days": deletion_days}, client
    )

    assert "deletion_days must be between 1 and 30" in message
    assert client.calls == []
    assert client.get_count == 0


@pytest.mark.parametrize("deletion_days", [1, 30])
def test_absent_accepts_deletion_days_at_the_window_edges(monkeypatch, deletion_days):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeVaultsClient([make_version(1)])

    payload = run_module(
        module_obj, {"state": "absent", "deletion_days": deletion_days}, client
    )

    assert payload == {"changed": True}


def test_deletion_days_is_not_validated_for_present(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeVaultsClient([make_version(1)])

    payload = run_module(module_obj, {"deletion_days": 99}, client)

    assert payload["changed"] is False


@pytest.mark.parametrize(
    "params, deletion",
    [({"state": "present"}, SCHEDULED_AT), ({"state": "absent"}, None)],
)
def test_wait_continues_until_the_secret_is_active(monkeypatch, params, deletion):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeVaultsClient([make_version(1, deletion=deletion)], secret_lag=3)

    payload = run_module(module_obj, dict(params, wait=True), client)

    assert payload["changed"] is True
    assert client.secret_updating_polls == 0
    assert client.secret_get_count == 4


def test_no_wait_does_not_read_the_secret(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeVaultsClient([make_version(1)], secret_lag=3)

    run_module(module_obj, {"state": "absent"}, client)

    assert client.secret_get_count == 0
