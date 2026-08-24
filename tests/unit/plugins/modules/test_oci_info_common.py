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


INFO_CASES = (
    {
        "module_name": "oci_network_vcn_info",
        "class_name": "OciNetworkVcnInfoModule",
        "results_key": "vcns",
        "id_param": "vcn_id",
        "id_value": "ocid1.vcn.oc1..example",
        "missing_id": "ocid1.vcn.oc1..missing",
        "get_method": "get_vcn",
        "list_method": "list_vcns",
        "list_params": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-vcn",
            "lifecycle_state": "AVAILABLE",
        },
        "expected_list_kwargs": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "lifecycle_state": "AVAILABLE",
        },
        "run_resource": FakeModel(
            id="ocid1.vcn.oc1..example",
            display_name="example-vcn",
            lifecycle_state="AVAILABLE",
        ),
        "expected_run_payload": {
            "id": "ocid1.vcn.oc1..example",
            "name": "example-vcn",
            "lifecycle_state": "AVAILABLE",
        },
    },
    {
        "module_name": "oci_network_drg_info",
        "class_name": "OciNetworkDrgInfoModule",
        "results_key": "drgs",
        "id_param": "drg_id",
        "id_value": "ocid1.drg.oc1..example",
        "missing_id": "ocid1.drg.oc1..missing",
        "get_method": "get_drg",
        "list_method": "list_drgs",
        "list_params": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-drg",
        },
        "expected_list_kwargs": {
            "compartment_id": "ocid1.compartment.oc1..example",
        },
        "run_resource": FakeModel(
            id="ocid1.drg.oc1..example",
            display_name="example-drg",
            lifecycle_state="AVAILABLE",
        ),
        "expected_run_payload": {
            "id": "ocid1.drg.oc1..example",
            "name": "example-drg",
            "lifecycle_state": "AVAILABLE",
        },
    },
    {
        "module_name": "oci_network_subnet_info",
        "class_name": "OciNetworkSubnetInfoModule",
        "results_key": "subnets",
        "id_param": "subnet_id",
        "id_value": "ocid1.subnet.oc1..example",
        "missing_id": "ocid1.subnet.oc1..missing",
        "get_method": "get_subnet",
        "list_method": "list_subnets",
        "list_params": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-subnet",
            "lifecycle_state": "AVAILABLE",
        },
        "expected_list_kwargs": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "lifecycle_state": "AVAILABLE",
        },
        "run_resource": FakeModel(
            id="ocid1.subnet.oc1..example",
            display_name="example-subnet",
            lifecycle_state="AVAILABLE",
            vcn_id="ocid1.vcn.oc1..example",
        ),
        "expected_run_payload": {
            "id": "ocid1.subnet.oc1..example",
            "name": "example-subnet",
            "lifecycle_state": "AVAILABLE",
            "vcn_id": "ocid1.vcn.oc1..example",
        },
    },
    {
        "module_name": "oci_image_info",
        "class_name": "OciImageInfoModule",
        "results_key": "images",
        "id_param": "image_id",
        "id_value": "ocid1.image.oc1..example",
        "missing_id": "ocid1.image.oc1..missing",
        "get_method": "get_image",
        "list_method": "list_images",
        "list_params": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-image",
            "operating_system": "Oracle Linux",
            "operating_system_version": "9",
            "shape": "VM.Standard.E4.Flex",
            "lifecycle_state": "AVAILABLE",
        },
        "expected_list_kwargs": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "operating_system": "Oracle Linux",
            "operating_system_version": "9",
            "shape": "VM.Standard.E4.Flex",
            "lifecycle_state": "AVAILABLE",
        },
        "run_resource": FakeModel(
            id="ocid1.image.oc1..example",
            display_name="example-image",
            compartment_id="ocid1.compartment.oc1..example",
            operating_system="Oracle Linux",
            operating_system_version="9",
            lifecycle_state="AVAILABLE",
            base_image_id="ocid1.image.oc1..base",
        ),
        "expected_run_payload": {
            "id": "ocid1.image.oc1..example",
            "name": "example-image",
            "compartment_id": "ocid1.compartment.oc1..example",
            "operating_system": "Oracle Linux",
            "operating_system_version": "9",
            "lifecycle_state": "AVAILABLE",
            "base_image_id": "ocid1.image.oc1..base",
        },
    },
    {
        "module_name": "oci_network_nat_gateway_info",
        "class_name": "OciNetworkNatGatewayInfoModule",
        "results_key": "nat_gateways",
        "id_param": "nat_gateway_id",
        "id_value": "ocid1.natgateway.oc1..example",
        "missing_id": "ocid1.natgateway.oc1..missing",
        "get_method": "get_nat_gateway",
        "list_method": "list_nat_gateways",
        "list_params": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-nat-gateway",
            "lifecycle_state": "AVAILABLE",
        },
        "expected_list_kwargs": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "lifecycle_state": "AVAILABLE",
        },
        "run_resource": FakeModel(
            id="ocid1.natgateway.oc1..example",
            display_name="example-nat-gateway",
            lifecycle_state="AVAILABLE",
            vcn_id="ocid1.vcn.oc1..example",
        ),
        "expected_run_payload": {
            "id": "ocid1.natgateway.oc1..example",
            "name": "example-nat-gateway",
            "lifecycle_state": "AVAILABLE",
            "vcn_id": "ocid1.vcn.oc1..example",
        },
    },
    {
        "module_name": "oci_network_security_list_info",
        "class_name": "OciNetworkSecurityListInfoModule",
        "results_key": "security_lists",
        "id_param": "security_list_id",
        "id_value": "ocid1.securitylist.oc1..example",
        "missing_id": "ocid1.securitylist.oc1..missing",
        "get_method": "get_security_list",
        "list_method": "list_security_lists",
        "list_params": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-security-list",
            "lifecycle_state": "AVAILABLE",
        },
        "expected_list_kwargs": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "lifecycle_state": "AVAILABLE",
        },
        "run_resource": FakeModel(
            id="ocid1.securitylist.oc1..example",
            display_name="example-security-list",
            lifecycle_state="AVAILABLE",
            vcn_id="ocid1.vcn.oc1..example",
        ),
        "expected_run_payload": {
            "id": "ocid1.securitylist.oc1..example",
            "name": "example-security-list",
            "lifecycle_state": "AVAILABLE",
            "vcn_id": "ocid1.vcn.oc1..example",
        },
    },
    {
        "module_name": "oci_network_service_gateway_info",
        "class_name": "OciNetworkServiceGatewayInfoModule",
        "results_key": "service_gateways",
        "id_param": "service_gateway_id",
        "id_value": "ocid1.servicegateway.oc1..example",
        "missing_id": "ocid1.servicegateway.oc1..missing",
        "get_method": "get_service_gateway",
        "list_method": "list_service_gateways",
        "list_params": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-service-gateway",
            "lifecycle_state": "AVAILABLE",
        },
        "expected_list_kwargs": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "lifecycle_state": "AVAILABLE",
        },
        "run_resource": FakeModel(
            id="ocid1.servicegateway.oc1..example",
            display_name="example-service-gateway",
            lifecycle_state="AVAILABLE",
            vcn_id="ocid1.vcn.oc1..example",
        ),
        "expected_run_payload": {
            "id": "ocid1.servicegateway.oc1..example",
            "name": "example-service-gateway",
            "lifecycle_state": "AVAILABLE",
            "vcn_id": "ocid1.vcn.oc1..example",
        },
    },
    {
        "module_name": "oci_network_drg_attachment_info",
        "class_name": "OciNetworkDrgAttachmentInfoModule",
        "results_key": "drg_attachments",
        "id_param": "drg_attachment_id",
        "id_value": "ocid1.drgattachment.oc1..example",
        "missing_id": "ocid1.drgattachment.oc1..missing",
        "get_method": "get_drg_attachment",
        "list_method": "list_drg_attachments",
        "list_params": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "drg_id": "ocid1.drg.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-drg-attachment",
            "lifecycle_state": "ATTACHED",
        },
        "expected_list_kwargs": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "drg_id": "ocid1.drg.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "lifecycle_state": "ATTACHED",
        },
        "run_resource": FakeModel(
            id="ocid1.drgattachment.oc1..example",
            display_name="example-drg-attachment",
            lifecycle_state="ATTACHED",
            drg_id="ocid1.drg.oc1..example",
            vcn_id="ocid1.vcn.oc1..example",
        ),
        "expected_run_payload": {
            "id": "ocid1.drgattachment.oc1..example",
            "name": "example-drg-attachment",
            "lifecycle_state": "ATTACHED",
            "drg_id": "ocid1.drg.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
        },
    },
    {
        "module_name": "oci_network_local_peering_gateway_info",
        "class_name": "OciNetworkLocalPeeringGatewayInfoModule",
        "results_key": "local_peering_gateways",
        "id_param": "local_peering_gateway_id",
        "id_value": "ocid1.localpeeringgateway.oc1..example",
        "missing_id": "ocid1.localpeeringgateway.oc1..missing",
        "get_method": "get_local_peering_gateway",
        "list_method": "list_local_peering_gateways",
        "list_params": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-lpg",
        },
        "expected_list_kwargs": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
        },
        "run_resource": FakeModel(
            id="ocid1.localpeeringgateway.oc1..example",
            display_name="example-lpg",
            lifecycle_state="AVAILABLE",
            vcn_id="ocid1.vcn.oc1..example",
        ),
        "expected_run_payload": {
            "id": "ocid1.localpeeringgateway.oc1..example",
            "name": "example-lpg",
            "lifecycle_state": "AVAILABLE",
            "vcn_id": "ocid1.vcn.oc1..example",
        },
    },
    {
        "module_name": "oci_blockstorage_volume_info",
        "class_name": "OciBlockstorageVolumeInfoModule",
        "results_key": "volumes",
        "id_param": "volume_id",
        "id_value": "ocid1.volume.oc1..example",
        "missing_id": "ocid1.volume.oc1..missing",
        "get_method": "get_volume",
        "list_method": "list_volumes",
        "list_params": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "availability_domain": "Uocm:PHX-AD-1",
            "name": "example-volume",
            "lifecycle_state": "AVAILABLE",
        },
        "expected_list_kwargs": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "availability_domain": "Uocm:PHX-AD-1",
            "lifecycle_state": "AVAILABLE",
        },
        "run_resource": FakeModel(
            id="ocid1.volume.oc1..example",
            display_name="example-volume",
            lifecycle_state="AVAILABLE",
        ),
        "expected_run_payload": {
            "id": "ocid1.volume.oc1..example",
            "name": "example-volume",
            "lifecycle_state": "AVAILABLE",
        },
    },
    {
        "module_name": "oci_boot_volume_info",
        "class_name": "OciBootVolumeInfoModule",
        "results_key": "boot_volumes",
        "id_param": "boot_volume_id",
        "id_value": "ocid1.bootvolume.oc1..example",
        "missing_id": "ocid1.bootvolume.oc1..missing",
        "get_method": "get_boot_volume",
        "list_method": "list_boot_volumes",
        "list_params": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "availability_domain": "Uocm:PHX-AD-1",
            "name": "example-boot-volume",
        },
        "expected_list_kwargs": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "availability_domain": "Uocm:PHX-AD-1",
        },
        "run_resource": FakeModel(
            id="ocid1.bootvolume.oc1..example",
            display_name="example-boot-volume",
            lifecycle_state="AVAILABLE",
            image_id="ocid1.image.oc1..example",
        ),
        "expected_run_payload": {
            "id": "ocid1.bootvolume.oc1..example",
            "name": "example-boot-volume",
            "lifecycle_state": "AVAILABLE",
            "image_id": "ocid1.image.oc1..example",
        },
    },
    {
        "module_name": "oci_volume_attachment_info",
        "class_name": "OciVolumeAttachmentInfoModule",
        "results_key": "volume_attachments",
        "id_param": "volume_attachment_id",
        "id_value": "ocid1.volumeattachment.oc1..example",
        "missing_id": "ocid1.volumeattachment.oc1..missing",
        "get_method": "get_volume_attachment",
        "list_method": "list_volume_attachments",
        "list_params": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "availability_domain": "Uocm:PHX-AD-1",
            "instance_id": "ocid1.instance.oc1..example",
            "volume_id": "ocid1.volume.oc1..example",
            "name": "example-attachment",
        },
        "expected_list_kwargs": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "availability_domain": "Uocm:PHX-AD-1",
            "instance_id": "ocid1.instance.oc1..example",
            "volume_id": "ocid1.volume.oc1..example",
        },
        "run_resource": FakeModel(
            id="ocid1.volumeattachment.oc1..example",
            display_name="example-attachment",
            lifecycle_state="ATTACHED",
            instance_id="ocid1.instance.oc1..example",
            volume_id="ocid1.volume.oc1..example",
        ),
        "expected_run_payload": {
            "id": "ocid1.volumeattachment.oc1..example",
            "name": "example-attachment",
            "lifecycle_state": "ATTACHED",
            "instance_id": "ocid1.instance.oc1..example",
            "volume_id": "ocid1.volume.oc1..example",
        },
    },
    {
        "module_name": "oci_volume_backup_info",
        "class_name": "OciVolumeBackupInfoModule",
        "results_key": "volume_backups",
        "id_param": "volume_backup_id",
        "id_value": "ocid1.volumebackup.oc1..example",
        "missing_id": "ocid1.volumebackup.oc1..missing",
        "get_method": "get_volume_backup",
        "list_method": "list_volume_backups",
        "list_params": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "volume_id": "ocid1.volume.oc1..example",
            "name": "example-backup",
            "lifecycle_state": "AVAILABLE",
        },
        "expected_list_kwargs": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "volume_id": "ocid1.volume.oc1..example",
            "lifecycle_state": "AVAILABLE",
        },
        "run_resource": FakeModel(
            id="ocid1.volumebackup.oc1..example",
            display_name="example-backup",
            lifecycle_state="AVAILABLE",
            volume_id="ocid1.volume.oc1..example",
        ),
        "expected_run_payload": {
            "id": "ocid1.volumebackup.oc1..example",
            "name": "example-backup",
            "lifecycle_state": "AVAILABLE",
            "volume_id": "ocid1.volume.oc1..example",
        },
    },
    {
        "module_name": "oci_boot_volume_backup_info",
        "class_name": "OciBootVolumeBackupInfoModule",
        "results_key": "boot_volume_backups",
        "id_param": "boot_volume_backup_id",
        "id_value": "ocid1.bootvolumebackup.oc1..example",
        "missing_id": "ocid1.bootvolumebackup.oc1..missing",
        "get_method": "get_boot_volume_backup",
        "list_method": "list_boot_volume_backups",
        "list_params": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "boot_volume_id": "ocid1.bootvolume.oc1..example",
            "name": "example-boot-backup",
            "lifecycle_state": "AVAILABLE",
        },
        "expected_list_kwargs": {
            "compartment_id": "ocid1.compartment.oc1..example",
            "boot_volume_id": "ocid1.bootvolume.oc1..example",
            "lifecycle_state": "AVAILABLE",
        },
        "run_resource": FakeModel(
            id="ocid1.bootvolumebackup.oc1..example",
            display_name="example-boot-backup",
            lifecycle_state="AVAILABLE",
            boot_volume_id="ocid1.bootvolume.oc1..example",
        ),
        "expected_run_payload": {
            "id": "ocid1.bootvolumebackup.oc1..example",
            "name": "example-boot-backup",
            "lifecycle_state": "AVAILABLE",
            "boot_volume_id": "ocid1.bootvolume.oc1..example",
        },
    },
)


@pytest.mark.parametrize("case", INFO_CASES, ids=lambda case: case["module_name"])
def test_list_resources_uses_list_filters(monkeypatch, case):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module(case["module_name"])
    paginate_calls = []
    instance = make_module_instance(
        info_module,
        case["class_name"],
        case["list_params"],
        client=types.SimpleNamespace(**{case["list_method"]: "list_method"}),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: paginate_calls.append((list_fn, kwargs)) or [],
    )

    resources = instance.fetch_resources()

    assert resources == []
    assert paginate_calls == [("list_method", case["expected_list_kwargs"])]


@pytest.mark.parametrize("case", INFO_CASES, ids=lambda case: case["module_name"])
def test_list_resources_prefers_id_lookup(monkeypatch, case):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module(case["module_name"])

    def get_resource(**kwargs):
        return FakeResponse(
            data=FakeModel(id=kwargs[case["id_param"]], display_name="example")
        )

    instance = make_module_instance(
        info_module,
        case["class_name"],
        {case["id_param"]: case["id_value"]},
        client=types.SimpleNamespace(
            **{case["get_method"]: get_resource}
        ),
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

    assert len(resources) == 1
    assert resources[0].id == case["id_value"]


@pytest.mark.parametrize("case", INFO_CASES, ids=lambda case: case["module_name"])
def test_list_resources_returns_empty_list_on_404(monkeypatch, case):
    _oci_module, ServiceError = install_fake_oci(monkeypatch)

    info_module = load_collection_module(case["module_name"])

    def get_missing_resource(**kwargs):
        raise ServiceError(404, "missing")

    instance = make_module_instance(
        info_module,
        case["class_name"],
        {case["id_param"]: case["missing_id"]},
        client=types.SimpleNamespace(
            **{case["get_method"]: get_missing_resource}
        ),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    assert instance.fetch_resources() == []


@pytest.mark.parametrize("case", INFO_CASES, ids=lambda case: case["module_name"])
def test_run_returns_results_key(monkeypatch, case):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module(case["module_name"])
    instance = make_module_instance(
        info_module,
        case["class_name"],
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": case["run_resource"].display_name,
        },
    )
    monkeypatch.setattr(instance, "fetch_resources", lambda: [case["run_resource"]])

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()

    assert exc_info.value.payload == {
        "changed": False,
        case["results_key"]: [case["expected_run_payload"]],
    }
