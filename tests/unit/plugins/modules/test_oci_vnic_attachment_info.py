from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

from conftest import DummyModule, install_fake_oci, load_collection_module


def test_main_exposes_expected_arguments(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_vnic_attachment_info")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule({})

    class FakeVnicAttachmentInfoModule:
        def __init__(self, module):
            self.module = module

        def execute_info_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(
        module_obj,
        "OciVnicAttachmentInfoModule",
        FakeVnicAttachmentInfoModule,
    )

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["required_one_of"] == [
        ["compartment_id", "vnic_attachment_id"]
    ]
    assert captured["argument_spec"]["vnic_attachment_id"] == {"type": "str"}
    assert captured["argument_spec"]["availability_domain"] == {"type": "str"}
    assert captured["argument_spec"]["instance_id"] == {"type": "str"}
    assert captured["argument_spec"]["vnic_id"] == {"type": "str"}
    assert captured["argument_spec"]["name"] == {"type": "str"}


def test_info_module_class_metadata(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_vnic_attachment_info")
    klass = module_obj.OciVnicAttachmentInfoModule

    assert klass.results_key == "vnic_attachments"
    assert klass.resource_id_param == "vnic_attachment_id"
    assert klass.resource_get_method == "get_vnic_attachment"
    assert klass.list_resource_method == "list_vnic_attachments"
    assert klass.list_filter_params == [
        "compartment_id",
        "availability_domain",
        "instance_id",
        "vnic_id",
    ]


def test_fetch_resources_forwards_server_filters_and_filters_name(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_vnic_attachment_info")
    list_calls = []
    instance = object.__new__(module_obj.OciVnicAttachmentInfoModule)
    instance.module = DummyModule(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "availability_domain": "Uocm:PHX-AD-1",
            "instance_id": "ocid1.instance.oc1..example",
            "vnic_id": "ocid1.vnic.oc1..example",
            "name": "matching",
        }
    )
    instance.client = types.SimpleNamespace(list_vnic_attachments="list_method")
    matching = types.SimpleNamespace(display_name="matching")
    other = types.SimpleNamespace(display_name="other")
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: list_calls.append((list_fn, kwargs))
        or [matching, other],
    )

    assert instance.fetch_resources() == [matching]
    assert list_calls == [
        (
            "list_method",
            {
                "compartment_id": "ocid1.compartment.oc1..example",
                "availability_domain": "Uocm:PHX-AD-1",
                "instance_id": "ocid1.instance.oc1..example",
                "vnic_id": "ocid1.vnic.oc1..example",
            },
        )
    ]
