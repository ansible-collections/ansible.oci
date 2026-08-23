from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

from conftest import install_fake_oci, load_collection_module


def test_main_requires_compartment_id_or_boot_volume_id(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_boot_volume_info")
    captured = {}

    class FakeAnsibleModule:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(info_module, "AnsibleModule", FakeAnsibleModule)
    monkeypatch.setattr(
        info_module,
        "OciBootVolumeInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )

    info_module.main()

    assert captured["required_one_of"] == [["compartment_id", "boot_volume_id"]]
    assert captured["argument_spec"]["boot_volume_id"] == {"type": "str"}
    assert captured["argument_spec"]["availability_domain"] == {"type": "str"}
    assert captured["argument_spec"]["name"] == {"type": "str"}
    # list_boot_volumes has no lifecycle_state query param in the OCI SDK.
    assert "lifecycle_state" not in captured["argument_spec"]


def test_info_module_class_metadata(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_boot_volume_info")

    assert info_module.OciBootVolumeInfoModule.results_key == "boot_volumes"
    assert info_module.OciBootVolumeInfoModule.resource_id_param == "boot_volume_id"
    assert (
        info_module.OciBootVolumeInfoModule.resource_get_method == "get_boot_volume"
    )
    assert (
        info_module.OciBootVolumeInfoModule.list_resource_method
        == "list_boot_volumes"
    )
    assert info_module.OciBootVolumeInfoModule.list_filter_params == [
        "compartment_id",
        "availability_domain",
    ]
