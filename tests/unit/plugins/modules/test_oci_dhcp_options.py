from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from conftest import (
    DummyModule,
    FakeModel,
    FakeResponse,
    FailJsonCalled,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)


DHCP_OPTIONS_MODEL_NAMES = (
    "CreateDhcpDetails",
    "UpdateDhcpDetails",
    "DhcpDnsOption",
    "DhcpSearchDomainOption",
)


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(
        monkeypatch,
        model_names=DHCP_OPTIONS_MODEL_NAMES,
    )


def make_dhcp_options_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciDhcpOptionsModule",
        params,
        client=client,
    )


def test_main_exposes_allow_duplicate_name_argument(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_dhcp_options")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        return DummyModule({})

    class FakeDhcpOptionsModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciDhcpOptionsModule", FakeDhcpOptionsModule)

    module_obj.main()

    assert captured["run_called"] is True
    assert module_obj.OCI_COMMON_ARGS["allow_duplicate_name"] == {
        "type": "bool",
        "default": False,
    }
    assert module_obj.OCI_COMMON_ARGS["name"] == {"type": "str"}
    assert module_obj.OCI_COMMON_ARGS["compartment_id"] == {"type": "str"}
    assert captured["argument_spec"]["allow_duplicate_name"] == {
        "type": "bool",
        "default": False,
    }
    assert captured["argument_spec"]["name"] == {"type": "str"}
    assert captured["argument_spec"]["compartment_id"] == {"type": "str"}
    assert captured["argument_spec"]["options"]["type"] == "list"
    assert captured["argument_spec"]["options"]["elements"] == "dict"
    assert captured["argument_spec"]["domain_name_type"]["choices"] == [
        "subnet_domain",
        "vcn_domain",
        "custom_domain",
    ]
    assert "display_name" not in captured["argument_spec"]


def test_build_create_dhcp_options_details_builds_both_option_types(monkeypatch):
    install_fake_oci(monkeypatch)

    dhcp_options_module = load_collection_module("oci_dhcp_options")
    details = dhcp_options_module.build_create_dhcp_options_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-dhcp-options",
            "domain_name_type": "subnet_domain",
            "options": [
                {
                    "option_type": "domain_name_server",
                    "server_type": "vcn_local_plus_internet",
                },
                {
                    "option_type": "search_domain",
                    "search_domain_names": ["example.oraclevcn.com"],
                },
            ],
            "freeform_tags": {"env": "dev"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        }
    )

    assert isinstance(details, FakeModel)
    assert details.compartment_id == "ocid1.compartment.oc1..example"
    assert details.vcn_id == "ocid1.vcn.oc1..example"
    assert details.display_name == "example-dhcp-options"
    # build_create_dhcp_options_details translates the ansible-facing
    # snake_case domain_name_type into the OCI SDK's native casing.
    assert details.domain_name_type == "SUBNET_DOMAIN"
    assert details.freeform_tags == {"env": "dev"}
    assert details.defined_tags == {"Operations": {"CostCenter": "42"}}
    assert len(details.options) == 2

    dns_option = details.options[0]
    # build_option_models translates the ansible-facing snake_case server_type
    # into the OCI SDK's native PascalCase enum value.
    assert dns_option.server_type == "VcnLocalPlusInternet"
    assert not hasattr(dns_option, "search_domain_names")

    search_domain_option = details.options[1]
    assert search_domain_option.search_domain_names == ["example.oraclevcn.com"]
    assert not hasattr(search_domain_option, "server_type")


def test_build_create_dhcp_options_details_omits_options_when_absent(monkeypatch):
    install_fake_oci(monkeypatch)

    dhcp_options_module = load_collection_module("oci_dhcp_options")
    details = dhcp_options_module.build_create_dhcp_options_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-dhcp-options",
        }
    )

    assert not hasattr(details, "options")


def test_build_option_models_builds_correct_model_types(monkeypatch):
    install_fake_oci(monkeypatch)

    dhcp_options_module = load_collection_module("oci_dhcp_options")
    models = dhcp_options_module.build_option_models(
        [
            {
                "option_type": "domain_name_server",
                "server_type": "custom_dns_server",
                "custom_dns_servers": ["10.0.0.10", "10.0.0.11"],
            },
            {
                "option_type": "search_domain",
                "search_domain_names": ["example.oraclevcn.com"],
            },
        ]
    )

    assert len(models) == 2
    # Output uses OCI's native enum casing, not the ansible-facing snake_case
    # input, since this is what actually gets sent to the SDK/API.
    assert models[0].server_type == "CustomDnsServer"
    assert models[0].custom_dns_servers == ["10.0.0.10", "10.0.0.11"]
    assert models[1].search_domain_names == ["example.oraclevcn.com"]


def test_needs_update_returns_false_when_options_match_regardless_of_order(monkeypatch):
    install_fake_oci(monkeypatch)

    dhcp_options_module = load_collection_module("oci_dhcp_options")
    instance = make_dhcp_options_module(
        dhcp_options_module,
        {
            "options": [
                {
                    "option_type": "search_domain",
                    "search_domain_names": [
                        "b.example.com",
                        "a.example.com",
                    ],
                },
                {
                    "option_type": "domain_name_server",
                    "server_type": "vcn_local_plus_internet",
                },
            ],
        },
    )
    # The resource dict mirrors a real serialized OCI API response, which
    # uses OCI's native "type"/server_type casing, not the ansible-facing
    # snake_case values above.
    resource = FakeModel(
        id="ocid1.dhcpoptions.oc1..example",
        options=[
            {
                "type": "DomainNameServer",
                "server_type": "VcnLocalPlusInternet",
                "custom_dns_servers": [],
            },
            {
                "type": "SearchDomain",
                "search_domain_names": [
                    "a.example.com",
                    "b.example.com",
                ],
            },
        ],
    )

    assert instance.needs_update(resource) is False


def test_needs_update_returns_true_when_options_differ(monkeypatch):
    install_fake_oci(monkeypatch)

    dhcp_options_module = load_collection_module("oci_dhcp_options")
    instance = make_dhcp_options_module(
        dhcp_options_module,
        {
            "options": [
                {
                    "option_type": "domain_name_server",
                    "server_type": "custom_dns_server",
                    "custom_dns_servers": ["10.0.0.10"],
                },
            ],
        },
    )
    resource = FakeModel(
        id="ocid1.dhcpoptions.oc1..example",
        options=[
            {
                "type": "DomainNameServer",
                "server_type": "VcnLocal",
                "custom_dns_servers": [],
            },
        ],
    )

    assert instance.needs_update(resource) is True


def test_needs_update_fails_on_unrecognized_option_type(monkeypatch):
    install_fake_oci(monkeypatch)

    dhcp_options_module = load_collection_module("oci_dhcp_options")
    instance = make_dhcp_options_module(
        dhcp_options_module,
        {
            "options": [
                {
                    "option_type": "domain_name_server",
                    "server_type": "vcn_local",
                },
            ],
        },
    )
    # Simulate a future OCI API adding a DhcpOption subtype this module does
    # not yet know how to translate.
    resource = FakeModel(
        id="ocid1.dhcpoptions.oc1..example",
        options=[
            {
                "type": "SomeFutureOptionType",
            },
        ],
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "SomeFutureOptionType" in exc_info.value.payload["msg"]


def test_needs_update_returns_true_for_domain_name_type_change(monkeypatch):
    install_fake_oci(monkeypatch)

    dhcp_options_module = load_collection_module("oci_dhcp_options")
    instance = make_dhcp_options_module(
        dhcp_options_module,
        {"domain_name_type": "vcn_domain"},
    )
    # The resource dict mirrors a real serialized OCI API response, which
    # uses OCI's native casing, not the ansible-facing snake_case value above.
    resource = FakeModel(
        id="ocid1.dhcpoptions.oc1..example",
        domain_name_type="SUBNET_DOMAIN",
    )

    assert instance.needs_update(resource) is True


def test_needs_update_returns_false_when_domain_name_type_matches_across_casing(monkeypatch):
    install_fake_oci(monkeypatch)

    dhcp_options_module = load_collection_module("oci_dhcp_options")
    instance = make_dhcp_options_module(
        dhcp_options_module,
        {"domain_name_type": "subnet_domain"},
    )
    resource = FakeModel(
        id="ocid1.dhcpoptions.oc1..example",
        domain_name_type="SUBNET_DOMAIN",
    )

    assert instance.needs_update(resource) is False


def test_needs_update_returns_true_for_name_change(monkeypatch):
    install_fake_oci(monkeypatch)

    dhcp_options_module = load_collection_module("oci_dhcp_options")
    instance = make_dhcp_options_module(
        dhcp_options_module,
        {"name": "updated-dhcp-options"},
    )
    resource = FakeModel(
        id="ocid1.dhcpoptions.oc1..example",
        display_name="current-dhcp-options",
    )

    assert instance.needs_update(resource) is True


def test_needs_update_rejects_vcn_id_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    dhcp_options_module = load_collection_module("oci_dhcp_options")
    instance = make_dhcp_options_module(
        dhcp_options_module,
        {"vcn_id": "ocid1.vcn.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.dhcpoptions.oc1..example",
        vcn_id="ocid1.vcn.oc1..current",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "vcn_id" in exc_info.value.payload["msg"]


def test_needs_update_rejects_compartment_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    dhcp_options_module = load_collection_module("oci_dhcp_options")
    instance = make_dhcp_options_module(
        dhcp_options_module,
        {"compartment_id": "ocid1.compartment.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.dhcpoptions.oc1..example",
        compartment_id="ocid1.compartment.oc1..current",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "compartment_id" in exc_info.value.payload["msg"]


def test_get_resource_response_uses_dhcp_id_kwarg(monkeypatch):
    install_fake_oci(monkeypatch)

    dhcp_options_module = load_collection_module("oci_dhcp_options")
    get_calls = []

    def get_dhcp_options(**kwargs):
        get_calls.append(kwargs)
        return FakeResponse(data=FakeModel(id=kwargs["dhcp_id"]))

    instance = make_dhcp_options_module(
        dhcp_options_module,
        {},
        client=types.SimpleNamespace(get_dhcp_options=get_dhcp_options),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    response = instance.get_resource_response("ocid1.dhcpoptions.oc1..example")

    assert get_calls == [{"dhcp_id": "ocid1.dhcpoptions.oc1..example"}]
    assert response.data.id == "ocid1.dhcpoptions.oc1..example"


def test_create_resource_uses_create_dhcp_options_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    dhcp_options_module = load_collection_module("oci_dhcp_options")
    create_calls = []
    response = FakeResponse(
        data=FakeModel(id="ocid1.dhcpoptions.oc1..example"),
    )

    def create_dhcp_options(create_dhcp_details):
        create_calls.append(create_dhcp_details)
        return response

    instance = make_dhcp_options_module(
        dhcp_options_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-dhcp-options",
            "options": [
                {
                    "option_type": "domain_name_server",
                    "server_type": "vcn_local_plus_internet",
                },
            ],
            "wait": True,
        },
        client=types.SimpleNamespace(create_dhcp_options=create_dhcp_options),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: FakeModel(
            id=resource_id,
            lifecycle_state="AVAILABLE",
        ),
    )

    resource = instance.create_resource()

    assert create_calls[0].display_name == "example-dhcp-options"
    assert create_calls[0].vcn_id == "ocid1.vcn.oc1..example"
    assert len(create_calls[0].options) == 1
    assert resource.id == "ocid1.dhcpoptions.oc1..example"
    assert resource.lifecycle_state == "AVAILABLE"


def test_update_resource_builds_option_models_and_calls_update_dhcp_options(monkeypatch):
    install_fake_oci(monkeypatch)

    dhcp_options_module = load_collection_module("oci_dhcp_options")
    update_calls = []
    response = FakeResponse(
        data=FakeModel(id="ocid1.dhcpoptions.oc1..example"),
    )

    def update_dhcp_options(dhcp_id, update_dhcp_details):
        update_calls.append((dhcp_id, update_dhcp_details))
        return response

    resource = FakeModel(
        id="ocid1.dhcpoptions.oc1..example",
        options=[
            {
                "type": "DomainNameServer",
                "server_type": "VcnLocal",
                "custom_dns_servers": [],
            },
        ],
    )
    instance = make_dhcp_options_module(
        dhcp_options_module,
        {
            "options": [
                {
                    "option_type": "domain_name_server",
                    "server_type": "custom_dns_server",
                    "custom_dns_servers": ["10.0.0.10"],
                },
                {
                    "option_type": "search_domain",
                    "search_domain_names": ["example.oraclevcn.com"],
                },
            ],
            "wait": True,
        },
        client=types.SimpleNamespace(update_dhcp_options=update_dhcp_options),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: FakeModel(
            id=resource_id,
            lifecycle_state="AVAILABLE",
        ),
    )

    updated_resource = instance.update_resource(resource)

    assert update_calls[0][0] == "ocid1.dhcpoptions.oc1..example"
    update_details = update_calls[0][1]
    assert len(update_details.options) == 2
    assert update_details.options[0].server_type == "CustomDnsServer"
    assert update_details.options[0].custom_dns_servers == ["10.0.0.10"]
    assert update_details.options[1].search_domain_names == ["example.oraclevcn.com"]
    assert updated_resource.id == "ocid1.dhcpoptions.oc1..example"


def test_update_resource_translates_domain_name_type(monkeypatch):
    install_fake_oci(monkeypatch)

    dhcp_options_module = load_collection_module("oci_dhcp_options")
    update_calls = []
    response = FakeResponse(
        data=FakeModel(id="ocid1.dhcpoptions.oc1..example"),
    )

    def update_dhcp_options(dhcp_id, update_dhcp_details):
        update_calls.append((dhcp_id, update_dhcp_details))
        return response

    resource = FakeModel(
        id="ocid1.dhcpoptions.oc1..example",
        domain_name_type="SUBNET_DOMAIN",
    )
    instance = make_dhcp_options_module(
        dhcp_options_module,
        {"domain_name_type": "vcn_domain", "wait": True},
        client=types.SimpleNamespace(update_dhcp_options=update_dhcp_options),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: FakeModel(
            id=resource_id,
            lifecycle_state="AVAILABLE",
        ),
    )

    instance.update_resource(resource)

    # update_resource sends OCI's native casing to the SDK, not the
    # ansible-facing snake_case value the caller set.
    assert update_calls[0][1].domain_name_type == "VCN_DOMAIN"


def test_update_resource_is_noop_when_no_fields_changed(monkeypatch):
    install_fake_oci(monkeypatch)

    dhcp_options_module = load_collection_module("oci_dhcp_options")
    resource = FakeModel(id="ocid1.dhcpoptions.oc1..example")
    instance = make_dhcp_options_module(
        dhcp_options_module,
        {},
        client=types.SimpleNamespace(),
    )

    updated_resource = instance.update_resource(resource)

    assert updated_resource is resource


def test_delete_resource_uses_dhcp_id_kwarg(monkeypatch):
    install_fake_oci(monkeypatch)

    dhcp_options_module = load_collection_module("oci_dhcp_options")
    delete_calls = []

    def delete_dhcp_options(**kwargs):
        delete_calls.append(kwargs)
        return FakeResponse(data=FakeModel(id=kwargs["dhcp_id"]))

    resource = FakeModel(id="ocid1.dhcpoptions.oc1..example")
    instance = make_dhcp_options_module(
        dhcp_options_module,
        {"wait": False},
        client=types.SimpleNamespace(delete_dhcp_options=delete_dhcp_options),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    instance.delete_resource(resource)

    assert delete_calls == [{"dhcp_id": "ocid1.dhcpoptions.oc1..example"}]


def test_serialize_result_resource_normalizes_options_to_ansible_shape(monkeypatch):
    install_fake_oci(monkeypatch)

    dhcp_options_module = load_collection_module("oci_dhcp_options")
    instance = make_dhcp_options_module(dhcp_options_module, {})
    resource = FakeModel(
        id="ocid1.dhcpoptions.oc1..example",
        display_name="example-dhcp-options",
        options=[
            {
                "type": "DomainNameServer",
                "server_type": "CustomDnsServer",
                "custom_dns_servers": ["10.0.0.10"],
            },
            {
                "type": "SearchDomain",
                "search_domain_names": ["example.oraclevcn.com"],
            },
        ],
    )

    result = instance.serialize_result_resource(resource)

    assert result["options"] == [
        {
            "option_type": "domain_name_server",
            "server_type": "custom_dns_server",
            "custom_dns_servers": ["10.0.0.10"],
        },
        {
            "option_type": "search_domain",
            "search_domain_names": ["example.oraclevcn.com"],
        },
    ]
    # The normalized options round-trip cleanly as input to the same module.
    assert dhcp_options_module.build_option_models(result["options"])[0].server_type == "CustomDnsServer"


def test_serialize_result_resource_normalizes_domain_name_type_to_ansible_shape(monkeypatch):
    install_fake_oci(monkeypatch)

    dhcp_options_module = load_collection_module("oci_dhcp_options")
    instance = make_dhcp_options_module(dhcp_options_module, {})
    resource = FakeModel(
        id="ocid1.dhcpoptions.oc1..example",
        display_name="example-dhcp-options",
        domain_name_type="VCN_DOMAIN",
    )

    result = instance.serialize_result_resource(resource)

    assert result["domain_name_type"] == "vcn_domain"
