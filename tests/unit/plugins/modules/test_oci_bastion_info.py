from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

from .conftest import (
    ExitJsonCalled,
    FakeModel,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)


def install_fake_oci(monkeypatch):
    oci_module, service_error = shared_install_fake_oci(monkeypatch)
    oci_module.bastion = types.SimpleNamespace(
        BastionClient=type("FakeBastionClient", (), {}),
        models=types.SimpleNamespace(),
    )
    return oci_module, service_error


def test_main_requires_compartment_id_or_bastion_id(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_bastion_info")
    captured = {}

    class FakeAnsibleModule:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(info_module, "AnsibleModule", FakeAnsibleModule)
    monkeypatch.setattr(
        info_module,
        "OciBastionInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )

    info_module.main()

    assert captured["required_one_of"] == [["compartment_id", "bastion_id"]]
    assert captured["argument_spec"]["bastion_id"] == {"type": "str"}
    assert captured["argument_spec"]["name"] == {"type": "str"}
    assert captured["argument_spec"]["bastion_lifecycle_state"] == {"type": "str"}
    assert captured["argument_spec"]["compartment_id"] == {"type": "str"}


def test_info_module_class_metadata(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_bastion_info")

    assert info_module.OciBastionInfoModule.results_key == "bastions"
    assert info_module.OciBastionInfoModule.resource_id_param == "bastion_id"
    assert info_module.OciBastionInfoModule.resource_get_method == "get_bastion"
    assert info_module.OciBastionInfoModule.list_resource_method == "list_bastions"
    assert info_module.OciBastionInfoModule.list_filter_params == [
        "compartment_id",
        "bastion_lifecycle_state",
    ]
    # Bastion summaries expose ``name`` (not ``display_name``).
    assert info_module.OciBastionInfoModule.name_filter_param == "name"
    assert info_module.OciBastionInfoModule.name_response_field == "name"


def test_fetch_resources_prefers_get_by_id(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_bastion_info")
    get_calls = []
    bastion = FakeModel(id="ocid1.bastion.oc1..example", name="example-bastion")

    def get_bastion(bastion_id):
        get_calls.append(bastion_id)
        return types.SimpleNamespace(data=bastion)

    instance = make_module_instance(
        info_module,
        "OciBastionInfoModule",
        {"bastion_id": "ocid1.bastion.oc1..example"},
        client=types.SimpleNamespace(get_bastion=get_bastion),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    resources = instance.fetch_resources()

    assert get_calls == ["ocid1.bastion.oc1..example"]
    assert resources == [bastion]


def test_execute_info_module_exits_with_serialized_bastions(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_bastion_info")
    instance = make_module_instance(
        info_module,
        "OciBastionInfoModule",
        {"compartment_id": "ocid1.compartment.oc1..example"},
    )
    monkeypatch.setattr(
        instance,
        "fetch_resources",
        lambda: [FakeModel(id="ocid1.bastion.oc1..example", name="example-bastion")],
    )

    try:
        instance.execute_info_module()
    except ExitJsonCalled as exc_info:
        payload = exc_info.payload
    else:
        raise AssertionError("execute_info_module did not call exit_json")

    assert payload["changed"] is False
    assert payload["bastions"] == [
        {"id": "ocid1.bastion.oc1..example", "name": "example-bastion"}
    ]
