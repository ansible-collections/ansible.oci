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
)


ADB_MODEL_NAMES = (
    "CreateAutonomousDatabaseDetails",
    "UpdateAutonomousDatabaseDetails",
)


def install_fake_oci(monkeypatch):
    oci_module, service_error = shared_install_fake_oci(monkeypatch)
    oci_module.database = types.SimpleNamespace(
        DatabaseClient=type("FakeDatabaseClient", (), {}),
        models=types.SimpleNamespace(
            **{model_name: FakeModel for model_name in ADB_MODEL_NAMES}
        ),
    )
    return oci_module, service_error


def make_adb_module(module_obj, params, client=None, check_mode=False):
    return make_module_instance(
        module_obj,
        "OciAutonomousDatabaseModule",
        params,
        client=client,
        check_mode=check_mode,
    )


def test_main_wires_argument_spec_and_runs_module(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        captured["supports_check_mode"] = kwargs.get("supports_check_mode")
        return DummyModule({})

    class FakeAdbModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciAutonomousDatabaseModule", FakeAdbModule)

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["supports_check_mode"] is True
    # name/compartment_id come from the shared OCI_COMMON_ARGS.
    assert captured["argument_spec"]["name"] == {"type": "str"}
    assert captured["argument_spec"]["compartment_id"] == {"type": "str"}
    # autonomous-database-specific params.
    assert captured["argument_spec"]["state"] == {
        "type": "str",
        "choices": ["present", "absent", "running", "stopped"],
        "default": "present",
    }
    assert captured["argument_spec"]["autonomous_database_id"] == {"type": "str"}
    assert captured["argument_spec"]["admin_password"] == {
        "type": "str",
        "no_log": True,
    }
    assert captured["argument_spec"]["compute_count"] == {"type": "float"}
    assert captured["argument_spec"]["db_workload"] == {
        "type": "str",
        "choices": ["oltp", "dw", "ajd", "apex"],
    }
    # The display field is exposed as ``name``, never ``display_name``.
    assert "display_name" not in captured["argument_spec"]


def test_main_normalizes_enum_values_to_sdk_constants(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database")
    captured = {}

    params = {
        "db_workload": "oltp",
        "compute_model": "ecpu",
        "license_model": "bring_your_own_license",
        "auth_type": "api_key",
    }

    def fake_ansible_module(**kwargs):
        return DummyModule(params)

    class FakeAdbModule:
        def __init__(self, module):
            captured["module"] = module

        def execute_resource_module(self):
            pass

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciAutonomousDatabaseModule", FakeAdbModule)

    module_obj.main()

    normalized = captured["module"].params
    # Enum values are upper-cased to the SDK vocabulary before the module runs.
    assert normalized["db_workload"] == "OLTP"
    assert normalized["compute_model"] == "ECPU"
    assert normalized["license_model"] == "BRING_YOUR_OWN_LICENSE"
    # Keys that merely end in "_type" are not enum keys and are left untouched.
    assert normalized["auth_type"] == "api_key"


def test_class_metadata(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database")
    cls = module_obj.OciAutonomousDatabaseModule

    assert cls.resource_id_param == "autonomous_database_id"
    assert cls.list_resource_method == "list_autonomous_databases"
    assert cls.update_method_name == "update_autonomous_database"
    assert cls.update_details_name == "update_autonomous_database_details"
    assert cls.create_resource_name == "autonomous database"
    # Standard display_name resource: base defaults resolve name against display_name.
    assert cls.name_response_field == "display_name"


def test_build_create_details_maps_name_to_display_name(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database")
    details = module_obj.build_create_autonomous_database_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "db_name": "exampleadb",
            "name": "example-adb",
            "admin_password": "Secret_Passw0rd",
            "db_workload": "OLTP",
            "compute_model": "ECPU",
            "compute_count": 2.0,
            "data_storage_size_in_tbs": 1,
            "is_auto_scaling_enabled": True,
            "whitelisted_ips": ["10.0.0.0/24"],
            "freeform_tags": {"env": "dev"},
        }
    )

    assert isinstance(details, FakeModel)
    assert details.display_name == "example-adb"
    assert not hasattr(details, "name")
    assert details.db_name == "exampleadb"
    assert details.admin_password == "Secret_Passw0rd"
    assert details.compute_count == 2.0
    assert details.is_auto_scaling_enabled is True
    assert details.whitelisted_ips == ["10.0.0.0/24"]
    assert details.freeform_tags == {"env": "dev"}


def test_build_create_details_omits_unset_values(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database")
    details = module_obj.build_create_autonomous_database_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "db_name": "exampleadb",
            "name": "example-adb",
            "admin_password": "Secret_Passw0rd",
            "compute_count": 2.0,
            "data_storage_size_in_tbs": 1,
            # A False bool is a real value and must be kept.
            "is_free_tier": False,
            "db_workload": None,
            "license_model": None,
            "nsg_ids": None,
        }
    )

    assert not hasattr(details, "db_workload")
    assert not hasattr(details, "license_model")
    assert not hasattr(details, "nsg_ids")
    assert details.is_free_tier is False


def test_validate_create_request_requires_compute(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database")
    instance = make_adb_module(
        module_obj,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-adb",
            "db_name": "exampleadb",
            "admin_password": "Secret_Passw0rd",
            "compute_count": None,
            "cpu_core_count": None,
            "data_storage_size_in_tbs": 1,
        },
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "compute_count" in exc_info.value.payload["msg"]


def test_validate_create_request_requires_storage(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database")
    instance = make_adb_module(
        module_obj,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-adb",
            "db_name": "exampleadb",
            "admin_password": "Secret_Passw0rd",
            "compute_count": 2.0,
            "data_storage_size_in_tbs": None,
            "data_storage_size_in_gbs": None,
        },
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "data_storage_size_in_tbs" in exc_info.value.payload["msg"]


def test_needs_update_true_for_compute_count_change(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database")
    instance = make_adb_module(module_obj, {"compute_count": 4.0})
    resource = FakeModel(id="ocid1.autonomousdatabase.oc1..example", compute_count=2.0)

    assert instance.needs_update(resource) is True


def test_needs_update_maps_name_param_to_display_name(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database")
    instance = make_adb_module(module_obj, {"name": "renamed-adb"})
    resource = FakeModel(
        id="ocid1.autonomousdatabase.oc1..example",
        display_name="example-adb",
    )

    assert instance.needs_update(resource) is True


def test_needs_update_ignores_whitelisted_ips_order(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database")
    instance = make_adb_module(
        module_obj,
        {"whitelisted_ips": ["10.0.0.0/24", "192.168.0.0/16"]},
    )
    resource = FakeModel(
        id="ocid1.autonomousdatabase.oc1..example",
        whitelisted_ips=["192.168.0.0/16", "10.0.0.0/24"],
    )

    assert instance.needs_update(resource) is False


@pytest.mark.parametrize(
    "params, resource_attrs, expected_field",
    [
        (
            {"db_name": "other"},
            {"db_name": "exampleadb"},
            "db_name",
        ),
        (
            {"compartment_id": "ocid1.compartment.oc1..other"},
            {"compartment_id": "ocid1.compartment.oc1..example"},
            "compartment_id",
        ),
        (
            {"db_workload": "DW"},
            {"db_workload": "OLTP"},
            "db_workload",
        ),
        (
            {"compute_model": "OCPU"},
            {"compute_model": "ECPU"},
            "compute_model",
        ),
    ],
)
def test_needs_update_rejects_immutable_field_drift(
    monkeypatch, params, resource_attrs, expected_field
):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database")
    instance = make_adb_module(module_obj, params)
    resource = FakeModel(id="ocid1.autonomousdatabase.oc1..example", **resource_attrs)

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert expected_field in exc_info.value.payload["msg"]


def test_create_resource_uses_create_autonomous_database_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database")
    create_calls = []
    response = FakeResponse(data=FakeModel(id="ocid1.autonomousdatabase.oc1..example"))

    def create_autonomous_database(create_autonomous_database_details):
        create_calls.append(create_autonomous_database_details)
        return response

    instance = make_adb_module(
        module_obj,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-adb",
            "db_name": "exampleadb",
            "admin_password": "Secret_Passw0rd",
            "compute_count": 2.0,
            "data_storage_size_in_tbs": 1,
            "wait": True,
        },
        client=types.SimpleNamespace(
            create_autonomous_database=create_autonomous_database
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: FakeModel(
            id=resource_id,
            lifecycle_state="AVAILABLE",
        ),
    )

    resource = instance.create_resource()

    assert create_calls[0].display_name == "example-adb"
    assert create_calls[0].db_name == "exampleadb"
    assert resource.lifecycle_state == "AVAILABLE"


def test_update_resource_uses_update_details_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database")
    update_calls = []
    response = FakeResponse(data=FakeModel(id="ocid1.autonomousdatabase.oc1..example"))

    def update_autonomous_database(autonomous_database_id, update_autonomous_database_details):
        update_calls.append((autonomous_database_id, update_autonomous_database_details))
        return response

    resource = FakeModel(id="ocid1.autonomousdatabase.oc1..example", compute_count=2.0)
    instance = make_adb_module(
        module_obj,
        {"compute_count": 4.0, "wait": True},
        client=types.SimpleNamespace(
            update_autonomous_database=update_autonomous_database
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: FakeModel(
            id=resource_id,
            lifecycle_state="AVAILABLE",
        ),
    )

    updated = instance.update_resource(resource)

    assert update_calls[0][0] == "ocid1.autonomousdatabase.oc1..example"
    assert update_calls[0][1].compute_count == 4.0
    assert updated.lifecycle_state == "AVAILABLE"


def test_delete_resource_calls_delete_autonomous_database(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database")
    delete_calls = []
    response = FakeResponse(data=FakeModel(id="ocid1.autonomousdatabase.oc1..example"))

    def delete_autonomous_database(autonomous_database_id):
        delete_calls.append(autonomous_database_id)
        return response

    resource = FakeModel(id="ocid1.autonomousdatabase.oc1..example")
    instance = make_adb_module(
        module_obj,
        {"wait": True},
        client=types.SimpleNamespace(
            delete_autonomous_database=delete_autonomous_database
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: None,
    )

    instance.delete_resource(resource)

    assert delete_calls == ["ocid1.autonomousdatabase.oc1..example"]


@pytest.mark.parametrize(
    "state, expected",
    [
        ("present", None),
        ("running", "AVAILABLE"),
        ("stopped", "STOPPED"),
    ],
)
def test_desired_power_state(monkeypatch, state, expected):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database")
    instance = make_adb_module(module_obj, {"state": state})

    assert instance.desired_power_state() == expected


@pytest.mark.parametrize(
    "state, current, expected",
    [
        ("running", "STOPPED", True),
        ("running", "AVAILABLE", False),
        ("stopped", "AVAILABLE", True),
        ("stopped", "STOPPED", False),
        ("present", "STOPPED", False),
        # A database mid-transition is left alone until it settles.
        ("running", "PROVISIONING", False),
    ],
)
def test_power_change_needed(monkeypatch, state, current, expected):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database")
    instance = make_adb_module(module_obj, {"state": state})
    resource = FakeModel(
        id="ocid1.autonomousdatabase.oc1..example",
        lifecycle_state=current,
    )

    assert instance.power_change_needed(resource) is expected


@pytest.mark.parametrize(
    "state, method_name, target_state",
    [
        ("running", "start_autonomous_database", "AVAILABLE"),
        ("stopped", "stop_autonomous_database", "STOPPED"),
    ],
)
def test_apply_power_state_calls_matching_api(
    monkeypatch, state, method_name, target_state
):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database")
    calls = []
    response = FakeResponse(data=FakeModel(id="ocid1.autonomousdatabase.oc1..example"))

    def power_fn(autonomous_database_id):
        calls.append(autonomous_database_id)
        return response

    instance = make_adb_module(
        module_obj,
        {"state": state, "wait": True},
        client=types.SimpleNamespace(**{method_name: power_fn}),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    captured_targets = {}

    def fake_wait(resource_id, target_states, **kwargs):
        captured_targets["target_states"] = target_states
        return FakeModel(id=resource_id, lifecycle_state=target_state)

    monkeypatch.setattr(instance, "wait_for_resource_id", fake_wait)

    resource = FakeModel(id="ocid1.autonomousdatabase.oc1..example")
    result = instance.apply_power_state(resource)

    assert calls == ["ocid1.autonomousdatabase.oc1..example"]
    assert captured_targets["target_states"] == [target_state]
    assert result.lifecycle_state == target_state


def _run_execute(instance):
    try:
        instance.execute_resource_module()
    except ExitJsonCalled as exc_info:
        return exc_info.payload
    raise AssertionError("execute_resource_module did not call exit_json")


def test_execute_check_mode_create_reports_changed(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database")
    instance = make_adb_module(
        module_obj,
        {
            "state": "present",
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-adb",
            "db_name": "exampleadb",
            "admin_password": "Secret_Passw0rd",
            "compute_count": 2.0,
            "data_storage_size_in_tbs": 1,
        },
        check_mode=True,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)

    payload = _run_execute(instance)

    assert payload == {"changed": True}


def test_execute_create_with_wait_false_skips_power_change(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database")
    # With wait=False, create_resource() has no way to confirm the database
    # reached AVAILABLE, so it is typically still PROVISIONING here.
    provisioning = FakeModel(
        id="ocid1.autonomousdatabase.oc1..example",
        lifecycle_state="PROVISIONING",
    )
    instance = make_adb_module(
        module_obj,
        {
            "state": "stopped",
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-adb",
            "db_name": "exampleadb",
            "admin_password": "Secret_Passw0rd",
            "compute_count": 2.0,
            "data_storage_size_in_tbs": 1,
            "wait": False,
        },
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)
    monkeypatch.setattr(instance, "create_resource", lambda: provisioning)
    power_calls = []
    monkeypatch.setattr(instance, "apply_power_state", power_calls.append)
    monkeypatch.setattr(
        instance, "serialize_result_resource", lambda resource: {"id": resource.id}
    )

    payload = _run_execute(instance)

    # apply_power_state() is never reached: chasing a power change on an
    # unsettled, unwaited-for resource would be unreliable, so the stop is
    # deferred to a follow-up run instead of being attempted against a
    # database that might still be PROVISIONING.
    assert power_calls == []
    assert payload["changed"] is True
    assert payload["resource"] == {"id": provisioning.id}


def test_execute_running_starts_stopped_database(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database")
    stopped = FakeModel(
        id="ocid1.autonomousdatabase.oc1..example",
        lifecycle_state="STOPPED",
    )
    started = FakeModel(
        id="ocid1.autonomousdatabase.oc1..example",
        lifecycle_state="AVAILABLE",
    )
    instance = make_adb_module(
        module_obj,
        {"state": "running", "autonomous_database_id": stopped.id},
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: stopped)
    monkeypatch.setattr(instance, "needs_update", lambda resource: False)
    power_calls = []

    def fake_apply_power_state(resource):
        power_calls.append(resource)
        return started

    monkeypatch.setattr(instance, "apply_power_state", fake_apply_power_state)
    monkeypatch.setattr(
        instance, "serialize_result_resource", lambda resource: {"id": resource.id}
    )

    payload = _run_execute(instance)

    assert power_calls == [stopped]
    assert payload["changed"] is True


def test_execute_present_available_is_idempotent(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database")
    resource = FakeModel(
        id="ocid1.autonomousdatabase.oc1..example",
        lifecycle_state="AVAILABLE",
    )
    instance = make_adb_module(
        module_obj,
        {"state": "present", "autonomous_database_id": resource.id},
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: resource)
    monkeypatch.setattr(instance, "needs_update", lambda res: False)
    monkeypatch.setattr(
        instance, "serialize_result_resource", lambda res: {"id": res.id}
    )

    payload = _run_execute(instance)

    assert payload["changed"] is False
    assert payload["resource"] == {"id": resource.id}


def test_execute_running_check_mode_reports_power_change(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database")
    stopped = FakeModel(
        id="ocid1.autonomousdatabase.oc1..example",
        lifecycle_state="STOPPED",
    )
    instance = make_adb_module(
        module_obj,
        {"state": "running", "autonomous_database_id": stopped.id},
        check_mode=True,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: stopped)
    monkeypatch.setattr(instance, "needs_update", lambda resource: False)

    payload = _run_execute(instance)

    assert payload == {"changed": True}
