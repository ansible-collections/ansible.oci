from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


def install_fake_oci(monkeypatch):
    oci_module, service_error = shared_install_fake_oci(monkeypatch)
    oci_module.container_engine = types.SimpleNamespace(
        ContainerEngineClient=type("FakeContainerEngineClient", (), {}),
    )
    return service_error


def test_main_exposes_filters_and_check_mode(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_oke_node_pool_options_info")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule()

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(
        module_obj,
        "OciOkeNodePoolOptionsInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )

    module_obj.main()

    assert captured["supports_check_mode"] is True
    assert "required_one_of" not in captured
    argument_spec = captured["argument_spec"]
    assert argument_spec["node_pool_option_id"] == {"type": "str", "default": "all"}
    assert argument_spec["compartment_id"] == {"type": "str"}
    assert argument_spec["node_pool_os_type"] == {
        "type": "str",
        "choices": ["ol7", "ol8", "ubuntu", "OL7", "OL8", "UBUNTU"],
    }
    assert argument_spec["node_pool_os_arch"] == {
        "type": "str",
        "choices": ["x86_64", "aarch64", "X86_64", "AARCH64"],
    }
    assert argument_spec["node_pool_k8s_version"] == {"type": "str"}


def test_fetch_defaults_to_all_and_returns_single_options(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_oke_node_pool_options_info")
    calls = []
    resource = FakeModel(
        sources=[FakeModel(source_type="IMAGE", source_name="OL8", image_id="img1")],
        shapes=["VM.Standard.E4.Flex"],
        kubernetes_versions=["v1.29.1"],
    )
    instance = make_module_instance(
        module_obj,
        "OciOkeNodePoolOptionsInfoModule",
        {
            "node_pool_option_id": "all",
            "compartment_id": None,
            "node_pool_os_type": None,
            "node_pool_os_arch": None,
            "node_pool_k8s_version": None,
        },
        client=types.SimpleNamespace(
            get_node_pool_options=lambda **kwargs: calls.append(kwargs)
            or FakeResponse(resource)
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.fetch_resources() == [resource]
    assert calls == [{"node_pool_option_id": "all"}]


def test_fetch_forwards_only_supplied_filters(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_oke_node_pool_options_info")
    calls = []
    resource = FakeModel(sources=[])
    instance = make_module_instance(
        module_obj,
        "OciOkeNodePoolOptionsInfoModule",
        {
            "node_pool_option_id": "ocid1.cluster.oc1..example",
            "compartment_id": None,
            "node_pool_os_type": None,
            "node_pool_os_arch": "AARCH64",
            "node_pool_k8s_version": "v1.29.1",
        },
        client=types.SimpleNamespace(
            get_node_pool_options=lambda **kwargs: calls.append(kwargs)
            or FakeResponse(resource)
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.fetch_resources() == [resource]
    assert calls == [
        {
            "node_pool_option_id": "ocid1.cluster.oc1..example",
            "node_pool_os_arch": "AARCH64",
            "node_pool_k8s_version": "v1.29.1",
        }
    ]


def test_fetch_404_returns_empty_list(monkeypatch):
    service_error = install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_oke_node_pool_options_info")
    instance = make_module_instance(
        module_obj,
        "OciOkeNodePoolOptionsInfoModule",
        {
            "node_pool_option_id": "ocid1.cluster.oc1..missing",
            "compartment_id": None,
            "node_pool_os_type": None,
            "node_pool_os_arch": None,
            "node_pool_k8s_version": None,
        },
        client=types.SimpleNamespace(
            get_node_pool_options=raising(service_error(404, "missing"))
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.fetch_resources() == []


def test_fetch_propagates_service_errors(monkeypatch):
    service_error = install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_oke_node_pool_options_info")
    instance = make_module_instance(
        module_obj,
        "OciOkeNodePoolOptionsInfoModule",
        {
            "node_pool_option_id": "all",
            "compartment_id": None,
            "node_pool_os_type": None,
            "node_pool_os_arch": None,
            "node_pool_k8s_version": None,
        },
        client=types.SimpleNamespace(
            get_node_pool_options=raising(service_error(500, "failed"))
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    with pytest.raises(service_error):
        instance.fetch_resources()


def test_execute_info_returns_options_with_changed_false(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_oke_node_pool_options_info")
    instance = make_module_instance(
        module_obj,
        "OciOkeNodePoolOptionsInfoModule",
        {"node_pool_option_id": "all"},
    )
    monkeypatch.setattr(
        instance,
        "fetch_resources",
        lambda: [
            FakeModel(
                sources=[
                    FakeModel(
                        source_type="IMAGE", source_name="OL8", image_id="img1"
                    )
                ],
                shapes=["VM.Standard.E4.Flex"],
                kubernetes_versions=["v1.29.1"],
            )
        ],
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()

    assert exc_info.value.payload == {
        "changed": False,
        "node_pool_options": [
            {
                "sources": [
                    {
                        "source_type": "IMAGE",
                        "source_name": "OL8",
                        "image_id": "img1",
                    }
                ],
                "shapes": ["VM.Standard.E4.Flex"],
                "kubernetes_versions": ["v1.29.1"],
            }
        ],
    }
