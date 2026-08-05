from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from conftest import (
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


def make_drg_attachment_info_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciDrgAttachmentInfoModule",
        params,
        client=client,
    )


def test_fetch_resources_prefers_id_lookup(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_drg_attachment_info")
    get_calls = []

    def get_drg_attachment(**kwargs):
        get_calls.append(kwargs)
        return FakeResponse(
            data=FakeModel(
                id=kwargs["drg_attachment_id"],
                display_name="example-drg-attachment",
            )
        )

    instance = make_drg_attachment_info_module(
        info_module,
        {"drg_attachment_id": "ocid1.drgattachment.oc1..example"},
        client=types.SimpleNamespace(get_drg_attachment=get_drg_attachment),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        raising(AssertionError("list_all_resources should not be called")),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    resources = instance.fetch_resources()

    assert get_calls == [{"drg_attachment_id": "ocid1.drgattachment.oc1..example"}]
    assert len(resources) == 1
    assert resources[0].id == "ocid1.drgattachment.oc1..example"


def test_fetch_resources_returns_empty_list_on_404(monkeypatch):
    _oci_module, ServiceError = install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_drg_attachment_info")

    def get_missing_drg_attachment(**kwargs):
        raise ServiceError(404, "missing")

    instance = make_drg_attachment_info_module(
        info_module,
        {"drg_attachment_id": "ocid1.drgattachment.oc1..missing"},
        client=types.SimpleNamespace(get_drg_attachment=get_missing_drg_attachment),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    assert instance.fetch_resources() == []


def test_fetch_resources_uses_list_filters(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_drg_attachment_info")
    paginate_calls = []
    instance = make_drg_attachment_info_module(
        info_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "drg_id": "ocid1.drg.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-drg-attachment",
            "lifecycle_state": "ATTACHED",
        },
        client=types.SimpleNamespace(list_drg_attachments="list_method"),
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
                "drg_id": "ocid1.drg.oc1..example",
                "vcn_id": "ocid1.vcn.oc1..example",
                "lifecycle_state": "ATTACHED",
            },
        )
    ]


def test_run_returns_drg_attachment_results_key(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_drg_attachment_info")
    instance = make_drg_attachment_info_module(
        info_module,
        {"compartment_id": "ocid1.compartment.oc1..example"},
    )
    run_resource = FakeModel(
        id="ocid1.drgattachment.oc1..example",
        display_name="example-drg-attachment",
        lifecycle_state="ATTACHED",
        drg_id="ocid1.drg.oc1..example",
        vcn_id="ocid1.vcn.oc1..example",
    )
    monkeypatch.setattr(instance, "fetch_resources", lambda: [run_resource])

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()

    assert exc_info.value.payload == {
        "changed": False,
        "drg_attachments": [
            {
                "id": "ocid1.drgattachment.oc1..example",
                "name": "example-drg-attachment",
                "lifecycle_state": "ATTACHED",
                "drg_id": "ocid1.drg.oc1..example",
                "vcn_id": "ocid1.vcn.oc1..example",
            }
        ],
    }


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
