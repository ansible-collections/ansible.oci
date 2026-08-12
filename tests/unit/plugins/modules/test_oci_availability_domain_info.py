from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from conftest import (
    DummyModule,
    ExitJsonCalled,
    FailJsonCalled,
    FakeModel,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
)


def test_main_builds_optional_compartment_id_arg(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_availability_domain_info")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        return DummyModule({})

    class FakeAvailabilityDomainInfoModule:
        def __init__(self, module):
            self.module = module

        def execute_info_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(
        module_obj,
        "OciAvailabilityDomainInfoModule",
        FakeAvailabilityDomainInfoModule,
    )

    module_obj.main()

    assert captured["run_called"] is True
    assert "compartment_id" in captured["argument_spec"]
    assert "required" not in captured["argument_spec"]["compartment_id"]


def test_fetch_resources_uses_explicit_compartment_id(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_availability_domain_info")
    paginate_calls = []
    instance = make_module_instance(
        info_module,
        "OciAvailabilityDomainInfoModule",
        {"compartment_id": "ocid1.compartment.oc1..example"},
        client=types.SimpleNamespace(
            list_availability_domains="list_method",
            # No base_client, to prove the explicit value short-circuits
            # tenancy resolution entirely.
        ),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: paginate_calls.append((list_fn, kwargs)) or [],
    )

    resources = instance.fetch_resources()

    assert resources == []
    assert paginate_calls == [
        ("list_method", {"compartment_id": "ocid1.compartment.oc1..example"})
    ]


def test_fetch_resources_defaults_compartment_id_to_tenancy(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_availability_domain_info")
    paginate_calls = []
    instance = make_module_instance(
        info_module,
        "OciAvailabilityDomainInfoModule",
        {},
        client=types.SimpleNamespace(
            list_availability_domains="list_method",
            base_client=types.SimpleNamespace(
                config={"tenancy": "ocid1.tenancy.oc1..fromconfig"}
            ),
        ),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: paginate_calls.append((list_fn, kwargs)) or [],
    )

    resources = instance.fetch_resources()

    assert resources == []
    assert paginate_calls == [
        ("list_method", {"compartment_id": "ocid1.tenancy.oc1..fromconfig"})
    ]


def test_fetch_resources_fails_without_compartment_id_or_tenancy(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_availability_domain_info")
    instance = make_module_instance(
        info_module,
        "OciAvailabilityDomainInfoModule",
        {},
        client=types.SimpleNamespace(list_availability_domains="list_method"),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: pytest.fail(
            "list_all_resources should not be called"
        ),
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.fetch_resources()

    assert "compartment_id" in exc_info.value.payload["msg"]


def test_run_returns_availability_domains_key(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_availability_domain_info")
    resource = FakeModel(
        name="Uocm:PHX-AD-1",
        id="ocid1.availabilitydomain.oc1..example",
        compartment_id="ocid1.tenancy.oc1..example",
    )
    instance = make_module_instance(
        module_obj,
        "OciAvailabilityDomainInfoModule",
        {"compartment_id": "ocid1.tenancy.oc1..example"},
    )
    monkeypatch.setattr(instance, "fetch_resources", lambda: [resource])

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()

    assert exc_info.value.payload == {
        "changed": False,
        "availability_domains": [
            {
                "name": "Uocm:PHX-AD-1",
                "id": "ocid1.availabilitydomain.oc1..example",
                "compartment_id": "ocid1.tenancy.oc1..example",
            }
        ],
    }
