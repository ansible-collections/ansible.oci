from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

from conftest import install_fake_oci, load_collection_module


def test_main_requires_compartment_id_or_volume_attachment_id(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_volume_attachment_info")
    captured = {}

    class FakeAnsibleModule:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(info_module, "AnsibleModule", FakeAnsibleModule)
    monkeypatch.setattr(
        info_module,
        "OciVolumeAttachmentInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )

    info_module.main()

    assert captured["required_one_of"] == [
        ["compartment_id", "volume_attachment_id"]
    ]
    assert captured["argument_spec"]["volume_attachment_id"] == {"type": "str"}
    assert captured["argument_spec"]["instance_id"] == {"type": "str"}
    assert captured["argument_spec"]["volume_id"] == {"type": "str"}
    assert captured["argument_spec"]["availability_domain"] == {"type": "str"}
    assert captured["argument_spec"]["name"] == {"type": "str"}


def test_info_module_class_metadata(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_volume_attachment_info")

    klass = info_module.OciVolumeAttachmentInfoModule
    assert klass.results_key == "volume_attachments"
    assert klass.resource_id_param == "volume_attachment_id"
    assert klass.resource_get_method == "get_volume_attachment"
    assert klass.list_resource_method == "list_volume_attachments"
    # list_volume_attachments has no server-side lifecycle_state filter.
    assert "lifecycle_state" not in klass.list_filter_params
    assert klass.redacted_result_keys == ("chap_username", "chap_secret")
