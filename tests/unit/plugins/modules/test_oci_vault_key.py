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


KEY_MODEL_NAMES = (
    "CreateKeyDetails",
    "KeyShape",
    "UpdateKeyDetails",
    "ScheduleKeyDeletionDetails",
    "AutoKeyRotationDetails",
    "ExternalKeyReference",
)
VAULT_ID = "ocid1.vault.oc1..example"
KEY_ID = "ocid1.key.oc1..example"
COMPARTMENT_ID = "ocid1.compartment.oc1..example"


def install_fake_oci(monkeypatch):
    oci_module, service_error = shared_install_fake_oci(monkeypatch)
    oci_module.key_management = types.SimpleNamespace(
        KmsManagementClient=type("FakeKmsManagementClient", (), {}),
        KmsVaultClient=type("FakeKmsVaultClient", (), {}),
        models=types.SimpleNamespace(
            **{model_name: FakeModel for model_name in KEY_MODEL_NAMES}
        ),
    )
    oci_module.retry.RetryStrategyBuilder = lambda **kwargs: types.SimpleNamespace(
        get_retry_strategy=lambda: oci_module.retry.DEFAULT_RETRY_STRATEGY
    )
    return oci_module, service_error


def make_key(state="ENABLED", **overrides):
    fields = dict(
        id=KEY_ID,
        display_name="example-key",
        compartment_id=COMPARTMENT_ID,
        lifecycle_state=state,
        key_shape=FakeModel(algorithm="AES", length=32, curve_id=None),
        protection_mode="HSM",
        is_auto_rotation_enabled=False,
        auto_key_rotation_details=None,
        freeform_tags={},
        defined_tags={},
    )
    fields.update(overrides)
    return FakeModel(**fields)


class FakeKmsClient:
    """Record key management calls and serve a mutable key."""

    def __init__(self, key=None, restored_state="ENABLED"):
        self.key = key
        self.restored_state = restored_state
        self.calls = []

    def get_key(self, key_id):
        self.calls.append(("get_key", key_id))
        return FakeResponse(self.key)

    def create_key(self, create_key_details):
        self.calls.append(("create_key", create_key_details))
        self.key = make_key()
        return FakeResponse(self.key)

    def update_key(self, key_id, update_key_details):
        self.calls.append(("update_key", key_id, update_key_details))
        assert self.key.lifecycle_state != "PENDING_DELETION"
        return FakeResponse(self.key)

    def cancel_key_deletion(self, key_id):
        self.calls.append(("cancel_key_deletion", key_id))
        self.key.lifecycle_state = self.restored_state
        return FakeResponse(self.key)

    def create_key_version(self, key_id):
        self.calls.append(("create_key_version", key_id))
        return FakeResponse(FakeModel(id="ocid1.keyversion.oc1..example"))

    def get_key_version(self, key_id, key_version_id):
        self.calls.append(("get_key_version", key_id, key_version_id))
        return FakeResponse(FakeModel(id=key_version_id, lifecycle_state="ENABLED"))

    def schedule_key_deletion(self, key_id, schedule_key_deletion_details):
        self.calls.append(("schedule_key_deletion", key_id, schedule_key_deletion_details))
        self.key.lifecycle_state = "PENDING_DELETION"
        return FakeResponse(self.key)

    def call_names(self):
        return [call[0] for call in self.calls if call[0] != "get_key"]


def run_module(module_obj, params, client, check_mode=False):
    full_params = {
        "state": "present",
        "key_id": KEY_ID,
        "wait": False,
        "rotate": False,
    }
    full_params.update(params)
    instance = make_module_instance(
        module_obj,
        "OciVaultKeyModule",
        full_params,
        client=client,
        check_mode=check_mode,
    )
    instance._update_plan_cache = None
    instance.call_with_retry = lambda fn, *args, **kwargs: fn(*args, **kwargs)
    with pytest.raises(ExitJsonCalled) as excinfo:
        instance.execute_resource_module()
    return excinfo.value.payload


def load_module():
    return load_collection_module("oci_vault_key")


def test_main_wires_argument_spec_and_runs_module(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule({})

    class FakeKeyModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciVaultKeyModule", FakeKeyModule)

    module_obj.main()

    spec = captured["argument_spec"]
    assert captured["run_called"] is True
    assert captured["supports_check_mode"] is True
    assert captured["required_one_of"] == [["vault_id", "management_endpoint"]]
    assert captured["mutually_exclusive"] == [["vault_id", "management_endpoint"]]
    assert spec["vault_id"] == {"type": "str"}
    assert spec["management_endpoint"] == {"type": "str"}
    assert spec["state"]["default"] == "present"
    assert spec["key_id"] == {"type": "str"}
    assert spec["protection_mode"]["choices"] == ["hsm", "software", "external"]
    assert spec["key_shape"]["options"]["algorithm"]["choices"] == ["aes", "rsa", "ecdsa"]
    assert spec["key_shape"]["options"]["curve_id"]["choices"] == [
        "nist_p256",
        "nist_p384",
        "nist_p521",
    ]
    assert spec["rotate"] == {"type": "bool", "default": False}
    assert spec["deletion_days"] == {"type": "int"}
    assert spec["auto_key_rotation_details"]["options"] == {
        "rotation_interval_in_days": {"type": "int"}
    }
    assert "display_name" not in spec


def test_main_normalizes_choices_to_oci_values(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    module = DummyModule(
        {
            "key_shape": {"algorithm": "ecdsa", "curve_id": "nist_p256", "length": 32},
            "protection_mode": "hsm",
        }
    )
    module_obj.normalize_choice_parameters(module, module_obj.CHOICE_VALUE_MAPS)

    assert module.params["key_shape"]["algorithm"] == "ECDSA"
    assert module.params["key_shape"]["curve_id"] == "NIST_P256"
    assert module.params["protection_mode"] == "HSM"


def test_build_create_key_details_maps_nested_models(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()

    details = module_obj.build_create_key_details(
        {
            "compartment_id": COMPARTMENT_ID,
            "name": "example-key",
            "key_shape": {"algorithm": "AES", "length": 32, "curve_id": None},
            "protection_mode": "EXTERNAL",
            "external_key_id": "external-1",
            "is_auto_rotation_enabled": True,
            "auto_key_rotation_details": {"rotation_interval_in_days": 90},
            "freeform_tags": {"env": "dev"},
            "defined_tags": None,
        }
    )

    assert details.display_name == "example-key"
    assert details.compartment_id == COMPARTMENT_ID
    assert details.key_shape.algorithm == "AES"
    assert details.key_shape.length == 32
    assert not hasattr(details.key_shape, "curve_id")
    assert details.protection_mode == "EXTERNAL"
    assert details.external_key_reference.external_key_id == "external-1"
    assert details.is_auto_rotation_enabled is True
    assert details.auto_key_rotation_details.rotation_interval_in_days == 90
    assert details.freeform_tags == {"env": "dev"}
    assert not hasattr(details, "defined_tags")


def test_build_create_key_details_omits_optional_models(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()

    details = module_obj.build_create_key_details(
        {
            "compartment_id": COMPARTMENT_ID,
            "name": "example-key",
            "key_shape": {"algorithm": "AES", "length": 32},
        }
    )

    assert not hasattr(details, "external_key_reference")
    assert not hasattr(details, "auto_key_rotation_details")


def test_dead_states_depend_on_state(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    present = make_module_instance(module_obj, "OciVaultKeyModule", {"state": "present"})
    absent = make_module_instance(module_obj, "OciVaultKeyModule", {"state": "absent"})

    assert present.dead_states == {"DELETED", "DELETING"}
    assert absent.dead_states == {
        "DELETED",
        "DELETING",
        "PENDING_DELETION",
        "SCHEDULING_DELETION",
    }


def test_create_key(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsClient()
    client.get_key = lambda key_id: FakeResponse(None)
    # No key_id and no existing match: resolve by name through an empty list.
    instance = make_module_instance(
        module_obj,
        "OciVaultKeyModule",
        {
            "state": "present",
            "wait": False,
            "rotate": True,
            "compartment_id": COMPARTMENT_ID,
            "name": "example-key",
            "key_shape": {"algorithm": "AES", "length": 32},
        },
        client=client,
    )
    instance.call_with_retry = lambda fn, *args, **kwargs: fn(*args, **kwargs)
    instance.resolve_resource_by_name = lambda: None

    with pytest.raises(ExitJsonCalled) as excinfo:
        instance.execute_resource_module()

    payload = excinfo.value.payload
    assert payload["changed"] is True
    assert payload["resource"]["id"] == KEY_ID
    # rotate is ignored for a key created by the same task.
    assert client.call_names() == ["create_key"]


def test_create_key_check_mode_and_missing_fields(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsClient()

    def make_instance(params, check_mode):
        instance = make_module_instance(
            module_obj,
            "OciVaultKeyModule",
            dict({"state": "present", "wait": False}, **params),
            client=client,
            check_mode=check_mode,
        )
        instance.resolve_resource_by_name = lambda: None
        return instance

    full = {
        "compartment_id": COMPARTMENT_ID,
        "name": "example-key",
        "key_shape": {"algorithm": "AES", "length": 32},
    }
    with pytest.raises(ExitJsonCalled) as excinfo:
        make_instance(full, True).execute_resource_module()
    assert excinfo.value.payload == {"changed": True}
    assert client.calls == []

    with pytest.raises(FailJsonCalled) as failure:
        make_instance({"compartment_id": COMPARTMENT_ID, "name": "x"}, False).execute_resource_module()
    assert "key_shape" in failure.value.payload["msg"]


def test_idempotent_rerun_makes_no_changes(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsClient(make_key())

    payload = run_module(
        module_obj,
        {
            "name": "example-key",
            "compartment_id": COMPARTMENT_ID,
            "key_shape": {"algorithm": "AES", "length": 32, "curve_id": None},
            "protection_mode": "HSM",
            "is_auto_rotation_enabled": False,
        },
        client,
    )

    assert payload["changed"] is False
    assert payload["resource"]["name"] == "example-key"
    assert client.call_names() == []


def test_update_name_and_auto_rotation(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsClient(make_key())

    payload = run_module(
        module_obj,
        {
            "name": "renamed-key",
            "is_auto_rotation_enabled": True,
            "auto_key_rotation_details": {"rotation_interval_in_days": 90},
        },
        client,
    )

    assert payload["changed"] is True
    update_call = [call for call in client.calls if call[0] == "update_key"][0]
    details = update_call[2]
    assert update_call[1] == KEY_ID
    assert details.display_name == "renamed-key"
    assert details.is_auto_rotation_enabled is True
    assert details.auto_key_rotation_details.rotation_interval_in_days == 90


def test_update_check_mode_does_not_call_oci(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsClient(make_key())

    payload = run_module(module_obj, {"name": "renamed-key"}, client, check_mode=True)

    assert payload == {"changed": True}
    assert client.call_names() == []


def test_auto_rotation_subset_compare_is_idempotent(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    key = make_key(
        is_auto_rotation_enabled=True,
        auto_key_rotation_details=FakeModel(
            rotation_interval_in_days=90, time_of_last_rotation="x"
        ),
    )
    client = FakeKmsClient(key)

    payload = run_module(
        module_obj,
        {"auto_key_rotation_details": {"rotation_interval_in_days": 90}},
        client,
    )

    assert payload["changed"] is False


def test_immutable_key_shape_change_fails(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsClient(make_key())
    instance = make_module_instance(
        module_obj,
        "OciVaultKeyModule",
        {
            "state": "present",
            "key_id": KEY_ID,
            "key_shape": {"algorithm": "AES", "length": 16, "curve_id": None},
        },
        client=client,
    )
    instance.call_with_retry = lambda fn, *args, **kwargs: fn(*args, **kwargs)

    with pytest.raises(FailJsonCalled) as excinfo:
        instance.execute_resource_module()

    assert "key_shape" in excinfo.value.payload["msg"]
    assert client.call_names() == []


def test_immutable_compartment_change_fails(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsClient(make_key())

    with pytest.raises(FailJsonCalled) as excinfo:
        run_module(module_obj, {"compartment_id": "ocid1.compartment.oc1..other"}, client)

    assert "compartment_id" in excinfo.value.payload["msg"]
    assert "move keys" in excinfo.value.payload["msg"]


def test_rotate_creates_exactly_one_version(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsClient(make_key())

    payload = run_module(module_obj, {"rotate": True}, client)

    assert payload["changed"] is True
    assert client.call_names() == ["create_key_version"]


def test_rotate_with_wait_waits_for_new_key_version(monkeypatch):
    oci_module = install_fake_oci(monkeypatch)[0]
    module_obj = load_module()
    client = FakeKmsClient(make_key())
    waited = {}

    def fake_wait_until(wait_client, response, *args, **kwargs):
        waited.update(response=response, args=args, kwargs=kwargs)
        return response

    oci_module.wait_until = fake_wait_until
    monkeypatch.setattr(
        module_obj.OciVaultKeyModule,
        "wait_for_resource_id",
        lambda self, resource_id, target_states: client.key,
    )

    run_module(
        module_obj,
        {"rotate": True, "wait": True, "wait_timeout": 60, "wait_interval": 5},
        client,
    )

    assert client.call_names() == ["create_key_version", "get_key_version"]
    assert waited["response"].data.id == "ocid1.keyversion.oc1..example"
    assert waited["args"] == ("lifecycle_state", "ENABLED")
    assert waited["kwargs"] == {"max_wait_seconds": 60, "max_interval_seconds": 5}


def test_rotate_with_update_creates_one_version(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsClient(make_key())

    run_module(module_obj, {"rotate": True, "name": "renamed-key"}, client)

    assert client.call_names() == ["update_key", "create_key_version"]


def test_rotate_check_mode_does_not_call_oci(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsClient(make_key())

    payload = run_module(module_obj, {"rotate": True}, client, check_mode=True)

    assert payload == {"changed": True}
    assert client.call_names() == []


def test_absent_schedules_deletion_with_default_window(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsClient(make_key())

    payload = run_module(module_obj, {"state": "absent"}, client)

    assert payload == {"changed": True}
    call = [c for c in client.calls if c[0] == "schedule_key_deletion"][0]
    assert call[1] == KEY_ID
    assert not hasattr(call[2], "time_of_deletion")


def test_absent_schedules_deletion_with_deletion_days(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsClient(make_key())
    before = datetime.now(timezone.utc)

    run_module(module_obj, {"state": "absent", "deletion_days": 7}, client)

    after = datetime.now(timezone.utc)
    call = [c for c in client.calls if c[0] == "schedule_key_deletion"][0]
    time_of_deletion = call[2].time_of_deletion
    assert before + timedelta(days=7) <= time_of_deletion <= after + timedelta(days=7)
    assert time_of_deletion.tzinfo is not None


@pytest.mark.parametrize("deletion_days", [0, 6, 31])
def test_absent_deletion_days_out_of_range_fails(monkeypatch, deletion_days):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsClient(make_key())

    with pytest.raises(FailJsonCalled) as excinfo:
        run_module(module_obj, {"state": "absent", "deletion_days": deletion_days}, client)

    assert "deletion_days" in excinfo.value.payload["msg"]
    assert client.calls == []


@pytest.mark.parametrize(
    "state", ["PENDING_DELETION", "SCHEDULING_DELETION", "DELETING", "DELETED"]
)
def test_absent_on_already_deleted_key_is_unchanged(monkeypatch, state):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsClient(make_key(state))

    payload = run_module(module_obj, {"state": "absent"}, client)

    assert payload == {"changed": False}
    assert client.call_names() == []


def test_absent_check_mode_does_not_call_oci(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsClient(make_key())

    payload = run_module(module_obj, {"state": "absent"}, client, check_mode=True)

    assert payload == {"changed": True}
    assert client.call_names() == []


def test_present_on_deleted_key_fails_as_missing(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsClient(make_key("DELETED"))

    with pytest.raises(FailJsonCalled) as excinfo:
        run_module(module_obj, {}, client)

    assert KEY_ID in excinfo.value.payload["msg"]


@pytest.mark.parametrize("restored_state", ["ENABLED", "DISABLED"])
def test_present_on_pending_key_cancels_deletion(monkeypatch, restored_state):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsClient(make_key("PENDING_DELETION"), restored_state=restored_state)

    payload = run_module(module_obj, {}, client)

    assert payload["changed"] is True
    assert payload["resource"]["lifecycle_state"] == restored_state
    assert client.call_names() == ["cancel_key_deletion"]


def test_present_on_pending_key_check_mode_does_not_call_oci(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsClient(make_key("PENDING_DELETION"))

    payload = run_module(module_obj, {}, client, check_mode=True)

    assert payload == {"changed": True}
    assert client.call_names() == []


def test_present_on_pending_key_with_update_cancels_once_before_update(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsClient(make_key("PENDING_DELETION"))

    payload = run_module(module_obj, {"name": "renamed-key"}, client)

    assert payload["changed"] is True
    assert client.call_names() == ["cancel_key_deletion", "update_key"]


def test_present_on_pending_key_with_rotate_cancels_then_rotates_once(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    client = FakeKmsClient(make_key("PENDING_DELETION"))

    run_module(module_obj, {"rotate": True}, client)

    assert client.call_names() == ["cancel_key_deletion", "create_key_version"]
