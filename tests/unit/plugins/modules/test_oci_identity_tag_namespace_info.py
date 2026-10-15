from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


def install_fake_oci(monkeypatch):
    """Install the fake OCI client used by namespace info tests."""
    return shared_install_fake_oci(monkeypatch)


def make_namespace_info_module(module_obj, params, client=None):
    """Build an info helper without creating a live OCI client."""
    return make_module_instance(
        module_obj,
        "OciIdentityTagNamespaceInfoModule",
        params,
        client=client,
    )


def test_main_requires_namespace_id_or_compartment_id(monkeypatch):
    """Verify info arguments require an ID or compartment."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_identity_tag_namespace_info")
    captured = {}

    def fake_ansible_module(**kwargs):
        """Test fake ansible module."""
        captured["required_one_of"] = kwargs["required_one_of"]
        return DummyModule({})

    class FakeInfoModule:
        def __init__(self, module):
            """Test   init  ."""
            self.module = module

        def execute_info_module(self):
            """Test execute info module."""
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciIdentityTagNamespaceInfoModule", FakeInfoModule)
    module_obj.main()
    assert captured["run_called"] is True
    assert captured["required_one_of"] == [["tag_namespace_id", "compartment_id"]]


def test_get_by_id_takes_priority(monkeypatch):
    """Verify ID lookup takes priority over list filters."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_identity_tag_namespace_info")
    calls = []
    instance = make_namespace_info_module(
        module_obj,
        {
            "tag_namespace_id": "ocid1.tagnamespace.oc1..example",
            "compartment_id": "ignored",
            "lifecycle_state": "active",
        },
        client=types.SimpleNamespace(
            get_tag_namespace=lambda **kwargs: calls.append(kwargs)
            or FakeResponse(FakeModel(id=kwargs["tag_namespace_id"], name="Ops"))
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(instance, "list_all_resources", lambda *args, **kwargs: pytest.fail("unexpected list"))
    assert instance.fetch_resources()[0].name == "Ops"
    assert calls == [{"tag_namespace_id": "ocid1.tagnamespace.oc1..example"}]


def test_list_uses_normalized_filters_and_case_insensitive_name(monkeypatch):
    """Verify list filters use OCI casing and preserve namespace names."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_identity_tag_namespace_info")
    calls = []
    match = FakeModel(id="ns1", name="Operations")
    other = FakeModel(id="ns2", name="Security")
    instance = make_namespace_info_module(
        module_obj,
        {
            "compartment_id": "ocid1.tenancy.oc1..example",
            "include_subcompartments": False,
            "lifecycle_state": "inactive",
            "name": "operations",
        },
        client=types.SimpleNamespace(list_tag_namespaces="list_method"),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: calls.append((list_fn, kwargs)) or [match, other],
    )
    assert instance.fetch_resources() == [match]
    assert calls == [
        (
            "list_method",
            {
                "compartment_id": "ocid1.tenancy.oc1..example",
                "include_subcompartments": False,
                "lifecycle_state": "INACTIVE",
            },
        )
    ]


def test_info_module_serializes_results(monkeypatch):
    """Verify info results use the namespace list key."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_identity_tag_namespace_info")
    instance = make_namespace_info_module(
        module_obj,
        {"compartment_id": "ocid1.tenancy.oc1..example"},
    )
    monkeypatch.setattr(instance, "fetch_resources", lambda: [FakeModel(id="ns", name="Ops")])
    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()
    assert exc_info.value.payload == {
        "changed": False,
        "tag_namespaces": [{"id": "ns", "name": "Ops"}],
    }


def test_get_by_id_returns_empty_list_on_404(monkeypatch):
    """Test that a missing namespace produces an empty info result."""
    service_error = install_fake_oci(monkeypatch)[1]
    module_obj = load_collection_module("oci_identity_tag_namespace_info")
    instance = make_namespace_info_module(module_obj, {})
    error = service_error(404, "not found")
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        raising(error),
    )
    assert instance.get_resource_by_id("missing", lambda **_kwargs: None) == []


def test_get_by_id_propagates_non_404_errors(monkeypatch):
    """Test that info lookup propagates service errors other than 404."""
    service_error = install_fake_oci(monkeypatch)[1]
    module_obj = load_collection_module("oci_identity_tag_namespace_info")
    instance = make_namespace_info_module(module_obj, {})
    error = service_error(500, "service failure")
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        raising(error),
    )
    with pytest.raises(service_error):
        instance.get_resource_by_id("ns", lambda **_kwargs: None)
