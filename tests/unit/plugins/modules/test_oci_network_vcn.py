import types

import pytest

from conftest import (
    DummyModule,
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    FailJsonCalled,
    FakeWorkRequestClient,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)


VCN_MODEL_NAMES = (
    "CreateVcnDetails",
    "UpdateVcnDetails",
    "AddVcnCidrDetails",
    "ModifyVcnCidrDetails",
    "RemoveVcnCidrDetails",
)


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(
        monkeypatch,
        model_names=VCN_MODEL_NAMES,
        include_work_requests=True,
    )


def make_vcn_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciNetworkVcnModule",
        params,
        client=client,
        work_request_client=types.SimpleNamespace(),
    )


def test_main_exposes_allow_duplicate_name_argument(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_network_vcn")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        return DummyModule({})

    class FakeVcnModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciNetworkVcnModule", FakeVcnModule)

    module_obj.main()

    assert captured["run_called"] is True
    assert module_obj.OCI_COMMON_ARGS["allow_duplicate_name"] == {
        "type": "bool",
        "default": False,
    }
    assert module_obj.OCI_COMMON_ARGS["name"] == {"type": "str"}
    assert module_obj.OCI_COMMON_ARGS["compartment_id"] == {"type": "str"}
    assert captured["argument_spec"]["allow_duplicate_name"] == {
        "type": "bool",
        "default": False,
    }
    assert captured["argument_spec"]["name"] == {"type": "str"}
    assert captured["argument_spec"]["compartment_id"] == {"type": "str"}
    assert "display_name" not in captured["argument_spec"]


def test_build_create_vcn_details_includes_dns_label_and_tags(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    details = vcn_module.build_create_vcn_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "cidr_blocks": ["10.0.0.0/16"],
            "name": "example-vcn",
            "dns_label": "examplevcn",
            "freeform_tags": {"env": "dev"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        }
    )

    assert isinstance(details, FakeModel)
    assert details.compartment_id == "ocid1.compartment.oc1..example"
    assert details.cidr_blocks == ["10.0.0.0/16"]
    assert details.display_name == "example-vcn"
    assert details.dns_label == "examplevcn"
    assert details.freeform_tags == {"env": "dev"}
    assert details.defined_tags == {"Operations": {"CostCenter": "42"}}


def test_build_update_vcn_details_only_includes_mutable_fields(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    details = vcn_module.build_update_vcn_details(
        {
            "display_name": "updated-vcn",
            "freeform_tags": {"env": "prod"},
            "defined_tags": {"Operations": {"CostCenter": "43"}},
        }
    )

    assert isinstance(details, FakeModel)
    assert details.display_name == "updated-vcn"
    assert details.freeform_tags == {"env": "prod"}
    assert details.defined_tags == {"Operations": {"CostCenter": "43"}}


def test_build_update_plan_maps_vcn_metadata_and_cidr_strategy(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    instance = make_vcn_module(
        vcn_module,
        {
            "name": "updated-vcn",
            "cidr_blocks": ["10.0.0.0/16", "10.1.0.0/16"],
            "wait": True,
        },
    )
    resource = FakeModel(
        id="ocid1.vcn.oc1..example",
        display_name="current-vcn",
        cidr_blocks=["10.0.0.0/16"],
    )

    update_plan = instance.build_update_plan(resource)

    assert update_plan["update_needed"] is True
    assert update_plan["update_model_fields"] == {"display_name": "updated-vcn"}
    assert update_plan["strategy_operations"] == [
        {
            "param_name": "cidr_blocks",
            "operations": [("add", "10.1.0.0/16")],
        }
    ]


def test_build_add_vcn_cidr_details_uses_cidr_block(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    details = vcn_module.build_add_vcn_cidr_details("10.1.0.0/16")

    assert isinstance(details, FakeModel)
    assert details.cidr_block == "10.1.0.0/16"


def test_build_modify_vcn_cidr_details_uses_original_and_new_cidr(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    details = vcn_module.build_modify_vcn_cidr_details(
        "10.0.0.0/16",
        "10.0.0.0/15",
    )

    assert isinstance(details, FakeModel)
    assert details.original_cidr_block == "10.0.0.0/16"
    assert details.new_cidr_block == "10.0.0.0/15"


def test_build_remove_vcn_cidr_details_uses_cidr_block(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    details = vcn_module.build_remove_vcn_cidr_details("10.1.0.0/16")

    assert isinstance(details, FakeModel)
    assert details.cidr_block == "10.1.0.0/16"


def test_plan_vcn_cidr_operations_returns_adds_in_desired_order(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")

    assert vcn_module.plan_vcn_cidr_operations(
        ["10.0.0.0/16"],
        ["10.0.0.0/16", "10.1.0.0/16", "10.2.0.0/16"],
    ) == [
        ("add", "10.1.0.0/16"),
        ("add", "10.2.0.0/16"),
    ]


def test_plan_vcn_cidr_operations_returns_removes_in_current_order(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")

    assert vcn_module.plan_vcn_cidr_operations(
        ["10.0.0.0/16", "10.1.0.0/16", "10.2.0.0/16"],
        ["10.0.0.0/16"],
    ) == [
        ("remove", "10.1.0.0/16"),
        ("remove", "10.2.0.0/16"),
    ]


def test_plan_vcn_cidr_operations_returns_single_modify(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")

    assert vcn_module.plan_vcn_cidr_operations(
        ["10.0.0.0/16"],
        ["10.0.0.0/15"],
    ) == [
        ("modify", "10.0.0.0/16", "10.0.0.0/15"),
    ]


def test_plan_vcn_cidr_operations_rejects_complex_changes(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")

    with pytest.raises(ValueError, match="Complex cidr_blocks changes"):
        vcn_module.plan_vcn_cidr_operations(
            ["10.0.0.0/16", "10.1.0.0/16"],
            ["10.2.0.0/16", "10.3.0.0/16"],
        )


def test_needs_update_treats_cidr_block_order_as_noop(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    instance = make_vcn_module(
        vcn_module,
        {"cidr_blocks": ["10.1.0.0/16", "10.0.0.0/16"]},
    )
    resource = FakeModel(
        id="ocid1.vcn.oc1..example",
        cidr_blocks=["10.0.0.0/16", "10.1.0.0/16"],
    )

    assert instance.needs_update(resource) is False


def test_needs_update_returns_true_for_simple_cidr_add(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    instance = make_vcn_module(
        vcn_module,
        {"cidr_blocks": ["10.0.0.0/16", "10.1.0.0/16"], "wait": True},
    )
    resource = FakeModel(
        id="ocid1.vcn.oc1..example",
        cidr_blocks=["10.0.0.0/16"],
    )

    assert instance.needs_update(resource) is True


def test_needs_update_rejects_cidr_updates_without_wait(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    instance = make_vcn_module(
        vcn_module,
        {"cidr_blocks": ["10.1.0.0/16"], "wait": False},
    )
    resource = FakeModel(id="ocid1.vcn.oc1..example", cidr_blocks=["10.0.0.0/16"])

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "wait=true" in exc_info.value.payload["msg"]


def test_needs_update_rejects_complex_cidr_changes(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    instance = make_vcn_module(
        vcn_module,
        {"cidr_blocks": ["10.2.0.0/16", "10.3.0.0/16"]},
    )
    resource = FakeModel(
        id="ocid1.vcn.oc1..example",
        cidr_blocks=["10.0.0.0/16", "10.1.0.0/16"],
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "Complex cidr_blocks changes" in exc_info.value.payload["msg"]


def test_needs_update_rejects_dns_label_drift(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    instance = make_vcn_module(
        vcn_module,
        {"dns_label": "desiredlabel"},
    )
    resource = FakeModel(id="ocid1.vcn.oc1..example", dns_label="currentlabel")

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "dns_label" in exc_info.value.payload["msg"]


def test_needs_update_returns_true_for_name_change(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    instance = make_vcn_module(
        vcn_module,
        {"name": "updated-vcn"},
    )
    resource = FakeModel(
        id="ocid1.vcn.oc1..example",
        display_name="current-vcn",
    )

    assert instance.needs_update(resource) is True


def test_create_resource_uses_create_vcn_and_waits(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    create_calls = []
    response = FakeResponse(
        data=FakeModel(id="ocid1.vcn.oc1..example"),
    )

    def create_vcn(create_vcn_details):
        create_calls.append(create_vcn_details)
        return response

    instance = make_vcn_module(
        vcn_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "cidr_blocks": ["10.0.0.0/16"],
            "name": "example-vcn",
            "dns_label": "examplevcn",
            "wait": True,
        },
        client=types.SimpleNamespace(create_vcn=create_vcn),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: FakeModel(
            id=resource_id,
            lifecycle_state="AVAILABLE",
        ),
    )

    resource = instance.create_resource()

    assert create_calls[0].display_name == "example-vcn"
    assert create_calls[0].dns_label == "examplevcn"
    assert resource.id == "ocid1.vcn.oc1..example"
    assert resource.lifecycle_state == "AVAILABLE"


def test_update_resource_uses_update_vcn_details_and_waits(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    update_calls = []
    response = FakeResponse(
        data=FakeModel(id="ocid1.vcn.oc1..example"),
    )

    def update_vcn(vcn_id, update_vcn_details):
        update_calls.append((vcn_id, update_vcn_details))
        return response

    resource = FakeModel(id="ocid1.vcn.oc1..example")
    instance = make_vcn_module(
        vcn_module,
        {
            "name": "updated-vcn",
            "freeform_tags": {"env": "prod"},
            "wait": True,
        },
        client=types.SimpleNamespace(update_vcn=update_vcn),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: FakeModel(
            id=resource_id,
            lifecycle_state="AVAILABLE",
        ),
    )

    updated_resource = instance.update_resource(resource)

    assert update_calls[0][0] == "ocid1.vcn.oc1..example"
    assert update_calls[0][1].display_name == "updated-vcn"
    assert update_calls[0][1].freeform_tags == {"env": "prod"}
    assert updated_resource.id == "ocid1.vcn.oc1..example"


def test_update_resource_adds_vcn_cidr_and_waits_for_work_request(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    add_calls = []
    waited_work_requests = []
    waited_resources = []

    def add_vcn_cidr(vcn_id, add_vcn_cidr_details):
        add_calls.append((vcn_id, add_vcn_cidr_details))
        return FakeResponse(
            data=None,
            headers={"opc-work-request-id": "wr-add-1"},
        )

    resource = FakeModel(
        id="ocid1.vcn.oc1..example",
        cidr_blocks=["10.0.0.0/16"],
    )
    instance = make_vcn_module(
        vcn_module,
        {
            "cidr_blocks": ["10.0.0.0/16", "10.1.0.0/16"],
            "wait": True,
        },
        client=types.SimpleNamespace(add_vcn_cidr=add_vcn_cidr),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )
    monkeypatch.setattr(
        instance,
        "wait_for_work_request",
        lambda work_request_client, work_request_id, **kwargs: waited_work_requests.append(
            work_request_id
        ) or FakeModel(status="SUCCEEDED"),
    )
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda vcn_id, target_states: waited_resources.append(vcn_id)
        or FakeModel(id=vcn_id, cidr_blocks=["10.0.0.0/16", "10.1.0.0/16"]),
    )

    updated_resource = instance.update_resource(resource)

    assert add_calls[0][0] == "ocid1.vcn.oc1..example"
    assert add_calls[0][1].cidr_block == "10.1.0.0/16"
    assert waited_work_requests == ["wr-add-1"]
    assert waited_resources == ["ocid1.vcn.oc1..example"]
    assert updated_resource.cidr_blocks == ["10.0.0.0/16", "10.1.0.0/16"]


def test_update_resource_applies_cidr_changes_before_metadata_update(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    remove_calls = []
    update_calls = []
    waited_work_requests = []
    waited_resources = []

    def remove_vcn_cidr(vcn_id, remove_vcn_cidr_details):
        remove_calls.append((vcn_id, remove_vcn_cidr_details))
        return FakeResponse(
            data=None,
            headers={"opc-work-request-id": "wr-remove-1"},
        )

    def update_vcn(vcn_id, update_vcn_details):
        update_calls.append((vcn_id, update_vcn_details))
        return FakeResponse(data=FakeModel(id=vcn_id))

    resource = FakeModel(
        id="ocid1.vcn.oc1..example",
        cidr_blocks=["10.0.0.0/16", "10.1.0.0/16"],
        display_name="example-vcn",
        freeform_tags={"phase": "create"},
    )
    instance = make_vcn_module(
        vcn_module,
        {
            "cidr_blocks": ["10.0.0.0/16"],
            "name": "example-vcn-updated",
            "freeform_tags": {"phase": "update"},
            "wait": True,
        },
        client=types.SimpleNamespace(
            remove_vcn_cidr=remove_vcn_cidr,
            update_vcn=update_vcn,
        ),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )
    monkeypatch.setattr(
        instance,
        "wait_for_work_request",
        lambda work_request_client, work_request_id, **kwargs: waited_work_requests.append(
            work_request_id
        ) or FakeModel(status="SUCCEEDED"),
    )

    def fake_wait_for_resource_id(vcn_id, target_states):
        waited_resources.append(vcn_id)
        if len(waited_resources) == 1:
            return FakeModel(
                id=vcn_id,
                cidr_blocks=["10.0.0.0/16"],
                display_name="example-vcn",
                freeform_tags={"phase": "create"},
            )
        return FakeModel(
            id=vcn_id,
            cidr_blocks=["10.0.0.0/16"],
            display_name="example-vcn-updated",
            freeform_tags={"phase": "update"},
        )

    monkeypatch.setattr(instance, "wait_for_resource_id", fake_wait_for_resource_id)

    updated_resource = instance.update_resource(resource)

    assert remove_calls[0][0] == "ocid1.vcn.oc1..example"
    assert remove_calls[0][1].cidr_block == "10.1.0.0/16"
    assert waited_work_requests == ["wr-remove-1"]
    assert waited_resources == [
        "ocid1.vcn.oc1..example",
        "ocid1.vcn.oc1..example",
    ]
    assert update_calls[0][0] == "ocid1.vcn.oc1..example"
    assert update_calls[0][1].display_name == "example-vcn-updated"
    assert update_calls[0][1].freeform_tags == {"phase": "update"}
    assert updated_resource.display_name == "example-vcn-updated"


