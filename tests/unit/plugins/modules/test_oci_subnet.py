import sys
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


SUBNET_MODEL_NAMES = (
    "CreateSubnetDetails",
    "UpdateSubnetDetails",
)


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(
        monkeypatch,
        model_names=SUBNET_MODEL_NAMES,
    )


def make_subnet_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciSubnetModule",
        params,
        client=client,
    )


def test_build_create_subnet_details_includes_supported_fields(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    subnet_module = load_collection_module("oci_subnet")
    details = subnet_module.build_create_subnet_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "cidr_block": "10.0.1.0/24",
            "display_name": "example-subnet",
            "dns_label": "examplesubnet",
            "availability_domain": "Uocm:PHX-AD-1",
            "route_table_id": "ocid1.routetable.oc1..example",
            "security_list_ids": ["ocid1.securitylist.oc1..example"],
            "prohibit_public_ip_on_vnic": True,
            "freeform_tags": {"env": "dev"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        }
    )

    assert isinstance(details, FakeModel)
    assert details.compartment_id == "ocid1.compartment.oc1..example"
    assert details.vcn_id == "ocid1.vcn.oc1..example"
    assert details.cidr_block == "10.0.1.0/24"
    assert details.display_name == "example-subnet"
    assert details.dns_label == "examplesubnet"
    assert details.availability_domain == "Uocm:PHX-AD-1"
    assert details.route_table_id == "ocid1.routetable.oc1..example"
    assert details.security_list_ids == ["ocid1.securitylist.oc1..example"]
    assert details.prohibit_public_ip_on_vnic is True
    assert details.freeform_tags == {"env": "dev"}
    assert details.defined_tags == {"Operations": {"CostCenter": "42"}}


def test_build_update_subnet_details_only_includes_mutable_fields(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    subnet_module = load_collection_module("oci_subnet")
    details = subnet_module.build_update_subnet_details(
        {
            "display_name": "updated-subnet",
            "route_table_id": "ocid1.routetable.oc1..updated",
            "security_list_ids": ["ocid1.securitylist.oc1..updated"],
            "cidr_block": "10.0.2.0/24",
            "dns_label": "immutablelabel",
            "availability_domain": "Uocm:PHX-AD-2",
            "vcn_id": "ocid1.vcn.oc1..other",
            "prohibit_public_ip_on_vnic": False,
            "freeform_tags": {"env": "prod"},
            "defined_tags": {"Operations": {"CostCenter": "43"}},
        }
    )

    assert isinstance(details, FakeModel)
    assert details.display_name == "updated-subnet"
    assert details.cidr_block == "10.0.2.0/24"
    assert details.route_table_id == "ocid1.routetable.oc1..updated"
    assert details.security_list_ids == ["ocid1.securitylist.oc1..updated"]
    assert details.freeform_tags == {"env": "prod"}
    assert details.defined_tags == {"Operations": {"CostCenter": "43"}}
    assert not hasattr(details, "dns_label")
    assert not hasattr(details, "availability_domain")
    assert not hasattr(details, "vcn_id")
    assert not hasattr(details, "prohibit_public_ip_on_vnic")


def test_needs_update_returns_true_for_cidr_block_change(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    subnet_module = load_collection_module("oci_subnet")
    instance = make_subnet_module(
        subnet_module,
        {"cidr_block": "10.0.2.0/24"},
    )
    resource = FakeModel(id="ocid1.subnet.oc1..example", cidr_block="10.0.1.0/24")

    assert instance.needs_update(resource) is True


def test_needs_update_rejects_mixed_cidr_and_dns_label_change(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    subnet_module = load_collection_module("oci_subnet")
    instance = make_subnet_module(
        subnet_module,
        {
            "cidr_block": "10.0.2.0/24",
            "dns_label": "desiredlabel",
        },
    )
    resource = FakeModel(
        id="ocid1.subnet.oc1..example",
        cidr_block="10.0.1.0/24",
        dns_label="currentlabel",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "dns_label" in exc_info.value.payload["msg"]


def test_needs_update_rejects_prohibit_public_ip_drift(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    subnet_module = load_collection_module("oci_subnet")
    instance = make_subnet_module(
        subnet_module,
        {"prohibit_public_ip_on_vnic": False},
    )
    resource = FakeModel(
        id="ocid1.subnet.oc1..example",
        prohibit_public_ip_on_vnic=True,
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "prohibit_public_ip_on_vnic" in exc_info.value.payload["msg"]


def test_needs_update_rejects_compartment_drift(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    subnet_module = load_collection_module("oci_subnet")
    instance = make_subnet_module(
        subnet_module,
        {"compartment_id": "ocid1.compartment.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.subnet.oc1..example",
        compartment_id="ocid1.compartment.oc1..current",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "compartment_id" in exc_info.value.payload["msg"]


def test_needs_update_returns_true_for_route_table_change(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    subnet_module = load_collection_module("oci_subnet")
    instance = make_subnet_module(
        subnet_module,
        {"route_table_id": "ocid1.routetable.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.subnet.oc1..example",
        route_table_id="ocid1.routetable.oc1..current",
    )

    assert instance.needs_update(resource) is True


def test_needs_update_ignores_security_list_order(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    subnet_module = load_collection_module("oci_subnet")
    instance = make_subnet_module(
        subnet_module,
        {
            "security_list_ids": [
                "ocid1.securitylist.oc1..two",
                "ocid1.securitylist.oc1..one",
            ],
        },
    )
    resource = FakeModel(
        id="ocid1.subnet.oc1..example",
        security_list_ids=[
            "ocid1.securitylist.oc1..one",
            "ocid1.securitylist.oc1..two",
        ],
    )

    assert instance.needs_update(resource) is False


def test_create_resource_uses_create_subnet_and_waits(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    subnet_module = load_collection_module("oci_subnet")
    create_calls = []
    response = FakeResponse(
        data=FakeModel(id="ocid1.subnet.oc1..example"),
    )

    def create_subnet(create_subnet_details):
        create_calls.append(create_subnet_details)
        return response

    instance = make_subnet_module(
        subnet_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "cidr_block": "10.0.1.0/24",
            "display_name": "example-subnet",
            "dns_label": "examplesubnet",
            "route_table_id": "ocid1.routetable.oc1..example",
            "security_list_ids": ["ocid1.securitylist.oc1..example"],
            "prohibit_public_ip_on_vnic": True,
            "wait": True,
        },
        client=types.SimpleNamespace(create_subnet=create_subnet),
    )
    monkeypatch.setattr(
        subnet_module,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )
    monkeypatch.setattr(
        sys.modules[instance.get_mutation_result.__module__],
        "wait_for_resource",
        lambda module, client, get_fn, resource_id, target_states, **kwargs: FakeModel(
            id=resource_id,
            lifecycle_state="AVAILABLE",
        ),
    )

    resource = instance.create_resource()

    assert create_calls[0].display_name == "example-subnet"
    assert create_calls[0].route_table_id == "ocid1.routetable.oc1..example"
    assert create_calls[0].security_list_ids == ["ocid1.securitylist.oc1..example"]
    assert create_calls[0].prohibit_public_ip_on_vnic is True
    assert resource.id == "ocid1.subnet.oc1..example"
    assert resource.lifecycle_state == "AVAILABLE"


def test_update_resource_uses_update_subnet_details_and_waits(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    subnet_module = load_collection_module("oci_subnet")
    update_calls = []
    response = FakeResponse(
        data=FakeModel(id="ocid1.subnet.oc1..example"),
    )

    def update_subnet(subnet_id, update_subnet_details):
        update_calls.append((subnet_id, update_subnet_details))
        return response

    resource = FakeModel(id="ocid1.subnet.oc1..example")
    instance = make_subnet_module(
        subnet_module,
        {
            "display_name": "updated-subnet",
            "route_table_id": "ocid1.routetable.oc1..updated",
            "security_list_ids": ["ocid1.securitylist.oc1..updated"],
            "freeform_tags": {"env": "prod"},
            "wait": True,
        },
        client=types.SimpleNamespace(update_subnet=update_subnet),
    )
    monkeypatch.setattr(
        subnet_module,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )
    monkeypatch.setattr(
        sys.modules[instance.get_mutation_result.__module__],
        "wait_for_resource",
        lambda module, client, get_fn, resource_id, target_states, **kwargs: FakeModel(
            id=resource_id,
            lifecycle_state="AVAILABLE",
        ),
    )

    updated_resource = instance.update_resource(resource)

    assert update_calls[0][0] == "ocid1.subnet.oc1..example"
    assert update_calls[0][1].display_name == "updated-subnet"
    assert update_calls[0][1].route_table_id == "ocid1.routetable.oc1..updated"
    assert update_calls[0][1].security_list_ids == ["ocid1.securitylist.oc1..updated"]
    assert updated_resource.id == "ocid1.subnet.oc1..example"


