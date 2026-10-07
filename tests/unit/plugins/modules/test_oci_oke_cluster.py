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


CLUSTER_MODEL_NAMES = (
    "CreateClusterDetails",
    "UpdateClusterDetails",
    "CreateClusterEndpointConfigDetails",
    "CreateImagePolicyConfigDetails",
    "UpdateImagePolicyConfigDetails",
    "KeyDetails",
    "ClusterPodNetworkOptionDetails",
    "ClusterCreateOptions",
    "KubernetesNetworkConfig",
    "AddOnOptions",
    "AdmissionControllerOptions",
)


def install_fake_oci(monkeypatch):
    oci_module, service_error = shared_install_fake_oci(monkeypatch)
    oci_module.container_engine = types.SimpleNamespace(
        ContainerEngineClient=type("FakeContainerEngineClient", (), {}),
        models=types.SimpleNamespace(
            **{model_name: FakeModel for model_name in CLUSTER_MODEL_NAMES}
        ),
    )
    return oci_module, service_error


def make_cluster_module(module_obj, params, client=None, check_mode=False):
    return make_module_instance(
        module_obj,
        "OciOkeClusterModule",
        params,
        client=client,
        check_mode=check_mode,
    )


def test_main_wires_argument_spec_and_runs_module(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_oke_cluster")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        captured["supports_check_mode"] = kwargs.get("supports_check_mode")
        return DummyModule({})

    class FakeClusterModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciOkeClusterModule", FakeClusterModule)

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["supports_check_mode"] is True
    spec = captured["argument_spec"]
    # name/compartment_id come from the shared OCI_COMMON_ARGS.
    assert spec["name"] == {"type": "str"}
    assert spec["compartment_id"] == {"type": "str"}
    # cluster-specific params.
    assert spec["cluster_id"] == {"type": "str", "aliases": ["id"]}
    assert spec["vcn_id"] == {"type": "str"}
    assert spec["kubernetes_version"] == {"type": "str"}
    assert spec["type"] == {
        "type": "str",
        "choices": ["BASIC_CLUSTER", "ENHANCED_CLUSTER"],
    }
    assert spec["endpoint_config"]["type"] == "dict"
    assert spec["endpoint_config"]["options"]["nsg_ids"] == {
        "type": "list",
        "elements": "str",
    }
    assert spec["cluster_pod_network_options"]["options"]["cni_type"]["choices"] == [
        "OCI_VCN_IP_NATIVE",
        "FLANNEL_OVERLAY",
    ]


def test_class_metadata(monkeypatch):
    install_fake_oci(monkeypatch)

    cluster_module = load_collection_module("oci_oke_cluster")

    assert cluster_module.OciOkeClusterModule.resource_id_param == "cluster_id"
    assert cluster_module.OciOkeClusterModule.list_resource_method == "list_clusters"
    assert cluster_module.OciOkeClusterModule.name_response_field == "name"
    assert cluster_module.OciOkeClusterModule.create_resource_name == "cluster"


def test_build_create_cluster_details_maps_nested_models(monkeypatch):
    install_fake_oci(monkeypatch)

    cluster_module = load_collection_module("oci_oke_cluster")
    details = cluster_module.build_create_cluster_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-cluster",
            "vcn_id": "ocid1.vcn.oc1..example",
            "kubernetes_version": "v1.29.1",
            "type": "ENHANCED_CLUSTER",
            "kms_key_id": None,
            "endpoint_config": {
                "subnet_id": "ocid1.subnet.oc1..endpoint",
                "nsg_ids": ["ocid1.nsg.oc1..a"],
                "is_public_ip_enabled": True,
            },
            "image_policy_config": {
                "is_policy_enabled": True,
                "key_details": [{"kms_key_id": "ocid1.key.oc1..k"}],
            },
            "cluster_pod_network_options": [{"cni_type": "OCI_VCN_IP_NATIVE"}],
            "options": {
                "service_lb_subnet_ids": ["ocid1.subnet.oc1..lb"],
                "ip_families": None,
                "kubernetes_network_config": {
                    "pods_cidr": "10.244.0.0/16",
                    "services_cidr": "10.96.0.0/16",
                },
                "add_ons": {
                    "is_kubernetes_dashboard_enabled": False,
                    "is_tiller_enabled": None,
                },
                "admission_controller_options": None,
            },
            "freeform_tags": {"env": "dev"},
            "defined_tags": None,
        }
    )

    assert isinstance(details, FakeModel)
    assert details.name == "example-cluster"
    assert details.vcn_id == "ocid1.vcn.oc1..example"
    assert details.kubernetes_version == "v1.29.1"
    assert details.type == "ENHANCED_CLUSTER"
    assert not hasattr(details, "kms_key_id")
    assert not hasattr(details, "defined_tags")
    assert details.freeform_tags == {"env": "dev"}
    # Nested models are constructed and unset values filtered out.
    assert details.endpoint_config.subnet_id == "ocid1.subnet.oc1..endpoint"
    assert details.endpoint_config.is_public_ip_enabled is True
    assert details.image_policy_config.is_policy_enabled is True
    assert details.image_policy_config.key_details[0].kms_key_id == "ocid1.key.oc1..k"
    assert details.cluster_pod_network_options[0].cni_type == "OCI_VCN_IP_NATIVE"
    assert details.options.service_lb_subnet_ids == ["ocid1.subnet.oc1..lb"]
    assert not hasattr(details.options, "ip_families")
    assert details.options.kubernetes_network_config.pods_cidr == "10.244.0.0/16"
    # False is preserved; only None is filtered.
    assert details.options.add_ons.is_kubernetes_dashboard_enabled is False
    assert not hasattr(details.options.add_ons, "is_tiller_enabled")
    assert not hasattr(details.options, "admission_controller_options")


def test_build_create_cluster_details_omits_unset_nested(monkeypatch):
    install_fake_oci(monkeypatch)

    cluster_module = load_collection_module("oci_oke_cluster")
    details = cluster_module.build_create_cluster_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-cluster",
            "vcn_id": "ocid1.vcn.oc1..example",
            "kubernetes_version": "v1.29.1",
            "type": None,
            "kms_key_id": None,
            "endpoint_config": None,
            "image_policy_config": None,
            "cluster_pod_network_options": None,
            "options": None,
            "freeform_tags": None,
            "defined_tags": None,
        }
    )

    assert not hasattr(details, "type")
    assert not hasattr(details, "endpoint_config")
    assert not hasattr(details, "options")
    assert not hasattr(details, "cluster_pod_network_options")


def test_needs_update_returns_true_for_name_change(monkeypatch):
    install_fake_oci(monkeypatch)

    cluster_module = load_collection_module("oci_oke_cluster")
    instance = make_cluster_module(cluster_module, {"name": "renamed"})
    resource = FakeModel(id="ocid1.cluster.oc1..c1", name="original")

    assert instance.needs_update(resource) is True


def test_needs_update_returns_false_for_matching_name(monkeypatch):
    install_fake_oci(monkeypatch)

    cluster_module = load_collection_module("oci_oke_cluster")
    instance = make_cluster_module(cluster_module, {"name": "same"})
    resource = FakeModel(id="ocid1.cluster.oc1..c1", name="same")

    assert instance.needs_update(resource) is False


def test_needs_update_returns_true_for_tag_change(monkeypatch):
    install_fake_oci(monkeypatch)

    cluster_module = load_collection_module("oci_oke_cluster")
    instance = make_cluster_module(
        cluster_module, {"freeform_tags": {"env": "prod"}}
    )
    resource = FakeModel(
        id="ocid1.cluster.oc1..c1",
        name="c1",
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
            {"vcn_id": "ocid1.vcn.oc1..other"},
            {"vcn_id": "ocid1.vcn.oc1..example"},
            "vcn_id",
        ),
        (
            {"type": "ENHANCED_CLUSTER"},
            {"type": "BASIC_CLUSTER"},
            "type",
        ),
    ],
)
def test_needs_update_rejects_immutable_field_drift(
    monkeypatch, params, resource_attrs, expected_field
):
    install_fake_oci(monkeypatch)

    cluster_module = load_collection_module("oci_oke_cluster")
    instance = make_cluster_module(cluster_module, params)
    resource = FakeModel(id="ocid1.cluster.oc1..c1", **resource_attrs)

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert expected_field in exc_info.value.payload["msg"]


def test_needs_update_false_when_kubernetes_version_matches(monkeypatch):
    install_fake_oci(monkeypatch)

    cluster_module = load_collection_module("oci_oke_cluster")
    instance = make_cluster_module(
        cluster_module, {"kubernetes_version": "v1.29.1"}
    )
    resource = FakeModel(
        id="ocid1.cluster.oc1..c1",
        kubernetes_version="v1.29.1",
        available_kubernetes_upgrades=["v1.30.1"],
    )

    assert instance.needs_update(resource) is False


def test_needs_update_true_for_allowed_kubernetes_upgrade(monkeypatch):
    install_fake_oci(monkeypatch)

    cluster_module = load_collection_module("oci_oke_cluster")
    instance = make_cluster_module(
        cluster_module, {"kubernetes_version": "v1.30.1"}
    )
    resource = FakeModel(
        id="ocid1.cluster.oc1..c1",
        kubernetes_version="v1.29.1",
        available_kubernetes_upgrades=["v1.30.1"],
    )

    assert instance.needs_update(resource) is True


def test_kubernetes_upgrade_rejects_version_outside_upgrade_path(monkeypatch):
    install_fake_oci(monkeypatch)

    cluster_module = load_collection_module("oci_oke_cluster")
    instance = make_cluster_module(
        cluster_module, {"kubernetes_version": "v1.31.1"}
    )
    resource = FakeModel(
        id="ocid1.cluster.oc1..c1",
        kubernetes_version="v1.29.1",
        available_kubernetes_upgrades=["v1.30.1"],
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    msg = exc_info.value.payload["msg"]
    assert "v1.31.1" in msg
    assert "v1.30.1" in msg


def test_kubernetes_upgrade_rejects_when_no_upgrades_available(monkeypatch):
    install_fake_oci(monkeypatch)

    cluster_module = load_collection_module("oci_oke_cluster")
    instance = make_cluster_module(
        cluster_module, {"kubernetes_version": "v1.30.1"}
    )
    resource = FakeModel(
        id="ocid1.cluster.oc1..c1",
        kubernetes_version="v1.29.1",
        available_kubernetes_upgrades=None,
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "none" in exc_info.value.payload["msg"]


def test_update_resource_upgrades_kubernetes_version(monkeypatch):
    install_fake_oci(monkeypatch)

    cluster_module = load_collection_module("oci_oke_cluster")
    update_calls = []
    response = FakeResponse(data=None, headers={"opc-work-request-id": "wr3"})

    def update_cluster(cluster_id, update_cluster_details):
        update_calls.append((cluster_id, update_cluster_details))
        return response

    resource = FakeModel(
        id="ocid1.cluster.oc1..c1",
        name="c1",
        kubernetes_version="v1.29.1",
        available_kubernetes_upgrades=["v1.30.1"],
    )
    instance = make_cluster_module(
        cluster_module,
        {"kubernetes_version": "v1.30.1", "wait": True},
        client=types.SimpleNamespace(update_cluster=update_cluster),
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
        lambda cluster_id: FakeModel(
            id=cluster_id, kubernetes_version="v1.30.1", lifecycle_state="ACTIVE"
        ),
    )

    updated = instance.update_resource(resource)

    assert update_calls[0][0] == "ocid1.cluster.oc1..c1"
    assert update_calls[0][1].kubernetes_version == "v1.30.1"
    assert waited == ["wr3"]
    assert updated.kubernetes_version == "v1.30.1"


def test_update_resource_no_change_when_version_matches(monkeypatch):
    install_fake_oci(monkeypatch)

    cluster_module = load_collection_module("oci_oke_cluster")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("update_cluster should not run without changes")

    resource = FakeModel(
        id="ocid1.cluster.oc1..c1",
        name="c1",
        kubernetes_version="v1.29.1",
        available_kubernetes_upgrades=["v1.30.1"],
    )
    instance = make_cluster_module(
        cluster_module,
        {"kubernetes_version": "v1.29.1", "wait": True},
        client=types.SimpleNamespace(update_cluster=fail_if_called),
    )

    assert instance.update_resource(resource) is resource


def test_needs_update_true_when_image_policy_enable_changes(monkeypatch):
    install_fake_oci(monkeypatch)

    cluster_module = load_collection_module("oci_oke_cluster")
    instance = make_cluster_module(
        cluster_module,
        {"image_policy_config": {"is_policy_enabled": True, "key_details": None}},
    )
    resource = FakeModel(
        id="ocid1.cluster.oc1..c1",
        image_policy_config={"is_policy_enabled": False, "key_details": []},
    )

    assert instance.needs_update(resource) is True


def test_needs_update_true_when_image_policy_keys_change(monkeypatch):
    install_fake_oci(monkeypatch)

    cluster_module = load_collection_module("oci_oke_cluster")
    instance = make_cluster_module(
        cluster_module,
        {
            "image_policy_config": {
                "is_policy_enabled": None,
                "key_details": [{"kms_key_id": "ocid1.key.oc1..b"}],
            }
        },
    )
    resource = FakeModel(
        id="ocid1.cluster.oc1..c1",
        image_policy_config={
            "is_policy_enabled": True,
            "key_details": [{"kms_key_id": "ocid1.key.oc1..a"}],
        },
    )

    assert instance.needs_update(resource) is True


def test_needs_update_false_when_image_policy_matches(monkeypatch):
    install_fake_oci(monkeypatch)

    cluster_module = load_collection_module("oci_oke_cluster")
    instance = make_cluster_module(
        cluster_module,
        {
            "image_policy_config": {
                "is_policy_enabled": True,
                "key_details": [
                    {"kms_key_id": "ocid1.key.oc1..a"},
                    {"kms_key_id": "ocid1.key.oc1..b"},
                ],
            }
        },
    )
    resource = FakeModel(
        id="ocid1.cluster.oc1..c1",
        image_policy_config={
            "is_policy_enabled": True,
            # Order-insensitive: reversed key order still matches.
            "key_details": [
                {"kms_key_id": "ocid1.key.oc1..b"},
                {"kms_key_id": "ocid1.key.oc1..a"},
            ],
        },
    )

    assert instance.needs_update(resource) is False


def test_needs_update_ignores_omitted_image_policy_subfields(monkeypatch):
    install_fake_oci(monkeypatch)

    cluster_module = load_collection_module("oci_oke_cluster")
    # Caller sets only is_policy_enabled, matching current; key_details omitted
    # must not force a change even though the cluster has keys.
    instance = make_cluster_module(
        cluster_module,
        {"image_policy_config": {"is_policy_enabled": True, "key_details": None}},
    )
    resource = FakeModel(
        id="ocid1.cluster.oc1..c1",
        image_policy_config={
            "is_policy_enabled": True,
            "key_details": [{"kms_key_id": "ocid1.key.oc1..a"}],
        },
    )

    assert instance.needs_update(resource) is False


def test_needs_update_true_when_image_policy_absent_on_cluster(monkeypatch):
    install_fake_oci(monkeypatch)

    cluster_module = load_collection_module("oci_oke_cluster")
    instance = make_cluster_module(
        cluster_module,
        {"image_policy_config": {"is_policy_enabled": True, "key_details": None}},
    )
    resource = FakeModel(id="ocid1.cluster.oc1..c1", image_policy_config=None)

    assert instance.needs_update(resource) is True


def test_update_resource_reconciles_image_policy_config(monkeypatch):
    install_fake_oci(monkeypatch)

    cluster_module = load_collection_module("oci_oke_cluster")
    update_calls = []
    response = FakeResponse(data=None, headers={"opc-work-request-id": "wr4"})

    def update_cluster(cluster_id, update_cluster_details):
        update_calls.append((cluster_id, update_cluster_details))
        return response

    resource = FakeModel(
        id="ocid1.cluster.oc1..c1",
        name="c1",
        image_policy_config={"is_policy_enabled": False, "key_details": []},
    )
    instance = make_cluster_module(
        cluster_module,
        {
            "image_policy_config": {
                "is_policy_enabled": True,
                "key_details": [{"kms_key_id": "ocid1.key.oc1..a"}],
            },
            "wait": True,
        },
        client=types.SimpleNamespace(update_cluster=update_cluster),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, *a, **k: fn(*a, **k))
    monkeypatch.setattr(
        instance,
        "wait_for_work_request",
        lambda client, work_request_id: None,
    )
    monkeypatch.setattr(
        instance,
        "get_resource_by_id",
        lambda cluster_id: FakeModel(id=cluster_id, lifecycle_state="ACTIVE"),
    )

    instance.update_resource(resource)

    sent_policy = update_calls[0][1].image_policy_config
    assert sent_policy.is_policy_enabled is True
    assert sent_policy.key_details[0].kms_key_id == "ocid1.key.oc1..a"


def test_cluster_id_from_work_request(monkeypatch):
    install_fake_oci(monkeypatch)

    cluster_module = load_collection_module("oci_oke_cluster")
    instance = make_cluster_module(cluster_module, {})
    work_request = FakeModel(
        resources=[
            FakeModel(entity_type="nodepool", identifier="ocid1.nodepool.oc1..n"),
            FakeModel(entity_type="CLUSTER", identifier="ocid1.cluster.oc1..c1"),
        ]
    )

    assert instance._cluster_id_from_work_request(work_request) == "ocid1.cluster.oc1..c1"


def test_cluster_id_from_work_request_missing_returns_none(monkeypatch):
    install_fake_oci(monkeypatch)

    cluster_module = load_collection_module("oci_oke_cluster")
    instance = make_cluster_module(cluster_module, {})
    work_request = FakeModel(resources=[FakeModel(entity_type="nodepool", identifier="n")])

    assert instance._cluster_id_from_work_request(work_request) is None


def test_create_resource_waits_for_work_request(monkeypatch):
    install_fake_oci(monkeypatch)

    cluster_module = load_collection_module("oci_oke_cluster")
    create_calls = []
    response = FakeResponse(data=None, headers={"opc-work-request-id": "wr1"})

    def create_cluster(create_cluster_details):
        create_calls.append(create_cluster_details)
        return response

    instance = make_cluster_module(
        cluster_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-cluster",
            "vcn_id": "ocid1.vcn.oc1..example",
            "kubernetes_version": "v1.29.1",
            "wait": True,
        },
        client=types.SimpleNamespace(create_cluster=create_cluster),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, *a, **k: fn(*a, **k))
    monkeypatch.setattr(
        instance,
        "wait_for_work_request",
        lambda client, work_request_id: FakeModel(
            status="SUCCEEDED",
            resources=[
                FakeModel(entity_type="cluster", identifier="ocid1.cluster.oc1..c1")
            ],
        ),
    )
    monkeypatch.setattr(
        instance,
        "get_resource_by_id",
        lambda cluster_id: FakeModel(id=cluster_id, lifecycle_state="ACTIVE"),
    )

    resource = instance.create_resource()

    assert create_calls[0].name == "example-cluster"
    assert resource.id == "ocid1.cluster.oc1..c1"
    assert resource.lifecycle_state == "ACTIVE"


def test_create_resource_without_wait_resolves_from_work_request(monkeypatch):
    install_fake_oci(monkeypatch)

    cluster_module = load_collection_module("oci_oke_cluster")
    response = FakeResponse(data=None, headers={"opc-work-request-id": "wr1"})
    work_request = FakeModel(
        resources=[FakeModel(entity_type="cluster", identifier="ocid1.cluster.oc1..c1")]
    )

    instance = make_cluster_module(
        cluster_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-cluster",
            "vcn_id": "ocid1.vcn.oc1..example",
            "kubernetes_version": "v1.29.1",
            "wait": False,
        },
        client=types.SimpleNamespace(
            create_cluster=lambda create_cluster_details: response,
            get_work_request=lambda work_request_id: FakeResponse(data=work_request),
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, *a, **k: fn(*a, **k))

    def fail_if_waited(*args, **kwargs):
        raise AssertionError("wait_for_work_request should not run when wait=False")

    monkeypatch.setattr(instance, "wait_for_work_request", fail_if_waited)
    monkeypatch.setattr(instance, "get_resource_by_id", lambda cluster_id: None)

    resource = instance.create_resource()

    # No live cluster yet, so an ID-only result is returned.
    assert resource == {"id": "ocid1.cluster.oc1..c1"}


def test_update_resource_renames_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    cluster_module = load_collection_module("oci_oke_cluster")
    update_calls = []
    response = FakeResponse(data=None, headers={"opc-work-request-id": "wr2"})

    def update_cluster(cluster_id, update_cluster_details):
        update_calls.append((cluster_id, update_cluster_details))
        return response

    resource = FakeModel(id="ocid1.cluster.oc1..c1", name="old")
    instance = make_cluster_module(
        cluster_module,
        {"name": "new", "wait": True},
        client=types.SimpleNamespace(update_cluster=update_cluster),
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
        lambda cluster_id: FakeModel(id=cluster_id, name="new", lifecycle_state="ACTIVE"),
    )

    updated = instance.update_resource(resource)

    assert update_calls[0][0] == "ocid1.cluster.oc1..c1"
    assert update_calls[0][1].name == "new"
    assert waited == ["wr2"]
    assert updated.name == "new"


def test_delete_resource_calls_delete_cluster(monkeypatch):
    install_fake_oci(monkeypatch)

    cluster_module = load_collection_module("oci_oke_cluster")
    delete_calls = []

    def delete_cluster(cluster_id):
        delete_calls.append(cluster_id)
        return FakeResponse(data=None)

    resource = FakeModel(id="ocid1.cluster.oc1..c1")
    instance = make_cluster_module(
        cluster_module,
        {"wait": True},
        client=types.SimpleNamespace(delete_cluster=delete_cluster),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, *a, **k: fn(*a, **k))
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: None,
    )

    instance.delete_resource(resource)

    assert delete_calls == ["ocid1.cluster.oc1..c1"]
