import sys
import types

import pytest

from conftest import load_collection_module


class FailJsonCalled(Exception):
    def __init__(self, payload):
        self.payload = payload


class ExitJsonCalled(Exception):
    def __init__(self, payload):
        self.payload = payload


class DummyModule:
    def __init__(self, params=None, check_mode=False):
        self.params = params or {}
        self.check_mode = check_mode

    def fail_json(self, **kwargs):
        raise FailJsonCalled(kwargs)

    def exit_json(self, **kwargs):
        raise ExitJsonCalled(kwargs)


class FakeModel:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeResponse:
    def __init__(self, data=None, headers=None):
        self.data = data
        self.headers = headers or {}


class FakeVirtualNetworkClient:
    pass


def install_fake_oci(monkeypatch):
    oci_module = types.ModuleType("oci")
    exceptions_module = types.ModuleType("oci.exceptions")

    class ServiceError(Exception):
        def __init__(self, status, message="service error"):
            super().__init__(message)
            self.status = status
            self.message = message

    exceptions_module.ServiceError = ServiceError
    oci_module.exceptions = exceptions_module
    oci_module.core = types.SimpleNamespace(
        VirtualNetworkClient=FakeVirtualNetworkClient,
        models=types.SimpleNamespace(
            CreateSubnetDetails=FakeModel,
            UpdateSubnetDetails=FakeModel,
        ),
    )

    monkeypatch.setitem(sys.modules, "oci", oci_module)
    monkeypatch.setitem(sys.modules, "oci.exceptions", exceptions_module)

    return oci_module, ServiceError


def make_subnet_module(module_obj, params, client=None):
    instance = object.__new__(module_obj.OciSubnetModule)
    instance.module = DummyModule(params)
    instance.client = client or types.SimpleNamespace()
    instance.check_mode = False
    return instance


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


def test_get_resource_prefers_subnet_id_lookup(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    subnet_module = load_collection_module("oci_subnet")
    get_calls = []

    def get_subnet(subnet_id):
        get_calls.append(subnet_id)
        return FakeResponse(data=FakeModel(id=subnet_id))

    instance = make_subnet_module(
        subnet_module,
        {"subnet_id": "ocid1.subnet.oc1..example"},
        client=types.SimpleNamespace(get_subnet=get_subnet),
    )
    monkeypatch.setattr(
        subnet_module,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    resource = instance.get_resource()

    assert resource.id == "ocid1.subnet.oc1..example"
    assert get_calls == ["ocid1.subnet.oc1..example"]


def test_get_resource_returns_none_without_subnet_id(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    subnet_module = load_collection_module("oci_subnet")
    instance = make_subnet_module(
        subnet_module,
        {
            "display_name": "example-subnet",
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
        },
    )

    assert instance.get_resource() is None


def test_run_fails_when_present_uses_missing_subnet_id(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    subnet_module = load_collection_module("oci_subnet")
    instance = make_subnet_module(
        subnet_module,
        {
            "state": "present",
            "subnet_id": "ocid1.subnet.oc1..missing",
        },
    )
    monkeypatch.setattr(instance, "get_resource", lambda: None)

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.run()

    assert "No subnet was found for subnet_id=" in exc_info.value.payload["msg"]
    assert "Create the subnet without subnet_id" in exc_info.value.payload["msg"]


def test_run_fails_when_absent_omits_subnet_id(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    subnet_module = load_collection_module("oci_subnet")
    instance = make_subnet_module(
        subnet_module,
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

    assert "Deleting a subnet requires subnet_id" in exc_info.value.payload["msg"]


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


def test_delete_resource_fails_cleanly_when_dependency_exists(monkeypatch):
    _, ServiceError = install_fake_oci(monkeypatch)

    subnet_module = load_collection_module("oci_subnet")
    resource = FakeModel(id="ocid1.subnet.oc1..example")

    def delete_subnet(subnet_id):
        raise ServiceError(409, "VNIC dependencies still exist")

    instance = make_subnet_module(
        subnet_module,
        {"wait": True},
        client=types.SimpleNamespace(delete_subnet=delete_subnet),
    )
    monkeypatch.setattr(
        sys.modules[instance.delete_resource_and_wait.__module__],
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.delete_resource(resource)

    assert "dependent resources" in exc_info.value.payload["msg"]


def test_run_check_mode_create_fails_when_required_fields_missing(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    subnet_module = load_collection_module("oci_subnet")
    instance = make_subnet_module(
        subnet_module,
        {
            "state": "present",
            "display_name": "example-subnet",
        },
    )
    instance.check_mode = True
    monkeypatch.setattr(instance, "get_resource", lambda: None)

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.run()

    assert "Creating a subnet requires" in exc_info.value.payload["msg"]


def test_run_check_mode_create_reports_changed_without_create(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    subnet_module = load_collection_module("oci_subnet")
    instance = make_subnet_module(
        subnet_module,
        {
            "state": "present",
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "cidr_block": "10.0.1.0/24",
            "display_name": "example-subnet",
        },
    )
    instance.check_mode = True
    monkeypatch.setattr(instance, "get_resource", lambda: None)
    monkeypatch.setattr(
        instance,
        "create_resource",
        lambda: (_ for _ in ()).throw(AssertionError("create_resource should not be called")),
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.run()

    assert exc_info.value.payload == {"changed": True}


def test_run_check_mode_update_reports_changed_when_tags_differ(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    subnet_module = load_collection_module("oci_subnet")
    resource = FakeModel(
        id="ocid1.subnet.oc1..example",
        display_name="example-subnet",
        lifecycle_state="AVAILABLE",
        freeform_tags={"env": "dev"},
        route_table_id="ocid1.routetable.oc1..current",
    )
    instance = make_subnet_module(
        subnet_module,
        {
            "state": "present",
            "display_name": "example-subnet",
            "freeform_tags": {"env": "prod"},
        },
    )
    instance.check_mode = True
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


def test_run_check_mode_delete_reports_changed_without_delete(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    subnet_module = load_collection_module("oci_subnet")
    resource = FakeModel(
        id="ocid1.subnet.oc1..example",
        lifecycle_state="AVAILABLE",
    )
    instance = make_subnet_module(
        subnet_module,
        {
            "state": "absent",
            "subnet_id": "ocid1.subnet.oc1..example",
        },
    )
    instance.check_mode = True
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
