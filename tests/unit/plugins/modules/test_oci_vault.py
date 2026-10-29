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


VAULT_MODEL_NAMES = (
    "CreateVaultDetails",
    "UpdateVaultDetails",
    "ScheduleVaultDeletionDetails",
)
VAULT_ID = "ocid1.vault.oc1..example"
COMPARTMENT_ID = "ocid1.compartment.oc1..example"


class FakeKmsVaultClientClass:
    pass


def install_fake_oci(monkeypatch):
    oci_module, service_error = shared_install_fake_oci(monkeypatch)
    oci_module.key_management = types.SimpleNamespace(
        KmsVaultClient=FakeKmsVaultClientClass,
        models=types.SimpleNamespace(
            **{model_name: FakeModel for model_name in VAULT_MODEL_NAMES}
        ),
    )
    return oci_module, service_error


def make_vault(state="ACTIVE", **overrides):
    fields = dict(
        id=VAULT_ID,
        display_name="example-vault",
        compartment_id=COMPARTMENT_ID,
        lifecycle_state=state,
        vault_type="DEFAULT",
        freeform_tags={},
        defined_tags={},
    )
    fields.update(overrides)
    return FakeModel(**fields)


class FakeKmsVaultClient:
    """Record vault calls and serve a mutable vault."""

    def __init__(self, vault=None):
        self.vault = vault
        self.calls = []

    def get_vault(self, vault_id):
        self.calls.append(("get_vault", vault_id))
        return FakeResponse(self.vault)

    def create_vault(self, create_vault_details):
        self.calls.append(("create_vault", create_vault_details))
        self.vault = make_vault()
        return FakeResponse(self.vault)

    def update_vault(self, vault_id, update_vault_details):
        self.calls.append(("update_vault", vault_id, update_vault_details))
        assert self.vault.lifecycle_state != "PENDING_DELETION"
        return FakeResponse(self.vault)

    def cancel_vault_deletion(self, vault_id):
        self.calls.append(("cancel_vault_deletion", vault_id))
        self.vault.lifecycle_state = "ACTIVE"
        return FakeResponse(self.vault)

    def schedule_vault_deletion(self, vault_id, schedule_vault_deletion_details):
        self.calls.append(
            ("schedule_vault_deletion", vault_id, schedule_vault_deletion_details)
        )
        self.vault.lifecycle_state = "PENDING_DELETION"
        return FakeResponse(self.vault)

    def call_names(self):
        return [call[0] for call in self.calls if call[0] != "get_vault"]


def make_instance(module_obj, params, client, check_mode=False):
    full_params = {"state": "present", "wait": False}
    full_params.update(params)
    instance = make_module_instance(
        module_obj,
        "OciVaultModule",
        full_params,
        client=client,
        check_mode=check_mode,
    )
    instance._update_plan_cache = None
    instance.call_with_retry = lambda fn, *args, **kwargs: fn(*args, **kwargs)
    return instance


def run_module(module_obj, params, client, check_mode=False):
    instance = make_instance(
        module_obj, dict({"vault_id": VAULT_ID}, **params), client, check_mode
    )
    with pytest.raises(ExitJsonCalled) as excinfo:
        instance.execute_resource_module()
    return excinfo.value.payload


def load_module():
    return load_collection_module("oci_vault")


def test_main_wires_argument_spec_and_runs_module(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule({})

    class FakeVaultModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciVaultModule", FakeVaultModule)

    module_obj.main()

    spec = captured["argument_spec"]
    assert captured["run_called"] is True
    assert captured["supports_check_mode"] is True
    assert spec["state"] == {
        "type": "str",
        "choices": ["present", "absent"],
        "default": "present",
    }
    assert spec["vault_id"] == {"type": "str"}
    assert spec["deletion_days"] == {"type": "int"}
    for name in ("name", "compartment_id", "freeform_tags", "wait", "auth_type"):
        assert name in spec
    assert "vault_type" not in spec
    assert "display_name" not in spec


def test_module_class_metadata(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    cls = module_obj.OciVaultModule
    instance = make_module_instance(module_obj, "OciVaultModule", {})

    assert instance.client_class is FakeKmsVaultClientClass
    assert issubclass(cls, module_obj.OciScheduledDeletionMixin)
    assert cls.__mro__.index(module_obj.OciScheduledDeletionMixin) < cls.__mro__.index(
        module_obj.OciResourceBase
    )
    assert cls.resource_id_param == "vault_id"
    assert cls.list_resource_method == "list_vaults"


def test_build_create_vault_details_creates_default_vault(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()

    details = module_obj.build_create_vault_details(
        {
            "compartment_id": COMPARTMENT_ID,
            "name": "example-vault",
            "freeform_tags": {"env": "dev"},
            "defined_tags": None,
        }
    )

    assert details.compartment_id == COMPARTMENT_ID
    assert details.display_name == "example-vault"
    assert details.vault_type == "DEFAULT"
    assert details.freeform_tags == {"env": "dev"}
    assert not hasattr(details, "defined_tags")


def test_dead_states_depend_on_state(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    present = make_module_instance(module_obj, "OciVaultModule", {"state": "present"})
    absent = make_module_instance(module_obj, "OciVaultModule", {"state": "absent"})

    assert present.dead_states == {"DELETED", "DELETING"}
    assert absent.dead_states == {
        "DELETED",
        "DELETING",
        "PENDING_DELETION",
        "SCHEDULING_DELETION",
    }


def test_create_vault(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsVaultClient()
    instance = make_instance(
        module_obj,
        {"compartment_id": COMPARTMENT_ID, "name": "example-vault"},
        client,
    )
    instance.resolve_resource_by_name = lambda: None

    with pytest.raises(ExitJsonCalled) as excinfo:
        instance.execute_resource_module()

    payload = excinfo.value.payload
    assert payload["changed"] is True
    assert payload["resource"]["id"] == VAULT_ID
    assert payload["resource"]["name"] == "example-vault"
    assert client.call_names() == ["create_vault"]
    assert client.calls[0][1].vault_type == "DEFAULT"


def test_create_vault_waits_for_active(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsVaultClient()
    waited = {}
    instance = make_instance(
        module_obj,
        {"compartment_id": COMPARTMENT_ID, "name": "example-vault", "wait": True},
        client,
    )
    instance.resolve_resource_by_name = lambda: None

    def fake_wait(resource_id, target_states):
        waited.update(resource_id=resource_id, target_states=target_states)
        return client.vault

    instance.wait_for_resource_id = fake_wait

    with pytest.raises(ExitJsonCalled):
        instance.execute_resource_module()

    assert waited == {"resource_id": VAULT_ID, "target_states": ("ACTIVE",)}


def test_create_vault_check_mode_and_missing_fields(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsVaultClient()

    instance = make_instance(
        module_obj,
        {"compartment_id": COMPARTMENT_ID, "name": "example-vault"},
        client,
        check_mode=True,
    )
    instance.resolve_resource_by_name = lambda: None
    with pytest.raises(ExitJsonCalled) as excinfo:
        instance.execute_resource_module()
    assert excinfo.value.payload == {"changed": True}
    assert client.calls == []

    instance = make_instance(module_obj, {"name": "example-vault"}, client)
    instance.resolve_resource_by_name = lambda: None
    with pytest.raises(FailJsonCalled) as failure:
        instance.execute_resource_module()
    assert "compartment_id" in failure.value.payload["msg"]
    assert client.calls == []


def test_name_lookup_finds_existing_vault(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsVaultClient(make_vault())
    list_calls = []

    def list_vaults(**kwargs):
        list_calls.append(kwargs)
        return [make_vault(id="ocid1.vault.oc1..other", display_name="other"), client.vault]

    client.list_vaults = list_vaults
    instance = make_instance(
        module_obj,
        {"compartment_id": COMPARTMENT_ID, "name": "example-vault"},
        client,
    )
    instance.list_all_resources = lambda fn, **kwargs: fn(**kwargs)

    with pytest.raises(ExitJsonCalled) as excinfo:
        instance.execute_resource_module()

    payload = excinfo.value.payload
    assert payload["changed"] is False
    assert payload["resource"]["id"] == VAULT_ID
    assert list_calls == [{"compartment_id": COMPARTMENT_ID}]
    assert client.call_names() == []


def test_idempotent_rerun_makes_no_changes(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsVaultClient(make_vault(freeform_tags={"env": "dev"}))

    payload = run_module(
        module_obj,
        {
            "name": "example-vault",
            "compartment_id": COMPARTMENT_ID,
            "freeform_tags": {"env": "dev"},
        },
        client,
    )

    assert payload["changed"] is False
    assert payload["resource"]["name"] == "example-vault"
    assert client.call_names() == []


def test_update_name_and_tags(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsVaultClient(make_vault())

    payload = run_module(
        module_obj,
        {"name": "renamed-vault", "freeform_tags": {"env": "prod"}},
        client,
    )

    assert payload["changed"] is True
    assert client.call_names() == ["update_vault"]
    update_call = client.calls[-1]
    assert update_call[1] == VAULT_ID
    assert update_call[2].display_name == "renamed-vault"
    assert update_call[2].freeform_tags == {"env": "prod"}


def test_update_check_mode_does_not_call_oci(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsVaultClient(make_vault())

    payload = run_module(module_obj, {"name": "renamed-vault"}, client, check_mode=True)

    assert payload == {"changed": True}
    assert client.call_names() == []


def test_immutable_compartment_change_fails(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsVaultClient(make_vault())

    with pytest.raises(FailJsonCalled) as excinfo:
        run_module(module_obj, {"compartment_id": "ocid1.compartment.oc1..other"}, client)

    assert "compartment_id" in excinfo.value.payload["msg"]
    assert "move vaults" in excinfo.value.payload["msg"]
    assert client.call_names() == []


def test_absent_schedules_deletion_with_default_window(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsVaultClient(make_vault())

    payload = run_module(module_obj, {"state": "absent"}, client)

    assert payload == {"changed": True}
    assert client.call_names() == ["schedule_vault_deletion"]
    call = client.calls[-1]
    assert call[1] == VAULT_ID
    assert not hasattr(call[2], "time_of_deletion")


def test_absent_schedules_deletion_with_deletion_days(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsVaultClient(make_vault())
    before = datetime.now(timezone.utc)

    run_module(module_obj, {"state": "absent", "deletion_days": 7}, client)

    after = datetime.now(timezone.utc)
    time_of_deletion = client.calls[-1][2].time_of_deletion
    assert before + timedelta(days=7) <= time_of_deletion <= after + timedelta(days=7)
    assert time_of_deletion.tzinfo is not None


def test_absent_waits_for_pending_deletion(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsVaultClient(make_vault())
    waited = {}
    instance = make_instance(
        module_obj, {"state": "absent", "vault_id": VAULT_ID, "wait": True}, client
    )

    def fake_wait(resource_id, target_states):
        waited.update(resource_id=resource_id, target_states=set(target_states))
        return client.vault

    instance.wait_for_resource_id = fake_wait

    with pytest.raises(ExitJsonCalled):
        instance.execute_resource_module()

    assert waited["resource_id"] == VAULT_ID
    assert "PENDING_DELETION" in waited["target_states"]
    assert "SCHEDULING_DELETION" not in waited["target_states"]


@pytest.mark.parametrize("deletion_days", [0, 6, 31])
def test_absent_deletion_days_out_of_range_fails(monkeypatch, deletion_days):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsVaultClient(make_vault())

    with pytest.raises(FailJsonCalled) as excinfo:
        run_module(module_obj, {"state": "absent", "deletion_days": deletion_days}, client)

    assert "deletion_days" in excinfo.value.payload["msg"]
    assert client.calls == []


def test_absent_without_target_fails(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsVaultClient(make_vault())
    instance = make_instance(module_obj, {"state": "absent"}, client)

    with pytest.raises(FailJsonCalled) as excinfo:
        instance.execute_resource_module()

    assert "vault_id" in excinfo.value.payload["msg"]
    assert client.calls == []


@pytest.mark.parametrize(
    "state", ["PENDING_DELETION", "SCHEDULING_DELETION", "DELETING", "DELETED"]
)
def test_absent_on_already_deleted_vault_is_unchanged(monkeypatch, state):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsVaultClient(make_vault(state))

    payload = run_module(module_obj, {"state": "absent"}, client)

    assert payload == {"changed": False}
    assert client.call_names() == []


def test_absent_check_mode_does_not_call_oci(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsVaultClient(make_vault())

    payload = run_module(module_obj, {"state": "absent"}, client, check_mode=True)

    assert payload == {"changed": True}
    assert client.call_names() == []


def test_present_on_deleted_vault_fails_as_missing(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsVaultClient(make_vault("DELETED"))

    with pytest.raises(FailJsonCalled) as excinfo:
        run_module(module_obj, {}, client)

    assert VAULT_ID in excinfo.value.payload["msg"]
    assert client.call_names() == []


def test_present_on_pending_vault_cancels_deletion(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsVaultClient(make_vault("PENDING_DELETION"))

    payload = run_module(module_obj, {}, client)

    assert payload["changed"] is True
    assert payload["resource"]["lifecycle_state"] == "ACTIVE"
    assert client.call_names() == ["cancel_vault_deletion"]


def test_present_on_pending_vault_check_mode_does_not_call_oci(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsVaultClient(make_vault("PENDING_DELETION"))

    payload = run_module(module_obj, {}, client, check_mode=True)

    assert payload == {"changed": True}
    assert client.call_names() == []


def test_present_on_pending_vault_with_update_cancels_once_before_update(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsVaultClient(make_vault("PENDING_DELETION"))

    payload = run_module(module_obj, {"name": "renamed-vault"}, client)

    assert payload["changed"] is True
    assert client.call_names() == ["cancel_vault_deletion", "update_vault"]
