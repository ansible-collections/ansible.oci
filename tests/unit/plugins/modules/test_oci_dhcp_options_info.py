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


def make_dhcp_options_info_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciDhcpOptionsInfoModule",
        params,
        client=client,
    )


def test_resource_id_kwarg_is_dhcp_id(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_dhcp_options_info")

    assert info_module.OciDhcpOptionsInfoModule.resource_id_param == "dhcp_options_id"
    assert info_module.OciDhcpOptionsInfoModule.resource_id_kwarg == "dhcp_id"


def test_fetch_resources_prefers_id_lookup_with_dhcp_id_kwarg(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_dhcp_options_info")
    get_calls = []

    def get_dhcp_options(**kwargs):
        get_calls.append(kwargs)
        return FakeResponse(
            data=FakeModel(
                id=kwargs["dhcp_id"],
                display_name="example-dhcp-options",
            )
        )

    instance = make_dhcp_options_info_module(
        info_module,
        {"dhcp_options_id": "ocid1.dhcpoptions.oc1..example"},
        client=types.SimpleNamespace(get_dhcp_options=get_dhcp_options),
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

    assert get_calls == [{"dhcp_id": "ocid1.dhcpoptions.oc1..example"}]
    assert len(resources) == 1
    assert resources[0].id == "ocid1.dhcpoptions.oc1..example"


def test_fetch_resources_returns_empty_list_on_404(monkeypatch):
    _oci_module, ServiceError = install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_dhcp_options_info")

    def get_missing_dhcp_options(**kwargs):
        raise ServiceError(404, "missing")

    instance = make_dhcp_options_info_module(
        info_module,
        {"dhcp_options_id": "ocid1.dhcpoptions.oc1..missing"},
        client=types.SimpleNamespace(get_dhcp_options=get_missing_dhcp_options),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    assert instance.fetch_resources() == []


def test_fetch_resources_uses_list_filters(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_dhcp_options_info")
    paginate_calls = []
    instance = make_dhcp_options_info_module(
        info_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-dhcp-options",
            "lifecycle_state": "AVAILABLE",
        },
        client=types.SimpleNamespace(list_dhcp_options="list_method"),
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


def test_run_returns_dhcp_options_results_key(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_dhcp_options_info")
    instance = make_dhcp_options_info_module(
        info_module,
        {"compartment_id": "ocid1.compartment.oc1..example"},
    )
    run_resource = FakeModel(
        id="ocid1.dhcpoptions.oc1..example",
        display_name="example-dhcp-options",
        lifecycle_state="AVAILABLE",
        vcn_id="ocid1.vcn.oc1..example",
    )
    monkeypatch.setattr(instance, "fetch_resources", lambda: [run_resource])

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()

    assert exc_info.value.payload == {
        "changed": False,
        "dhcp_options": [
            {
                "id": "ocid1.dhcpoptions.oc1..example",
                "name": "example-dhcp-options",
                "lifecycle_state": "AVAILABLE",
                "vcn_id": "ocid1.vcn.oc1..example",
            }
        ],
    }


def test_run_normalizes_options_to_ansible_shape(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_dhcp_options_info")
    instance = make_dhcp_options_info_module(
        info_module,
        {"compartment_id": "ocid1.compartment.oc1..example"},
    )
    run_resource = FakeModel(
        id="ocid1.dhcpoptions.oc1..example",
        display_name="example-dhcp-options",
        lifecycle_state="AVAILABLE",
        options=[
            {
                "type": "DomainNameServer",
                "server_type": "VcnLocalPlusInternet",
            },
            {
                "type": "SearchDomain",
                "search_domain_names": ["example.oraclevcn.com"],
            },
        ],
    )
    monkeypatch.setattr(instance, "fetch_resources", lambda: [run_resource])

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()

    assert exc_info.value.payload["dhcp_options"][0]["options"] == [
        {
            "option_type": "domain_name_server",
            "server_type": "vcn_local_plus_internet",
        },
        {
            "option_type": "search_domain",
            "search_domain_names": ["example.oraclevcn.com"],
        },
    ]


def test_run_normalizes_domain_name_type_to_ansible_shape(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_dhcp_options_info")
    instance = make_dhcp_options_info_module(
        info_module,
        {"compartment_id": "ocid1.compartment.oc1..example"},
    )
    run_resource = FakeModel(
        id="ocid1.dhcpoptions.oc1..example",
        display_name="example-dhcp-options",
        lifecycle_state="AVAILABLE",
        domain_name_type="CUSTOM_DOMAIN",
    )
    monkeypatch.setattr(instance, "fetch_resources", lambda: [run_resource])

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()

    assert exc_info.value.payload["dhcp_options"][0]["domain_name_type"] == "custom_domain"


def test_main_requires_compartment_id_or_dhcp_options_id(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_dhcp_options_info")
    captured = {}

    class FakeAnsibleModule:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(info_module, "AnsibleModule", FakeAnsibleModule)
    monkeypatch.setattr(
        info_module,
        "OciDhcpOptionsInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )

    info_module.main()

    assert captured["required_one_of"] == [["compartment_id", "dhcp_options_id"]]
    assert captured["argument_spec"]["dhcp_options_id"] == {"type": "str"}
    assert captured["argument_spec"]["vcn_id"] == {"type": "str"}
