from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from .conftest import (
    DummyModule,
    FakeModel,
    FakeResponse,
    FailJsonCalled,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)


NODE_POOL_MODEL_NAMES = (
    "CreateNodePoolDetails",
    "UpdateNodePoolDetails",
    "CreateNodePoolNodeConfigDetails",
    "UpdateNodePoolNodeConfigDetails",
    "CreateNodeShapeConfigDetails",
    "UpdateNodeShapeConfigDetails",
    "NodeSourceViaImageDetails",
    "NodePoolPlacementConfigDetails",
    "OciVcnIpNativeNodePoolPodNetworkOptionDetails",
    "FlannelOverlayNodePoolPodNetworkOptionDetails",
    "KeyValue",
    "NodeEvictionNodePoolSettings",
    "NodePoolCyclingDetails",
)


def install_fake_oci(monkeypatch):
    oci_module, service_error = shared_install_fake_oci(monkeypatch)
    oci_module.container_engine = types.SimpleNamespace(
        ContainerEngineClient=type("FakeContainerEngineClient", (), {}),
        models=types.SimpleNamespace(
            **{model_name: FakeModel for model_name in NODE_POOL_MODEL_NAMES}
        ),
    )
    return oci_module, service_error


def make_node_pool_module(module_obj, params, client=None, check_mode=False):
    return make_module_instance(
        module_obj,
        "OciOkeNodePoolModule",
        params,
        client=client,
        check_mode=check_mode,
    )


def test_main_wires_argument_spec_and_runs_module(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_oke_node_pool")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        captured["supports_check_mode"] = kwargs.get("supports_check_mode")
        return DummyModule({})

    class FakeNodePoolModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciOkeNodePoolModule", FakeNodePoolModule)

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["supports_check_mode"] is True
    spec = captured["argument_spec"]
    # name/compartment_id come from the shared OCI_COMMON_ARGS.
    assert spec["name"] == {"type": "str"}
    assert spec["compartment_id"] == {"type": "str"}
    # node pool specific params.
    assert spec["node_pool_id"] == {"type": "str"}
    assert spec["cluster_id"] == {"type": "str"}
    assert spec["node_shape"] == {"type": "str"}
    assert spec["node_config_details"]["type"] == "dict"
    assert spec["node_config_details"]["options"]["size"] == {"type": "int"}
    pod_network = spec["node_config_details"]["options"][
        "node_pool_pod_network_option_details"
    ]
    assert pod_network["options"]["cni_type"]["choices"] == [
        "oci_vcn_ip_native",
        "flannel_overlay",
    ]


def test_main_normalizes_enum_values_to_sdk_constants(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_oke_node_pool")
    captured = {}

    params = {
        "node_config_details": {
            "node_pool_pod_network_option_details": {
                "cni_type": "oci_vcn_ip_native",
            }
        },
        "auth_type": "api_key",
    }

    def fake_ansible_module(**kwargs):
        return DummyModule(params)

    class FakeNodePoolModule:
        def __init__(self, module):
            captured["module"] = module

        def execute_resource_module(self):
            pass

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciOkeNodePoolModule", FakeNodePoolModule)

    module_obj.main()

    normalized = captured["module"].params
    cni_type = normalized["node_config_details"][
        "node_pool_pod_network_option_details"
    ]["cni_type"]
    assert cni_type == "OCI_VCN_IP_NATIVE"
    # Keys that merely end in "_type" are not enum keys and are left untouched.
    assert normalized["auth_type"] == "api_key"


def test_class_metadata(monkeypatch):
    install_fake_oci(monkeypatch)

    node_pool_module = load_collection_module("oci_oke_node_pool")

    assert node_pool_module.OciOkeNodePoolModule.resource_id_param == "node_pool_id"
    assert node_pool_module.OciOkeNodePoolModule.list_resource_method == "list_node_pools"
    assert node_pool_module.OciOkeNodePoolModule.list_filter_params == ("cluster_id",)
    assert node_pool_module.OciOkeNodePoolModule.name_response_field == "name"
    assert node_pool_module.OciOkeNodePoolModule.create_resource_name == "node pool"


def test_build_create_node_pool_details_maps_nested_models(monkeypatch):
    install_fake_oci(monkeypatch)

    node_pool_module = load_collection_module("oci_oke_node_pool")
    details = node_pool_module.build_create_node_pool_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "cluster_id": "ocid1.cluster.oc1..example",
            "name": "example-pool",
            "kubernetes_version": "v1.29.1",
            "node_shape": "VM.Standard.E4.Flex",
            "node_shape_config": {"ocpus": 2.0, "memory_in_gbs": 16.0},
            "node_source_details": {
                "image_id": "ocid1.image.oc1..example",
                "boot_volume_size_in_gbs": None,
            },
            "node_config_details": {
                "size": 3,
                "nsg_ids": None,
                "kms_key_id": None,
                "is_pv_encryption_in_transit_enabled": False,
                "freeform_tags": None,
                "defined_tags": None,
                "placement_configs": [
                    {
                        "availability_domain": "AD-1",
                        "subnet_id": "ocid1.subnet.oc1..nodes",
                        "capacity_reservation_id": None,
                        "fault_domains": None,
                    }
                ],
                "node_pool_pod_network_option_details": {
                    "cni_type": "OCI_VCN_IP_NATIVE",
                    "max_pods_per_node": 31,
                    "pod_nsg_ids": None,
                    "pod_subnet_ids": ["ocid1.subnet.oc1..pods"],
                },
            },
            "subnet_ids": None,
            "quantity_per_subnet": None,
            "initial_node_labels": [{"key": "team", "value": "platform"}],
            "ssh_public_key": "ssh-rsa AAAA",
            "node_metadata": {"role": "worker"},
            "node_eviction_node_pool_settings": None,
            "node_pool_cycling_details": None,
            "freeform_tags": {"env": "dev"},
            "defined_tags": None,
        }
    )

    assert isinstance(details, FakeModel)
    assert details.name == "example-pool"
    assert details.cluster_id == "ocid1.cluster.oc1..example"
    assert details.node_shape == "VM.Standard.E4.Flex"
    assert not hasattr(details, "defined_tags")
    assert details.freeform_tags == {"env": "dev"}
    # Nested models are constructed and unset values filtered out.
    assert details.node_shape_config.ocpus == 2.0
    assert details.node_source_details.image_id == "ocid1.image.oc1..example"
    assert not hasattr(details.node_source_details, "boot_volume_size_in_gbs")
    # False is preserved; only None is filtered.
    assert details.node_config_details.is_pv_encryption_in_transit_enabled is False
    assert not hasattr(details.node_config_details, "nsg_ids")
    assert details.node_config_details.size == 3
    placement = details.node_config_details.placement_configs[0]
    assert placement.availability_domain == "AD-1"
    assert not hasattr(placement, "capacity_reservation_id")
    pod_network = details.node_config_details.node_pool_pod_network_option_details
    assert pod_network.max_pods_per_node == 31
    assert pod_network.pod_subnet_ids == ["ocid1.subnet.oc1..pods"]
    assert details.initial_node_labels[0].key == "team"
    assert details.node_metadata == {"role": "worker"}


def test_build_create_node_pool_details_omits_unset_nested(monkeypatch):
    install_fake_oci(monkeypatch)

    node_pool_module = load_collection_module("oci_oke_node_pool")
    details = node_pool_module.build_create_node_pool_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "cluster_id": "ocid1.cluster.oc1..example",
            "name": "example-pool",
            "kubernetes_version": "v1.29.1",
            "node_shape": "VM.Standard.E4.Flex",
            "node_shape_config": None,
            "node_source_details": None,
            "node_config_details": None,
            "subnet_ids": None,
            "quantity_per_subnet": None,
            "initial_node_labels": None,
            "ssh_public_key": None,
            "node_metadata": None,
            "node_eviction_node_pool_settings": None,
            "node_pool_cycling_details": None,
            "freeform_tags": None,
            "defined_tags": None,
        }
    )

    assert not hasattr(details, "node_shape_config")
    assert not hasattr(details, "node_source_details")
    assert not hasattr(details, "node_config_details")
    assert not hasattr(details, "initial_node_labels")


def test_build_pod_network_option_flannel_drops_ip_native_fields(monkeypatch):
    install_fake_oci(monkeypatch)

    node_pool_module = load_collection_module("oci_oke_node_pool")
    details = node_pool_module.build_create_node_pool_details(
        {
            "compartment_id": "c",
            "cluster_id": "cl",
            "name": "pool",
            "kubernetes_version": "v1.29.1",
            "node_shape": "VM",
            "node_config_details": {
                "node_pool_pod_network_option_details": {
                    "cni_type": "FLANNEL_OVERLAY",
                    "max_pods_per_node": 31,
                    "pod_nsg_ids": None,
                    "pod_subnet_ids": None,
                },
            },
        }
    )

    pod_network = details.node_config_details.node_pool_pod_network_option_details
    # Flannel overlay carries no pod networking fields, so they are dropped.
    assert not hasattr(pod_network, "max_pods_per_node")


def test_validate_create_request_requires_node_source_details(monkeypatch):
    install_fake_oci(monkeypatch)

    node_pool_module = load_collection_module("oci_oke_node_pool")
    instance = make_node_pool_module(
        node_pool_module,
        {
            "compartment_id": "c",
            "cluster_id": "cl",
            "name": "pool",
            "node_shape": "VM",
            "node_source_details": None,
        },
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "node_source_details" in exc_info.value.payload["msg"]


def test_needs_update_returns_true_for_name_change(monkeypatch):
    install_fake_oci(monkeypatch)

    node_pool_module = load_collection_module("oci_oke_node_pool")
    instance = make_node_pool_module(node_pool_module, {"name": "renamed"})
    resource = FakeModel(id="ocid1.nodepool.oc1..n1", name="original")

    assert instance.needs_update(resource) is True


def test_needs_update_returns_false_for_matching_name(monkeypatch):
    install_fake_oci(monkeypatch)

    node_pool_module = load_collection_module("oci_oke_node_pool")
    instance = make_node_pool_module(node_pool_module, {"name": "same"})
    resource = FakeModel(id="ocid1.nodepool.oc1..n1", name="same")

    assert instance.needs_update(resource) is False


def test_needs_update_returns_true_for_tag_change(monkeypatch):
    install_fake_oci(monkeypatch)

    node_pool_module = load_collection_module("oci_oke_node_pool")
    instance = make_node_pool_module(
        node_pool_module, {"freeform_tags": {"env": "prod"}}
    )
    resource = FakeModel(
        id="ocid1.nodepool.oc1..n1",
        name="n1",
        freeform_tags={"env": "dev"},
    )

    assert instance.needs_update(resource) is True


@pytest.mark.parametrize(
    "params, resource_attrs, expected_field",
    [
        (
            {"compartment_id": "ocid1.compartment.oc1..other"},
            {"compartment_id": "ocid1.compartment.oc1..example"},
            "compartment_id",
        ),
        (
            {"cluster_id": "ocid1.cluster.oc1..other"},
            {"cluster_id": "ocid1.cluster.oc1..example"},
            "cluster_id",
        ),
    ],
)
def test_needs_update_rejects_immutable_field_drift(
    monkeypatch, params, resource_attrs, expected_field
):
    install_fake_oci(monkeypatch)

    node_pool_module = load_collection_module("oci_oke_node_pool")
    instance = make_node_pool_module(node_pool_module, params)
    resource = FakeModel(id="ocid1.nodepool.oc1..n1", **resource_attrs)

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert expected_field in exc_info.value.payload["msg"]


def test_needs_update_false_when_kubernetes_version_matches(monkeypatch):
    install_fake_oci(monkeypatch)

    node_pool_module = load_collection_module("oci_oke_node_pool")
    instance = make_node_pool_module(
        node_pool_module, {"kubernetes_version": "v1.29.1"}
    )
    resource = FakeModel(id="ocid1.nodepool.oc1..n1", kubernetes_version="v1.29.1")

    assert instance.needs_update(resource) is False


def test_needs_update_true_for_kubernetes_upgrade(monkeypatch):
    install_fake_oci(monkeypatch)

    node_pool_module = load_collection_module("oci_oke_node_pool")
    instance = make_node_pool_module(
        node_pool_module, {"kubernetes_version": "v1.30.1"}
    )
    resource = FakeModel(id="ocid1.nodepool.oc1..n1", kubernetes_version="v1.29.1")

    assert instance.needs_update(resource) is True


def test_needs_update_true_when_node_config_size_changes(monkeypatch):
    install_fake_oci(monkeypatch)

    node_pool_module = load_collection_module("oci_oke_node_pool")
    instance = make_node_pool_module(
        node_pool_module,
        {"node_config_details": {"size": 5, "placement_configs": None}},
    )
    resource = FakeModel(
        id="ocid1.nodepool.oc1..n1",
        node_config_details={"size": 3, "placement_configs": []},
    )

    assert instance.needs_update(resource) is True


def test_needs_update_false_when_node_config_subset_matches(monkeypatch):
    install_fake_oci(monkeypatch)

    node_pool_module = load_collection_module("oci_oke_node_pool")
    # Caller sets only size; omitted sub-options must not force a change even
    # though the current config has extra populated fields.
    instance = make_node_pool_module(
        node_pool_module,
        {"node_config_details": {"size": 3, "placement_configs": None}},
    )
    resource = FakeModel(
        id="ocid1.nodepool.oc1..n1",
        node_config_details={
            "size": 3,
            "kms_key_id": "ocid1.key.oc1..k",
            "placement_configs": [
                {"availability_domain": "AD-1", "subnet_id": "s1"}
            ],
        },
    )

    assert instance.needs_update(resource) is False


def test_needs_update_false_when_placement_matches_despite_oci_extras(monkeypatch):
    install_fake_oci(monkeypatch)

    node_pool_module = load_collection_module("oci_oke_node_pool")
    # Caller sets availability_domain + subnet_id; OCI echoes extra populated
    # fields (fault_domains) that must not register as drift.
    instance = make_node_pool_module(
        node_pool_module,
        {
            "node_config_details": {
                "size": 3,
                "placement_configs": [
                    {
                        "availability_domain": "AD-1",
                        "subnet_id": "s1",
                        "capacity_reservation_id": None,
                        "fault_domains": None,
                    }
                ],
            }
        },
    )
    resource = FakeModel(
        id="ocid1.nodepool.oc1..n1",
        node_config_details={
            "size": 3,
            "placement_configs": [
                {
                    "availability_domain": "AD-1",
                    "subnet_id": "s1",
                    "capacity_reservation_id": None,
                    "fault_domains": ["FD-1", "FD-2"],
                }
            ],
        },
    )

    assert instance.needs_update(resource) is False


def test_needs_update_true_when_placement_subnet_changes(monkeypatch):
    install_fake_oci(monkeypatch)

    node_pool_module = load_collection_module("oci_oke_node_pool")
    instance = make_node_pool_module(
        node_pool_module,
        {
            "node_config_details": {
                "placement_configs": [
                    {
                        "availability_domain": "AD-1",
                        "subnet_id": "s2",
                        "capacity_reservation_id": None,
                        "fault_domains": None,
                    }
                ]
            }
        },
    )
    resource = FakeModel(
        id="ocid1.nodepool.oc1..n1",
        node_config_details={
            "placement_configs": [
                {"availability_domain": "AD-1", "subnet_id": "s1"}
            ]
        },
    )

    assert instance.needs_update(resource) is True


def test_needs_update_false_when_sibling_placement_supplies_extra_key(monkeypatch):
    install_fake_oci(monkeypatch)

    node_pool_module = load_collection_module("oci_oke_node_pool")
    # One desired placement supplies fault_domains; the other omits it. The
    # omitted key must not be required of the sibling entry just because a
    # neighbor supplied it, even though OCI populates it on both current entries.
    instance = make_node_pool_module(
        node_pool_module,
        {
            "node_config_details": {
                "size": 2,
                "placement_configs": [
                    {
                        "availability_domain": "AD-1",
                        "subnet_id": "s1",
                        "capacity_reservation_id": None,
                        "fault_domains": ["FD-1"],
                    },
                    {
                        "availability_domain": "AD-2",
                        "subnet_id": "s2",
                        "capacity_reservation_id": None,
                        "fault_domains": None,
                    },
                ],
            }
        },
    )
    resource = FakeModel(
        id="ocid1.nodepool.oc1..n1",
        node_config_details={
            "size": 2,
            "placement_configs": [
                {
                    "availability_domain": "AD-1",
                    "subnet_id": "s1",
                    "capacity_reservation_id": None,
                    "fault_domains": ["FD-1"],
                },
                {
                    "availability_domain": "AD-2",
                    "subnet_id": "s2",
                    "capacity_reservation_id": None,
                    "fault_domains": ["FD-2", "FD-3"],
                },
            ],
        },
    )

    assert instance.needs_update(resource) is False


def test_needs_update_true_when_node_shape_config_changes(monkeypatch):
    install_fake_oci(monkeypatch)

    node_pool_module = load_collection_module("oci_oke_node_pool")
    instance = make_node_pool_module(
        node_pool_module,
        {"node_shape_config": {"ocpus": 4.0, "memory_in_gbs": None}},
    )
    resource = FakeModel(
        id="ocid1.nodepool.oc1..n1",
        node_shape_config={"ocpus": 2.0, "memory_in_gbs": 16.0},
    )

    assert instance.needs_update(resource) is True


def test_needs_update_false_when_initial_node_labels_reordered(monkeypatch):
    install_fake_oci(monkeypatch)

    node_pool_module = load_collection_module("oci_oke_node_pool")
    instance = make_node_pool_module(
        node_pool_module,
        {
            "initial_node_labels": [
                {"key": "team", "value": "platform"},
                {"key": "tier", "value": "backend"},
            ]
        },
    )
    resource = FakeModel(
        id="ocid1.nodepool.oc1..n1",
        # Order-insensitive: reversed order still matches.
        initial_node_labels=[
            {"key": "tier", "value": "backend"},
            {"key": "team", "value": "platform"},
        ],
    )

    assert instance.needs_update(resource) is False


def test_needs_update_false_when_subnet_ids_reordered(monkeypatch):
    install_fake_oci(monkeypatch)

    node_pool_module = load_collection_module("oci_oke_node_pool")
    instance = make_node_pool_module(
        node_pool_module, {"subnet_ids": ["s2", "s1"]}
    )
    resource = FakeModel(id="ocid1.nodepool.oc1..n1", subnet_ids=["s1", "s2"])

    assert instance.needs_update(resource) is False


def test_node_pool_id_from_work_request(monkeypatch):
    install_fake_oci(monkeypatch)

    node_pool_module = load_collection_module("oci_oke_node_pool")
    instance = make_node_pool_module(node_pool_module, {})
    work_request = FakeModel(
        resources=[
            FakeModel(entity_type="cluster", identifier="ocid1.cluster.oc1..c1"),
            FakeModel(entity_type="NODEPOOL", identifier="ocid1.nodepool.oc1..n1"),
        ]
    )

    assert (
        instance._node_pool_id_from_work_request(work_request)
        == "ocid1.nodepool.oc1..n1"
    )


def test_create_resource_waits_and_defaults_version_from_cluster(monkeypatch):
    install_fake_oci(monkeypatch)

    node_pool_module = load_collection_module("oci_oke_node_pool")
    create_calls = []
    response = FakeResponse(data=None, headers={"opc-work-request-id": "wr1"})

    def create_node_pool(create_node_pool_details):
        create_calls.append(create_node_pool_details)
        return response

    def get_cluster(cluster_id):
        return FakeResponse(FakeModel(kubernetes_version="v1.29.1"))

    instance = make_node_pool_module(
        node_pool_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "cluster_id": "ocid1.cluster.oc1..example",
            "name": "example-pool",
            "node_shape": "VM.Standard.E4.Flex",
            "kubernetes_version": None,
            "wait": True,
        },
        client=types.SimpleNamespace(
            create_node_pool=create_node_pool,
            get_cluster=get_cluster,
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, *a, **k: fn(*a, **k))
    monkeypatch.setattr(
        instance,
        "wait_for_work_request",
        lambda client, work_request_id: FakeModel(
            status="SUCCEEDED",
            resources=[
                FakeModel(
                    entity_type="nodepool", identifier="ocid1.nodepool.oc1..n1"
                )
            ],
        ),
    )
    monkeypatch.setattr(
        instance,
        "get_resource_by_id",
        lambda node_pool_id: FakeModel(id=node_pool_id, lifecycle_state="ACTIVE"),
    )

    resource = instance.create_resource()

    # kubernetes_version was defaulted from the parent cluster.
    assert create_calls[0].kubernetes_version == "v1.29.1"
    assert resource.id == "ocid1.nodepool.oc1..n1"
    assert resource.lifecycle_state == "ACTIVE"


def test_create_resource_without_wait_resolves_from_work_request(monkeypatch):
    install_fake_oci(monkeypatch)

    node_pool_module = load_collection_module("oci_oke_node_pool")
    response = FakeResponse(data=None, headers={"opc-work-request-id": "wr1"})
    work_request = FakeModel(
        resources=[
            FakeModel(entity_type="nodepool", identifier="ocid1.nodepool.oc1..n1")
        ]
    )

    instance = make_node_pool_module(
        node_pool_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "cluster_id": "ocid1.cluster.oc1..example",
            "name": "example-pool",
            "node_shape": "VM.Standard.E4.Flex",
            "kubernetes_version": "v1.29.1",
            "wait": False,
        },
        client=types.SimpleNamespace(
            create_node_pool=lambda create_node_pool_details: response,
            get_work_request=lambda work_request_id: FakeResponse(data=work_request),
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, *a, **k: fn(*a, **k))

    def fail_if_waited(*args, **kwargs):
        raise AssertionError("wait_for_work_request should not run when wait=False")

    monkeypatch.setattr(instance, "wait_for_work_request", fail_if_waited)
    monkeypatch.setattr(instance, "get_resource_by_id", lambda node_pool_id: None)

    resource = instance.create_resource()

    assert resource == {"id": "ocid1.nodepool.oc1..n1"}


def test_update_resource_scales_node_config_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    node_pool_module = load_collection_module("oci_oke_node_pool")
    update_calls = []
    response = FakeResponse(data=None, headers={"opc-work-request-id": "wr2"})

    def update_node_pool(node_pool_id, update_node_pool_details):
        update_calls.append((node_pool_id, update_node_pool_details))
        return response

    resource = FakeModel(
        id="ocid1.nodepool.oc1..n1",
        name="n1",
        node_config_details={"size": 3},
    )
    instance = make_node_pool_module(
        node_pool_module,
        {
            "node_config_details": {"size": 5, "placement_configs": None},
            "wait": True,
        },
        client=types.SimpleNamespace(update_node_pool=update_node_pool),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, *a, **k: fn(*a, **k))
    waited = []
    monkeypatch.setattr(
        instance,
        "wait_for_work_request",
        lambda client, work_request_id: waited.append(work_request_id),
    )
    monkeypatch.setattr(
        instance,
        "get_resource_by_id",
        lambda node_pool_id: FakeModel(id=node_pool_id, lifecycle_state="ACTIVE"),
    )

    instance.update_resource(resource)

    sent_config = update_calls[0][1].node_config_details
    assert sent_config.size == 5
    assert waited == ["wr2"]


def test_update_resource_no_change_returns_resource(monkeypatch):
    install_fake_oci(monkeypatch)

    node_pool_module = load_collection_module("oci_oke_node_pool")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("update_node_pool should not run without changes")

    resource = FakeModel(id="ocid1.nodepool.oc1..n1", name="n1")
    instance = make_node_pool_module(
        node_pool_module,
        {"name": "n1", "wait": True},
        client=types.SimpleNamespace(update_node_pool=fail_if_called),
    )

    assert instance.update_resource(resource) is resource


def test_delete_resource_waits_for_work_request(monkeypatch):
    install_fake_oci(monkeypatch)

    node_pool_module = load_collection_module("oci_oke_node_pool")
    delete_calls = []
    waited = []
    response = FakeResponse(data=None, headers={"opc-work-request-id": "wr1"})

    def delete_node_pool(node_pool_id):
        delete_calls.append(node_pool_id)
        return response

    resource = FakeModel(id="ocid1.nodepool.oc1..n1")
    instance = make_node_pool_module(
        node_pool_module,
        {"wait": True},
        client=types.SimpleNamespace(delete_node_pool=delete_node_pool),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, *a, **k: fn(*a, **k))
    monkeypatch.setattr(
        instance,
        "wait_for_work_request",
        lambda client, work_request_id: waited.append(work_request_id),
    )
    monkeypatch.setattr(
        instance,
        "get_resource_by_id",
        lambda node_pool_id: FakeModel(id=node_pool_id, lifecycle_state="DELETED"),
    )

    result = instance.delete_resource(resource)

    assert delete_calls == ["ocid1.nodepool.oc1..n1"]
    assert waited == ["wr1"]
    assert result.lifecycle_state == "DELETED"


def test_delete_resource_without_wait_skips_work_request(monkeypatch):
    install_fake_oci(monkeypatch)

    node_pool_module = load_collection_module("oci_oke_node_pool")
    delete_calls = []
    response = FakeResponse(data=None, headers={"opc-work-request-id": "wr1"})

    def delete_node_pool(node_pool_id):
        delete_calls.append(node_pool_id)
        return response

    resource = FakeModel(id="ocid1.nodepool.oc1..n1")
    instance = make_node_pool_module(
        node_pool_module,
        {"wait": False},
        client=types.SimpleNamespace(delete_node_pool=delete_node_pool),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, *a, **k: fn(*a, **k))
    monkeypatch.setattr(instance, "get_resource_by_id", lambda node_pool_id: None)

    def fail_if_waited(*args, **kwargs):
        raise AssertionError("wait_for_work_request should not run when wait=False")

    monkeypatch.setattr(instance, "wait_for_work_request", fail_if_waited)

    result = instance.delete_resource(resource)

    assert delete_calls == ["ocid1.nodepool.oc1..n1"]
    assert result == {"id": "ocid1.nodepool.oc1..n1"}
