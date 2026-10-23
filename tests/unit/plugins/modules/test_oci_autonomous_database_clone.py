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


CLONE_ID = "ocid1.autonomousdatabase.oc1..clone"
SOURCE_ID = "ocid1.autonomousdatabase.oc1..source"
CLONE_MODEL_NAMES = (
    "CreateAutonomousDatabaseCloneDetails",
    "CreateRefreshableAutonomousDatabaseCloneDetails",
    "UpdateAutonomousDatabaseDetails",
)


def install_fake_oci(monkeypatch):
    oci_module, service_error = shared_install_fake_oci(monkeypatch)
    # Distinct subclasses so tests can tell which create-details model was built.
    oci_module.database = types.SimpleNamespace(
        DatabaseClient=type("FakeDatabaseClient", (), {}),
        models=types.SimpleNamespace(
            **{name: type(name, (FakeModel,), {}) for name in CLONE_MODEL_NAMES}
        ),
    )
    return oci_module, service_error


def make_clone_module(module_obj, params, client=None, check_mode=False):
    return make_module_instance(
        module_obj,
        "OciAutonomousDatabaseCloneModule",
        params,
        client=client,
        check_mode=check_mode,
    )


def standard_create_params(**overrides):
    params = {
        "state": "present",
        "compartment_id": "ocid1.compartment.oc1..example",
        "name": "example-clone",
        "source_id": SOURCE_ID,
        "db_name": "exampleclone",
        "admin_password": "Secret_Passw0rd",
        "clone_type": "METADATA",
        "refreshable": False,
    }
    params.update(overrides)
    return params


def run_execute(instance):
    try:
        instance.execute_resource_module()
    except ExitJsonCalled as exc_info:
        return exc_info.payload
    raise AssertionError("execute_resource_module did not call exit_json")


def test_main_wires_argument_spec_and_normalizes_enums(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database_clone")
    captured = {}
    params = {
        "clone_type": "metadata",
        "compute_model": "ecpu",
        "license_model": "license_included",
        "refreshable_mode": "manual",
        "open_mode": "read_only",
        "freeform_tags": {"clone_type": "metadata"},
        "auth_type": "api_key",
    }

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule(params)

    class FakeCloneModule:
        def __init__(self, module):
            captured["module"] = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciAutonomousDatabaseCloneModule", FakeCloneModule)

    module_obj.main()

    spec = captured["argument_spec"]
    assert captured["run_called"] is True
    assert captured["supports_check_mode"] is True
    assert captured["mutually_exclusive"] == [
        ["data_storage_size_in_tbs", "data_storage_size_in_gbs"]
    ]
    assert spec["state"] == {
        "type": "str",
        "choices": ["present", "absent"],
        "default": "present",
    }
    assert spec["admin_password"] == {"type": "str", "no_log": True}
    assert spec["clone_type"] == {"type": "str", "choices": ["full", "metadata"]}
    assert spec["refreshable"] == {"type": "bool", "default": False}
    assert "display_name" not in spec

    normalized = captured["module"].params
    assert normalized["clone_type"] == "METADATA"
    assert normalized["compute_model"] == "ECPU"
    assert normalized["license_model"] == "LICENSE_INCLUDED"
    assert normalized["refreshable_mode"] == "MANUAL"
    assert normalized["open_mode"] == "READ_ONLY"
    # Tag values are never treated as enums.
    assert normalized["freeform_tags"] == {"clone_type": "metadata"}
    assert normalized["auth_type"] == "api_key"


def test_build_create_clone_details_standard(monkeypatch):
    oci_module = install_fake_oci(monkeypatch)[0]

    module_obj = load_collection_module("oci_autonomous_database_clone")
    details = module_obj.build_create_clone_details(
        standard_create_params(
            compute_model="ECPU",
            compute_count=2.0,
            data_storage_size_in_gbs=None,
            freeform_tags={"env": "dev"},
        )
    )

    assert isinstance(details, oci_module.database.models.CreateAutonomousDatabaseCloneDetails)
    assert details.display_name == "example-clone"
    assert details.source_id == SOURCE_ID
    assert details.clone_type == "METADATA"
    assert details.admin_password == "Secret_Passw0rd"
    assert details.compute_count == 2.0
    assert details.freeform_tags == {"env": "dev"}
    assert not hasattr(details, "name")
    assert not hasattr(details, "data_storage_size_in_gbs")


def test_build_create_clone_details_refreshable(monkeypatch):
    oci_module = install_fake_oci(monkeypatch)[0]

    module_obj = load_collection_module("oci_autonomous_database_clone")
    details = module_obj.build_create_clone_details(
        standard_create_params(
            refreshable=True,
            admin_password=None,
            clone_type=None,
            refreshable_mode="MANUAL",
            open_mode="READ_ONLY",
            auto_refresh_point_lag_in_seconds=0,
        )
    )

    assert isinstance(
        details,
        oci_module.database.models.CreateRefreshableAutonomousDatabaseCloneDetails,
    )
    assert details.source_id == SOURCE_ID
    assert details.refreshable_mode == "MANUAL"
    assert details.open_mode == "READ_ONLY"
    # A zero lag is a real value and must be kept.
    assert details.auto_refresh_point_lag_in_seconds == 0
    assert not hasattr(details, "admin_password")
    assert not hasattr(details, "refreshable")


def test_validate_create_request_requires_source_id(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database_clone")
    instance = make_clone_module(module_obj, standard_create_params(source_id=None))

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "source_id" in exc_info.value.payload["msg"]


@pytest.mark.parametrize("missing_field", ["clone_type", "admin_password"])
def test_validate_create_request_standard_clone_requirements(monkeypatch, missing_field):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database_clone")
    instance = make_clone_module(
        module_obj, standard_create_params(**{missing_field: None})
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert missing_field in exc_info.value.payload["msg"]


def test_validate_create_request_rejects_refreshable_options_for_standard_clone(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database_clone")
    instance = make_clone_module(
        module_obj, standard_create_params(refreshable_mode="MANUAL")
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "refreshable_mode" in exc_info.value.payload["msg"]
    assert "refreshable=true" in exc_info.value.payload["msg"]


def test_validate_create_request_refreshable_needs_no_password(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database_clone")
    instance = make_clone_module(
        module_obj,
        standard_create_params(
            refreshable=True,
            admin_password=None,
            clone_type=None,
            refreshable_mode="AUTOMATIC",
        ),
    )

    instance.validate_create_request()


def test_resolve_target_resource_returns_matching_clone(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database_clone")
    clone = FakeModel(id=CLONE_ID, source_id=SOURCE_ID, lifecycle_state="AVAILABLE")
    instance = make_clone_module(
        module_obj, {"autonomous_database_id": CLONE_ID, "source_id": SOURCE_ID}
    )
    monkeypatch.setattr(
        instance, "get_resource_response", lambda resource_id: FakeResponse(data=clone)
    )

    assert instance.resolve_target_resource() is clone


def test_resolve_target_resource_returns_none_when_missing(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database_clone")
    instance = make_clone_module(
        module_obj,
        {"name": "example-clone", "compartment_id": "ocid1.compartment.oc1..example"},
    )
    monkeypatch.setattr(instance, "resolve_resource_by_name", lambda: None)

    assert instance.resolve_target_resource() is None


def test_resolve_target_resource_rejects_non_clone(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database_clone")
    database = FakeModel(id=CLONE_ID, source_id=None, lifecycle_state="AVAILABLE")
    instance = make_clone_module(module_obj, {"autonomous_database_id": CLONE_ID})
    monkeypatch.setattr(
        instance, "get_resource_response", lambda resource_id: FakeResponse(data=database)
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.resolve_target_resource()

    assert "is not a clone" in exc_info.value.payload["msg"]


def test_resolve_target_resource_rejects_different_source(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database_clone")
    clone = FakeModel(
        id=CLONE_ID,
        source_id="ocid1.autonomousdatabase.oc1..other",
        lifecycle_state="AVAILABLE",
    )
    instance = make_clone_module(
        module_obj, {"autonomous_database_id": CLONE_ID, "source_id": SOURCE_ID}
    )
    monkeypatch.setattr(
        instance, "get_resource_response", lambda resource_id: FakeResponse(data=clone)
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.resolve_target_resource()

    assert "ocid1.autonomousdatabase.oc1..other" in exc_info.value.payload["msg"]
    assert SOURCE_ID in exc_info.value.payload["msg"]


def test_needs_update_ignores_create_only_options(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database_clone")
    instance = make_clone_module(
        module_obj, standard_create_params(compute_count=4.0, clone_type="FULL")
    )
    resource = FakeModel(
        id=CLONE_ID,
        display_name="example-clone",
        compute_count=2.0,
        clone_type="METADATA",
    )

    assert instance.needs_update(resource) is False


@pytest.mark.parametrize(
    "params, resource_attrs",
    [
        ({"name": "renamed-clone"}, {"display_name": "example-clone"}),
        ({"freeform_tags": {"phase": "update"}}, {"freeform_tags": {"phase": "create"}}),
    ],
)
def test_needs_update_detects_name_and_tag_drift(monkeypatch, params, resource_attrs):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database_clone")
    instance = make_clone_module(module_obj, params)
    resource = FakeModel(id=CLONE_ID, **resource_attrs)

    assert instance.needs_update(resource) is True


def test_create_resource_uses_create_autonomous_database_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database_clone")
    create_calls = []

    def create_autonomous_database(create_autonomous_database_details):
        create_calls.append(create_autonomous_database_details)
        return FakeResponse(data=FakeModel(id=CLONE_ID, lifecycle_state="PROVISIONING"))

    instance = make_clone_module(
        module_obj,
        standard_create_params(wait=True),
        client=types.SimpleNamespace(create_autonomous_database=create_autonomous_database),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    wait_calls = []

    def fake_wait(resource_id, target_states, **kwargs):
        wait_calls.append((resource_id, target_states))
        return FakeModel(id=resource_id, lifecycle_state="AVAILABLE")

    monkeypatch.setattr(instance, "wait_for_resource_id", fake_wait)

    resource = instance.create_resource()

    assert create_calls[0].source_id == SOURCE_ID
    assert create_calls[0].clone_type == "METADATA"
    assert wait_calls == [(CLONE_ID, ["AVAILABLE"])]
    assert resource.lifecycle_state == "AVAILABLE"


def test_update_resource_renames_and_waits_for_settled_state(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database_clone")
    update_calls = []

    def update_autonomous_database(autonomous_database_id, update_autonomous_database_details):
        update_calls.append((autonomous_database_id, update_autonomous_database_details))
        return FakeResponse(data=FakeModel(id=autonomous_database_id))

    instance = make_clone_module(
        module_obj,
        {"name": "renamed-clone", "wait": True},
        client=types.SimpleNamespace(update_autonomous_database=update_autonomous_database),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    wait_calls = []

    def fake_wait(resource_id, target_states, **kwargs):
        wait_calls.append(target_states)
        return FakeModel(id=resource_id, display_name="renamed-clone")

    monkeypatch.setattr(instance, "wait_for_resource_id", fake_wait)

    updated = instance.update_resource(FakeModel(id=CLONE_ID, display_name="example-clone"))

    assert update_calls[0][0] == CLONE_ID
    assert update_calls[0][1].display_name == "renamed-clone"
    assert wait_calls == [["AVAILABLE", "STOPPED"]]
    assert updated.display_name == "renamed-clone"


def test_delete_resource_calls_delete_autonomous_database(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database_clone")
    delete_calls = []

    def delete_autonomous_database(autonomous_database_id):
        delete_calls.append(autonomous_database_id)
        return FakeResponse(data=None)

    instance = make_clone_module(
        module_obj,
        {"wait": True},
        client=types.SimpleNamespace(delete_autonomous_database=delete_autonomous_database),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance, "wait_for_resource_id", lambda resource_id, target_states, **kwargs: None
    )

    instance.delete_resource(FakeModel(id=CLONE_ID))

    assert delete_calls == [CLONE_ID]


def test_execute_check_mode_create_reports_changed_without_creating(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database_clone")
    instance = make_clone_module(module_obj, standard_create_params(), check_mode=True)
    monkeypatch.setattr(instance, "resolve_resource_by_name", lambda: None)
    monkeypatch.setattr(
        instance, "create_resource", lambda: pytest.fail("check mode must not create")
    )

    assert run_execute(instance) == {"changed": True}


def test_execute_present_existing_clone_is_idempotent(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database_clone")
    clone = FakeModel(
        id=CLONE_ID,
        display_name="example-clone",
        source_id=SOURCE_ID,
        lifecycle_state="AVAILABLE",
    )
    instance = make_clone_module(module_obj, standard_create_params())
    monkeypatch.setattr(instance, "resolve_resource_by_name", lambda: clone)
    monkeypatch.setattr(
        instance, "update_resource", lambda resource: pytest.fail("no update expected")
    )

    payload = run_execute(instance)

    assert payload["changed"] is False
    assert payload["resource"]["id"] == CLONE_ID
    assert payload["resource"]["name"] == "example-clone"


def test_execute_check_mode_update_reports_changed_without_updating(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database_clone")
    clone = FakeModel(
        id=CLONE_ID,
        display_name="example-clone",
        source_id=SOURCE_ID,
        lifecycle_state="AVAILABLE",
        freeform_tags={"phase": "create"},
    )
    instance = make_clone_module(
        module_obj,
        {"autonomous_database_id": CLONE_ID, "freeform_tags": {"phase": "update"}},
        check_mode=True,
    )
    monkeypatch.setattr(
        instance, "get_resource_response", lambda resource_id: FakeResponse(data=clone)
    )
    monkeypatch.setattr(
        instance, "update_resource", lambda resource: pytest.fail("check mode must not update")
    )

    assert run_execute(instance) == {"changed": True}


@pytest.mark.parametrize("check_mode", [True, False])
def test_execute_absent_refuses_to_delete_non_clone(monkeypatch, check_mode):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database_clone")
    database = FakeModel(id=CLONE_ID, source_id=None, lifecycle_state="AVAILABLE")
    instance = make_clone_module(
        module_obj,
        {"state": "absent", "autonomous_database_id": CLONE_ID},
        check_mode=check_mode,
    )
    monkeypatch.setattr(
        instance, "get_resource_response", lambda resource_id: FakeResponse(data=database)
    )
    monkeypatch.setattr(
        instance, "delete_resource", lambda resource: pytest.fail("must not delete")
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert "is not a clone" in exc_info.value.payload["msg"]


def test_execute_absent_terminated_clone_is_unchanged(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_autonomous_database_clone")
    terminated = FakeModel(id=CLONE_ID, source_id=SOURCE_ID, lifecycle_state="TERMINATED")
    instance = make_clone_module(
        module_obj, {"state": "absent", "autonomous_database_id": CLONE_ID}
    )
    monkeypatch.setattr(
        instance, "get_resource_response", lambda resource_id: FakeResponse(data=terminated)
    )

    assert run_execute(instance) == {"changed": False}
