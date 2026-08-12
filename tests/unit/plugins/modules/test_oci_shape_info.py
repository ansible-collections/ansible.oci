from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from conftest import (
    DummyModule,
    ExitJsonCalled,
    FakeModel,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
)


def test_main_requires_compartment_id(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_shape_info")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        return DummyModule({})

    class FakeShapeInfoModule:
        def __init__(self, module):
            self.module = module

        def execute_info_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciShapeInfoModule", FakeShapeInfoModule)

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["argument_spec"]["compartment_id"]["required"] is True
    assert "availability_domain" in captured["argument_spec"]
    assert "image_id" in captured["argument_spec"]
    assert "shape" in captured["argument_spec"]
    assert "name" not in captured["argument_spec"]
    assert "lifecycle_state" not in captured["argument_spec"]


def test_fetch_resources_lists_by_supported_filters(monkeypatch):
    install_fake_oci(monkeypatch)

    shape_info_module = load_collection_module("oci_shape_info")
    paginate_calls = []
    instance = make_module_instance(
        shape_info_module,
        "OciShapeInfoModule",
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "availability_domain": "Uocm:PHX-AD-1",
            "image_id": "ocid1.image.oc1..example",
            "shape": "VM.Standard.E4.Flex",
        },
        client=types.SimpleNamespace(list_shapes="list_method"),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: paginate_calls.append((list_fn, kwargs)) or [],
    )

    resources = instance.fetch_resources()

    assert resources == []
    assert paginate_calls == [
        (
            "list_method",
            {
                "compartment_id": "ocid1.compartment.oc1..example",
                "availability_domain": "Uocm:PHX-AD-1",
                "image_id": "ocid1.image.oc1..example",
                "shape": "VM.Standard.E4.Flex",
            },
        )
    ]


def test_run_returns_shapes_key(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_shape_info")
    resource = FakeModel(
        shape="VM.Standard.E4.Flex",
        ocpus=1,
        memory_in_gbs=16,
        is_flexible=True,
    )
    instance = make_module_instance(
        module_obj,
        "OciShapeInfoModule",
        {"compartment_id": "ocid1.compartment.oc1..example"},
    )
    monkeypatch.setattr(instance, "fetch_resources", lambda: [resource])

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()

    assert exc_info.value.payload == {
        "changed": False,
        "shapes": [
            {
                "shape": "VM.Standard.E4.Flex",
                "ocpus": 1,
                "memory_in_gbs": 16,
                "is_flexible": True,
            }
        ],
    }
