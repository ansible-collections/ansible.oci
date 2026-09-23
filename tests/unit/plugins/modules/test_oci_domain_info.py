from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from .conftest import (
    ExitJsonCalled,
    FakeModel,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(monkeypatch)


def test_main_requires_domain_id_or_compartment_id(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_domain_info")
    captured = {}

    class FakeAnsibleModule:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(module_obj, "AnsibleModule", FakeAnsibleModule)
    monkeypatch.setattr(
        module_obj,
        "OciDomainInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )

    module_obj.main()

    assert captured["required_one_of"] == [["domain_id", "compartment_id"]]
    assert captured["argument_spec"]["domain_id"] == {"type": "str"}
    assert captured["argument_spec"]["lifecycle_state"] == {"type": "str"}


def test_fetch_resources_lists_domains_with_filters(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_domain_info")
    listed = [
        FakeModel(id="ocid1.domain.oc1..one", display_name="example-domain"),
        FakeModel(id="ocid1.domain.oc1..two", display_name="other-domain"),
    ]
    calls = []

    def list_domains(**kwargs):
        calls.append(kwargs)
        return types.SimpleNamespace(data=listed)

    instance = make_module_instance(
        module_obj,
        "OciDomainInfoModule",
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-domain",
            "lifecycle_state": "ACTIVE",
        },
        client=types.SimpleNamespace(list_domains=list_domains),
    )
    monkeypatch.setattr(instance, "list_all_resources", lambda fn, **kwargs: fn(**kwargs).data)

    resources = instance.fetch_resources()

    assert calls == [
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "lifecycle_state": "ACTIVE",
        }
    ]
    assert resources == [listed[0]]


def test_execute_info_module_serializes_domains(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_domain_info")
    instance = make_module_instance(
        module_obj,
        "OciDomainInfoModule",
        {"domain_id": "ocid1.domain.oc1..example"},
    )
    monkeypatch.setattr(
        instance,
        "fetch_resources",
        lambda: [FakeModel(id="ocid1.domain.oc1..example", display_name="example-domain")],
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()

    assert exc_info.value.payload == {
        "changed": False,
        "domains": [{"id": "ocid1.domain.oc1..example", "name": "example-domain"}],
    }
