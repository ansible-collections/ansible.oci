from __future__ import absolute_import, division, print_function

import types

from .conftest import (
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
)


def test_main_requires_cpe_id_or_compartment(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_cpe_info")
    captured = {}

    class FakeAnsibleModule:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(module_obj, "AnsibleModule", FakeAnsibleModule)
    monkeypatch.setattr(
        module_obj,
        "OciNetworkCpeInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )
    module_obj.main()
    assert captured["required_one_of"] == [["compartment_id", "cpe_id"]]
    assert captured["argument_spec"]["cpe_id"] == {"type": "str"}


def test_info_metadata_uses_cpe_operations(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_cpe_info")
    info = module_obj.OciNetworkCpeInfoModule.__new__(
        module_obj.OciNetworkCpeInfoModule
    )
    assert info.results_key == "cpes"
    assert info.resource_id_param == "cpe_id"
    assert info.resource_get_method == "get_cpe"
    assert info.list_resource_method == "list_cpes"


def test_info_list_filters_by_name_and_passes_compartment(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_cpe_info")
    instance = make_module_instance(
        module_obj,
        "OciNetworkCpeInfoModule",
        {"compartment_id": "compartment", "name": "wanted"},
        client=types.SimpleNamespace(list_cpes=lambda **kwargs: None),
    )
    calls = []
    resources = [
        FakeModel(id="one", display_name="wanted"),
        FakeModel(id="two", display_name="other"),
    ]
    instance.list_all_resources = lambda fn, **kwargs: calls.append(kwargs) or resources
    result = instance.fetch_resources()
    assert [resource.id for resource in result] == ["one"]
    assert calls == [{"compartment_id": "compartment"}]


def test_info_get_uses_id_and_returns_empty_on_404(monkeypatch):
    _oci, service_error = install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_cpe_info")
    instance = make_module_instance(
        module_obj,
        "OciNetworkCpeInfoModule",
        {"cpe_id": "cpe-id"},
        client=types.SimpleNamespace(
            get_cpe=lambda **kwargs: FakeResponse(FakeModel(id="cpe-id"))
        ),
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    result = instance.fetch_resources()
    assert result[0].id == "cpe-id"

    instance.call_with_retry = lambda fn, **kwargs: (value for value in ()).throw(
        service_error(404)
    )
    assert instance.fetch_resources() == []
