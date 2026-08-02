from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from conftest import (
    ExitJsonCalled,
    FailJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


RESOURCE_CASES = (
    {
        "module_name": "oci_network_vcn",
        "class_name": "OciNetworkVcnModule",
        "id_param": "vcn_id",
        "id_value": "ocid1.vcn.oc1..example",
        "missing_id": "ocid1.vcn.oc1..missing",
        "get_method": "get_vcn",
        "list_method": "list_vcns",
        "delete_method": "delete_vcn",
        "not_found_label": "VCN",
        "delete_required_msg": "Deleting a VCN requires either vcn_id or name (with compartment_id)",
        "create_missing_msg": "Creating a VCN requires",
        "name_lookup_params": {
            "name": "example-vcn",
            "compartment_id": "ocid1.compartment.oc1..example",
        },
        "expected_name_lookup_kwargs": {
            "compartment_id": "ocid1.compartment.oc1..example",
        },
        "create_missing_params": {
            "state": "present",
            "name": "example-vcn",
        },
        "create_complete_params": {
            "state": "present",
            "compartment_id": "ocid1.compartment.oc1..example",
            "cidr_blocks": ["10.0.0.0/16"],
            "name": "example-vcn",
        },
    },
    {
        "module_name": "oci_subnet",
        "class_name": "OciSubnetModule",
        "id_param": "subnet_id",
        "id_value": "ocid1.subnet.oc1..example",
        "missing_id": "ocid1.subnet.oc1..missing",
        "get_method": "get_subnet",
        "list_method": "list_subnets",
        "delete_method": "delete_subnet",
        "not_found_label": "subnet",
        "delete_required_msg": "Deleting a subnet requires either subnet_id or name (with compartment_id, vcn_id)",
        "create_missing_msg": "Creating a subnet requires",
        "name_lookup_params": {
            "name": "example-subnet",
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
        },
        "expected_name_lookup_kwargs": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
        },
        "create_missing_params": {
            "state": "present",
            "name": "example-subnet",
        },
        "create_complete_params": {
            "state": "present",
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "cidr_block": "10.0.1.0/24",
            "name": "example-subnet",
        },
    },
    {
        "module_name": "oci_security_list",
        "class_name": "OciSecurityListModule",
        "id_param": "security_list_id",
        "id_value": "ocid1.securitylist.oc1..example",
        "missing_id": "ocid1.securitylist.oc1..missing",
        "get_method": "get_security_list",
        "list_method": "list_security_lists",
        "delete_method": "delete_security_list",
        "not_found_label": "security list",
        "delete_required_msg": "Deleting a security list requires either security_list_id or name (with compartment_id, vcn_id)",
        "create_missing_msg": "Creating a security list requires",
        "name_lookup_params": {
            "name": "example-security-list",
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
        },
        "expected_name_lookup_kwargs": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
        },
        "create_missing_params": {
            "state": "present",
            "name": "example-security-list",
        },
        "create_complete_params": {
            "state": "present",
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-security-list",
        },
    },
)


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case["module_name"])
def test_get_resource_prefers_id_lookup(monkeypatch, case):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module(case["module_name"])
    get_calls = []

    def get_resource(**kwargs):
        resource_id = kwargs[case["id_param"]]
        get_calls.append(resource_id)
        return FakeResponse(data=FakeModel(id=resource_id))

    instance = make_module_instance(
        module_obj,
        case["class_name"],
        {case["id_param"]: case["id_value"]},
        client=types.SimpleNamespace(**{case["get_method"]: get_resource}),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    resource = instance.resolve_target_resource()

    assert resource.id == case["id_value"]
    assert get_calls == [case["id_value"]]


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case["module_name"])
def test_get_resource_uses_unique_name_lookup_without_id(monkeypatch, case):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module(case["module_name"])
    paginate_calls = []
    instance = make_module_instance(
        module_obj,
        case["class_name"],
        case["name_lookup_params"],
        client=types.SimpleNamespace(**{case["list_method"]: "list_resources_method"}),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: paginate_calls.append((list_fn, kwargs))
        or [
            FakeModel(
                id=case["id_value"],
                display_name=case["name_lookup_params"]["name"],
            )
        ],
    )

    resource = instance.resolve_target_resource()

    assert resource.id == case["id_value"]
    assert paginate_calls == [("list_resources_method", case["expected_name_lookup_kwargs"])]


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case["module_name"])
def test_run_fails_when_present_uses_missing_id(monkeypatch, case):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module(case["module_name"])
    instance = make_module_instance(
        module_obj,
        case["class_name"],
        {
            "state": "present",
            case["id_param"]: case["missing_id"],
        },
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert f"No {case['not_found_label']} was found for {case['id_param']}=" in exc_info.value.payload["msg"]
    assert f"Create the {case['not_found_label']} without {case['id_param']}" in exc_info.value.payload["msg"]


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case["module_name"])
def test_run_check_mode_reports_update_when_unique_name_match_has_tag_drift(monkeypatch, case):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module(case["module_name"])
    resource = FakeModel(
        id=case["id_value"],
        lifecycle_state="AVAILABLE",
        freeform_tags={"env": "dev"},
        display_name=case["name_lookup_params"]["name"],
        **{
            key: value
            for key, value in case["expected_name_lookup_kwargs"].items()
            if key != "display_name"
        },
    )
    params = dict(case["name_lookup_params"])
    params.update(
        {
            "state": "present",
            "freeform_tags": {"env": "prod"},
            "allow_duplicate_name": False,
        }
    )
    instance = make_module_instance(
        module_obj,
        case["class_name"],
        params,
        check_mode=True,
        client=types.SimpleNamespace(**{case["list_method"]: "list_resources_method"}),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: [resource],
    )
    monkeypatch.setattr(
        instance,
        "create_resource",
        raising(AssertionError("create_resource should not be called")),
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload == {"changed": True}


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case["module_name"])
def test_run_check_mode_reports_update_when_shared_planner_detects_field_drift(monkeypatch, case):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module(case["module_name"])
    resource = FakeModel(
        id=case["id_value"],
        lifecycle_state="AVAILABLE",
        display_name=case["name_lookup_params"]["name"],
    )
    instance = make_module_instance(
        module_obj,
        case["class_name"],
        {
            "state": "present",
            case["id_param"]: case["id_value"],
            "name": f"{case['name_lookup_params']['name']}-updated",
        },
        check_mode=True,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: resource)
    monkeypatch.setattr(
        instance,
        "update_resource",
        raising(AssertionError("update_resource should not be called in check mode")),
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload == {"changed": True}


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case["module_name"])
def test_run_creates_duplicate_when_unique_name_match_and_flag_enabled(monkeypatch, case):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module(case["module_name"])
    params = dict(case["create_complete_params"])
    params["allow_duplicate_name"] = True
    instance = make_module_instance(
        module_obj,
        case["class_name"],
        params,
        client=types.SimpleNamespace(**{case["list_method"]: "list_resources_method"}),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: [FakeModel(id=case["id_value"])],
    )
    monkeypatch.setattr(
        instance,
        "create_resource",
        lambda: FakeModel(id="created-resource"),
    )
    monkeypatch.setattr(
        instance,
        "update_resource",
        raising(AssertionError("update_resource should not be called")),
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload["changed"] is True
    assert exc_info.value.payload["resource"]["id"] == "created-resource"


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case["module_name"])
def test_run_creates_duplicate_when_multiple_name_matches_and_flag_enabled(monkeypatch, case):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module(case["module_name"])
    params = dict(case["create_complete_params"])
    params["allow_duplicate_name"] = True
    instance = make_module_instance(
        module_obj,
        case["class_name"],
        params,
        client=types.SimpleNamespace(**{case["list_method"]: "list_resources_method"}),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: [
            FakeModel(id=f"{case['id_value']}.one", display_name=case["name_lookup_params"]["name"]),
            FakeModel(id=f"{case['id_value']}.two", display_name=case["name_lookup_params"]["name"]),
        ],
    )
    monkeypatch.setattr(
        instance,
        "create_resource",
        lambda: FakeModel(id="created-resource"),
    )
    monkeypatch.setattr(
        instance,
        "update_resource",
        raising(AssertionError("update_resource should not be called")),
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload["changed"] is True
    assert exc_info.value.payload["resource"]["id"] == "created-resource"


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case["module_name"])
def test_run_fails_when_name_lookup_matches_multiple_resources(monkeypatch, case):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module(case["module_name"])
    params = dict(case["create_complete_params"])
    instance = make_module_instance(
        module_obj,
        case["class_name"],
        params,
        client=types.SimpleNamespace(**{case["list_method"]: "list_resources_method"}),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: [
            FakeModel(id=f"{case['id_value']}.one", display_name=case["name_lookup_params"]["name"]),
            FakeModel(id=f"{case['id_value']}.two", display_name=case["name_lookup_params"]["name"]),
        ],
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert f"Provide {case['id_param']} to distinguish" in exc_info.value.payload["msg"]


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case["module_name"])
def test_run_absent_reports_no_change_when_name_lookup_finds_no_resources(monkeypatch, case):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module(case["module_name"])
    params = dict(case["name_lookup_params"])
    params["state"] = "absent"
    instance = make_module_instance(
        module_obj,
        case["class_name"],
        params,
        client=types.SimpleNamespace(**{case["list_method"]: "list_resources_method"}),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: [],
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload == {"changed": False}


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case["module_name"])
def test_run_absent_deletes_unique_name_match_without_explicit_id(monkeypatch, case):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module(case["module_name"])
    params = dict(case["name_lookup_params"])
    params["state"] = "absent"
    instance = make_module_instance(
        module_obj,
        case["class_name"],
        params,
        client=types.SimpleNamespace(**{case["list_method"]: "list_resources_method"}),
    )
    resource = FakeModel(
        id=case["id_value"],
        lifecycle_state="AVAILABLE",
        display_name=case["name_lookup_params"]["name"],
    )
    delete_calls = []
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: [resource],
    )
    monkeypatch.setattr(
        instance,
        "delete_resource",
        delete_calls.append,
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload == {"changed": True}
    assert delete_calls == [resource]


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case["module_name"])
def test_run_fails_when_absent_omits_id(monkeypatch, case):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module(case["module_name"])
    instance = make_module_instance(
        module_obj,
        case["class_name"],
        {
            "state": "absent",
        },
    )
    monkeypatch.setattr(
        instance,
        "resolve_target_resource",
        raising(AssertionError("resolve_target_resource should not be called")),
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert case["delete_required_msg"] in exc_info.value.payload["msg"]


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case["module_name"])
def test_delete_resource_fails_cleanly_when_dependency_exists(monkeypatch, case):
    _oci_module, ServiceError = install_fake_oci(monkeypatch)

    module_obj = load_collection_module(case["module_name"])
    resource = FakeModel(id=case["id_value"])

    def delete_resource(**kwargs):
        raise ServiceError(409, "dependency exists")

    instance = make_module_instance(
        module_obj,
        case["class_name"],
        {"wait": True},
        client=types.SimpleNamespace(**{case["delete_method"]: delete_resource}),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.delete_resource(resource)

    assert "dependent resources" in exc_info.value.payload["msg"]


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case["module_name"])
def test_run_check_mode_create_fails_when_required_fields_missing(monkeypatch, case):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module(case["module_name"])
    instance = make_module_instance(
        module_obj,
        case["class_name"],
        case["create_missing_params"],
        check_mode=True,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert case["create_missing_msg"] in exc_info.value.payload["msg"]


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case["module_name"])
def test_run_check_mode_create_reports_changed_without_create(monkeypatch, case):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module(case["module_name"])
    instance = make_module_instance(
        module_obj,
        case["class_name"],
        case["create_complete_params"],
        check_mode=True,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)
    monkeypatch.setattr(
        instance,
        "create_resource",
        raising(AssertionError("create_resource should not be called")),
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload == {"changed": True}


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case["module_name"])
def test_run_check_mode_update_reports_changed_when_tags_differ(monkeypatch, case):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module(case["module_name"])
    resource = FakeModel(
        id=case["id_value"],
        display_name="example-resource",
        lifecycle_state="AVAILABLE",
        freeform_tags={"env": "dev"},
    )
    instance = make_module_instance(
        module_obj,
        case["class_name"],
        {
            "state": "present",
            "display_name": "example-resource",
            "freeform_tags": {"env": "prod"},
        },
        check_mode=True,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: resource)
    monkeypatch.setattr(
        instance,
        "update_resource",
        raising(AssertionError("update_resource should not be called")),
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload == {"changed": True}


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case["module_name"])
def test_run_check_mode_delete_reports_changed_without_delete(monkeypatch, case):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module(case["module_name"])
    resource = FakeModel(
        id=case["id_value"],
        lifecycle_state="AVAILABLE",
    )
    instance = make_module_instance(
        module_obj,
        case["class_name"],
        {
            "state": "absent",
            case["id_param"]: case["id_value"],
        },
        check_mode=True,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: resource)
    monkeypatch.setattr(
        instance,
        "delete_resource",
        raising(AssertionError("delete_resource should not be called")),
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload == {"changed": True}
