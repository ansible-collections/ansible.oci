from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from conftest import (
    DummyModule,
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


def make_network_security_group_info_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciNetworkSecurityGroupInfoModule",
        params,
        client=client,
    )


def test_main_requires_compartment_or_full_resource_id(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_security_group_info")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule({})

    class FakeNetworkSecurityGroupInfoModule:
        def __init__(self, module):
            self.module = module

        def execute_info_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(
        module_obj,
        "OciNetworkSecurityGroupInfoModule",
        FakeNetworkSecurityGroupInfoModule,
    )

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["required_one_of"] == [
        ["compartment_id", "network_security_group_id"]
    ]
    assert captured["argument_spec"]["network_security_group_id"] == {"type": "str"}


def test_fetch_resources_lists_with_existing_info_filters(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_security_group_info")
    list_calls = []
    instance = make_network_security_group_info_module(
        module_obj,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "lifecycle_state": "AVAILABLE",
        },
        client=types.SimpleNamespace(list_network_security_groups="list_method"),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: list_calls.append((list_fn, kwargs)) or [],
    )

    assert instance.fetch_resources() == []
    assert list_calls == [
        (
            "list_method",
            {
                "compartment_id": "ocid1.compartment.oc1..example",
                "vcn_id": "ocid1.vcn.oc1..example",
                "lifecycle_state": "AVAILABLE",
            },
        )
    ]


def test_fetch_resources_prefers_full_id_lookup(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_security_group_info")
    get_calls = []

    def get_network_security_group(**kwargs):
        get_calls.append(kwargs)
        return FakeResponse(data=FakeModel(id=kwargs["network_security_group_id"]))

    instance = make_network_security_group_info_module(
        module_obj,
        {"network_security_group_id": "ocid1.networksecuritygroup.oc1..example"},
        client=types.SimpleNamespace(
            get_network_security_group=get_network_security_group
        ),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        raising(AssertionError("list_all_resources should not be called")),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    resources = instance.fetch_resources()

    assert resources[0].id == "ocid1.networksecuritygroup.oc1..example"
    assert get_calls == [
        {"network_security_group_id": "ocid1.networksecuritygroup.oc1..example"}
    ]


def test_fetch_resources_returns_empty_list_on_404(monkeypatch):
    _oci_module, ServiceError = install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_security_group_info")

    def get_missing_network_security_group(**kwargs):
        raise ServiceError(404, "missing")

    instance = make_network_security_group_info_module(
        module_obj,
        {"network_security_group_id": "ocid1.networksecuritygroup.oc1..missing"},
        client=types.SimpleNamespace(
            get_network_security_group=get_missing_network_security_group
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.fetch_resources() == []


def test_execute_info_module_returns_full_results_key(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_security_group_info")
    instance = make_network_security_group_info_module(
        module_obj,
        {"compartment_id": "ocid1.compartment.oc1..example"},
    )
    monkeypatch.setattr(
        instance,
        "fetch_resources",
        lambda: [
            FakeModel(
                id="ocid1.networksecuritygroup.oc1..example",
                display_name="example-network-security-group",
                vcn_id="ocid1.vcn.oc1..example",
                lifecycle_state="AVAILABLE",
            )
        ],
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()

    assert exc_info.value.payload == {
        "changed": False,
        "network_security_groups": [
            {
                "id": "ocid1.networksecuritygroup.oc1..example",
                "name": "example-network-security-group",
                "vcn_id": "ocid1.vcn.oc1..example",
                "lifecycle_state": "AVAILABLE",
            }
        ],
    }
