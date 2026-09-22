from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from .conftest import (
    DummyModule,
    FakeModel,
    FakeResponse,
    FailJsonCalled,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(
        monkeypatch,
        model_names=("CreateDomainDetails", "UpdateDomainDetails"),
    )


def make_domain_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciDomainModule",
        params,
        client=client,
    )


def test_main_exposes_domain_arguments(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_domain")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule()

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(
        module_obj,
        "OciDomainModule",
        lambda module: types.SimpleNamespace(execute_resource_module=lambda: None),
    )

    module_obj.main()

    assert captured["argument_spec"]["domain_id"] == {"type": "str"}
    assert captured["argument_spec"]["home_region"] == {"type": "str"}
    assert captured["argument_spec"]["license_type"] == {"type": "str"}
    assert captured["supports_check_mode"] is True


def test_build_create_domain_details_includes_supported_fields(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_domain")

    details = module_obj.build_create_domain_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-domain",
            "description": "Example domain",
            "home_region": "us-ashburn-1",
            "license_type": "free",
            "is_hidden_on_login": True,
            "admin_email": "admin@example.com",
            "freeform_tags": {"environment": "test"},
        }
    )

    assert details.compartment_id == "ocid1.compartment.oc1..example"
    assert details.display_name == "example-domain"
    assert details.description == "Example domain"
    assert details.home_region == "us-ashburn-1"
    assert details.license_type == "free"
    assert details.is_hidden_on_login is True
    assert details.admin_email == "admin@example.com"
    assert details.freeform_tags == {"environment": "test"}
    assert not hasattr(details, "admin_first_name")


def test_create_resource_waits_for_iam_work_request_and_domain(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_domain")
    calls = []

    def create_domain(create_domain_details):
        calls.append(create_domain_details)
        return FakeResponse(headers={"opc-work-request-id": "work-request"})

    instance = make_domain_module(
        module_obj,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-domain",
            "description": "Example domain",
            "home_region": "us-ashburn-1",
            "license_type": "free",
            "wait": True,
        },
        client=types.SimpleNamespace(
            create_domain=create_domain,
            get_iam_work_request=lambda work_request_id: None,
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "wait_for_work_request",
        lambda client, work_request_id, **kwargs: FakeModel(
            resources=[FakeModel(identifier="ocid1.domain.oc1..example")]
        ),
    )
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda domain_id, states: FakeModel(id=domain_id, lifecycle_state="ACTIVE"),
    )

    resource = instance.create_resource()

    assert calls[0].display_name == "example-domain"
    assert resource.id == "ocid1.domain.oc1..example"


def test_update_resource_uses_iam_work_request(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_domain")
    update_calls = []

    def update_domain(domain_id, update_domain_details):
        update_calls.append((domain_id, update_domain_details))
        return FakeResponse(headers={"opc-work-request-id": "work-request"})

    instance = make_domain_module(
        module_obj,
        {"description": "Updated", "wait": True},
        client=types.SimpleNamespace(
            update_domain=update_domain,
            get_iam_work_request=lambda work_request_id: None,
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "wait_for_work_request",
        lambda *args, **kwargs: FakeModel(resources=[]),
    )
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda domain_id, states: FakeModel(id=domain_id, lifecycle_state="ACTIVE"),
    )

    resource = instance.update_resource(
        FakeModel(id="ocid1.domain.oc1..example", description="Old")
    )

    assert update_calls[0][0] == "ocid1.domain.oc1..example"
    assert update_calls[0][1].description == "Updated"
    assert resource.id == "ocid1.domain.oc1..example"


def test_delete_resource_deactivates_active_domain_before_deleting(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_domain")
    calls = []

    def deactivate_domain(domain_id):
        calls.append(("deactivate", domain_id))
        return FakeResponse(headers={"opc-work-request-id": "deactivate-request"})

    def delete_domain(domain_id):
        calls.append(("delete", domain_id))
        return FakeResponse(headers={"opc-work-request-id": "delete-request"})

    instance = make_domain_module(
        module_obj,
        {"wait": True},
        client=types.SimpleNamespace(
            deactivate_domain=deactivate_domain,
            delete_domain=delete_domain,
            get_iam_work_request=lambda work_request_id: None,
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "wait_for_work_request",
        lambda *args, **kwargs: FakeModel(resources=[]),
    )

    instance.delete_resource(
        FakeModel(id="ocid1.domain.oc1..example", lifecycle_state="ACTIVE")
    )

    assert calls == [
        ("deactivate", "ocid1.domain.oc1..example"),
        ("delete", "ocid1.domain.oc1..example"),
    ]


def test_create_requires_domain_create_fields(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_domain")
    instance = make_domain_module(module_obj, {"name": "example-domain"})

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "compartment_id" in exc_info.value.payload["msg"]
    assert "license_type" in exc_info.value.payload["msg"]


def test_create_only_domain_fields_are_immutable(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_domain")
    instance = make_domain_module(module_obj, {"home_region": "us-phoenix-1"})

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(
            FakeModel(id="ocid1.domain.oc1..example", home_region="us-ashburn-1")
        )

    assert "home_region" in exc_info.value.payload["msg"]
