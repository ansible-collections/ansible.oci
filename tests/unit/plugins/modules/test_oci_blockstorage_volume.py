from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from conftest import (
    DummyModule,
    FakeModel,
    FakeResponse,
    FailJsonCalled,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)


VOLUME_MODEL_NAMES = (
    "CreateVolumeDetails",
    "UpdateVolumeDetails",
    "PerformanceBasedAutotunePolicy",
    "DetachedVolumeAutotunePolicy",
)


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(
        monkeypatch,
        model_names=VOLUME_MODEL_NAMES,
    )


def make_volume_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciBlockstorageVolumeModule",
        params,
        client=client,
    )


def test_main_exposes_expected_arguments(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_blockstorage_volume")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        captured["required_if"] = kwargs.get("required_if")
        return DummyModule({})

    class FakeVolumeModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciBlockstorageVolumeModule", FakeVolumeModule)

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["argument_spec"]["allow_duplicate_name"] == {
        "type": "bool",
        "default": False,
    }
    assert captured["argument_spec"]["name"] == {"type": "str"}
    assert captured["argument_spec"]["compartment_id"] == {"type": "str"}
    assert captured["argument_spec"]["volume_id"] == {"type": "str"}
    assert captured["argument_spec"]["availability_domain"] == {"type": "str"}
    assert captured["argument_spec"]["size_in_gbs"] == {"type": "int"}
    assert captured["argument_spec"]["vpus_per_gb"] == {"type": "int"}
    assert captured["argument_spec"]["kms_key_id"] == {"type": "str"}
    assert captured["argument_spec"]["backup_policy_id"] == {"type": "str"}
    assert captured["argument_spec"]["cluster_placement_group_id"] == {"type": "str"}
    assert captured["argument_spec"]["reservations_enabled"] == {"type": "bool"}
    assert captured["argument_spec"]["performance_based_auto_tune"] == {"type": "bool"}
    assert captured["argument_spec"]["max_vpus_per_gb"] == {"type": "int"}
    assert captured["argument_spec"]["detached_volume_auto_tune"] == {"type": "bool"}
    assert captured["required_if"] == [
        ["performance_based_auto_tune", True, ["vpus_per_gb", "max_vpus_per_gb"]],
    ]
    # Console vault/compartment pickers and removed SDK fields must not leak in.
    assert "is_auto_tune_enabled" not in captured["argument_spec"]
    assert "is_reservations_enabled" not in captured["argument_spec"]
    assert "auto_tune_enabled" not in captured["argument_spec"]
    assert "autotune_policies" not in captured["argument_spec"]
    assert "source_details" not in captured["argument_spec"]
    assert "block_volume_replicas" not in captured["argument_spec"]
    assert "xrc_kms_key_id" not in captured["argument_spec"]
    assert "display_name" not in captured["argument_spec"]


def test_build_create_volume_details_includes_supported_fields(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    details = volume_module.build_create_volume_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "availability_domain": "Uocm:PHX-AD-1",
            "name": "example-volume",
            "size_in_gbs": 50,
            "vpus_per_gb": 10,
            "freeform_tags": {"env": "dev"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        }
    )

    assert isinstance(details, FakeModel)
    assert details.compartment_id == "ocid1.compartment.oc1..example"
    assert details.availability_domain == "Uocm:PHX-AD-1"
    assert details.display_name == "example-volume"
    assert details.size_in_gbs == 50
    assert details.vpus_per_gb == 10
    assert details.freeform_tags == {"env": "dev"}
    assert details.defined_tags == {"Operations": {"CostCenter": "42"}}


def test_build_create_volume_details_omits_unset_optional_fields(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    details = volume_module.build_create_volume_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "availability_domain": "Uocm:PHX-AD-1",
            "name": "example-volume",
            "size_in_gbs": None,
            "vpus_per_gb": None,
            "freeform_tags": None,
            "defined_tags": None,
        }
    )

    assert not hasattr(details, "size_in_gbs")
    assert not hasattr(details, "vpus_per_gb")
    assert not hasattr(details, "freeform_tags")
    assert not hasattr(details, "autotune_policies")


def test_build_create_volume_details_includes_encryption_and_reservations(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    details = volume_module.build_create_volume_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "availability_domain": "Uocm:PHX-AD-1",
            "name": "example-volume",
            "kms_key_id": "ocid1.key.oc1..example",
            "backup_policy_id": "ocid1.volumebackuppolicy.oc1..example",
            "reservations_enabled": False,
        }
    )

    assert details.kms_key_id == "ocid1.key.oc1..example"
    assert details.backup_policy_id == "ocid1.volumebackuppolicy.oc1..example"
    assert details.is_reservations_enabled is False
    assert not hasattr(details, "xrc_kms_key_id")
    assert not hasattr(details, "is_auto_tune_enabled")


def test_build_create_volume_details_includes_cluster_placement_group(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    details = volume_module.build_create_volume_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "availability_domain": "Uocm:PHX-AD-1",
            "name": "placed-volume",
            "cluster_placement_group_id": "ocid1.clusterplacementgroup.oc1..example",
        }
    )

    assert details.cluster_placement_group_id == "ocid1.clusterplacementgroup.oc1..example"
    assert not hasattr(details, "source_details")
    assert not hasattr(details, "block_volume_replicas")


def test_build_create_volume_details_builds_autotune_from_ui_flags(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    details = volume_module.build_create_volume_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "availability_domain": "Uocm:PHX-AD-1",
            "name": "example-volume",
            "vpus_per_gb": 10,
            "performance_based_auto_tune": True,
            "max_vpus_per_gb": 120,
            "detached_volume_auto_tune": True,
        }
    )

    assert details.autotune_policies[0].max_vpus_per_gb == 120
    assert not hasattr(details.autotune_policies[1], "max_vpus_per_gb")
    assert len(details.autotune_policies) == 2


def test_build_autotune_policies_rejects_unknown_type(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    with pytest.raises(ValueError, match="autotune_type"):
        volume_module.build_autotune_policies(
            [{"autotune_type": "unknown_policy"}]
        )


def test_desired_autotune_policy_dicts_unmanaged_when_all_omitted(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    assert volume_module.desired_autotune_policy_dicts({}) is None
    assert volume_module.build_autotune_policies(None) is None


def test_desired_autotune_policy_dicts_create_both_false_returns_empty(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    assert volume_module.desired_autotune_policy_dicts(
        {
            "performance_based_auto_tune": False,
            "detached_volume_auto_tune": False,
        }
    ) == []


def test_desired_autotune_policy_dicts_overlays_current_on_update(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    current = [FakeModel(autotune_type="PERFORMANCE_BASED", max_vpus_per_gb=40)]
    result = volume_module.desired_autotune_policy_dicts(
        {"detached_volume_auto_tune": True},
        current_policies=current,
    )

    assert result == [
        {"autotune_type": "performance_based", "max_vpus_per_gb": 40},
        {"autotune_type": "detached_volume"},
    ]


def test_desired_autotune_policy_dicts_can_disable_performance_keeping_detached(
    monkeypatch,
):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    current = [
        FakeModel(autotune_type="PERFORMANCE_BASED", max_vpus_per_gb=40),
        FakeModel(autotune_type="DETACHED_VOLUME"),
    ]
    result = volume_module.desired_autotune_policy_dicts(
        {"performance_based_auto_tune": False},
        current_policies=current,
    )

    assert result == [{"autotune_type": "detached_volume"}]


def test_desired_autotune_policy_dicts_overlays_max_vpus_only(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    result = volume_module.desired_autotune_policy_dicts(
        {"max_vpus_per_gb": 80},
        current_policies=[
            FakeModel(autotune_type="PERFORMANCE_BASED", max_vpus_per_gb=40)
        ],
    )

    assert result == [
        {"autotune_type": "performance_based", "max_vpus_per_gb": 80},
    ]


def test_validate_rejects_invalid_vpus_per_gb(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    with pytest.raises(FailJsonCalled) as exc_info:
        volume_module.validate_volume_performance(
            {"vpus_per_gb": 15},
            DummyModule({}).fail_json,
        )

    assert "vpus_per_gb" in exc_info.value.payload["msg"]


def test_validate_rejects_vpus_zero_with_performance_autotune(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    with pytest.raises(FailJsonCalled) as exc_info:
        volume_module.validate_volume_performance(
            {
                "vpus_per_gb": 0,
                "performance_based_auto_tune": True,
                "max_vpus_per_gb": 20,
            },
            DummyModule({}).fail_json,
        )

    assert "vpus_per_gb" in exc_info.value.payload["msg"]
    assert "autotune" in exc_info.value.payload["msg"]


def test_validate_rejects_max_vpus_when_autotune_false(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    with pytest.raises(FailJsonCalled) as exc_info:
        volume_module.validate_volume_performance(
            {"performance_based_auto_tune": False, "max_vpus_per_gb": 40},
            DummyModule({}).fail_json,
            current_policies=[
                FakeModel(autotune_type="PERFORMANCE_BASED", max_vpus_per_gb=40),
            ],
        )

    assert "max_vpus_per_gb" in exc_info.value.payload["msg"]


def test_validate_rejects_max_vpus_below_vpus(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    with pytest.raises(FailJsonCalled) as exc_info:
        volume_module.validate_volume_performance(
            {
                "performance_based_auto_tune": True,
                "vpus_per_gb": 40,
                "max_vpus_per_gb": 20,
            },
            DummyModule({}).fail_json,
        )

    assert "max_vpus_per_gb" in exc_info.value.payload["msg"]


def test_validate_rejects_max_vpus_without_autotune_flag(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    with pytest.raises(FailJsonCalled) as exc_info:
        volume_module.validate_volume_performance(
            {"max_vpus_per_gb": 40},
            DummyModule({}).fail_json,
        )

    assert "max_vpus_per_gb" in exc_info.value.payload["msg"]


def test_validate_allows_max_vpus_overlay_when_current_has_performance_autotune(
    monkeypatch,
):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    volume_module.validate_volume_performance(
        {"max_vpus_per_gb": 60},
        DummyModule({}).fail_json,
        current_policies=[
            FakeModel(autotune_type="PERFORMANCE_BASED", max_vpus_per_gb=40),
        ],
    )


def test_validate_accepts_balanced_and_uhp_vpus(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    volume_module.validate_volume_performance(
        {"vpus_per_gb": 10},
        DummyModule({}).fail_json,
    )
    volume_module.validate_volume_performance(
        {"vpus_per_gb": 0},
        DummyModule({}).fail_json,
    )
    volume_module.validate_volume_performance(
        {
            "vpus_per_gb": 30,
            "performance_based_auto_tune": True,
            "max_vpus_per_gb": 120,
        },
        DummyModule({}).fail_json,
    )


def test_needs_update_rejects_cluster_placement_group_id_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    instance = make_volume_module(
        volume_module,
        {"cluster_placement_group_id": "ocid1.clusterplacementgroup.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.volume.oc1..example",
        cluster_placement_group_id="ocid1.clusterplacementgroup.oc1..current",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "cluster_placement_group_id" in exc_info.value.payload["msg"]


def test_needs_update_rejects_compartment_id_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    instance = make_volume_module(
        volume_module,
        {"compartment_id": "ocid1.compartment.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.volume.oc1..example",
        compartment_id="ocid1.compartment.oc1..current",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "compartment_id" in exc_info.value.payload["msg"]


def test_needs_update_ignores_backup_policy_id_on_existing_volume(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    instance = make_volume_module(
        volume_module,
        {"backup_policy_id": "ocid1.volumebackuppolicy.oc1..other"},
    )
    resource = FakeModel(
        id="ocid1.volume.oc1..example",
        display_name="example-volume",
    )

    assert instance.needs_update(resource) is False


def test_needs_update_detects_autotune_policy_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    instance = make_volume_module(
        volume_module,
        {
            "performance_based_auto_tune": True,
            "vpus_per_gb": 80,
            "max_vpus_per_gb": 80,
        },
    )
    resource = FakeModel(
        id="ocid1.volume.oc1..example",
        vpus_per_gb=120,
        autotune_policies=[
            FakeModel(autotune_type="PERFORMANCE_BASED", max_vpus_per_gb=120),
        ],
    )

    assert instance.needs_update(resource) is True


def test_needs_update_no_autotune_drift_when_equal(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    instance = make_volume_module(
        volume_module,
        {
            "performance_based_auto_tune": True,
            "vpus_per_gb": 120,
            "max_vpus_per_gb": 120,
        },
    )
    resource = FakeModel(
        id="ocid1.volume.oc1..example",
        vpus_per_gb=120,
        autotune_policies=[
            FakeModel(autotune_type="PERFORMANCE_BASED", max_vpus_per_gb=120),
        ],
    )

    assert instance.needs_update(resource) is False


def test_needs_update_omits_autotune_when_flags_unset(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    instance = make_volume_module(
        volume_module,
        {"name": "current-volume"},
    )
    resource = FakeModel(
        id="ocid1.volume.oc1..example",
        display_name="current-volume",
        autotune_policies=[
            FakeModel(autotune_type="PERFORMANCE_BASED", max_vpus_per_gb=120),
        ],
    )

    update_plan = instance.build_update_plan(resource)

    assert update_plan["update_needed"] is False
    assert "autotune_policies" not in update_plan["update_model_fields"]


def test_needs_update_overlays_max_vpus_only(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    instance = make_volume_module(
        volume_module,
        {"max_vpus_per_gb": 60},
    )
    resource = FakeModel(
        id="ocid1.volume.oc1..example",
        vpus_per_gb=20,
        autotune_policies=[
            FakeModel(autotune_type="DETACHED_VOLUME"),
            FakeModel(autotune_type="PERFORMANCE_BASED", max_vpus_per_gb=40),
        ],
    )

    update_plan = instance.build_update_plan(resource)

    assert update_plan["update_needed"] is True
    assert update_plan["update_model_fields"]["autotune_policies"] == [
        {"autotune_type": "performance_based", "max_vpus_per_gb": 60},
        {"autotune_type": "detached_volume"},
    ]


def test_needs_update_can_disable_autotune_with_false_flags(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    instance = make_volume_module(
        volume_module,
        {
            "performance_based_auto_tune": False,
            "detached_volume_auto_tune": False,
        },
    )
    resource = FakeModel(
        id="ocid1.volume.oc1..example",
        autotune_policies=[
            FakeModel(autotune_type="PERFORMANCE_BASED", max_vpus_per_gb=120),
        ],
    )

    update_plan = instance.build_update_plan(resource)

    assert update_plan["update_needed"] is True
    assert update_plan["update_model_fields"]["autotune_policies"] == []


def test_needs_update_rejects_kms_key_id_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    instance = make_volume_module(
        volume_module,
        {"kms_key_id": "ocid1.key.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.volume.oc1..example",
        kms_key_id="ocid1.key.oc1..current",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "kms_key_id" in exc_info.value.payload["msg"]


def test_build_update_details_converts_autotune_models(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    instance = make_volume_module(volume_module, {})

    update_details = instance.build_update_details(
        {
            "size_in_gbs": 100,
            "autotune_policies": [
                {"autotune_type": "performance_based", "max_vpus_per_gb": 120},
            ],
        }
    )

    assert update_details.size_in_gbs == 100
    assert update_details.autotune_policies[0].max_vpus_per_gb == 120
    assert not hasattr(update_details, "block_volume_replicas")


def test_build_update_plan_maps_volume_fields_to_update_model(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    instance = make_volume_module(
        volume_module,
        {"name": "updated-volume", "size_in_gbs": 100, "vpus_per_gb": 20},
    )
    resource = FakeModel(
        id="ocid1.volume.oc1..example",
        display_name="current-volume",
        size_in_gbs=50,
        vpus_per_gb=10,
    )

    update_plan = instance.build_update_plan(resource)

    assert update_plan["update_needed"] is True
    assert update_plan["update_model_fields"] == {
        "display_name": "updated-volume",
        "size_in_gbs": 100,
        "vpus_per_gb": 20,
    }
    assert update_plan["strategy_operations"] == []


def test_needs_update_returns_false_when_fields_match(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    instance = make_volume_module(
        volume_module,
        {"name": "current-volume", "size_in_gbs": 50},
    )
    resource = FakeModel(
        id="ocid1.volume.oc1..example",
        display_name="current-volume",
        size_in_gbs=50,
    )

    assert instance.needs_update(resource) is False


def test_needs_update_rejects_availability_domain_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    instance = make_volume_module(
        volume_module,
        {"availability_domain": "Uocm:PHX-AD-2"},
    )
    resource = FakeModel(
        id="ocid1.volume.oc1..example",
        availability_domain="Uocm:PHX-AD-1",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "availability_domain" in exc_info.value.payload["msg"]


def test_create_resource_uses_create_volume_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    create_calls = []
    response = FakeResponse(data=FakeModel(id="ocid1.volume.oc1..example"))

    def create_volume(create_volume_details):
        create_calls.append(create_volume_details)
        return response

    instance = make_volume_module(
        volume_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "availability_domain": "Uocm:PHX-AD-1",
            "name": "example-volume",
            "wait": True,
        },
        client=types.SimpleNamespace(create_volume=create_volume),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: FakeModel(
            id=resource_id,
            lifecycle_state="AVAILABLE",
        ),
    )

    resource = instance.create_resource()

    assert create_calls[0].compartment_id == "ocid1.compartment.oc1..example"
    assert create_calls[0].display_name == "example-volume"
    assert resource.id == "ocid1.volume.oc1..example"
    assert resource.lifecycle_state == "AVAILABLE"


def test_update_resource_uses_update_volume_details_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    update_calls = []
    response = FakeResponse(data=FakeModel(id="ocid1.volume.oc1..example"))

    def update_volume(volume_id, update_volume_details):
        update_calls.append((volume_id, update_volume_details))
        return response

    resource = FakeModel(id="ocid1.volume.oc1..example")
    instance = make_volume_module(
        volume_module,
        {"name": "updated-volume", "size_in_gbs": 100, "wait": True},
        client=types.SimpleNamespace(update_volume=update_volume),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: FakeModel(
            id=resource_id,
            lifecycle_state="AVAILABLE",
        ),
    )

    updated_resource = instance.update_resource(resource)

    assert update_calls[0][0] == "ocid1.volume.oc1..example"
    assert update_calls[0][1].display_name == "updated-volume"
    assert update_calls[0][1].size_in_gbs == 100
    assert updated_resource.id == "ocid1.volume.oc1..example"


def test_delete_resource_uses_delete_volume_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    delete_calls = []
    response = FakeResponse(data=None)

    def delete_volume(volume_id):
        delete_calls.append(volume_id)
        return response

    resource = FakeModel(id="ocid1.volume.oc1..example")
    instance = make_volume_module(
        volume_module,
        {"wait": True},
        client=types.SimpleNamespace(delete_volume=delete_volume),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: None,
    )

    instance.delete_resource(resource)

    assert delete_calls == ["ocid1.volume.oc1..example"]


def test_create_required_fields_enforced(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    instance = make_volume_module(
        volume_module,
        {"name": "example-volume"},
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "Creating a block volume requires" in exc_info.value.payload["msg"]
    assert "compartment_id" in exc_info.value.payload["msg"]
    assert "availability_domain" in exc_info.value.payload["msg"]


def test_validate_create_request_rejects_invalid_performance(monkeypatch):
    install_fake_oci(monkeypatch)

    volume_module = load_collection_module("oci_blockstorage_volume")
    instance = make_volume_module(
        volume_module,
        {
            "name": "example-volume",
            "compartment_id": "ocid1.compartment.oc1..example",
            "availability_domain": "Uocm:PHX-AD-1",
            "vpus_per_gb": 0,
            "performance_based_auto_tune": True,
            "max_vpus_per_gb": 20,
        },
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "vpus_per_gb" in exc_info.value.payload["msg"]
