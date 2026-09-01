from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from conftest import (
    DummyModule,
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    FailJsonCalled,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)


NETWORK_SECURITY_GROUP_RULE_MODEL_NAMES = (
    "AddNetworkSecurityGroupSecurityRulesDetails",
    "AddSecurityRuleDetails",
    "UpdateNetworkSecurityGroupSecurityRulesDetails",
    "UpdateSecurityRuleDetails",
    "RemoveNetworkSecurityGroupSecurityRulesDetails",
    "PortRange",
    "TcpOptions",
    "UdpOptions",
    "IcmpOptions",
)


def install_fake_oci(monkeypatch):
    fake_oci = shared_install_fake_oci(
        monkeypatch,
        model_names=NETWORK_SECURITY_GROUP_RULE_MODEL_NAMES,
    )
    fake_oci[0].response = types.SimpleNamespace(
        Response=lambda _status, headers, data, _request: FakeResponse(
            data=data,
            headers=headers,
        )
    )
    return fake_oci


def make_rule_module(module_obj, params, client=None, check_mode=False):
    return make_module_instance(
        module_obj,
        "OciNetworkSecurityGroupRuleModule",
        params,
        client=client,
        check_mode=check_mode,
    )


def make_rule(**overrides):
    fields = {
        "id": "04ABEC",
        "direction": "INGRESS",
        "protocol": "6",
        "source": "10.0.0.0/16",
        "source_type": "CIDR_BLOCK",
        "destination": None,
        "destination_type": None,
        "description": "allow ssh",
        "is_stateless": False,
        "tcp_options": FakeModel(
            source_port_range=None,
            destination_port_range=FakeModel(min=22, max=22),
        ),
        "udp_options": None,
        "icmp_options": None,
        "is_valid": True,
        "time_created": "2026-01-01T00:00:00Z",
    }
    fields.update(overrides)
    return FakeModel(**fields)


def test_main_exposes_rule_arguments(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_security_group_rule")
    rule_module_class = module_obj.OciNetworkSecurityGroupRuleModule
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule({})

    class FakeRuleModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(
        module_obj,
        "OciNetworkSecurityGroupRuleModule",
        FakeRuleModule,
    )

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["supports_check_mode"] is True
    assert captured["argument_spec"]["network_security_group_id"]["required"] is True
    assert captured["argument_spec"]["security_rule_id"] == {"type": "str"}
    assert captured["argument_spec"]["direction"]["choices"] == [
        "ingress",
        "egress",
    ]
    assert captured["argument_spec"]["source_type"]["choices"] == [
        "cidr_block",
        "service_cidr_block",
        "network_security_group",
    ]
    assert captured["required_if"] == [
        ("state", "absent", ["security_rule_id"])
    ]
    assert {
        spec.param_name
        for spec in rule_module_class.update_field_specs
    } == {
        "description",
        "destination",
        "destination_type",
        "direction",
        "icmp_options",
        "is_stateless",
        "protocol",
        "source",
        "source_type",
        "tcp_options",
        "udp_options",
    }


def test_normalize_and_build_add_rule_models(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_security_group_rule")

    normalized = module_obj.normalize_rule_params(
        {
            "direction": "ingress",
            "protocol": "6",
            "source": "10.0.0.0/16",
            "tcp_options": {
                "destination_port_min": 22,
                "destination_port_max": 22,
            },
        },
        apply_create_defaults=True,
    )
    model = module_obj.build_security_rule_model(
        module_obj.oci.core.models.AddSecurityRuleDetails,
        normalized,
    )

    assert normalized["source_type"] == "CIDR_BLOCK"
    assert normalized["is_stateless"] is False
    assert model.direction == "INGRESS"
    assert model.source == "10.0.0.0/16"
    assert model.tcp_options.destination_port_range.min == 22
    assert model.tcp_options.destination_port_range.max == 22


def test_list_security_rules_uses_network_security_group_id(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_security_group_rule")
    list_method = object()
    list_calls = []
    instance = make_rule_module(
        module_obj,
        {"network_security_group_id": "ocid1.networksecuritygroup.oc1..example"},
        client=types.SimpleNamespace(
            list_network_security_group_security_rules=list_method
        ),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda method, **kwargs: list_calls.append((method, kwargs)) or [],
    )

    assert instance.list_security_rules() == []
    assert list_calls == [
        (
            list_method,
            {
                "network_security_group_id": (
                    "ocid1.networksecuritygroup.oc1..example"
                )
            },
        )
    ]


def test_create_is_idempotent_when_matching_rule_exists(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_security_group_rule")
    params = {
        "network_security_group_id": "ocid1.networksecuritygroup.oc1..example",
        "state": "present",
        "direction": "ingress",
        "protocol": "6",
        "source": "10.0.0.0/16",
        "description": "allow ssh",
        "tcp_options": {
            "destination_port_min": 22,
            "destination_port_max": 22,
        },
    }
    instance = make_rule_module(module_obj, params)
    monkeypatch.setattr(instance, "list_security_rules", lambda: [make_rule()])
    monkeypatch.setattr(
        instance,
        "create_resource",
        lambda: pytest.fail("create_resource should not be called"),
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload["changed"] is False
    assert exc_info.value.payload["resource"]["id"] == "04ABEC"


def test_create_calls_bulk_add_and_returns_created_rule(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_security_group_rule")
    params = {
        "network_security_group_id": "ocid1.networksecuritygroup.oc1..example",
        "state": "present",
        "direction": "egress",
        "protocol": "17",
        "destination": "0.0.0.0/0",
        "udp_options": {
            "destination_port_min": 53,
            "destination_port_max": 53,
        },
    }
    add_calls = []

    def add_rules(**kwargs):
        add_calls.append(kwargs)
        return FakeResponse(
            data=FakeModel(
                security_rules=[
                    make_rule(
                        id="09CDEF",
                        direction="EGRESS",
                        protocol="17",
                        source=None,
                        source_type=None,
                        destination="0.0.0.0/0",
                        destination_type="CIDR_BLOCK",
                    )
                ]
            )
        )

    instance = make_rule_module(
        module_obj,
        params,
        client=types.SimpleNamespace(
            add_network_security_group_security_rules=add_rules
        ),
    )
    monkeypatch.setattr(instance, "list_security_rules", lambda: [])
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload["changed"] is True
    assert exc_info.value.payload["resource"]["id"] == "09CDEF"
    assert exc_info.value.payload["resource"]["direction"] == "egress"
    assert exc_info.value.payload["resource"]["destination_type"] == "cidr_block"
    details = add_calls[0]["add_network_security_group_security_rules_details"]
    assert len(details.security_rules) == 1
    assert details.security_rules[0].destination_type == "CIDR_BLOCK"
    assert details.security_rules[0].udp_options.destination_port_range.min == 53


def test_create_check_mode_does_not_call_add(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_security_group_rule")
    instance = make_rule_module(
        module_obj,
        {
            "network_security_group_id": "ocid1.networksecuritygroup.oc1..example",
            "state": "present",
            "direction": "ingress",
            "protocol": "all",
            "source": "0.0.0.0/0",
        },
        check_mode=True,
    )
    monkeypatch.setattr(instance, "list_security_rules", lambda: [])
    monkeypatch.setattr(
        instance,
        "create_resource",
        lambda: pytest.fail("create_resource should not be called"),
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload == {"changed": True}


def test_update_preserves_omitted_required_fields(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_security_group_rule")
    update_calls = []

    def update_rules(**kwargs):
        update_calls.append(kwargs)
        return FakeResponse(
            data=FakeModel(
                security_rules=[make_rule(description="updated description")]
            )
        )

    instance = make_rule_module(
        module_obj,
        {
            "network_security_group_id": "ocid1.networksecuritygroup.oc1..example",
            "security_rule_id": "04ABEC",
            "state": "present",
            "description": "updated description",
        },
        client=types.SimpleNamespace(
            update_network_security_group_security_rules=update_rules
        ),
    )
    monkeypatch.setattr(instance, "list_security_rules", lambda: [make_rule()])
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload["changed"] is True
    details = update_calls[0]["update_network_security_group_security_rules_details"]
    updated_model = details.security_rules[0]
    assert updated_model.id == "04ABEC"
    assert updated_model.description == "updated description"
    assert updated_model.direction == "INGRESS"
    assert updated_model.protocol == "6"
    assert updated_model.source == "10.0.0.0/16"


def test_update_is_idempotent(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_security_group_rule")
    instance = make_rule_module(
        module_obj,
        {
            "network_security_group_id": "ocid1.networksecuritygroup.oc1..example",
            "security_rule_id": "04ABEC",
            "state": "present",
            "description": "allow ssh",
        },
    )
    monkeypatch.setattr(instance, "list_security_rules", lambda: [make_rule()])
    monkeypatch.setattr(
        instance,
        "update_resource",
        lambda resource: pytest.fail("update_resource should not be called"),
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload["changed"] is False
    assert exc_info.value.payload["resource"]["id"] == "04ABEC"


def test_update_fails_when_rule_id_is_missing(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_security_group_rule")
    instance = make_rule_module(
        module_obj,
        {
            "network_security_group_id": "ocid1.networksecuritygroup.oc1..example",
            "security_rule_id": "missing",
            "state": "present",
            "description": "updated description",
        },
    )
    monkeypatch.setattr(instance, "list_security_rules", lambda: [])

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert "security_rule_id=missing" in exc_info.value.payload["msg"]


@pytest.mark.parametrize(
    "check_mode,expected_changed,expected_remove_calls",
    [(False, True, 1), (True, True, 0)],
)
def test_delete_existing_rule(
    monkeypatch,
    check_mode,
    expected_changed,
    expected_remove_calls,
):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_security_group_rule")
    remove_calls = []

    def remove_rules(**kwargs):
        remove_calls.append(kwargs)
        return FakeResponse(data=None)

    instance = make_rule_module(
        module_obj,
        {
            "network_security_group_id": "ocid1.networksecuritygroup.oc1..example",
            "security_rule_id": "04ABEC",
            "state": "absent",
        },
        client=types.SimpleNamespace(
            remove_network_security_group_security_rules=remove_rules
        ),
        check_mode=check_mode,
    )
    monkeypatch.setattr(instance, "list_security_rules", lambda: [make_rule()])
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload["changed"] is expected_changed
    assert len(remove_calls) == expected_remove_calls
    if remove_calls:
        details = remove_calls[0][
            "remove_network_security_group_security_rules_details"
        ]
        assert details.security_rule_ids == ["04ABEC"]


def test_delete_missing_rule_is_idempotent(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_security_group_rule")
    instance = make_rule_module(
        module_obj,
        {
            "network_security_group_id": "ocid1.networksecuritygroup.oc1..example",
            "security_rule_id": "missing",
            "state": "absent",
        },
    )
    monkeypatch.setattr(instance, "list_security_rules", lambda: [])

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert exc_info.value.payload == {"changed": False}


@pytest.mark.parametrize(
    "params,missing_field",
    [
        ({"direction": "ingress", "protocol": "6"}, "source"),
        ({"direction": "egress", "protocol": "6"}, "destination"),
        ({"source": "10.0.0.0/16"}, "direction"),
    ],
)
def test_create_validates_direction_specific_fields(
    monkeypatch,
    params,
    missing_field,
):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_security_group_rule")
    instance = make_rule_module(
        module_obj,
        dict(
            {
                "network_security_group_id": (
                    "ocid1.networksecuritygroup.oc1..example"
                ),
                "state": "present",
            },
            **params,
        ),
    )
    monkeypatch.setattr(instance, "list_security_rules", lambda: [])

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.execute_resource_module()

    assert missing_field in exc_info.value.payload["msg"]
