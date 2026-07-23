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
    instance = object.__new__(module_obj.OciNetworkVcnInfoModule)
    instance.module = DummyModule(params)
    instance.client = client or types.SimpleNamespace()
    return instance


def test_list_resources_uses_list_filters(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_network_vcn_info")
    paginate_calls = []
    instance = make_info_module(
        info_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "display_name": "example-vcn",
            "lifecycle_state": "AVAILABLE",
        },
        client=types.SimpleNamespace(list_vcns="list_vcns_method"),
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
            "list_vcns_method",
            {
                "compartment_id": "ocid1.compartment.oc1..example",
                "display_name": "example-vcn",
                "lifecycle_state": "AVAILABLE",
            },
        )
    ]


def test_list_resources_prefers_vcn_id_lookup(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_network_vcn_info")
    instance = make_info_module(
        info_module,
        {
            "vcn_id": "ocid1.vcn.oc1..example",
        },
        client=types.SimpleNamespace(
            get_vcn=lambda vcn_id: FakeResponse(
                data=FakeModel(id=vcn_id, display_name="example-vcn")
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
        info_module,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    resources = instance.list_resources()

    assert len(resources) == 1
    assert resources[0].id == "ocid1.vcn.oc1..example"


def test_list_resources_returns_empty_list_on_404(monkeypatch):
    _, ServiceError = install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_network_vcn_info")
    instance = make_info_module(
        info_module,
        {
            "vcn_id": "ocid1.vcn.oc1..missing",
        },
        client=types.SimpleNamespace(
            get_vcn=lambda vcn_id: (_ for _ in ()).throw(ServiceError(404, "missing"))
        ),
    )
    monkeypatch.setattr(
        info_module,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    assert instance.list_resources() == []


def test_run_returns_vcns_results_key(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_network_vcn_info")
    instance = make_info_module(
        info_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "display_name": "example-vcn",
        },
    )
    monkeypatch.setattr(
        instance,
        "list_resources",
        lambda: [
            FakeModel(
                id="ocid1.vcn.oc1..example",
                display_name="example-vcn",
                lifecycle_state="AVAILABLE",
            )
        ],
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.run()

    assert exc_info.value.payload == {
        "changed": False,
        "vcns": [
            {
                "id": "ocid1.vcn.oc1..example",
                "lifecycle_state": "AVAILABLE",
            }
        ],
    }
