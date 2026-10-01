from __future__ import absolute_import, division, print_function
__metaclass__ = type

from threading import Barrier, Event, Lock, get_ident

import pytest

from ansible.module_utils.common.parameters import env_fallback

from .conftest import load_collection_module


def test_threaded_map_skips_empty_input():
    oci_common = load_collection_module("oci_common")

    def unused_worker(value):
        pytest.fail("Empty input must not call a worker")

    assert oci_common.threaded_map(unused_worker, iter(())) == []


def test_threaded_map_runs_iterator_concurrently_with_worker_limit():
    oci_common = load_collection_module("oci_common")
    barrier = Barrier(2, timeout=5)
    lock = Lock()
    running = 0
    peak = 0
    thread_ids = set()

    def worker(value):
        nonlocal running, peak
        with lock:
            running += 1
            peak = max(peak, running)
            thread_ids.add(get_ident())
        barrier.wait()
        with lock:
            running -= 1
        return value * 2

    assert oci_common.threaded_map(worker, iter([3, 1, 4, 2]), max_workers=2) == [6, 2, 8, 4]
    assert peak == 2
    assert len(thread_ids) == 2
    assert running == 0


def test_threaded_map_returns_results_in_input_order():
    oci_common = load_collection_module("oci_common")
    second_finished = Event()

    def worker(value):
        if value == "first":
            assert second_finished.wait(5)
        else:
            second_finished.set()
        return value

    assert oci_common.threaded_map(worker, ["first", "second"]) == ["first", "second"]


def test_threaded_map_finishes_submitted_work_before_propagating_error():
    oci_common = load_collection_module("oci_common")
    second_started = Event()
    failed = Event()
    completed = []
    lock = Lock()
    error = RuntimeError("cleanup failed")

    def worker(value):
        if value == 0:
            assert second_started.wait(5)
            failed.set()
            raise error
        second_started.set()
        assert failed.wait(5)
        with lock:
            completed.append(value)
        return value

    with pytest.raises(RuntimeError, match="cleanup failed") as result:
        oci_common.threaded_map(worker, range(6), max_workers=2)

    assert result.value is error
    assert sorted(completed) == [1, 2, 3, 4, 5]


def test_filter_none_values_only_removes_none_entries():
    oci_common = load_collection_module("oci_common")

    result = oci_common.filter_none_values(
        {
            "string": "value",
            "none_value": None,
            "false_value": False,
            "zero_value": 0,
            "empty_string": "",
            "empty_list": [],
            "empty_dict": {},
        }
    )

    assert result == {
        "string": "value",
        "false_value": False,
        "zero_value": 0,
        "empty_string": "",
        "empty_list": [],
        "empty_dict": {},
    }


def test_normalize_enum_values_upper_cases_only_declared_keys_recursively():
    oci_common = load_collection_module("oci_common")

    result = oci_common.normalize_enum_values(
        {
            "recovery_action": "stop_instance",
            "nested": {"type": "amd_vm"},
            "items": [{"desired_state": "enabled"}],
            "unrelated": "left_alone",
        },
        {"recovery_action", "type", "desired_state"},
    )

    assert result == {
        "recovery_action": "STOP_INSTANCE",
        "nested": {"type": "AMD_VM"},
        "items": [{"desired_state": "ENABLED"}],
        "unrelated": "left_alone",
    }


def test_strip_none_values_removes_none_at_every_nesting_level():
    oci_common = load_collection_module("oci_common")

    result = oci_common.strip_none_values(
        {
            "kept": "value",
            "dropped": None,
            "nested": {"kept": 1, "dropped": None},
            "items": [{"kept": "a", "dropped": None}, None],
        }
    )

    assert result == {
        "kept": "value",
        "nested": {"kept": 1},
        "items": [{"kept": "a"}, None],
    }


def test_values_differ_as_subset_ignores_extra_current_fields_at_any_depth():
    oci_common = load_collection_module("oci_common")

    current_value = {"mode": "ACTIVE", "routing": {"policy": "STATIC", "priority": 10}}
    desired_value = {"mode": "ACTIVE", "routing": {"policy": "STATIC", "priority": None}}

    assert oci_common.values_differ_as_subset(current_value, desired_value) is False


def test_values_differ_as_subset_detects_nested_drift():
    oci_common = load_collection_module("oci_common")

    current_value = {"routing": {"policy": "STATIC"}}
    desired_value = {"routing": {"policy": "DYNAMIC"}}

    assert oci_common.values_differ_as_subset(current_value, desired_value) is True


def test_values_differ_as_subset_compares_nested_lists_as_a_whole():
    oci_common = load_collection_module("oci_common")

    current_value = {"items": [{"name": "a", "state": "ENABLED"}]}

    matching_value = {"items": [{"name": "a", "state": "ENABLED"}]}
    assert oci_common.values_differ_as_subset(current_value, matching_value) is False

    drifted_value = {"items": [{"name": "a", "state": "DISABLED"}]}
    assert oci_common.values_differ_as_subset(current_value, drifted_value) is True


class FakeOciNestedModel:
    swagger_types = {"name": "str"}
    attribute_map = {"name": "name"}

    def __init__(self, name):
        self._name = name

    @property
    def name(self):
        return self._name


class FakeOciModel:
    swagger_types = {
        "id": "str",
        "display_name": "str",
        "cidr_blocks": "list[str]",
        "nested": "FakeOciNestedModel",
    }
    attribute_map = {
        "id": "id",
        "display_name": "displayName",
        "cidr_blocks": "cidrBlocks",
        "nested": "nested",
    }

    def __init__(self):
        self._id = "ocid1.vcn.oc1..example"
        self._display_name = "example-vcn"
        self._cidr_blocks = ["10.0.0.0/16"]
        self._nested = FakeOciNestedModel("nested-resource")

    @property
    def id(self):
        return self._id

    @property
    def display_name(self):
        return self._display_name

    @property
    def cidr_blocks(self):
        return self._cidr_blocks

    @property
    def nested(self):
        return self._nested


def test_serialize_oci_model_serializes_oci_sdk_style_model_properties():
    oci_common = load_collection_module("oci_common")

    result = oci_common.serialize_oci_model(FakeOciModel())

    assert result == {
        "id": "ocid1.vcn.oc1..example",
        "display_name": "example-vcn",
        "cidr_blocks": ["10.0.0.0/16"],
        "nested": {"name": "nested-resource"},
    }


def test_oci_auth_args_define_defaults_and_env_fallbacks():
    oci_common = load_collection_module("oci_common")

    assert oci_common.OCI_AUTH_ARGS["config_file_location"]["default"] == "~/.oci/config"
    assert oci_common.OCI_AUTH_ARGS["config_file_location"]["fallback"] == (
        env_fallback,
        ["OCI_CONFIG_FILE"],
    )

    assert oci_common.OCI_AUTH_ARGS["config_profile_name"]["default"] == "DEFAULT"
    assert oci_common.OCI_AUTH_ARGS["config_profile_name"]["fallback"] == (
        env_fallback,
        ["OCI_CONFIG_PROFILE"],
    )

    assert oci_common.OCI_AUTH_ARGS["auth_type"]["default"] == "api_key"
    assert oci_common.OCI_AUTH_ARGS["auth_type"]["choices"] == [
        "api_key",
        "instance_principal",
        "resource_principal",
        "session_token",
    ]
    assert oci_common.OCI_AUTH_ARGS["auth_type"]["fallback"] == (
        env_fallback,
        ["OCI_AUTH_TYPE"],
    )

    expected_fallbacks = {
        "tenancy": ["OCI_TENANCY_ID"],
        "region": ["OCI_REGION"],
        "api_user": ["OCI_USER_ID"],
        "api_user_fingerprint": ["OCI_USER_FINGERPRINT"],
        "api_user_key_file": ["OCI_USER_KEY_FILE"],
        "api_user_key_pass_phrase": ["OCI_USER_KEY_PASS_PHRASE"],
    }

    for param_name, env_vars in expected_fallbacks.items():
        assert oci_common.OCI_AUTH_ARGS[param_name]["fallback"] == (
            env_fallback,
            env_vars,
        )
