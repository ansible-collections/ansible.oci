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


VOLUME_ATTACHMENT_MODEL_NAMES = (
    "AttachIScsiVolumeDetails",
    "AttachParavirtualizedVolumeDetails",
)


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(
        monkeypatch,
        model_names=VOLUME_ATTACHMENT_MODEL_NAMES,
    )


def make_volume_attachment_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciVolumeAttachmentModule",
        params,
        client=client,
    )


def test_main_exposes_expected_arguments(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_attachment")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        captured["mutually_exclusive"] = kwargs.get("mutually_exclusive")
        return DummyModule({})

    class FakeVolumeAttachmentModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(
        module_obj, "OciVolumeAttachmentModule", FakeVolumeAttachmentModule
    )

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["argument_spec"]["name"] == {"type": "str"}
    assert captured["argument_spec"]["compartment_id"] == {"type": "str"}
    assert captured["argument_spec"]["instance_id"] == {"type": "str"}
    assert captured["argument_spec"]["volume_id"] == {"type": "str"}
    assert captured["argument_spec"]["volume_attachment_id"] == {"type": "str"}
    assert captured["argument_spec"]["type"] == {
        "type": "str",
        "choices": ["iscsi", "paravirtualized"],
    }
    assert captured["argument_spec"]["device"] == {"type": "str"}
    assert captured["argument_spec"]["read_only"] == {"type": "bool"}
    assert captured["argument_spec"]["shareable"] == {"type": "bool"}
    assert captured["argument_spec"]["use_chap"] == {"type": "bool"}
    assert captured["argument_spec"]["encryption_in_transit_type"] == {
        "type": "str",
        "choices": ["none", "bm_encryption_in_transit"],
    }
    assert captured["argument_spec"]["pv_encryption_in_transit_enabled"] == {
        "type": "bool",
    }
    assert captured["mutually_exclusive"] == [
        ("use_chap", "pv_encryption_in_transit_enabled"),
        ("encryption_in_transit_type", "pv_encryption_in_transit_enabled"),
    ]
    # The is_-prefixed OCI field names must not leak into the module parameters.
    assert "is_read_only" not in captured["argument_spec"]
    assert "is_shareable" not in captured["argument_spec"]
    # Volume attachments do not support tags.
    assert "freeform_tags" not in captured["argument_spec"]
    assert "defined_tags" not in captured["argument_spec"]


def test_build_attach_volume_details_defaults_to_paravirtualized(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_attachment")
    details = module_obj.build_attach_volume_details(
        {
            "instance_id": "ocid1.instance.oc1..example",
            "volume_id": "ocid1.volume.oc1..example",
            "name": "example-attachment",
            "device": "/dev/oracleoci/oraclevdb",
            "read_only": True,
            "shareable": None,
            "pv_encryption_in_transit_enabled": True,
        }
    )

    assert isinstance(details, FakeModel)
    assert details.instance_id == "ocid1.instance.oc1..example"
    assert details.volume_id == "ocid1.volume.oc1..example"
    assert details.display_name == "example-attachment"
    assert details.device == "/dev/oracleoci/oraclevdb"
    # The friendly parameter names map to OCI's is_-prefixed model fields.
    assert details.is_read_only is True
    assert details.is_pv_encryption_in_transit_enabled is True
    # compartment_id is never part of the attach payload.
    assert not hasattr(details, "compartment_id")
    # unset optional fields are omitted.
    assert not hasattr(details, "is_shareable")


def test_build_attach_volume_details_iscsi_uppercases_encryption(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_attachment")
    details = module_obj.build_attach_volume_details(
        {
            "type": "iscsi",
            "instance_id": "ocid1.instance.oc1..example",
            "volume_id": "ocid1.volume.oc1..example",
            "name": "example-attachment",
            "use_chap": True,
            "encryption_in_transit_type": "bm_encryption_in_transit",
        }
    )

    assert isinstance(details, FakeModel)
    assert details.use_chap is True
    assert details.encryption_in_transit_type == "BM_ENCRYPTION_IN_TRANSIT"
    # paravirtualized-only field is not present on an iSCSI attachment.
    assert not hasattr(details, "is_pv_encryption_in_transit_enabled")


def test_needs_update_returns_false_when_fields_match(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_attachment")
    instance = make_volume_attachment_module(
        module_obj,
        {"name": "example-attachment"},
    )
    resource = FakeModel(
        id="ocid1.volumeattachment.oc1..example",
        display_name="example-attachment",
    )

    assert instance.needs_update(resource) is False


def test_needs_update_rejects_instance_id_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_attachment")
    instance = make_volume_attachment_module(
        module_obj,
        {"instance_id": "ocid1.instance.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.volumeattachment.oc1..example",
        instance_id="ocid1.instance.oc1..current",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "instance_id" in exc_info.value.payload["msg"]


def test_needs_update_rejects_volume_id_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_attachment")
    instance = make_volume_attachment_module(
        module_obj,
        {"volume_id": "ocid1.volume.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.volumeattachment.oc1..example",
        volume_id="ocid1.volume.oc1..current",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "volume_id" in exc_info.value.payload["msg"]


def test_needs_update_rejects_type_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_attachment")
    instance = make_volume_attachment_module(
        module_obj,
        {"type": "iscsi"},
    )
    resource = FakeModel(
        id="ocid1.volumeattachment.oc1..example",
        attachment_type="paravirtualized",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "type" in exc_info.value.payload["msg"]


def test_needs_update_omitted_type_does_not_fail_on_iscsi(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_attachment")
    instance = make_volume_attachment_module(module_obj, {})
    resource = FakeModel(
        id="ocid1.volumeattachment.oc1..example",
        attachment_type="iscsi",
    )

    assert instance.needs_update(resource) is False


def test_needs_update_rejects_read_only_device_and_shareable_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_attachment")
    resource = FakeModel(
        id="ocid1.volumeattachment.oc1..example",
        is_read_only=False,
        device="/dev/oracleoci/oraclevdb",
        is_shareable=False,
    )

    for params, field_name in (
        ({"read_only": True}, "read_only"),
        ({"device": "/dev/oracleoci/oraclevdc"}, "device"),
        ({"shareable": True}, "shareable"),
    ):
        instance = make_volume_attachment_module(module_obj, params)
        with pytest.raises(FailJsonCalled) as exc_info:
            instance.needs_update(resource)
        assert field_name in exc_info.value.payload["msg"]


def test_needs_update_rejects_pv_encryption_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_attachment")
    instance = make_volume_attachment_module(
        module_obj,
        {
            "type": "paravirtualized",
            "pv_encryption_in_transit_enabled": True,
        },
    )
    resource = FakeModel(
        id="ocid1.volumeattachment.oc1..example",
        attachment_type="paravirtualized",
        is_pv_encryption_in_transit_enabled=False,
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "pv_encryption_in_transit_enabled" in exc_info.value.payload["msg"]


def test_needs_update_rejects_use_chap_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_attachment")
    instance = make_volume_attachment_module(
        module_obj,
        {"type": "iscsi", "use_chap": True},
    )
    resource = FakeModel(
        id="ocid1.volumeattachment.oc1..example",
        attachment_type="iscsi",
        chap_username=None,
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "use_chap" in exc_info.value.payload["msg"]


def test_needs_update_use_chap_matches_existing_chap_username(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_attachment")
    instance = make_volume_attachment_module(
        module_obj,
        {"type": "iscsi", "use_chap": True},
    )
    resource = FakeModel(
        id="ocid1.volumeattachment.oc1..example",
        attachment_type="iscsi",
        chap_username="ocid1.user.oc1..chap",
    )

    assert instance.needs_update(resource) is False


def test_needs_update_rejects_encryption_in_transit_type_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_attachment")
    instance = make_volume_attachment_module(
        module_obj,
        {"type": "iscsi", "encryption_in_transit_type": "bm_encryption_in_transit"},
    )
    resource = FakeModel(
        id="ocid1.volumeattachment.oc1..example",
        attachment_type="iscsi",
        encryption_in_transit_type="NONE",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "encryption_in_transit_type" in exc_info.value.payload["msg"]


def test_needs_update_encryption_none_matches_uppercase_resource(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_attachment")
    instance = make_volume_attachment_module(
        module_obj,
        {"type": "iscsi", "encryption_in_transit_type": "none"},
    )
    resource = FakeModel(
        id="ocid1.volumeattachment.oc1..example",
        attachment_type="iscsi",
        encryption_in_transit_type="NONE",
    )

    assert instance.needs_update(resource) is False


def test_validate_rejects_iscsi_params_on_paravirtualized(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_attachment")
    with pytest.raises(FailJsonCalled) as exc_info:
        module_obj.validate_attachment_type_params(
            {"type": "paravirtualized", "use_chap": True},
            DummyModule({}).fail_json,
        )

    assert "use_chap" in exc_info.value.payload["msg"]
    assert "iscsi" in exc_info.value.payload["msg"]


def test_validate_rejects_pv_params_on_iscsi(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_attachment")
    with pytest.raises(FailJsonCalled) as exc_info:
        module_obj.validate_attachment_type_params(
            {"type": "iscsi", "pv_encryption_in_transit_enabled": True},
            DummyModule({}).fail_json,
        )

    assert "pv_encryption_in_transit_enabled" in exc_info.value.payload["msg"]


def test_validate_create_rejects_use_chap_when_type_omitted(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_attachment")
    instance = make_volume_attachment_module(
        module_obj,
        {
            "name": "example-attachment",
            "compartment_id": "ocid1.compartment.oc1..example",
            "instance_id": "ocid1.instance.oc1..example",
            "volume_id": "ocid1.volume.oc1..example",
            "use_chap": True,
        },
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "use_chap" in exc_info.value.payload["msg"]


def test_serialize_result_resource_omits_chap_credentials(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_attachment")
    instance = make_volume_attachment_module(module_obj, {})
    resource = FakeModel(
        id="ocid1.volumeattachment.oc1..example",
        display_name="example-attachment",
        attachment_type="iscsi",
        chap_username="iqn.user",
        chap_secret="super-secret",
        ipv4="10.0.0.12",
        iqn="iqn.2015-12.com.oracleiaas:example",
        port=3260,
    )

    result = instance.serialize_result_resource(resource)

    assert "chap_secret" not in result
    assert "chap_username" not in result
    assert result["ipv4"] == "10.0.0.12"
    assert result["name"] == "example-attachment"


def test_create_resource_uses_attach_volume_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_attachment")
    create_calls = []
    response = FakeResponse(
        data=FakeModel(id="ocid1.volumeattachment.oc1..example"),
    )

    def attach_volume(attach_volume_details):
        create_calls.append(attach_volume_details)
        return response

    instance = make_volume_attachment_module(
        module_obj,
        {
            "type": "paravirtualized",
            "compartment_id": "ocid1.compartment.oc1..example",
            "instance_id": "ocid1.instance.oc1..example",
            "volume_id": "ocid1.volume.oc1..example",
            "name": "example-attachment",
            "wait": True,
        },
        client=types.SimpleNamespace(attach_volume=attach_volume),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: FakeModel(
            id=resource_id,
            lifecycle_state="ATTACHED",
        ),
    )

    resource = instance.create_resource()

    assert create_calls[0].instance_id == "ocid1.instance.oc1..example"
    assert create_calls[0].volume_id == "ocid1.volume.oc1..example"
    assert create_calls[0].display_name == "example-attachment"
    assert not hasattr(create_calls[0], "compartment_id")
    assert resource.id == "ocid1.volumeattachment.oc1..example"
    assert resource.lifecycle_state == "ATTACHED"


def test_delete_resource_detaches_and_waits_for_detached_state(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_attachment")
    detach_calls = []
    response = FakeResponse(data=None)

    def detach_volume(volume_attachment_id):
        detach_calls.append(volume_attachment_id)
        return response

    resource = FakeModel(id="ocid1.volumeattachment.oc1..example")
    instance = make_volume_attachment_module(
        module_obj,
        {"wait": True},
        client=types.SimpleNamespace(detach_volume=detach_volume),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "_wait_for_volume_attachment_detached",
        lambda volume_attachment_id: None,
    )

    instance.delete_resource(resource)

    assert detach_calls == ["ocid1.volumeattachment.oc1..example"]


def test_delete_resource_treats_404_as_already_detached(monkeypatch):
    _oci_module, ServiceError = install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_attachment")

    def detach_volume(volume_attachment_id):
        return FakeResponse(data=None)

    def get_missing_volume_attachment(**kwargs):
        raise ServiceError(404, "missing")

    resource = FakeModel(id="ocid1.volumeattachment.oc1..example")
    instance = make_volume_attachment_module(
        module_obj,
        {"wait": True},
        client=types.SimpleNamespace(
            detach_volume=detach_volume,
            get_volume_attachment=get_missing_volume_attachment,
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    result = instance.delete_resource(resource)

    assert result is None


def test_resolve_target_resource_treats_detached_as_not_found(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_attachment")
    instance = make_volume_attachment_module(
        module_obj,
        {"volume_attachment_id": "ocid1.volumeattachment.oc1..example"},
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


def _make_instance_with_live_and_stale_detached_matches(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_attachment")
    instance = make_volume_attachment_module(
        module_obj,
        {
            "name": "example-attachment",
            "compartment_id": "ocid1.compartment.oc1..example",
            "instance_id": "ocid1.instance.oc1..example",
            "volume_id": "ocid1.volume.oc1..example",
        },
        client=types.SimpleNamespace(list_volume_attachments="list_volume_attachments"),
    )
    live_resource = FakeModel(
        id="ocid1.volumeattachment.oc1..live",
        display_name="example-attachment",
        lifecycle_state="ATTACHED",
    )
    stale_detached_resource = FakeModel(
        id="ocid1.volumeattachment.oc1..stale",
        display_name="example-attachment",
        lifecycle_state="DETACHED",
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: [live_resource, stale_detached_resource],
    )
    return instance, live_resource


def test_find_resources_by_name_excludes_detached_matches(monkeypatch):
    instance, live_resource = _make_instance_with_live_and_stale_detached_matches(
        monkeypatch
    )

    assert instance.find_resources_by_name() == [live_resource]


def test_resolve_resource_by_name_ignores_stale_detached_duplicate(monkeypatch):
    instance, live_resource = _make_instance_with_live_and_stale_detached_matches(
        monkeypatch
    )

    assert instance.resolve_target_resource() is live_resource


def test_create_required_fields_enforced(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_attachment")
    instance = make_volume_attachment_module(
        module_obj,
        {"name": "example-attachment"},
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "Creating a volume attachment requires" in exc_info.value.payload["msg"]
    assert "compartment_id" in exc_info.value.payload["msg"]
    assert "instance_id" in exc_info.value.payload["msg"]
    assert "volume_id" in exc_info.value.payload["msg"]


def test_name_lookup_scope_requires_instance_and_volume_id(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_attachment")
    instance = make_volume_attachment_module(
        module_obj,
        {
            "name": "example-attachment",
            "compartment_id": "ocid1.compartment.oc1..example",
        },
        client=types.SimpleNamespace(list_volume_attachments="list_volume_attachments"),
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.find_resources_by_name()

    assert "instance_id" in exc_info.value.payload["msg"]
    assert "volume_id" in exc_info.value.payload["msg"]
