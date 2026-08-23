from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from conftest import (
    DummyModule,
    FailJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)


IMAGE_MODEL_NAMES = (
    "CreateImageDetails",
    "UpdateImageDetails",
    "ImageSourceViaObjectStorageTupleDetails",
    "ImageSourceViaObjectStorageUriDetails",
)


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(
        monkeypatch,
        model_names=IMAGE_MODEL_NAMES,
    )


def make_image_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciImageModule",
        params,
        client=client,
    )


def test_main_exposes_expected_arguments(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_image")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        captured["mutually_exclusive"] = kwargs.get("mutually_exclusive")
        return DummyModule({})

    class FakeImageModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciImageModule", FakeImageModule)

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["argument_spec"]["image_id"] == {"type": "str"}
    assert captured["argument_spec"]["instance_id"] == {"type": "str"}
    assert captured["argument_spec"]["launch_mode"] == {
        "type": "str",
        "choices": ["native", "emulated", "paravirtualized"],
    }
    assert captured["argument_spec"]["name"] == {"type": "str"}
    assert captured["argument_spec"]["compartment_id"] == {"type": "str"}
    assert captured["argument_spec"]["source_uri"] == {"type": "str"}
    assert captured["argument_spec"]["operating_system"] == {
        "type": "str",
        "choices": [
            "almalinux",
            "centos",
            "debian",
            "generic_linux",
            "oracle_linux",
            "rhel",
            "rocky_linux",
            "suse",
            "ubuntu",
            "windows",
        ],
    }
    assert captured["argument_spec"]["operating_system_version"] == {"type": "str"}
    assert captured["argument_spec"]["source_image_type"] == {
        "type": "str",
        "choices": ["vmdk", "qcow2", "oci"],
    }
    assert captured["argument_spec"]["object_storage"]["type"] == "dict"
    assert captured["argument_spec"]["object_storage"]["options"]["namespace_name"] == {
        "type": "str",
        "required": True,
    }
    assert captured["argument_spec"]["object_storage"]["options"]["bucket_name"] == {
        "type": "str",
        "required": True,
    }
    assert captured["argument_spec"]["object_storage"]["options"]["object_name"] == {
        "type": "str",
        "required": True,
    }
    assert captured["mutually_exclusive"] == [
        ("instance_id", "object_storage", "source_uri"),
    ]
    assert captured["argument_spec"]["allow_duplicate_name"] == {
        "type": "bool",
        "default": False,
    }
    assert "display_name" not in captured["argument_spec"]


def test_build_create_image_details_includes_supported_fields(monkeypatch):
    install_fake_oci(monkeypatch)

    image_module = load_collection_module("oci_image")
    details = image_module.build_create_image_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "instance_id": "ocid1.instance.oc1..example",
            "name": "example-image",
            "launch_mode": "paravirtualized",
            "freeform_tags": {"env": "dev"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        }
    )

    assert isinstance(details, FakeModel)
    assert details.compartment_id == "ocid1.compartment.oc1..example"
    assert details.instance_id == "ocid1.instance.oc1..example"
    assert details.display_name == "example-image"
    # Ansible lowercase choice is normalized to the OCI wire constant.
    assert details.launch_mode == "PARAVIRTUALIZED"
    assert details.freeform_tags == {"env": "dev"}
    assert details.defined_tags == {"Operations": {"CostCenter": "42"}}
    assert not hasattr(details, "image_source_details")


def test_build_create_image_details_omits_unset_optional_fields(monkeypatch):
    install_fake_oci(monkeypatch)

    image_module = load_collection_module("oci_image")
    details = image_module.build_create_image_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "instance_id": "ocid1.instance.oc1..example",
            "name": "example-image",
        }
    )

    assert not hasattr(details, "launch_mode")
    assert not hasattr(details, "freeform_tags")
    assert not hasattr(details, "image_source_details")


def test_build_update_plan_maps_image_fields_to_update_model(monkeypatch):
    install_fake_oci(monkeypatch)

    image_module = load_collection_module("oci_image")
    instance = make_image_module(
        image_module,
        {"name": "updated-image"},
    )
    resource = FakeModel(
        id="ocid1.image.oc1..example",
        display_name="current-image",
    )

    update_plan = instance.build_update_plan(resource)

    assert update_plan["update_needed"] is True
    assert update_plan["update_model_fields"] == {"display_name": "updated-image"}
    assert update_plan["strategy_operations"] == []


def test_needs_update_ignores_create_only_instance_id(monkeypatch):
    install_fake_oci(monkeypatch)

    image_module = load_collection_module("oci_image")
    # Rerunning the create task (which supplies instance_id) against an existing
    # image must be a no-op: instance_id has no counterpart on the resource and
    # must not trigger a spurious immutable-field failure or update.
    instance = make_image_module(
        image_module,
        {
            "name": "current-image",
            "instance_id": "ocid1.instance.oc1..example",
        },
    )
    resource = FakeModel(
        id="ocid1.image.oc1..example",
        display_name="current-image",
    )

    assert instance.needs_update(resource) is False


def test_create_resource_uses_create_image_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    image_module = load_collection_module("oci_image")
    create_calls = []
    response = FakeResponse(data=FakeModel(id="ocid1.image.oc1..example"))

    def create_image(create_image_details):
        create_calls.append(create_image_details)
        return response

    instance = make_image_module(
        image_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "instance_id": "ocid1.instance.oc1..example",
            "name": "example-image",
            "wait": True,
        },
        client=types.SimpleNamespace(create_image=create_image),
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

    assert create_calls[0].instance_id == "ocid1.instance.oc1..example"
    assert create_calls[0].display_name == "example-image"
    assert resource.id == "ocid1.image.oc1..example"
    assert resource.lifecycle_state == "AVAILABLE"


def test_update_resource_uses_update_image_details_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    image_module = load_collection_module("oci_image")
    update_calls = []
    response = FakeResponse(data=FakeModel(id="ocid1.image.oc1..example"))

    def update_image(image_id, update_image_details):
        update_calls.append((image_id, update_image_details))
        return response

    resource = FakeModel(id="ocid1.image.oc1..example")
    instance = make_image_module(
        image_module,
        {
            "name": "updated-image",
            "freeform_tags": {"env": "prod"},
            "wait": True,
        },
        client=types.SimpleNamespace(update_image=update_image),
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

    assert update_calls[0][0] == "ocid1.image.oc1..example"
    assert update_calls[0][1].display_name == "updated-image"
    assert updated_resource.id == "ocid1.image.oc1..example"


def test_delete_resource_uses_delete_image_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    image_module = load_collection_module("oci_image")
    delete_calls = []
    response = FakeResponse(data=None)

    def delete_image(image_id):
        delete_calls.append(image_id)
        return response

    resource = FakeModel(id="ocid1.image.oc1..example")
    instance = make_image_module(
        image_module,
        {"wait": True},
        client=types.SimpleNamespace(delete_image=delete_image),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: None,
    )

    instance.delete_resource(resource)

    assert delete_calls == ["ocid1.image.oc1..example"]


def test_create_required_fields_enforced(monkeypatch):
    install_fake_oci(monkeypatch)

    image_module = load_collection_module("oci_image")
    instance = make_image_module(
        image_module,
        {"name": "example-image"},
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "Creating a image requires" in exc_info.value.payload["msg"]
    assert "compartment_id" in exc_info.value.payload["msg"]
    assert "instance_id" not in exc_info.value.payload["msg"]


def test_validate_create_request_requires_a_source(monkeypatch):
    install_fake_oci(monkeypatch)

    image_module = load_collection_module("oci_image")
    instance = make_image_module(
        image_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-image",
        },
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "instance_id, object_storage, or source_uri" in exc_info.value.payload["msg"]


def test_validate_create_request_rejects_import_fields_on_instance_capture(
    monkeypatch,
):
    install_fake_oci(monkeypatch)

    image_module = load_collection_module("oci_image")
    instance = make_image_module(
        image_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-image",
            "instance_id": "ocid1.instance.oc1..example",
            "operating_system": "oracle_linux",
        },
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "only valid when importing" in exc_info.value.payload["msg"]


def test_validate_create_request_requires_operating_system_for_import(monkeypatch):
    install_fake_oci(monkeypatch)

    image_module = load_collection_module("oci_image")
    instance = make_image_module(
        image_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-image",
            "source_uri": "https://objectstorage.example/n/ns/b/bucket/o/image.qcow2",
            "source_image_type": "qcow2",
        },
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "operating_system is required" in exc_info.value.payload["msg"]


def test_validate_create_request_requires_source_image_type_for_import(monkeypatch):
    install_fake_oci(monkeypatch)

    image_module = load_collection_module("oci_image")
    instance = make_image_module(
        image_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-image",
            "source_uri": "https://objectstorage.example/n/ns/b/bucket/o/image.qcow2",
            "operating_system": "oracle_linux",
        },
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "source_image_type is required" in exc_info.value.payload["msg"]


def test_validate_create_request_requires_version_for_windows_import(monkeypatch):
    install_fake_oci(monkeypatch)

    image_module = load_collection_module("oci_image")
    instance = make_image_module(
        image_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-image",
            "source_uri": "https://objectstorage.example/n/ns/b/bucket/o/image.vmdk",
            "operating_system": "windows",
            "source_image_type": "vmdk",
        },
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "operating_system_version is required" in exc_info.value.payload["msg"]


def test_validate_create_request_rejects_launch_mode_for_oci_image_type(monkeypatch):
    install_fake_oci(monkeypatch)

    image_module = load_collection_module("oci_image")
    instance = make_image_module(
        image_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-image",
            "source_uri": "https://objectstorage.example/n/ns/b/bucket/o/image.oci",
            "operating_system": "oracle_linux",
            "source_image_type": "oci",
            "launch_mode": "paravirtualized",
        },
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "launch_mode cannot be set" in exc_info.value.payload["msg"]


def test_validate_create_request_accepts_bucket_import(monkeypatch):
    install_fake_oci(monkeypatch)

    image_module = load_collection_module("oci_image")
    instance = make_image_module(
        image_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-image",
            "object_storage": {
                "namespace_name": "mytenancy",
                "bucket_name": "images",
                "object_name": "golden.qcow2",
            },
            "operating_system": "oracle_linux",
            "source_image_type": "qcow2",
        },
    )

    instance.validate_create_request()


def test_build_create_image_details_imports_from_object_storage_bucket(monkeypatch):
    install_fake_oci(monkeypatch)

    image_module = load_collection_module("oci_image")
    details = image_module.build_create_image_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "imported-linux",
            "object_storage": {
                "namespace_name": "mytenancy",
                "bucket_name": "images",
                "object_name": "golden.qcow2",
            },
            "operating_system": "oracle_linux",
            "operating_system_version": "9",
            "source_image_type": "qcow2",
            "launch_mode": "paravirtualized",
        }
    )

    assert not hasattr(details, "instance_id")
    assert details.display_name == "imported-linux"
    assert details.launch_mode == "PARAVIRTUALIZED"
    assert isinstance(details.image_source_details, FakeModel)
    assert details.image_source_details.namespace_name == "mytenancy"
    assert details.image_source_details.bucket_name == "images"
    assert details.image_source_details.object_name == "golden.qcow2"
    assert details.image_source_details.operating_system == "Oracle Linux"
    assert details.image_source_details.operating_system_version == "9"
    assert details.image_source_details.source_image_type == "QCOW2"


def test_build_create_image_details_imports_from_object_storage_uri(monkeypatch):
    install_fake_oci(monkeypatch)

    image_module = load_collection_module("oci_image")
    details = image_module.build_create_image_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "imported-from-url",
            "source_uri": "https://objectstorage.example/n/ns/b/bucket/o/image.vmdk",
            "operating_system": "ubuntu",
            "source_image_type": "vmdk",
        }
    )

    assert not hasattr(details, "instance_id")
    assert isinstance(details.image_source_details, FakeModel)
    assert details.image_source_details.source_uri == (
        "https://objectstorage.example/n/ns/b/bucket/o/image.vmdk"
    )
    assert details.image_source_details.operating_system == "Ubuntu"
    assert details.image_source_details.source_image_type == "VMDK"
    assert not hasattr(details.image_source_details, "bucket_name")


def test_build_create_image_details_maps_rhel_choice_to_console_label(monkeypatch):
    install_fake_oci(monkeypatch)

    image_module = load_collection_module("oci_image")
    details = image_module.build_create_image_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "imported-rhel",
            "source_uri": "https://objectstorage.example/n/ns/b/bucket/o/image.qcow2",
            "operating_system": "rhel",
            "source_image_type": "qcow2",
        }
    )

    assert details.image_source_details.operating_system == "Red Hat Enterprise Linux"


def test_build_create_image_details_omits_source_image_type_for_oci_format(
    monkeypatch,
):
    install_fake_oci(monkeypatch)

    image_module = load_collection_module("oci_image")
    details = image_module.build_create_image_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "imported-oci",
            "source_uri": "https://objectstorage.example/n/ns/b/bucket/o/image.oci",
            "operating_system": "oracle_linux",
            "source_image_type": "oci",
        }
    )

    assert isinstance(details.image_source_details, FakeModel)
    assert details.image_source_details.operating_system == "Oracle Linux"
    assert not hasattr(details.image_source_details, "source_image_type")
    assert not hasattr(details, "launch_mode")


def test_needs_update_ignores_create_only_import_fields(monkeypatch):
    install_fake_oci(monkeypatch)

    image_module = load_collection_module("oci_image")
    instance = make_image_module(
        image_module,
        {
            "name": "current-image",
            "source_uri": "https://objectstorage.example/n/ns/b/bucket/o/image.qcow2",
            "operating_system": "oracle_linux",
            "source_image_type": "qcow2",
        },
    )
    resource = FakeModel(
        id="ocid1.image.oc1..example",
        display_name="current-image",
    )

    assert instance.needs_update(resource) is False


def test_create_resource_imports_from_object_storage_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    image_module = load_collection_module("oci_image")
    create_calls = []
    response = FakeResponse(data=FakeModel(id="ocid1.image.oc1..example"))

    def create_image(create_image_details):
        create_calls.append(create_image_details)
        return response

    instance = make_image_module(
        image_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "imported-linux",
            "object_storage": {
                "namespace_name": "mytenancy",
                "bucket_name": "images",
                "object_name": "golden.qcow2",
            },
            "operating_system": "oracle_linux",
            "source_image_type": "qcow2",
            "wait": True,
        },
        client=types.SimpleNamespace(create_image=create_image),
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

    assert not hasattr(create_calls[0], "instance_id")
    assert create_calls[0].image_source_details.bucket_name == "images"
    assert create_calls[0].image_source_details.source_image_type == "QCOW2"
    assert resource.id == "ocid1.image.oc1..example"
    assert resource.lifecycle_state == "AVAILABLE"
