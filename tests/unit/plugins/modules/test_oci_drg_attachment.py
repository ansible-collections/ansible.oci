from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from conftest import (
    DummyModule,
    FakeModel,
    FakeResponse,
    FailJsonCalled,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)


DRG_ATTACHMENT_MODEL_NAMES = (
    "CreateDrgAttachmentDetails",
    "UpdateDrgAttachmentDetails",
)


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(
        monkeypatch,
        model_names=DRG_ATTACHMENT_MODEL_NAMES,
    )


def make_drg_attachment_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciDrgAttachmentModule",
        params,
        client=client,
    )


def test_main_exposes_expected_arguments(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_drg_attachment")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        return DummyModule({})

    class FakeDrgAttachmentModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciDrgAttachmentModule", FakeDrgAttachmentModule)

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["argument_spec"]["allow_duplicate_name"] == {
        "type": "bool",
        "default": False,
    }
    assert captured["argument_spec"]["name"] == {"type": "str"}
    assert captured["argument_spec"]["compartment_id"] == {"type": "str"}
    assert captured["argument_spec"]["drg_id"] == {"type": "str"}
    assert captured["argument_spec"]["vcn_id"] == {"type": "str"}
    assert captured["argument_spec"]["route_table_id"] == {"type": "str"}
    assert captured["argument_spec"]["drg_route_table_id"] == {"type": "str"}
    assert "network_details" not in captured["argument_spec"]


def test_build_create_drg_attachment_details_excludes_compartment_id(monkeypatch):
    install_fake_oci(monkeypatch)

    drg_attachment_module = load_collection_module("oci_drg_attachment")
    details = drg_attachment_module.build_create_drg_attachment_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "drg_id": "ocid1.drg.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-drg-attachment",
            "route_table_id": "ocid1.routetable.oc1..example",
            "drg_route_table_id": "ocid1.drgroutetable.oc1..example",
            "freeform_tags": {"env": "dev"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        }
    )

    assert isinstance(details, FakeModel)
    assert details.drg_id == "ocid1.drg.oc1..example"
    assert details.vcn_id == "ocid1.vcn.oc1..example"
    assert details.display_name == "example-drg-attachment"
    assert details.route_table_id == "ocid1.routetable.oc1..example"
    assert details.drg_route_table_id == "ocid1.drgroutetable.oc1..example"
    assert details.freeform_tags == {"env": "dev"}
    assert details.defined_tags == {"Operations": {"CostCenter": "42"}}
    # compartment_id is not part of CreateDrgAttachmentDetails and must not
    # end up in the actual create payload.
    assert not hasattr(details, "compartment_id")
    # network_details (the polymorphic field) is intentionally unused.
    assert not hasattr(details, "network_details")


def test_needs_update_returns_true_for_route_table_id_change(monkeypatch):
    install_fake_oci(monkeypatch)

    drg_attachment_module = load_collection_module("oci_drg_attachment")
    instance = make_drg_attachment_module(
        drg_attachment_module,
        {"route_table_id": "ocid1.routetable.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.drgattachment.oc1..example",
        route_table_id="ocid1.routetable.oc1..current",
    )

    assert instance.needs_update(resource) is True


def test_needs_update_returns_true_for_drg_route_table_id_change(monkeypatch):
    install_fake_oci(monkeypatch)

    drg_attachment_module = load_collection_module("oci_drg_attachment")
    instance = make_drg_attachment_module(
        drg_attachment_module,
        {"drg_route_table_id": "ocid1.drgroutetable.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.drgattachment.oc1..example",
        drg_route_table_id="ocid1.drgroutetable.oc1..current",
    )

    assert instance.needs_update(resource) is True


def test_needs_update_returns_true_for_name_change(monkeypatch):
    install_fake_oci(monkeypatch)

    drg_attachment_module = load_collection_module("oci_drg_attachment")
    instance = make_drg_attachment_module(
        drg_attachment_module,
        {"name": "updated-drg-attachment"},
    )
    resource = FakeModel(
        id="ocid1.drgattachment.oc1..example",
        display_name="current-drg-attachment",
    )

    assert instance.needs_update(resource) is True


def test_needs_update_rejects_drg_id_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    drg_attachment_module = load_collection_module("oci_drg_attachment")
    instance = make_drg_attachment_module(
        drg_attachment_module,
        {"drg_id": "ocid1.drg.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.drgattachment.oc1..example",
        drg_id="ocid1.drg.oc1..current",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "drg_id" in exc_info.value.payload["msg"]


def test_needs_update_rejects_vcn_id_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    drg_attachment_module = load_collection_module("oci_drg_attachment")
    instance = make_drg_attachment_module(
        drg_attachment_module,
        {"vcn_id": "ocid1.vcn.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.drgattachment.oc1..example",
        vcn_id="ocid1.vcn.oc1..current",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "vcn_id" in exc_info.value.payload["msg"]


def test_create_resource_uses_create_drg_attachment_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    drg_attachment_module = load_collection_module("oci_drg_attachment")
    create_calls = []
    response = FakeResponse(
        data=FakeModel(id="ocid1.drgattachment.oc1..example"),
    )

    def create_drg_attachment(create_drg_attachment_details):
        create_calls.append(create_drg_attachment_details)
        return response

    instance = make_drg_attachment_module(
        drg_attachment_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "drg_id": "ocid1.drg.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-drg-attachment",
            "wait": True,
        },
        client=types.SimpleNamespace(create_drg_attachment=create_drg_attachment),
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

    resource = instance.create_resource()

    assert create_calls[0].drg_id == "ocid1.drg.oc1..example"
    assert create_calls[0].vcn_id == "ocid1.vcn.oc1..example"
    assert create_calls[0].display_name == "example-drg-attachment"
    assert not hasattr(create_calls[0], "compartment_id")
    assert resource.id == "ocid1.drgattachment.oc1..example"
    assert resource.lifecycle_state == "AVAILABLE"


def test_update_resource_uses_update_drg_attachment_details_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    drg_attachment_module = load_collection_module("oci_drg_attachment")
    update_calls = []
    response = FakeResponse(
        data=FakeModel(id="ocid1.drgattachment.oc1..example"),
    )

    def update_drg_attachment(drg_attachment_id, update_drg_attachment_details):
        update_calls.append((drg_attachment_id, update_drg_attachment_details))
        return response

    resource = FakeModel(id="ocid1.drgattachment.oc1..example")
    instance = make_drg_attachment_module(
        drg_attachment_module,
        {
            "name": "updated-drg-attachment",
            "route_table_id": "ocid1.routetable.oc1..updated",
            "drg_route_table_id": "ocid1.drgroutetable.oc1..updated",
            "wait": True,
        },
        client=types.SimpleNamespace(update_drg_attachment=update_drg_attachment),
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

    assert update_calls[0][0] == "ocid1.drgattachment.oc1..example"
    assert update_calls[0][1].display_name == "updated-drg-attachment"
    assert update_calls[0][1].route_table_id == "ocid1.routetable.oc1..updated"
    assert update_calls[0][1].drg_route_table_id == "ocid1.drgroutetable.oc1..updated"
    assert updated_resource.id == "ocid1.drgattachment.oc1..example"


def test_delete_resource_waits_for_detached_state(monkeypatch):
    install_fake_oci(monkeypatch)

    drg_attachment_module = load_collection_module("oci_drg_attachment")
    delete_calls = []
    response = FakeResponse(data=None)

    def delete_drg_attachment(drg_attachment_id):
        delete_calls.append(drg_attachment_id)
        return response

    resource = FakeModel(id="ocid1.drgattachment.oc1..example")
    instance = make_drg_attachment_module(
        drg_attachment_module,
        {"wait": True},
        client=types.SimpleNamespace(delete_drg_attachment=delete_drg_attachment),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )
    monkeypatch.setattr(
        instance,
        "_wait_for_drg_attachment_detached",
        lambda drg_attachment_id: None,
    )

    instance.delete_resource(resource)

    assert delete_calls == ["ocid1.drgattachment.oc1..example"]


def test_delete_resource_treats_404_as_already_detached(monkeypatch):
    _oci_module, ServiceError = install_fake_oci(monkeypatch)

    drg_attachment_module = load_collection_module("oci_drg_attachment")

    def delete_drg_attachment(drg_attachment_id):
        return FakeResponse(data=None)

    def get_missing_drg_attachment(**kwargs):
        raise ServiceError(404, "missing")

    resource = FakeModel(id="ocid1.drgattachment.oc1..example")
    instance = make_drg_attachment_module(
        drg_attachment_module,
        {"wait": True},
        client=types.SimpleNamespace(
            delete_drg_attachment=delete_drg_attachment,
            get_drg_attachment=get_missing_drg_attachment,
        ),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    result = instance.delete_resource(resource)

    assert result is None


def test_resolve_target_resource_treats_detached_as_not_found(monkeypatch):
    install_fake_oci(monkeypatch)

    drg_attachment_module = load_collection_module("oci_drg_attachment")
    instance = make_drg_attachment_module(
        drg_attachment_module,
        {"drg_attachment_id": "ocid1.drgattachment.oc1..example"},
    )
    monkeypatch.setattr(
        instance,
        "get_resource_by_id",
        lambda resource_id: FakeModel(
            id=resource_id,
            lifecycle_state="DETACHED",
        ),
    )

    assert instance.resolve_target_resource() is None


def test_create_required_fields_enforced(monkeypatch):
    install_fake_oci(monkeypatch)

    drg_attachment_module = load_collection_module("oci_drg_attachment")
    instance = make_drg_attachment_module(
        drg_attachment_module,
        {"name": "example-drg-attachment"},
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "Creating a DRG attachment requires" in exc_info.value.payload["msg"]
    assert "compartment_id" in exc_info.value.payload["msg"]
    assert "drg_id" in exc_info.value.payload["msg"]
    assert "vcn_id" in exc_info.value.payload["msg"]


def test_name_lookup_scope_requires_drg_and_vcn_id(monkeypatch):
    install_fake_oci(monkeypatch)

    drg_attachment_module = load_collection_module("oci_drg_attachment")
    instance = make_drg_attachment_module(
        drg_attachment_module,
        {
            "name": "example-drg-attachment",
            "compartment_id": "ocid1.compartment.oc1..example",
        },
        client=types.SimpleNamespace(list_drg_attachments="list_drg_attachments"),
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.find_resources_by_name()

    assert "drg_id" in exc_info.value.payload["msg"]
    assert "vcn_id" in exc_info.value.payload["msg"]
