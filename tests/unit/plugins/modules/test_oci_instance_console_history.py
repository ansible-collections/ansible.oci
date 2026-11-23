from __future__ import absolute_import, division, print_function

__metaclass__ = type

import types

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
    raising,
)


MODEL_NAMES = ("CaptureConsoleHistoryDetails", "UpdateConsoleHistoryDetails")


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(monkeypatch, model_names=MODEL_NAMES)


def make_history_module(module_obj, params, client=None, check_mode=False):
    return make_module_instance(
        module_obj,
        "OciInstanceConsoleHistoryModule",
        params,
        client=client,
        check_mode=check_mode,
    )


def test_main_exposes_history_arguments(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_console_history")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule({})

    class FakeHistoryModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciInstanceConsoleHistoryModule", FakeHistoryModule)

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["argument_spec"]["instance_console_history_id"] == {"type": "str"}
    assert captured["argument_spec"]["name"] == {"type": "str"}
    assert captured["argument_spec"]["state"]["choices"] == ["present", "absent"]


def test_resolve_target_resource_prefers_id(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_console_history")
    instance = make_history_module(
        module_obj,
        {"instance_console_history_id": "history-id", "name": "history"},
    )
    monkeypatch.setattr(
        instance, "get_resource_by_id", lambda resource_id: FakeModel(id=resource_id, lifecycle_state="SUCCEEDED")
    )
    monkeypatch.setattr(instance, "list_all_resources", raising(AssertionError("name lookup was called")))

    assert instance.resolve_target_resource().id == "history-id"


def test_name_lookup_is_scoped_and_exact(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_console_history")
    calls = []
    matching = FakeModel(
        id="matching", display_name="history", compartment_id="compartment",
        instance_id="instance", lifecycle_state="SUCCEEDED",
    )
    instance = make_history_module(
        module_obj,
        {
            "name": "history",
            "compartment_id": "compartment",
            "instance_id": "instance",
        },
        client=types.SimpleNamespace(list_console_histories="list-histories"),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda method, **kwargs: calls.append((method, kwargs)) or [
            FakeModel(id="prefix", display_name="history-other"),
            matching,
        ],
    )

    assert instance.resolve_target_resource() is matching
    assert calls == [
        (
            "list-histories",
            {"compartment_id": "compartment", "instance_id": "instance"},
        )
    ]


def test_name_lookup_rejects_ambiguous_matches(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_console_history")
    instance = make_history_module(
        module_obj,
        {"name": "history", "compartment_id": "compartment", "instance_id": "instance"},
        client=types.SimpleNamespace(list_console_histories="list-histories"),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda method, **kwargs: [
            FakeModel(id="one", display_name="history"),
            FakeModel(id="two", display_name="history"),
        ],
    )
    with pytest.raises(FailJsonCalled):
        instance.resolve_target_resource()


def test_create_rejects_instance_from_other_compartment(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_console_history")
    instance = make_history_module(
        module_obj,
        {"instance_id": "instance", "compartment_id": "wanted", "name": "history"},
        client=types.SimpleNamespace(
            get_instance=lambda **kwargs: FakeResponse(FakeModel(compartment_id="other"))
        ),
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()
    assert "specified compartment" in exc_info.value.payload["msg"]


def test_create_captures_history_with_stable_retry_token(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_console_history")
    calls = []

    def capture_console_history(**kwargs):
        calls.append(kwargs)
        return FakeResponse(FakeModel(id="history-id", lifecycle_state="REQUESTED"))

    instance = make_history_module(
        module_obj,
        {
            "instance_id": "instance",
            "compartment_id": "compartment",
            "name": "history",
            "freeform_tags": {"env": "test"},
            "wait": False,
        },
        client=types.SimpleNamespace(capture_console_history=capture_console_history),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    result = instance.create_resource()

    assert result.id == "history-id"
    assert calls[0]["opc_retry_token"]
    details = calls[0]["capture_console_history_details"]
    assert details.instance_id == "instance"
    assert not hasattr(details, "compartment_id")
    assert details.display_name == "history"
    assert details.freeform_tags == {"env": "test"}


def test_create_check_mode_does_not_call_capture(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_console_history")
    instance = make_history_module(
        module_obj,
        {"state": "present", "instance_id": "instance", "compartment_id": "compartment", "name": "history"},
        client=types.SimpleNamespace(
            capture_console_history=raising(AssertionError("capture was called"))
        ),
        check_mode=True,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)
    monkeypatch.setattr(instance, "validate_create_request", lambda: None)
    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()
    assert exc_info.value.payload["changed"] is True


def test_update_rejects_immutable_scope_changes(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_console_history")
    instance = make_history_module(module_obj, {"instance_id": "new-instance"})

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(FakeModel(id="history-id", instance_id="old-instance"))

    assert "instance_id" in exc_info.value.payload["msg"]


def test_delete_waits_for_disappearance(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_console_history")
    calls = []
    instance = make_history_module(
        module_obj,
        {"wait": True},
        client=types.SimpleNamespace(
            delete_console_history=lambda **kwargs: calls.append(kwargs)
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, failure_states: calls.append((resource_id, target_states, failure_states)),
    )

    instance.delete_resource(FakeModel(id="history-id", lifecycle_state="FAILED"))

    assert calls[0] == {"instance_console_history_id": "history-id"}
    assert calls[1][0] == "history-id"
    assert set(calls[1][1]) == {"DELETED", "TERMINATED"}
    assert not calls[1][2]


@pytest.mark.parametrize("check_mode", [False, True])
def test_existing_named_capture_is_unchanged(monkeypatch, check_mode):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_console_history")
    current = FakeModel(
        id="history-id", display_name="history", compartment_id="compartment",
        instance_id="instance", lifecycle_state="SUCCEEDED",
    )
    instance = make_history_module(
        module_obj,
        {"name": "history", "compartment_id": "compartment", "instance_id": "instance"},
        client=types.SimpleNamespace(list_console_histories="list-histories"),
        check_mode=check_mode,
    )
    monkeypatch.setattr(instance, "list_all_resources", lambda *args, **kwargs: [current])

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload["changed"] is False
    assert exc_info.value.payload["resource"]["id"] == "history-id"


def test_create_waits_for_capture_success(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_console_history")
    current = FakeModel(id="history-id", lifecycle_state="REQUESTED")
    completed = FakeModel(id="history-id", lifecycle_state="SUCCEEDED")
    instance = make_history_module(
        module_obj,
        {"instance_id": "instance", "name": "history"},
        client=types.SimpleNamespace(capture_console_history=lambda **kwargs: FakeResponse(current)),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    def wait_for_capture(resource_id, target_states):
        assert resource_id == current.id
        assert target_states == ("SUCCEEDED",)
        return completed

    monkeypatch.setattr(instance, "wait_for_resource_id", wait_for_capture)

    assert instance.create_resource() is completed


@pytest.mark.parametrize("lookup_by_id", [False, True], ids=["name", "ocid"])
@pytest.mark.parametrize(
    ("initial_state", "final_state"),
    [
        ("REQUESTED", "SUCCEEDED"),
        ("GETTING-HISTORY", "SUCCEEDED"),
        ("FAILED", "FAILED"),
        ("GETTING-HISTORY", "FAILED"),
    ],
)
def test_existing_capture_waits_on_rerun(monkeypatch, lookup_by_id, initial_state, final_state):
    """Verify reruns wait for success or report a capture failure."""
    from ansible_collections.ansible.oci.plugins.module_utils import oci_resource

    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_console_history")
    fields = dict(id="history-id", display_name="history", compartment_id="compartment", instance_id="instance")
    current = FakeModel(**fields, lifecycle_state=initial_state)
    final = FakeModel(**fields, lifecycle_state=final_state)
    params = {"wait": True}
    if lookup_by_id:
        params["instance_console_history_id"] = current.id
    else:
        params.update(name=current.display_name, compartment_id=current.compartment_id, instance_id=current.instance_id)

    responses = iter([current] * (2 if lookup_by_id else 1) + [final])
    client = types.SimpleNamespace(
        list_console_histories="list-histories",
        get_console_history=lambda **kwargs: FakeResponse(next(responses)),
    )
    instance = make_history_module(module_obj, params, client=client)
    monkeypatch.setattr(instance, "list_all_resources", lambda *args, **kwargs: [current])
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    def wait_until(client, response, evaluate_response, fetch_func, **kwargs):
        """Simulate one OCI poll if the initial response is pending."""
        if evaluate_response(response):
            return response
        response = fetch_func(response)
        assert evaluate_response(response)
        return response

    monkeypatch.setattr(oci_resource, "oci", types.SimpleNamespace(wait_until=wait_until))
    if final_state == "FAILED":
        with pytest.raises(FailJsonCalled) as exc_info:
            instance.execute_resource_module()

        assert "Resource history-id entered failure state: FAILED" in exc_info.value.payload["msg"]
    else:
        with pytest.raises(ExitJsonCalled) as exc_info:
            instance.execute_resource_module()

        assert exc_info.value.payload["changed"] is False
        assert exc_info.value.payload["resource"]["lifecycle_state"] == "SUCCEEDED"


@pytest.mark.parametrize("state", ["REQUESTED", "GETTING-HISTORY", "FAILED"])
@pytest.mark.parametrize(("wait", "check_mode"), [(False, False), (True, True)])
def test_existing_capture_returns_current_state_without_waiting(monkeypatch, state, wait, check_mode):
    """Verify that check mode and wait=false return the current state."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_console_history")
    instance = make_history_module(
        module_obj, {"instance_console_history_id": "history-id", "wait": wait}, check_mode=check_mode
    )
    current = FakeModel(id="history-id", lifecycle_state=state)
    monkeypatch.setattr(instance, "get_resource_by_id", lambda resource_id: current)
    monkeypatch.setattr(instance, "wait_for_resource_id", raising(AssertionError("wait was called")))

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload["changed"] is False
    assert exc_info.value.payload["resource"]["lifecycle_state"] == state


def test_delete_failed_capture_skips_capture_completion(monkeypatch):
    """Verify that state=absent can delete an existing failed capture."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_console_history")
    instance = make_history_module(
        module_obj, {"instance_console_history_id": "history-id", "state": "absent"}
    )
    current = FakeModel(id="history-id", lifecycle_state="FAILED")
    deleted = []
    monkeypatch.setattr(instance, "get_resource_by_id", lambda resource_id: current)
    monkeypatch.setattr(instance, "wait_for_resource_id", raising(AssertionError("capture wait was called")))
    monkeypatch.setattr(instance, "delete_resource", deleted.append)

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload == {"changed": True}
    assert deleted == [current]


@pytest.mark.parametrize("wait", [False, True])
def test_delete_returns_without_wait_for_disabled_wait_or_missing_capture(monkeypatch, wait):
    """Verify that delete skips polling when waiting is disabled or OCI returns 404."""
    _oci_module, service_error = install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_console_history")

    def delete_console_history(instance_console_history_id):
        """Simulate OCI deleting the capture or returning 404."""
        assert instance_console_history_id == "history-id"
        if wait:
            raise service_error(404)

    instance = make_history_module(
        module_obj, {"wait": wait}, client=types.SimpleNamespace(delete_console_history=delete_console_history)
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(instance, "wait_for_resource_id", raising(AssertionError("wait was called")))

    assert instance.delete_resource(FakeModel(id="history-id")) is None
