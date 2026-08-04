from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

from conftest import (
    FakeModel,
    FakeResponse,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)


SECURITY_LIST_MODEL_NAMES = (
    "CreateSecurityListDetails",
    "UpdateSecurityListDetails",
    "IngressSecurityRule",
    "EgressSecurityRule",
    "TcpOptions",
    "UdpOptions",
    "IcmpOptions",
    "PortRange",
)


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(
        monkeypatch,
        model_names=SECURITY_LIST_MODEL_NAMES,
    )


def make_security_list_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciSecurityListModule",
        params,
        client=client,
    )


def test_build_create_security_list_details_builds_nested_rule_models(monkeypatch):
    install_fake_oci(monkeypatch)

    security_list_module = load_collection_module("oci_security_list")
    details = security_list_module.build_create_security_list_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-security-list",
            "ingress_security_rules": [
                {
                    "source": "0.0.0.0/0",
                    "source_type": "CIDR_BLOCK",
                    "protocol": "6",
                    "is_stateless": False,
                    "description": "allow ssh",
                    "tcp_options": {
                        "destination_port_min": 22,
                        "destination_port_max": 22,
                    },
                    "udp_options": None,
                    "icmp_options": None,
                }
            ],
            "egress_security_rules": [
                {
                    "destination": "0.0.0.0/0",
                    "destination_type": "CIDR_BLOCK",
                    "protocol": "all",
                    "is_stateless": False,
                    "description": None,
                    "tcp_options": None,
                    "udp_options": None,
                    "icmp_options": None,
                }
            ],
        }
    )

    assert isinstance(details, FakeModel)
    assert len(details.ingress_security_rules) == 1
    ingress_rule = details.ingress_security_rules[0]
    assert ingress_rule.source == "0.0.0.0/0"
    assert ingress_rule.protocol == "6"
    assert ingress_rule.tcp_options.destination_port_range.min == 22
    assert ingress_rule.tcp_options.destination_port_range.max == 22
    assert ingress_rule.tcp_options.source_port_range is None
    assert ingress_rule.udp_options is None
    assert ingress_rule.icmp_options is None

    assert len(details.egress_security_rules) == 1
    egress_rule = details.egress_security_rules[0]
    assert egress_rule.destination == "0.0.0.0/0"
    assert egress_rule.protocol == "all"
    assert egress_rule.tcp_options is None


def test_needs_update_returns_false_when_ingress_rules_match_regardless_of_order(monkeypatch):
    install_fake_oci(monkeypatch)

    security_list_module = load_collection_module("oci_security_list")
    instance = make_security_list_module(
        security_list_module,
        {
            "ingress_security_rules": [
                {
                    "source": "10.0.0.0/16",
                    "source_type": "CIDR_BLOCK",
                    "protocol": "all",
                    "is_stateless": False,
                    "description": None,
                    "tcp_options": None,
                    "udp_options": None,
                    "icmp_options": None,
                },
                {
                    "source": "0.0.0.0/0",
                    "source_type": "CIDR_BLOCK",
                    "protocol": "6",
                    "is_stateless": False,
                    "description": None,
                    "tcp_options": {
                        "destination_port_min": 22,
                        "destination_port_max": 22,
                    },
                    "udp_options": None,
                    "icmp_options": None,
                },
            ],
        },
    )
    resource = FakeModel(
        id="ocid1.securitylist.oc1..example",
        ingress_security_rules=[
            {
                "source": "0.0.0.0/0",
                "source_type": "CIDR_BLOCK",
                "protocol": "6",
                "is_stateless": False,
                "description": None,
                "tcp_options": {
                    "source_port_range": None,
                    "destination_port_range": {"min": 22, "max": 22},
                },
                "udp_options": None,
                "icmp_options": None,
            },
            {
                "source": "10.0.0.0/16",
                "source_type": "CIDR_BLOCK",
                "protocol": "all",
                "is_stateless": False,
                "description": None,
                "tcp_options": None,
                "udp_options": None,
                "icmp_options": None,
            },
        ],
    )

    assert instance.needs_update(resource) is False


def test_needs_update_returns_true_when_egress_rules_change(monkeypatch):
    install_fake_oci(monkeypatch)

    security_list_module = load_collection_module("oci_security_list")
    instance = make_security_list_module(
        security_list_module,
        {
            "egress_security_rules": [
                {
                    "destination": "10.0.0.0/16",
                    "destination_type": "CIDR_BLOCK",
                    "protocol": "all",
                    "is_stateless": False,
                    "description": None,
                    "tcp_options": None,
                    "udp_options": None,
                    "icmp_options": None,
                },
            ],
        },
    )
    resource = FakeModel(
        id="ocid1.securitylist.oc1..example",
        egress_security_rules=[
            {
                "destination": "0.0.0.0/0",
                "destination_type": "CIDR_BLOCK",
                "protocol": "all",
                "is_stateless": False,
                "description": None,
                "tcp_options": None,
                "udp_options": None,
                "icmp_options": None,
            },
        ],
    )

    assert instance.needs_update(resource) is True


def test_update_resource_replaces_both_rule_sets_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    security_list_module = load_collection_module("oci_security_list")
    update_calls = []
    response = FakeResponse(data=FakeModel(id="ocid1.securitylist.oc1..example"))

    def update_security_list(security_list_id, update_security_list_details):
        update_calls.append((security_list_id, update_security_list_details))
        return response

    resource = FakeModel(
        id="ocid1.securitylist.oc1..example",
        ingress_security_rules=[],
        egress_security_rules=[],
    )
    instance = make_security_list_module(
        security_list_module,
        {
            "ingress_security_rules": [
                {
                    "source": "0.0.0.0/0",
                    "source_type": "CIDR_BLOCK",
                    "protocol": "6",
                    "is_stateless": False,
                    "description": None,
                    "tcp_options": None,
                    "udp_options": None,
                    "icmp_options": None,
                },
            ],
            "egress_security_rules": [
                {
                    "destination": "0.0.0.0/0",
                    "destination_type": "CIDR_BLOCK",
                    "protocol": "all",
                    "is_stateless": False,
                    "description": None,
                    "tcp_options": None,
                    "udp_options": None,
                    "icmp_options": None,
                },
            ],
            "wait": True,
        },
        client=types.SimpleNamespace(update_security_list=update_security_list),
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

    assert update_calls[0][0] == "ocid1.securitylist.oc1..example"
    assert len(update_calls[0][1].ingress_security_rules) == 1
    assert len(update_calls[0][1].egress_security_rules) == 1
    assert updated_resource.id == "ocid1.securitylist.oc1..example"
