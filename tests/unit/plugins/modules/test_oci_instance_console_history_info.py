from __future__ import absolute_import, division, print_function

__metaclass__ = type

import types

import pytest
from ansible.module_utils.common.arg_spec import ModuleArgumentSpecValidator

from .conftest import (
    DummyModule,
    FailJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


def make_history_info_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciInstanceConsoleHistoryInfoModule",
        params,
        client=client,
    )


def test_main_validates_content_options(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_console_history_info")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        validator = ModuleArgumentSpecValidator(
            kwargs["argument_spec"], required_if=kwargs["required_if"], required_one_of=kwargs["required_one_of"]
        )
        result = validator.validate(
            {"instance_console_history_id": "history-id", "name": "history", "include_content": True}
        )
        assert not result.error_messages
        capture_by_list = validator.validate({"compartment_id": "compartment", "include_content": True})
        assert any("instance_console_history_id" in error for error in capture_by_list.error_messages)
        return DummyModule(result.validated_parameters)

    class FakeHistoryInfoModule:
        def __init__(self, module):
            self.module = module

        def execute_info_module(self):
            captured["params"] = self.module.params

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciInstanceConsoleHistoryInfoModule", FakeHistoryInfoModule)

    module_obj.main()

    assert captured["params"]["instance_console_history_id"] == "history-id"
    assert captured["params"]["name"] == "history"
    assert captured["required_one_of"] == [["compartment_id", "instance_console_history_id"]]
    assert captured["argument_spec"]["instance_console_history_id"] == {"type": "str"}
    assert captured["argument_spec"]["name"] == {"type": "str"}
    assert captured["argument_spec"]["include_content"] == {"type": "bool", "default": False}
    assert captured["argument_spec"]["lifecycle_state"]["choices"] == [
        "requested",
        "getting_history",
        "succeeded",
        "failed",
    ]


def test_fetch_resources_prefers_id_lookup(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_console_history_info")
    calls = []

    def get_history(**kwargs):
        calls.append(kwargs)
        return FakeResponse(FakeModel(id="history-id", lifecycle_state="SUCCEEDED"))

    instance = make_history_info_module(
        module_obj,
        {
            "instance_console_history_id": "history-id",
            "compartment_id": "compartment",
            "lifecycle_state": "FAILED",
        },
        client=types.SimpleNamespace(get_console_history=get_history),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(instance, "list_all_resources", raising(AssertionError("list was called")))

    resources = instance.fetch_resources()

    assert calls == [{"instance_console_history_id": "history-id"}]
    assert len(resources) == 1
    assert resources[0].id == "history-id"


def test_fetch_resources_returns_empty_list_on_missing_id(monkeypatch):
    _oci_module, service_error = install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_console_history_info")

    def get_missing(**kwargs):
        raise service_error(404, "missing")

    instance = make_history_info_module(
        module_obj,
        {"instance_console_history_id": "missing"},
        client=types.SimpleNamespace(get_console_history=get_missing),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.fetch_resources() == []


def test_fetch_resources_lists_with_scope_and_filters(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_console_history_info")
    calls = []
    instance = make_history_info_module(
        module_obj,
        {
            "compartment_id": "compartment",
            "instance_id": "instance",
            "name": "history",
            "lifecycle_state": "GETTING-HISTORY",
        },
        client=types.SimpleNamespace(list_console_histories="list-histories"),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda method, **kwargs: calls.append((method, kwargs)) or [
            FakeModel(id="history-id", display_name="history", lifecycle_state="GETTING-HISTORY")
        ],
    )

    resources = instance.fetch_resources()

    assert len(resources) == 1
    assert calls == [
        (
            "list-histories",
            {
                "compartment_id": "compartment",
                "instance_id": "instance",
                "lifecycle_state": "GETTING-HISTORY",
            },
        )
    ]


@pytest.mark.parametrize(
    "sdk_state, expected_state",
    [
        ("requested", "REQUESTED"),
        ("getting_history", "GETTING-HISTORY"),
        ("succeeded", "SUCCEEDED"),
        ("failed", "FAILED"),
    ],
)
def test_state_mapping_is_stable(monkeypatch, sdk_state, expected_state):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_console_history_info")
    captured = {}
    fake_module = DummyModule({"lifecycle_state": sdk_state})
    fake_module.deprecate = lambda *args, **kwargs: None

    def fake_ansible_module(**kwargs):
        return fake_module

    class FakeInfo:
        def __init__(self, module):
            pass

        def execute_info_module(self):
            captured["state"] = fake_module.params["lifecycle_state"]

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciInstanceConsoleHistoryInfoModule", FakeInfo)
    module_obj.main()
    assert captured["state"] == expected_state


def test_content_is_not_requested_by_default(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_console_history_info")
    calls = []
    instance = make_history_info_module(
        module_obj,
        {"instance_console_history_id": "history-id"},
        client=types.SimpleNamespace(
            get_console_history=lambda **kwargs: FakeResponse(
                FakeModel(id="history-id", lifecycle_state="SUCCEEDED")
            ),
            get_console_history_content=lambda **kwargs: calls.append(kwargs),
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    result = instance.serialize_result_resource(instance.fetch_resources()[0])

    assert "content_base64" not in result
    assert calls == []


def test_include_content_decodes_succeeded_history(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_console_history_info")
    instance = make_history_info_module(
        module_obj,
        {"instance_console_history_id": "history-id", "include_content": True},
        client=types.SimpleNamespace(
            get_console_history=lambda **kwargs: FakeResponse(
                FakeModel(id="history-id", lifecycle_state="SUCCEEDED")
            ),
            get_console_history_content=lambda **kwargs: FakeResponse(
                data=b"\x00\xffconsole\n"
            ),
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    resources = instance.fetch_resources()

    result = instance.serialize_result_resource(resources[0])
    assert result["content_base64"] == "AP9jb25zb2xlCg=="


@pytest.mark.parametrize("state", ["REQUESTED", "GETTING-HISTORY", "FAILED"])
def test_include_content_rejects_non_succeeded_history(monkeypatch, state):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_console_history_info")
    instance = make_history_info_module(
        module_obj,
        {"instance_console_history_id": "history-id", "include_content": True},
        client=types.SimpleNamespace(
            get_console_history_content=raising(AssertionError("content was requested"))
        ),
    )
    with pytest.raises(FailJsonCalled) as exc_info:
        instance.serialize_result_resource(FakeModel(id="history-id", lifecycle_state=state))
    assert f"is in state {state}" in exc_info.value.payload["msg"]
