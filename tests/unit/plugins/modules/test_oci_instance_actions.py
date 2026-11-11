from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types
import json

import pytest
from ansible.module_utils import basic

from .conftest import (
    DummyModule,
    FakeModel,
    FakeResponse,
    ExitJsonCalled,
    FailJsonCalled,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
)


INSTANCE_ACTIONS = [
    "start",
    "stop",
    "softstop",
    "softreset",
    "reset",
    "rebootmigrate",
    "senddiagnosticinterrupt",
    "diagnosticreboot",
]
INSTANCE_ID = "ocid1.instance.oc1..example"


def make_actions_module(module_obj, params, client=None, check_mode=False):
    """Create an action helper without constructing an OCI client."""
    instance = make_module_instance(
        module_obj,
        "OciInstanceActionsModule",
        params,
        client=client,
        check_mode=check_mode,
    )
    return instance


def load_actions_module(monkeypatch):
    """Load the module with an isolated fake OCI namespace."""
    fake_oci = install_fake_oci(monkeypatch)[0]
    module_obj = load_collection_module("oci_instance_actions")
    monkeypatch.setattr(module_obj, "oci", fake_oci)
    return module_obj


def install_composite(monkeypatch, module_obj, response=None):
    """Install a fake composite operation and return its captured calls."""
    calls = []
    response = response or FakeResponse(data=FakeModel(lifecycle_state="RUNNING"))

    class FakeCompositeOperations:
        def __init__(self, client):
            calls.append(("client", client))

        def instance_action_and_wait_for_state(self, *args, **kwargs):
            calls.append((args, kwargs))
            return response

    module_obj.oci.core.ComputeClientCompositeOperations = FakeCompositeOperations
    module_obj.oci.retry = types.SimpleNamespace(DEFAULT_RETRY_STRATEGY="default")
    return calls


def test_main_defines_required_action_and_default_options(monkeypatch):
    """Test required arguments, action choices, and wait defaults."""
    module_obj = load_actions_module(monkeypatch)
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule({"instance_id": INSTANCE_ID, "action": "start"})

    class FakeActionsModule:
        def __init__(self, module):
            pass

        def process_action(self):
            return False, FakeResponse()

        def serialize_result_resource(self, resource):
            return {}

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciInstanceActionsModule", FakeActionsModule)
    with pytest.raises(ExitJsonCalled):
        module_obj.main()

    spec = captured["argument_spec"]
    assert spec["instance_id"] == {"type": "str", "required": True}
    assert spec["action"]["required"] is True
    assert spec["action"]["choices"] == INSTANCE_ACTIONS
    assert spec["wait"]["default"] is True
    assert spec["wait_timeout"]["default"] == 1200
    assert spec["wait_interval"]["default"] == 30
    assert captured["supports_check_mode"] is True


@pytest.mark.parametrize(
    "params,invalid_value",
    [
        ({"action": "start"}, "instance_id"),
        ({"instance_id": INSTANCE_ID}, "action"),
        ({"instance_id": INSTANCE_ID, "action": "invalid"}, "invalid"),
    ],
)
def test_main_rejects_missing_or_unsupported_arguments(
    monkeypatch, capsys, params, invalid_value
):
    """Test Ansible rejects missing required fields and invalid actions."""
    module_obj = load_actions_module(monkeypatch)
    supplied = dict(params, _ansible_check_mode=False)
    monkeypatch.setattr(
        basic,
        "_ANSIBLE_ARGS",
        json.dumps({"ANSIBLE_MODULE_ARGS": supplied}).encode(),
    )
    monkeypatch.setattr(basic, "_ANSIBLE_PROFILE", "legacy", raising=False)
    monkeypatch.setattr(basic, "_PARSED_MODULE_ARGS", supplied.copy(), raising=False)

    with pytest.raises(SystemExit) as result:
        module_obj.main()

    assert result.value.code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["failed"] is True
    assert invalid_value in payload["msg"]


@pytest.mark.parametrize(
    "action,model_name,option_name",
    [
        ("rebootmigrate", "RebootMigrateActionDetails", "delete_local_storage"),
        ("reset", "ResetActionDetails", "allow_dense_reboot_migration"),
        ("softreset", "SoftResetActionDetails", "allow_dense_reboot_migration"),
    ],
)
@pytest.mark.parametrize("option_value", [True, False])
def test_process_action_builds_sdk_action_details_when_option_is_supplied(
    monkeypatch, action, model_name, option_name, option_value
):
    """Test that each optional action field uses its SDK model."""
    module_obj = load_actions_module(monkeypatch)
    model_calls = []

    class ActionDetails:
        def __init__(self, **kwargs):
            model_calls.append(kwargs)
            self.values = kwargs

    setattr(module_obj.oci.core.models, model_name, ActionDetails)
    calls = install_composite(monkeypatch, module_obj)
    params = {"instance_id": INSTANCE_ID, "action": action, "wait": False, option_name: option_value}
    instance = make_actions_module(module_obj, params, client="compute")

    changed, response = instance.process_action()

    assert changed is True
    assert response.data.lifecycle_state == "RUNNING"
    assert model_calls == [{option_name: option_value}]
    operation_call = calls[-1]
    assert operation_call[0] == (INSTANCE_ID, module_obj.ACTION_TO_SDK[action])
    details = operation_call[1]["operation_kwargs"]["instance_power_action_details"]
    assert isinstance(details, ActionDetails)
    assert details.values == {option_name: option_value}


@pytest.mark.parametrize(
    "action,model_name,option_name",
    [
        ("rebootmigrate", "RebootMigrateActionDetails", "delete_local_storage"),
        ("reset", "ResetActionDetails", "allow_dense_reboot_migration"),
        ("softreset", "SoftResetActionDetails", "allow_dense_reboot_migration"),
    ],
)
def test_process_action_uses_real_sdk_action_discriminator(
    monkeypatch, action, model_name, option_name
):
    """Test SDK action models set the correct discriminator value."""
    import oci

    sdk_model = getattr(oci.core.models, model_name)
    module_obj = load_actions_module(monkeypatch)
    setattr(module_obj.oci.core.models, model_name, sdk_model)
    calls = install_composite(monkeypatch, module_obj)
    instance = make_actions_module(
        module_obj,
        {"instance_id": INSTANCE_ID, "action": action, "wait": False, option_name: True},
        client="compute",
    )

    instance.process_action()

    model = calls[-1][1]["operation_kwargs"]["instance_power_action_details"]
    assert isinstance(model, sdk_model)
    assert model.swagger_types["action_type"] == "str"
    expected_discriminator = "rebootMigrate" if action == "rebootmigrate" else action
    assert model.action_type == expected_discriminator


@pytest.mark.parametrize("action", INSTANCE_ACTIONS)
def test_process_action_submits_action_without_optional_body(monkeypatch, action):
    """Test that each action submits without an optional request body."""
    module_obj = load_actions_module(monkeypatch)
    calls = install_composite(monkeypatch, module_obj)
    instance = make_actions_module(
        module_obj,
        {"instance_id": INSTANCE_ID, "action": action, "wait": False},
        client="compute",
    )

    instance.process_action()

    operation_call = calls[-1]
    assert operation_call[0] == (INSTANCE_ID, module_obj.ACTION_TO_SDK[action])
    assert operation_call[1]["operation_kwargs"] == {
        "retry_strategy": "default"
    }
    assert operation_call[1]["wait_for_states"] == []
    assert operation_call[1]["waiter_kwargs"] == {}


@pytest.mark.parametrize(
    "action,target_state",
    [("stop", "STOPPED"), ("softstop", "STOPPED"), ("start", "RUNNING"), ("reset", "RUNNING")],
)
def test_process_action_waits_for_expected_state_and_failures(
    monkeypatch, action, target_state
):
    """Test target states, terminal states, timeout, and polling interval."""
    module_obj = load_actions_module(monkeypatch)
    calls = install_composite(monkeypatch, module_obj)
    instance = make_actions_module(
        module_obj,
        {
            "instance_id": INSTANCE_ID,
            "action": action,
            "wait": True,
            "wait_timeout": 123,
            "wait_interval": 7,
        },
        client="compute",
    )

    instance.process_action()

    operation_call = calls[-1]
    assert operation_call[1]["wait_for_states"] == [
        target_state,
        "TERMINATED",
        "TERMINATING",
    ]
    assert operation_call[1]["waiter_kwargs"] == {
        "max_wait_seconds": 123,
        "max_interval_seconds": 7,
    }


def test_process_action_fails_when_waiter_returns_terminal_state(monkeypatch):
    """Test that a terminal lifecycle state causes a wait failure."""
    module_obj = load_actions_module(monkeypatch)
    install_composite(
        monkeypatch,
        module_obj,
        FakeResponse(data=FakeModel(lifecycle_state="TERMINATED")),
    )
    instance = make_actions_module(
        module_obj,
        {"instance_id": INSTANCE_ID, "action": "reset", "wait": True},
        client="compute",
    )

    with pytest.raises(RuntimeError, match="TERMINATED"):
        instance.process_action()


def test_process_action_submits_repeated_invocations(monkeypatch):
    """Test that repeated calls submit the action on every invocation."""
    module_obj = load_actions_module(monkeypatch)
    calls = install_composite(monkeypatch, module_obj)
    instance = make_actions_module(
        module_obj,
        {"instance_id": INSTANCE_ID, "action": "reset", "wait": False},
        client="compute",
    )

    instance.process_action()
    instance.process_action()

    assert len([call for call in calls if isinstance(call[0], tuple)]) == 2


def test_check_mode_gets_instance_without_submitting_action(monkeypatch):
    """Test that check mode reads the instance and skips the action API."""
    module_obj = load_actions_module(monkeypatch)
    response = FakeResponse(data=FakeModel(id=INSTANCE_ID))
    get_calls = []
    client = types.SimpleNamespace(
        get_instance=lambda instance_id: get_calls.append(instance_id) or response
    )
    instance = make_actions_module(
        module_obj,
        {"instance_id": INSTANCE_ID, "action": "reset"},
        client=client,
        check_mode=True,
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, *args, **kwargs: fn(*args, **kwargs))
    monkeypatch.setattr(
        module_obj.oci.core,
        "ComputeClientCompositeOperations",
        lambda client: pytest.fail("check mode must not submit an action"),
        raising=False,
    )

    changed, result = instance.process_action()

    assert changed is True
    assert result is response
    assert get_calls == [INSTANCE_ID]


@pytest.mark.parametrize(
    "params,expected_message",
    [
        ({"delete_local_storage": True}, "delete_local_storage"),
        ({"allow_dense_reboot_migration": False}, "allow_dense_reboot_migration"),
    ],
)
def test_run_module_rejects_options_for_invalid_actions(monkeypatch, params, expected_message):
    """Test that action-specific options reject invalid action pairings."""
    module_obj = load_actions_module(monkeypatch)
    module = DummyModule(dict({"instance_id": INSTANCE_ID, "action": "start"}, **params))
    monkeypatch.setattr(module_obj, "AnsibleModule", lambda **kwargs: module)

    with pytest.raises(FailJsonCalled) as exc_info:
        module_obj.main()

    assert expected_message in exc_info.value.payload["msg"]


def test_run_module_rejects_explicit_false_for_invalid_pairing(monkeypatch):
    """Test that explicit false still counts as a supplied option."""
    module_obj = load_actions_module(monkeypatch)
    module = DummyModule(
        {
            "instance_id": INSTANCE_ID,
            "action": "rebootmigrate",
            "allow_dense_reboot_migration": False,
        }
    )
    monkeypatch.setattr(module_obj, "AnsibleModule", lambda **kwargs: module)

    with pytest.raises(FailJsonCalled) as exc_info:
        module_obj.main()

    assert "allow_dense_reboot_migration" in exc_info.value.payload["msg"]


def test_run_module_reports_action_and_instance_when_api_fails(monkeypatch):
    """Test that API failures include the action and instance ID."""
    module_obj = load_actions_module(monkeypatch)
    module = DummyModule({"instance_id": INSTANCE_ID, "action": "softstop"})
    monkeypatch.setattr(module_obj, "AnsibleModule", lambda **kwargs: module)

    class FailedActionsModule:
        def __init__(self, module):
            pass

        def process_action(self):
            raise RuntimeError("SDK failure")

    monkeypatch.setattr(module_obj, "OciInstanceActionsModule", FailedActionsModule)

    with pytest.raises(FailJsonCalled) as exc_info:
        module_obj.main()

    assert "softstop" in exc_info.value.payload["msg"]
    assert INSTANCE_ID in exc_info.value.payload["msg"]
    assert "SDK failure" in exc_info.value.payload["msg"]


def test_run_module_returns_action_and_resource(monkeypatch):
    """Test that a successful action returns its name and resource."""
    module_obj = load_actions_module(monkeypatch)
    module = DummyModule({"instance_id": INSTANCE_ID, "action": "start"})
    monkeypatch.setattr(module_obj, "AnsibleModule", lambda **kwargs: module)

    class SuccessfulActionsModule:
        def __init__(self, module):
            pass

        def process_action(self):
            return True, FakeResponse(data=FakeModel(id=INSTANCE_ID, lifecycle_state="RUNNING"))

        def serialize_result_resource(self, resource):
            return {"id": resource.id, "lifecycle_state": resource.lifecycle_state}

    monkeypatch.setattr(module_obj, "OciInstanceActionsModule", SuccessfulActionsModule)

    with pytest.raises(ExitJsonCalled) as exc_info:
        module_obj.main()

    assert exc_info.value.payload == {
        "changed": True,
        "action": "start",
        "resource": {"id": INSTANCE_ID, "lifecycle_state": "RUNNING"},
    }


def test_process_action_does_not_repeat_action_after_wait_failure(monkeypatch):
    """Verify that a wait failure does not repeat the action."""
    module_obj = load_actions_module(monkeypatch)
    calls = []

    class FailedComposite:
        """Simulate an accepted action followed by a wait failure."""

        def __init__(self, client):
            """Accept the compute client without making API calls."""

        def instance_action_and_wait_for_state(self, *args, **kwargs):
            """Record the call and report a wait failure."""
            calls.append(args)
            raise RuntimeError("Wait timeout")

    module_obj.oci.core.ComputeClientCompositeOperations = FailedComposite
    instance = make_actions_module(
        module_obj,
        {"instance_id": INSTANCE_ID, "action": "reset", "wait": True},
    )
    with pytest.raises(RuntimeError, match="Wait timeout"):
        instance.process_action()
    assert calls == [(INSTANCE_ID, "RESET")]
