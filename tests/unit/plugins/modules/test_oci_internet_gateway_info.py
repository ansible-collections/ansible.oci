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


def make_internet_gateway_info_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciInternetGatewayInfoModule",
        params,
        client=client,
    )


def test_main_requires_compartment_id_or_internet_gateway_id(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_internet_gateway_info")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        captured["required_one_of"] = kwargs["required_one_of"]
        return types.SimpleNamespace()

    class FakeInternetGatewayInfoModule:
        def __init__(self, module):
            self.module = module

        def execute_info_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(
        module_obj, "OciInternetGatewayInfoModule", FakeInternetGatewayInfoModule
    )

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["required_one_of"] == [["compartment_id", "internet_gateway_id"]]
    assert captured["argument_spec"]["internet_gateway_id"] == {"type": "str"}
    assert captured["argument_spec"]["vcn_id"] == {"type": "str"}


def test_resource_id_kwarg_is_ig_id_not_internet_gateway_id(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_internet_gateway_info")

    assert info_module.OciInternetGatewayInfoModule.resource_id_param == (
        "internet_gateway_id"
    )
    assert info_module.OciInternetGatewayInfoModule.resource_id_kwarg == "ig_id"


def test_fetch_resources_prefers_id_lookup_using_ig_id_kwarg(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_internet_gateway_info")
    get_calls = []

    def get_internet_gateway(**kwargs):
        get_calls.append(kwargs)
        return FakeResponse(
            data=FakeModel(id=kwargs["ig_id"], display_name="example-ig")
        )

    instance = make_internet_gateway_info_module(
        info_module,
        {"internet_gateway_id": "ocid1.internetgateway.oc1..example"},
        client=types.SimpleNamespace(get_internet_gateway=get_internet_gateway),
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

    assert get_calls == [{"ig_id": "ocid1.internetgateway.oc1..example"}]
    assert len(resources) == 1
    assert resources[0].id == "ocid1.internetgateway.oc1..example"


def test_fetch_resources_returns_empty_list_on_404(monkeypatch):
    _oci_module, ServiceError = install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_internet_gateway_info")

    def get_missing_internet_gateway(**kwargs):
        raise ServiceError(404, "missing")

    instance = make_internet_gateway_info_module(
        info_module,
        {"internet_gateway_id": "ocid1.internetgateway.oc1..missing"},
        client=types.SimpleNamespace(
            get_internet_gateway=get_missing_internet_gateway
        ),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    assert instance.fetch_resources() == []


def test_fetch_resources_lists_with_filters(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_internet_gateway_info")
    paginate_calls = []
    instance = make_internet_gateway_info_module(
        info_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-ig",
            "lifecycle_state": "AVAILABLE",
        },
        client=types.SimpleNamespace(list_internet_gateways="list_method"),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: paginate_calls.append((list_fn, kwargs)) or [],
    )

    resources = instance.fetch_resources()

    assert resources == []
    assert paginate_calls == [
        (
            "list_method",
            {
                "compartment_id": "ocid1.compartment.oc1..example",
                "vcn_id": "ocid1.vcn.oc1..example",
                "lifecycle_state": "AVAILABLE",
            },
        )
    ]


def test_run_returns_results_key(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_internet_gateway_info")
    resource = FakeModel(
        id="ocid1.internetgateway.oc1..example",
        display_name="example-ig",
        lifecycle_state="AVAILABLE",
        vcn_id="ocid1.vcn.oc1..example",
    )
    instance = make_internet_gateway_info_module(
        info_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-ig",
        },
    )
    monkeypatch.setattr(instance, "fetch_resources", lambda: [resource])

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()

    assert exc_info.value.payload == {
        "changed": False,
        "internet_gateways": [
            {
                "id": "ocid1.internetgateway.oc1..example",
                "name": "example-ig",
                "lifecycle_state": "AVAILABLE",
                "vcn_id": "ocid1.vcn.oc1..example",
            }
        ],
    }
