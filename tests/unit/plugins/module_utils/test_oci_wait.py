import sys
import types

import pytest

from conftest import load_collection_module


class FailJsonCalled(Exception):
    def __init__(self, payload):
        self.payload = payload


class DummyModule:
    def __init__(self, params):
        self.params = params

    def fail_json(self, **kwargs):
        raise FailJsonCalled(kwargs)


def install_fake_oci(monkeypatch, *, pagination=None, retry=None, wait_until=None):
    oci_module = types.ModuleType("oci")
    exceptions_module = types.ModuleType("oci.exceptions")

    class ServiceError(Exception):
        def __init__(self, status):
            super().__init__(status)
            self.status = status

    exceptions_module.ServiceError = ServiceError
    oci_module.exceptions = exceptions_module
    oci_module.pagination = pagination or types.SimpleNamespace()
    oci_module.retry = retry or types.SimpleNamespace()
    oci_module.wait_until = wait_until

    monkeypatch.setitem(sys.modules, "oci", oci_module)
    monkeypatch.setitem(sys.modules, "oci.exceptions", exceptions_module)

    return ServiceError


@pytest.mark.parametrize(
    ("helper_name", "args", "kwargs"),
    [
        ("list_all_resources", (object(),), {}),
        ("wait_for_resource", (DummyModule({"wait": True}), object(), object(), "resource-id", ("ACTIVE",)), {}),
        ("wait_for_work_request", (DummyModule({}), object(), "work-request-id"), {}),
        ("call_with_retry", (lambda: None,), {}),
    ],
)
def test_wait_helpers_use_shared_sdk_required_message(
    monkeypatch,
    helper_name,
    args,
    kwargs,
):
    oci_wait = load_collection_module("oci_wait")
    monkeypatch.setattr(oci_wait, "HAS_OCI_SDK", False)
    oci_wait.OCI_SDK_REQUIRED_MSG = "Shared OCI SDK message"

    with pytest.raises(ImportError, match="Shared OCI SDK message"):
        getattr(oci_wait, helper_name)(*args, **kwargs)


def test_list_all_resources_uses_oci_pagination_helper(monkeypatch):
    recorded_call = {}

    def fake_list_call_get_all_results(list_fn, *args, **kwargs):
        recorded_call["list_fn"] = list_fn
        recorded_call["args"] = args
        recorded_call["kwargs"] = kwargs
        return types.SimpleNamespace(data=["first", "second"])

    install_fake_oci(
        monkeypatch,
        pagination=types.SimpleNamespace(
            list_call_get_all_results=fake_list_call_get_all_results,
        ),
    )

    oci_wait = load_collection_module("oci_wait")

    list_fn = object()
    results = oci_wait.list_all_resources(list_fn, "compartment-id", limit=25)

    assert results == ["first", "second"]
    assert recorded_call == {
        "list_fn": list_fn,
        "args": ("compartment-id",),
        "kwargs": {"limit": 25},
    }


def test_call_with_retry_uses_oci_retry_strategy_builder(monkeypatch):
    recorded_call = {}

    class FakeRetryStrategy:
        def make_retrying_call(self, fn, *args, **kwargs):
            recorded_call["fn"] = fn
            recorded_call["args"] = args
            recorded_call["kwargs"] = kwargs
            return fn(*args, **kwargs)

    class FakeRetryStrategyBuilder:
        def __init__(self, **kwargs):
            recorded_call["builder_kwargs"] = kwargs

        def get_retry_strategy(self):
            return FakeRetryStrategy()

    install_fake_oci(
        monkeypatch,
        retry=types.SimpleNamespace(
            RetryStrategyBuilder=FakeRetryStrategyBuilder,
        ),
    )

    oci_wait = load_collection_module("oci_wait")

    result = oci_wait.call_with_retry(
        lambda value, *, suffix: f"{value}-{suffix}",
        "retry",
        suffix="ok",
        max_retries=4,
        retry_on=(429, 503),
    )

    assert result == "retry-ok"
    assert recorded_call["args"] == ("retry",)
    assert recorded_call["kwargs"] == {"suffix": "ok"}
    assert recorded_call["builder_kwargs"]["max_attempts"] == 5
    assert recorded_call["builder_kwargs"]["service_error_retry_config"] == {
        429: [],
        503: [],
    }


def test_wait_for_resource_uses_oci_wait_until(monkeypatch):
    recorded_call = {}
    final_response = types.SimpleNamespace(
        data=types.SimpleNamespace(lifecycle_state="ACTIVE"),
    )

    def fake_wait_until(client, response, **kwargs):
        recorded_call["client"] = client
        recorded_call["response"] = response
        recorded_call["kwargs"] = kwargs
        return final_response

    install_fake_oci(monkeypatch, wait_until=fake_wait_until)

    oci_wait = load_collection_module("oci_wait")

    initial_response = types.SimpleNamespace(
        data=types.SimpleNamespace(lifecycle_state="CREATING"),
    )
    client = types.SimpleNamespace(base_client=types.SimpleNamespace())
    module = DummyModule(
        {
            "wait": True,
            "wait_timeout": 900,
            "wait_interval": 15,
        }
    )

    result = oci_wait.wait_for_resource(
        module,
        client,
        lambda resource_id: initial_response,
        "resource-ocid",
        ("ACTIVE", "AVAILABLE"),
    )

    assert result is final_response.data
    assert recorded_call["client"] is client
    assert recorded_call["response"] is initial_response
    assert recorded_call["kwargs"]["max_wait_seconds"] == 900
    assert recorded_call["kwargs"]["max_interval_seconds"] == 15
    assert recorded_call["kwargs"]["evaluate_response"](final_response) is True


def test_wait_for_work_request_accepts_getter_callback(monkeypatch):
    recorded_call = {}
    final_response = types.SimpleNamespace(
        data=types.SimpleNamespace(status="SUCCEEDED"),
    )

    def fake_wait_until(client, response, **kwargs):
        recorded_call["client"] = client
        recorded_call["response"] = response
        recorded_call["kwargs"] = kwargs
        return final_response

    install_fake_oci(monkeypatch, wait_until=fake_wait_until)

    oci_wait = load_collection_module("oci_wait")

    initial_response = types.SimpleNamespace(
        data=types.SimpleNamespace(status="IN_PROGRESS"),
    )
    requested_ids = []

    def get_work_request(work_request_id):
        requested_ids.append(work_request_id)
        return initial_response

    client = types.SimpleNamespace(base_client=types.SimpleNamespace())
    module = DummyModule(
        {
            "wait_timeout": 1200,
            "wait_interval": 30,
        }
    )

    result = oci_wait.wait_for_work_request(
        module,
        client,
        "work-request-ocid",
        get_work_request_fn=get_work_request,
    )

    assert result is final_response.data
    assert requested_ids == ["work-request-ocid"]
    assert recorded_call["client"] is client
    assert recorded_call["response"] is initial_response
    assert recorded_call["kwargs"]["evaluate_response"](final_response) is True


def test_wait_for_resource_uses_dead_states_for_not_found_handling(monkeypatch):
    ServiceError = install_fake_oci(
        monkeypatch,
        wait_until=lambda client, response, **kwargs: response,
    )

    oci_wait = load_collection_module("oci_wait")
    monkeypatch.setattr(
        oci_wait,
        "DEAD_STATES",
        frozenset({"REMOVED"}),
        raising=False,
    )

    module = DummyModule(
        {
            "wait": True,
            "wait_timeout": 1200,
            "wait_interval": 30,
        }
    )
    client = types.SimpleNamespace(base_client=types.SimpleNamespace())

    def get_resource(resource_id):
        raise ServiceError(404)

    result = oci_wait.wait_for_resource(
        module,
        client,
        get_resource,
        "resource-ocid",
        ("REMOVED",),
    )

    assert result is None
