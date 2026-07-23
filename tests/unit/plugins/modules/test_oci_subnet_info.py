import sys
import types

import pytest

from conftest import load_collection_module


class ExitJsonCalled(Exception):
    def __init__(self, payload):
        self.payload = payload


class DummyModule:
    def __init__(self, params=None):
        self.params = params or {}
        self.check_mode = False

    def exit_json(self, **kwargs):
        raise ExitJsonCalled(kwargs)


class FakeModel:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeResponse:
    def __init__(self, data=None):
        self.data = data


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
    )

    monkeypatch.setitem(sys.modules, "oci", oci_module)
    monkeypatch.setitem(sys.modules, "oci.exceptions", exceptions_module)

    return oci_module, ServiceError


def make_info_module(module_obj, params, client=None):
    instance = object.__new__(module_obj.OciSubnetInfoModule)
    instance.module = DummyModule(params)
    instance.client = client or types.SimpleNamespace()
    return instance


def test_list_resources_uses_list_filters(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_subnet_info")
    paginate_calls = []
    instance = make_info_module(
        info_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "display_name": "example-subnet",
            "lifecycle_state": "AVAILABLE",
        },
        client=types.SimpleNamespace(list_subnets="list_subnets_method"),
    )
    monkeypatch.setattr(
        instance,
        "paginate",
        lambda list_fn, **kwargs: paginate_calls.append((list_fn, kwargs)) or [],
    )

    resources = instance.list_resources()

    assert resources == []
    assert paginate_calls == [
        (
            "list_subnets_method",
            {
                "compartment_id": "ocid1.compartment.oc1..example",
                "vcn_id": "ocid1.vcn.oc1..example",
                "display_name": "example-subnet",
                "lifecycle_state": "AVAILABLE",
            },
        )
    ]


def test_list_resources_prefers_subnet_id_lookup(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_subnet_info")
    instance = make_info_module(
        info_module,
        {
            "subnet_id": "ocid1.subnet.oc1..example",
        },
        client=types.SimpleNamespace(
            get_subnet=lambda subnet_id: FakeResponse(
                data=FakeModel(id=subnet_id, display_name="example-subnet")
            )
        ),
    )
    monkeypatch.setattr(
        instance,
        "paginate",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("paginate should not be called")
        ),
    )
    monkeypatch.setattr(
        sys.modules[instance.get_resource_by_id.__module__],
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    resources = instance.list_resources()

    assert len(resources) == 1
    assert resources[0].id == "ocid1.subnet.oc1..example"


def test_list_resources_returns_empty_list_on_404(monkeypatch):
    _, ServiceError = install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_subnet_info")
    instance = make_info_module(
        info_module,
        {
            "subnet_id": "ocid1.subnet.oc1..missing",
        },
        client=types.SimpleNamespace(
            get_subnet=lambda subnet_id: (_ for _ in ()).throw(ServiceError(404, "missing"))
        ),
    )
    monkeypatch.setattr(
        sys.modules[instance.get_resource_by_id.__module__],
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    assert instance.list_resources() == []


def test_run_returns_subnets_results_key(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_subnet_info")
    instance = make_info_module(
        info_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "display_name": "example-subnet",
        },
    )
    monkeypatch.setattr(
        instance,
        "list_resources",
        lambda: [
            FakeModel(
                id="ocid1.subnet.oc1..example",
                display_name="example-subnet",
                lifecycle_state="AVAILABLE",
                vcn_id="ocid1.vcn.oc1..example",
            )
        ],
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.run()

    assert exc_info.value.payload == {
        "changed": False,
        "subnets": [
            {
                "id": "ocid1.subnet.oc1..example",
                "lifecycle_state": "AVAILABLE",
                "vcn_id": "ocid1.vcn.oc1..example",
            }
        ],
    }
