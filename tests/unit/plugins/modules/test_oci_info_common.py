from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from conftest import (
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


INFO_CASES = (
    {
        "module_name": "oci_network_vcn_info",
        "class_name": "OciNetworkVcnInfoModule",
        "results_key": "vcns",
        "id_param": "vcn_id",
        "id_value": "ocid1.vcn.oc1..example",
        "missing_id": "ocid1.vcn.oc1..missing",
        "get_method": "get_vcn",
        "list_method": "list_vcns",
        "list_params": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-vcn",
            "lifecycle_state": "AVAILABLE",
        },
        "expected_list_kwargs": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "lifecycle_state": "AVAILABLE",
        },
        "run_resource": FakeModel(
            id="ocid1.vcn.oc1..example",
            display_name="example-vcn",
            lifecycle_state="AVAILABLE",
        ),
        "expected_run_payload": {
            "id": "ocid1.vcn.oc1..example",
            "name": "example-vcn",
            "lifecycle_state": "AVAILABLE",
        },
    },
    {
        "module_name": "oci_subnet_info",
        "class_name": "OciSubnetInfoModule",
        "results_key": "subnets",
        "id_param": "subnet_id",
        "id_value": "ocid1.subnet.oc1..example",
        "missing_id": "ocid1.subnet.oc1..missing",
        "get_method": "get_subnet",
        "list_method": "list_subnets",
        "list_params": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-subnet",
            "lifecycle_state": "AVAILABLE",
        },
        "expected_list_kwargs": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "lifecycle_state": "AVAILABLE",
        },
        "run_resource": FakeModel(
            id="ocid1.subnet.oc1..example",
            display_name="example-subnet",
            lifecycle_state="AVAILABLE",
            vcn_id="ocid1.vcn.oc1..example",
        ),
        "expected_run_payload": {
            "id": "ocid1.subnet.oc1..example",
            "name": "example-subnet",
            "lifecycle_state": "AVAILABLE",
            "vcn_id": "ocid1.vcn.oc1..example",
        },
    },
    {
        "module_name": "oci_service_gateway_info",
        "class_name": "OciServiceGatewayInfoModule",
        "results_key": "service_gateways",
        "id_param": "service_gateway_id",
        "id_value": "ocid1.servicegateway.oc1..example",
        "missing_id": "ocid1.servicegateway.oc1..missing",
        "get_method": "get_service_gateway",
        "list_method": "list_service_gateways",
        "list_params": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-service-gateway",
            "lifecycle_state": "AVAILABLE",
        },
        "expected_list_kwargs": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "lifecycle_state": "AVAILABLE",
        },
        "run_resource": FakeModel(
            id="ocid1.servicegateway.oc1..example",
            display_name="example-service-gateway",
            lifecycle_state="AVAILABLE",
            vcn_id="ocid1.vcn.oc1..example",
        ),
        "expected_run_payload": {
            "id": "ocid1.servicegateway.oc1..example",
            "name": "example-service-gateway",
            "lifecycle_state": "AVAILABLE",
            "vcn_id": "ocid1.vcn.oc1..example",
        },
    },
)


@pytest.mark.parametrize("case", INFO_CASES, ids=lambda case: case["module_name"])
def test_list_resources_uses_list_filters(monkeypatch, case):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module(case["module_name"])
    paginate_calls = []
    instance = make_module_instance(
        info_module,
        case["class_name"],
        case["list_params"],
        client=types.SimpleNamespace(**{case["list_method"]: "list_method"}),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: paginate_calls.append((list_fn, kwargs)) or [],
    )

    resources = instance.fetch_resources()

    assert resources == []
    assert paginate_calls == [("list_method", case["expected_list_kwargs"])]


@pytest.mark.parametrize("case", INFO_CASES, ids=lambda case: case["module_name"])
def test_list_resources_prefers_id_lookup(monkeypatch, case):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module(case["module_name"])

    def get_resource(**kwargs):
        return FakeResponse(
            data=FakeModel(id=kwargs[case["id_param"]], display_name="example")
        )

    instance = make_module_instance(
        info_module,
        case["class_name"],
        {case["id_param"]: case["id_value"]},
        client=types.SimpleNamespace(
            **{case["get_method"]: get_resource}
        ),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        raising(AssertionError("list_all_resources should not be called")),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    resources = instance.fetch_resources()

    assert len(resources) == 1
    assert resources[0].id == case["id_value"]


@pytest.mark.parametrize("case", INFO_CASES, ids=lambda case: case["module_name"])
def test_list_resources_returns_empty_list_on_404(monkeypatch, case):
    _oci_module, ServiceError = install_fake_oci(monkeypatch)

    info_module = load_collection_module(case["module_name"])

    def get_missing_resource(**kwargs):
        raise ServiceError(404, "missing")

    instance = make_module_instance(
        info_module,
        case["class_name"],
        {case["id_param"]: case["missing_id"]},
        client=types.SimpleNamespace(
            **{case["get_method"]: get_missing_resource}
        ),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    assert instance.fetch_resources() == []


@pytest.mark.parametrize("case", INFO_CASES, ids=lambda case: case["module_name"])
def test_run_returns_results_key(monkeypatch, case):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module(case["module_name"])
    instance = make_module_instance(
        info_module,
        case["class_name"],
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": case["run_resource"].display_name,
        },
    )
    monkeypatch.setattr(instance, "fetch_resources", lambda: [case["run_resource"]])

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()

    assert exc_info.value.payload == {
        "changed": False,
        case["results_key"]: [case["expected_run_payload"]],
    }
