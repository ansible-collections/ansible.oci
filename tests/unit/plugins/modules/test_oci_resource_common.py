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
)


RESOURCE_CASES = (
    {
        "module_name": "oci_network_vcn",
        "class_name": "OciNetworkVcnModule",
        "id_param": "vcn_id",
        "id_value": "ocid1.vcn.oc1..example",
        "missing_id": "ocid1.vcn.oc1..missing",
        "get_method": "get_vcn",
        "delete_method": "delete_vcn",
        "not_found_label": "VCN",
        "delete_required_msg": "Deleting a VCN requires vcn_id",
        "create_missing_msg": "Creating a VCN requires",
        "create_missing_params": {
            "state": "present",
            "display_name": "example-vcn",
        },
        "create_complete_params": {
            "state": "present",
            "compartment_id": "ocid1.compartment.oc1..example",
            "cidr_blocks": ["10.0.0.0/16"],
            "display_name": "example-vcn",
        },
    },
    {
        "module_name": "oci_subnet",
        "class_name": "OciSubnetModule",
        "id_param": "subnet_id",
        "id_value": "ocid1.subnet.oc1..example",
        "missing_id": "ocid1.subnet.oc1..missing",
        "get_method": "get_subnet",
        "delete_method": "delete_subnet",
        "not_found_label": "subnet",
        "delete_required_msg": "Deleting a subnet requires subnet_id",
        "create_missing_msg": "Creating a subnet requires",
        "create_missing_params": {
            "state": "present",
            "display_name": "example-subnet",
        },
        "create_complete_params": {
            "state": "present",
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "cidr_block": "10.0.1.0/24",
            "display_name": "example-subnet",
        },
    },
)


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case["module_name"])
def test_get_resource_prefers_id_lookup(monkeypatch, case):
    _, _ = install_fake_oci(monkeypatch)

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
        module_obj,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    resource = instance.get_resource()

    assert resource.id == case["id_value"]
    assert get_calls == [case["id_value"]]


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case["module_name"])
def test_get_resource_returns_none_without_id(monkeypatch, case):
    _, _ = install_fake_oci(monkeypatch)

    module_obj = load_collection_module(case["module_name"])
    instance = make_module_instance(
        module_obj,
        case["class_name"],
        {
            "display_name": "example-resource",
            "compartment_id": "ocid1.compartment.oc1..example",
        },
    )

    assert instance.get_resource() is None


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case["module_name"])
def test_run_fails_when_present_uses_missing_id(monkeypatch, case):
    _, _ = install_fake_oci(monkeypatch)

    module_obj = load_collection_module(case["module_name"])
    instance = make_module_instance(
        module_obj,
        case["class_name"],
        {
            "state": "present",
            case["id_param"]: case["missing_id"],
        },
    )
    monkeypatch.setattr(instance, "get_resource", lambda: None)

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.run()

    assert f"No {case['not_found_label']} was found for {case['id_param']}=" in exc_info.value.payload["msg"]
    assert f"Create the {case['not_found_label']} without {case['id_param']}" in exc_info.value.payload["msg"]


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case["module_name"])
def test_run_fails_when_absent_omits_id(monkeypatch, case):
    _, _ = install_fake_oci(monkeypatch)

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
        "get_resource",
        lambda: (_ for _ in ()).throw(
            AssertionError("get_resource should not be called")
        ),
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.run()

    assert case["delete_required_msg"] in exc_info.value.payload["msg"]


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case["module_name"])
def test_delete_resource_fails_cleanly_when_dependency_exists(monkeypatch, case):
    _, ServiceError = install_fake_oci(monkeypatch)

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
        module_obj,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )
    monkeypatch.setattr(
        __import__(instance.delete_resource_and_wait.__module__, fromlist=["call_with_retry"]),
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.delete_resource(resource)

    assert "dependent resources" in exc_info.value.payload["msg"]


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case["module_name"])
def test_run_check_mode_create_fails_when_required_fields_missing(monkeypatch, case):
    _, _ = install_fake_oci(monkeypatch)

    module_obj = load_collection_module(case["module_name"])
    instance = make_module_instance(
        module_obj,
        case["class_name"],
        case["create_missing_params"],
        check_mode=True,
    )
    monkeypatch.setattr(instance, "get_resource", lambda: None)

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.run()

    assert case["create_missing_msg"] in exc_info.value.payload["msg"]


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case["module_name"])
def test_run_check_mode_create_reports_changed_without_create(monkeypatch, case):
    _, _ = install_fake_oci(monkeypatch)

    module_obj = load_collection_module(case["module_name"])
    instance = make_module_instance(
        module_obj,
        case["class_name"],
        case["create_complete_params"],
        check_mode=True,
    )
    monkeypatch.setattr(instance, "get_resource", lambda: None)
    monkeypatch.setattr(
        instance,
        "create_resource",
        lambda: (_ for _ in ()).throw(
            AssertionError("create_resource should not be called")
        ),
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.run()

    assert exc_info.value.payload == {"changed": True}


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case["module_name"])
def test_run_check_mode_update_reports_changed_when_tags_differ(monkeypatch, case):
    _, _ = install_fake_oci(monkeypatch)

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
    monkeypatch.setattr(instance, "get_resource", lambda: resource)
    monkeypatch.setattr(
        instance,
        "update_resource",
        lambda resource: (_ for _ in ()).throw(
            AssertionError("update_resource should not be called")
        ),
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.run()

    assert exc_info.value.payload == {"changed": True}


@pytest.mark.parametrize("case", RESOURCE_CASES, ids=lambda case: case["module_name"])
def test_run_check_mode_delete_reports_changed_without_delete(monkeypatch, case):
    _, _ = install_fake_oci(monkeypatch)

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
    monkeypatch.setattr(instance, "get_resource", lambda: resource)
    monkeypatch.setattr(
        instance,
        "delete_resource",
        lambda resource: (_ for _ in ()).throw(
            AssertionError("delete_resource should not be called")
        ),
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.run()

    assert exc_info.value.payload == {"changed": True}
