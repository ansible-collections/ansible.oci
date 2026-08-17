from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

from conftest import install_fake_oci, load_collection_module


def test_main_requires_compartment_id_or_volume_id(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_blockstorage_volume_info")
    captured = {}

    class FakeAnsibleModule:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(info_module, "AnsibleModule", FakeAnsibleModule)
    monkeypatch.setattr(
        info_module,
        "OciBlockstorageVolumeInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )

    info_module.main()

    assert captured["required_one_of"] == [["compartment_id", "volume_id"]]
    assert captured["argument_spec"]["volume_id"] == {"type": "str"}
    assert captured["argument_spec"]["availability_domain"] == {"type": "str"}
    assert captured["argument_spec"]["name"] == {"type": "str"}
    assert captured["argument_spec"]["lifecycle_state"] == {"type": "str"}


def test_info_module_class_metadata(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_blockstorage_volume_info")

    assert info_module.OciBlockstorageVolumeInfoModule.results_key == "volumes"
    assert info_module.OciBlockstorageVolumeInfoModule.resource_id_param == "volume_id"
    assert (
        info_module.OciBlockstorageVolumeInfoModule.resource_get_method == "get_volume"
    )
    assert (
        info_module.OciBlockstorageVolumeInfoModule.list_resource_method
        == "list_volumes"
    )
