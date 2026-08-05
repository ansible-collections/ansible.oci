from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

from conftest import install_fake_oci, load_collection_module


def test_main_requires_compartment_id_or_drg_attachment_id(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_drg_attachment_info")
    captured = {}

    class FakeAnsibleModule:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(info_module, "AnsibleModule", FakeAnsibleModule)
    monkeypatch.setattr(
        info_module,
        "OciDrgAttachmentInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )

    info_module.main()

    assert captured["required_one_of"] == [["compartment_id", "drg_attachment_id"]]
    assert captured["argument_spec"]["drg_attachment_id"] == {"type": "str"}
    assert captured["argument_spec"]["drg_id"] == {"type": "str"}
    assert captured["argument_spec"]["vcn_id"] == {"type": "str"}
    assert captured["argument_spec"]["lifecycle_state"] == {"type": "str"}
