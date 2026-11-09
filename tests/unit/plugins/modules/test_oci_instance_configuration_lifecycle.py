from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from .conftest import (
    ExitJsonCalled,
    FailJsonCalled,
    FakeResponse,
    load_collection_module,
    make_module_instance,
    raising,
)


INSTANCE_DETAILS = {
    "instance_type": "compute",
    "launch_details": {
        "shape": "VM.Standard.E4.Flex",
        "shape_config": {"ocpus": 1, "memory_in_gbs": 16},
    },
}


def load_real_configuration_module(monkeypatch):
    import oci

    load_collection_module("oci_base", plugin_dir="module_utils")
    load_collection_module("oci_info", plugin_dir="module_utils")
    load_collection_module("oci_resource", plugin_dir="module_utils")
    compute = load_collection_module("oci_instance", plugin_dir="module_utils")
    monkeypatch.setattr(compute, "oci", oci)
    module_obj = load_collection_module("oci_instance_configuration")
    monkeypatch.setattr(module_obj, "oci", oci)
    info_module = load_collection_module("oci_instance_configuration_info")
    monkeypatch.setattr(info_module, "oci", oci)
    return module_obj, info_module, oci


def make_instance_configuration(module_obj, *, name="template", details=None, tags=None):
    model = module_obj.oci.core.models.InstanceConfiguration
    instance_details = module_obj.build_instance_configuration_details(
        details or INSTANCE_DETAILS
    )
    return model(
        id="ocid1.instanceconfiguration.oc1..example",
        compartment_id="ocid1.compartment.oc1..example",
        display_name=name,
        instance_details=instance_details,
        freeform_tags=tags or {},
        defined_tags={},
    )


def make_resource(module_obj, params, resource, *, check_mode=False, client=None):
    instance = make_module_instance(
        module_obj,
        "OciInstanceConfigurationModule",
        params,
        client=client,
        check_mode=check_mode,
    )
    instance.resolve_target_resource = lambda: resource
    instance.call_with_retry = lambda fn, *args, **kwargs: fn(*args, **kwargs)
    return instance


def test_create_check_mode_does_not_call_create(monkeypatch):
    module_obj = load_real_configuration_module(monkeypatch)[0]
    create_calls = []
    client = types.SimpleNamespace(
        create_instance_configuration=lambda **kwargs: create_calls.append(kwargs)
    )
    instance = make_resource(
        module_obj,
        {
            "state": "present",
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "template",
            "source": "none",
            "instance_details": INSTANCE_DETAILS,
        },
        None,
        check_mode=True,
        client=client,
    )

    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()

    assert result.value.payload["changed"] is True
    assert create_calls == []


def test_repeated_present_with_same_template_is_unchanged(monkeypatch):
    module_obj = load_real_configuration_module(monkeypatch)[0]
    resource = make_instance_configuration(module_obj)
    instance = make_resource(
        module_obj,
        {
            "state": "present",
            "instance_configuration_id": resource.id,
            "compartment_id": resource.compartment_id,
            "name": resource.display_name,
            "source": "none",
            "instance_details": INSTANCE_DETAILS,
        },
        resource,
    )

    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()

    assert result.value.payload["changed"] is False


def test_template_drift_fails_as_immutable(monkeypatch):
    module_obj = load_real_configuration_module(monkeypatch)[0]
    resource = make_instance_configuration(module_obj)
    desired_details = {
        "instance_type": "compute",
        "launch_details": {
            "shape": "VM.Standard.E4.Flex",
            "shape_config": {"ocpus": 2, "memory_in_gbs": 16},
        },
    }
    instance = make_resource(
        module_obj,
        {
            "state": "present",
            "instance_configuration_id": resource.id,
            "name": resource.display_name,
            "instance_details": desired_details,
        },
        resource,
    )

    with pytest.raises(FailJsonCalled) as result:
        instance.execute_resource_module()

    assert "instance_details" in result.value.payload["msg"]
    assert "not supported" in result.value.payload["msg"]


def test_tag_update_check_mode_and_update_payload(monkeypatch):
    module_obj = load_real_configuration_module(monkeypatch)[0]
    current = make_instance_configuration(module_obj, tags={"owner": "old"})
    desired_tags = {"owner": "new"}
    update_calls = []

    def update_configuration(**kwargs):
        update_calls.append(kwargs)
        updated = make_instance_configuration(module_obj, tags=desired_tags)
        return FakeResponse(updated)

    client = types.SimpleNamespace(update_instance_configuration=update_configuration)
    check = make_resource(
        module_obj,
        {
            "state": "present",
            "instance_configuration_id": current.id,
            "freeform_tags": desired_tags,
        },
        current,
        check_mode=True,
        client=client,
    )

    with pytest.raises(ExitJsonCalled) as check_result:
        check.execute_resource_module()

    assert check_result.value.payload["changed"] is True
    assert update_calls == []

    actual = make_resource(
        module_obj,
        {
            "state": "present",
            "instance_configuration_id": current.id,
            "freeform_tags": desired_tags,
        },
        current,
        client=client,
    )
    with pytest.raises(ExitJsonCalled) as update_result:
        actual.execute_resource_module()

    assert update_result.value.payload["changed"] is True
    assert len(update_calls) == 1
    payload = update_calls[0]["update_instance_configuration_details"]
    assert isinstance(
        payload, module_obj.oci.core.models.UpdateInstanceConfigurationDetails
    )
    assert payload.freeform_tags == desired_tags


def test_delete_check_mode_and_absent_noop_do_not_call_delete(monkeypatch):
    module_obj = load_real_configuration_module(monkeypatch)[0]
    resource = make_instance_configuration(module_obj)
    delete_calls = []
    client = types.SimpleNamespace(
        delete_instance_configuration=lambda **kwargs: delete_calls.append(kwargs)
    )
    params = {"state": "absent", "instance_configuration_id": resource.id}

    check = make_resource(
        module_obj, params, resource, check_mode=True, client=client
    )
    with pytest.raises(ExitJsonCalled) as check_result:
        check.execute_resource_module()
    assert check_result.value.payload["changed"] is True
    assert delete_calls == []

    absent = make_resource(module_obj, params, None, client=client)
    with pytest.raises(ExitJsonCalled) as absent_result:
        absent.execute_resource_module()
    assert absent_result.value.payload["changed"] is False
    assert delete_calls == []


def test_info_get_404_returns_empty_list(monkeypatch):
    module_obj, oci = load_real_configuration_module(monkeypatch)[1:]
    missing = oci.exceptions.ServiceError(
        404, "NotAuthorizedOrNotFound", {}, "configuration not found"
    )
    client = types.SimpleNamespace(
        get_instance_configuration=raising(missing)
    )
    info = make_module_instance(
        module_obj,
        "OciInstanceConfigurationInfoModule",
        {"instance_configuration_id": "ocid1.instanceconfiguration.oc1..missing"},
        client=client,
    )
    info.call_with_retry = lambda fn, *args, **kwargs: fn(*args, **kwargs)

    assert info.fetch_resources() == []


def test_info_list_uses_pagination_filters_and_local_name_filter(monkeypatch):
    resource_module, info_module, oci = load_real_configuration_module(monkeypatch)
    target = make_instance_configuration(resource_module, name="target")
    other = make_instance_configuration(resource_module, name="other")
    page_calls = []

    def list_configurations(page=None, **kwargs):
        page_calls.append((page, kwargs))
        if page is None:
            return FakeResponse([other], headers={"opc-next-page": "page-two"})
        return FakeResponse([target])

    def paginate(list_fn, **kwargs):
        first = list_fn(**kwargs)
        second = list_fn(page=first.headers["opc-next-page"], **kwargs)
        return FakeResponse(first.data + second.data)

    monkeypatch.setattr(oci.pagination, "list_call_get_all_results", paginate)
    client = types.SimpleNamespace(list_instance_configurations=list_configurations)
    info = make_module_instance(
        info_module,
        "OciInstanceConfigurationInfoModule",
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "target",
        },
        client=client,
    )

    resources = info.fetch_resources()

    assert [resource.display_name for resource in resources] == ["target"]
    assert page_calls == [
        (None, {"compartment_id": "ocid1.compartment.oc1..example"}),
        (
            "page-two",
            {"compartment_id": "ocid1.compartment.oc1..example"},
        ),
    ]


@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize(
    "invalid_details, unsupported",
    [
        (
            {
                "instance_type": "compute",
                "options": [{"instance_type": "compute", "launch_details": {"shape": "different"}}],
            },
            "options",
        ),
        (
            {"instance_type": "instance_options", "launch_details": {"shape": "different"}},
            "launch_details",
        ),
        (
            {
                "launch_details": {
                    "source_details": {"source_type": "image", "boot_volume_id": "BootID"}
                }
            },
            "boot_volume_id",
        ),
    ],
)
def test_invalid_templates_fail_before_mutations(
    monkeypatch, check_mode, existing, invalid_details, unsupported
):
    """Reject invalid templates before creation or existing-resource comparison."""
    module_obj = load_real_configuration_module(monkeypatch)[0]
    current = make_instance_configuration(module_obj) if existing else None
    mutation_calls = []
    client = types.SimpleNamespace(
        create_instance_configuration=lambda **kwargs: mutation_calls.append(kwargs),
        update_instance_configuration=lambda **kwargs: mutation_calls.append(kwargs),
    )
    instance = make_resource(
        module_obj,
        {
            "state": "present",
            "name": "template",
            "compartment_id": "ocid1.compartment.oc1..example",
            "source": "none",
            "instance_details": invalid_details,
        },
        current,
        check_mode=check_mode,
        client=client,
    )
    with pytest.raises(FailJsonCalled) as result:
        instance.execute_resource_module()
    assert "Invalid instance_details" in result.value.payload["msg"]
    assert unsupported in result.value.payload["msg"]
    assert mutation_calls == []
