from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
import types

import pytest

from .conftest import (
    DummyModule,
    FailJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
)

MODEL_NAMES = (
    "CreateInstanceConfigurationDetails",
    "CreateInstanceConfigurationFromInstanceDetails",
    "UpdateInstanceConfigurationDetails",
    "ComputeInstanceOptions",
    "ComputeInstanceDetails",
)


class SchemaModel(FakeModel):
    """Fake SDK model with the field schema used by the template builder."""

    swagger_types = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


def install_configuration_oci(monkeypatch):
    fake_oci = install_fake_oci(monkeypatch, model_names=MODEL_NAMES)[0]
    fake_oci.core.ComputeManagementClient = type("FakeComputeManagementClient", (), {})
    fake_oci.retry.RetryStrategyBuilder = lambda **kwargs: types.SimpleNamespace(
        get_retry_strategy=lambda: types.SimpleNamespace(
            make_retrying_call=lambda fn, *args, **call_kwargs: fn(*args, **call_kwargs)
        )
    )
    compute = sys.modules.get("ansible_collections.ansible.oci.plugins.module_utils.oci_instance")
    if compute is not None:
        monkeypatch.setattr(compute, "oci", fake_oci)
    return fake_oci


def test_create_from_instance_uses_expected_sdk_method(monkeypatch):
    install_configuration_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_configuration")
    captured = {}
    client = types.SimpleNamespace(
        retry_strategy=None,
        create_instance_configuration=lambda **kwargs: captured.update(kwargs)
        or FakeResponse(FakeModel(id="ocid1.instanceconfiguration.oc1..x")),
    )
    resource = make_module_instance(
        module_obj,
        "OciInstanceConfigurationModule",
        {
            "source": "instance",
            "instance_id": "ocid1.instance.oc1..x",
            "compartment_id": "ocid1.compartment.oc1..x",
            "name": "template",
        },
        client=client,
    )
    resource.call_with_retry = lambda fn, **kwargs: fn(**kwargs)

    result = resource.create_resource()

    assert result.id == "ocid1.instanceconfiguration.oc1..x"
    assert captured["create_instance_configuration"].source == "INSTANCE"
    assert captured["create_instance_configuration"].instance_id == "ocid1.instance.oc1..x"


def test_create_from_template_builds_compute_discriminator(monkeypatch):
    fake_oci = install_configuration_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_configuration")
    builder_models = fake_oci.core.models
    monkeypatch.setattr(
        builder_models,
        "ComputeInstanceOptions",
        type(
            "ComputeInstanceOptions",
            (SchemaModel,),
            {"swagger_types": {"instance_type": "str", "options": "list[ComputeInstanceDetails]"}},
        ),
    )
    monkeypatch.setattr(
        builder_models,
        "ComputeInstanceDetails",
        type(
            "ComputeInstanceDetails",
            (SchemaModel,),
            {
                "swagger_types": {
                    "instance_type": "str",
                    "launch_details": "InstanceConfigurationLaunchInstanceDetails",
                }
            },
        ),
    )
    monkeypatch.setattr(
        builder_models,
        "InstanceConfigurationLaunchInstanceDetails",
        type(
            "InstanceConfigurationLaunchInstanceDetails",
            (SchemaModel,),
            {"swagger_types": {"shape": "str"}},
        ),
        raising=False,
    )
    captured = {}
    client = types.SimpleNamespace(
        retry_strategy=None,
        create_instance_configuration=lambda **kwargs: captured.update(kwargs)
        or FakeResponse(FakeModel(id="config-id")),
    )
    template = {
        "instance_type": "instance_options",
        "options": [{"instance_type": "compute", "launch_details": {"shape": "x"}}],
    }
    resource = make_module_instance(
        module_obj,
        "OciInstanceConfigurationModule",
        {
            "source": "none",
            "instance_details": template,
            "compartment_id": "compartment-id",
            "name": "template",
        },
        client=client,
    )
    resource.call_with_retry = lambda fn, **kwargs: fn(**kwargs)

    resource.create_resource()

    details = captured["create_instance_configuration"]
    assert details.source == "NONE"
    assert details.instance_details.instance_type == "instance_options"
    assert details.instance_details.options[0].instance_type == "compute"


def test_validate_requires_source_fields(monkeypatch):
    install_configuration_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_configuration")
    resource = make_module_instance(
        module_obj,
        "OciInstanceConfigurationModule",
        {"source": "instance", "compartment_id": "c", "name": "n"},
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        resource.validate_create_request()

    assert "requires instance_id" in exc_info.value.payload["msg"]


def test_info_declares_get_and_list_operations(monkeypatch):
    install_configuration_oci(monkeypatch)
    module_obj = load_collection_module("oci_instance_configuration_info")
    info_class = module_obj.OciInstanceConfigurationInfoModule
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule({})

    class FakeInfoModule:
        def __init__(self, module):
            pass

        def execute_info_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciInstanceConfigurationInfoModule", FakeInfoModule)

    module_obj.main()

    assert captured["run_called"] is True
    assert "instance_configuration_id" in captured["argument_spec"]
    assert captured["required_one_of"] == [["compartment_id", "instance_configuration_id"]]
    assert info_class.results_key == "instance_configurations"
