from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import types

import pytest

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FailJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


MODELS = (
    "DynamicResourceGroup",
    "ExtensionOCITags",
    "FreeformTags",
    "DefinedTags",
    "PatchOp",
    "Operations",
)


def load_dynamic_group_module(monkeypatch):
    """Load the resource module with fake OCI SDK models.

    Args:
        monkeypatch: Pytest fixture for temporary module changes.

    Returns:
        The imported dynamic group module.
    """
    install_fake_oci(monkeypatch, model_names=MODELS)
    return load_collection_module("oci_identity_dynamic_group")


def make_dynamic_group(module_obj, params, client=None, check_mode=False):
    """Create a resource helper without opening an OCI client.

    Args:
        module_obj: Imported dynamic group module.
        params: Parameters for the fake Ansible module.
        client: Optional fake Identity Domains client.
        check_mode: Whether to enable check mode.

    Returns:
        An initialized resource helper.
    """
    return make_module_instance(
        module_obj,
        "OciIdentityDynamicGroupModule",
        params,
        client=client,
        check_mode=check_mode,
    )


def test_main_contract_and_create_model(monkeypatch):
    """Check module inputs and the SDK create model."""
    module_obj = load_dynamic_group_module(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        module_obj,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule({}),
    )
    monkeypatch.setattr(
        module_obj,
        "OciIdentityDynamicGroupModule",
        lambda module: types.SimpleNamespace(execute_resource_module=lambda: None),
    )
    module_obj.main()
    assert captured["required_one_of"] == [["domain_id", "domain_url"]]
    assert captured["mutually_exclusive"] == [["domain_id", "domain_url"]]
    assert captured["argument_spec"]["dynamic_group_id"] == {"type": "str"}
    assert captured["argument_spec"]["matching_rule"] == {"type": "str"}

    helper = sys.modules[module_obj.OciIdentityDomainResourceBase.__module__]
    model = module_obj.build_dynamic_group(
        {
            "name": "compute",
            "description": "Compute instances",
            "matching_rule": "instance.compartment.id = 'ocid1.compartment.example'",
            "freeform_tags": {"team": "iam"},
        }
    )
    assert model.display_name == "compute"
    assert model.description == "Compute instances"
    assert model.matching_rule == "instance.compartment.id = 'ocid1.compartment.example'"
    assert helper.CORE_DYNAMIC_GROUP_SCHEMA in model.schemas
    assert helper.OCI_TAGS_SCHEMA in model.schemas


@pytest.mark.parametrize(
    "params,field",
    [
        ({"name": None, "matching_rule": "rule"}, "name"),
        ({"name": "  ", "matching_rule": "rule"}, "name"),
        ({"name": "compute", "matching_rule": None}, "matching_rule"),
        ({"name": "compute", "matching_rule": "  "}, "matching_rule"),
    ],
)
def test_create_requires_nonempty_name_and_rule(monkeypatch, params, field):
    """Reject a create request with an empty required string."""
    module_obj = load_dynamic_group_module(monkeypatch)
    instance = make_dynamic_group(module_obj, params)
    with pytest.raises(FailJsonCalled) as result:
        instance.validate_create_request()
    assert field in result.value.payload["msg"]


def test_name_lookup_escapes_filter_and_selects_matching_rule(monkeypatch):
    """Use an exact escaped name filter and request the SCIM rule field."""
    module_obj = load_dynamic_group_module(monkeypatch)
    list_groups = object()
    instance = make_dynamic_group(
        module_obj,
        {"name": 'compute\\"prod'},
        types.SimpleNamespace(list_dynamic_resource_groups=list_groups),
    )
    calls = []
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda method, **kwargs: calls.append((method, kwargs)) or [],
    )
    assert instance.find_resources_by_name() == []
    assert calls == [
        (
            list_groups,
            {
                "filter": 'displayName eq "compute\\\\\\"prod"',
                "attributes": "matchingRule",
                "attribute_sets": ["default"],
            },
        )
    ]


@pytest.mark.parametrize(
    "field,path",
    [("name", "displayName"), ("description", "description"), ("matching_rule", "matchingRule")],
)
def test_patch_uses_dynamic_group_id_and_requested_attributes(monkeypatch, field, path):
    """Patch scalar fields with the SDK identifier argument and rule response."""
    module_obj = load_dynamic_group_module(monkeypatch)
    calls = []
    updated = FakeModel(id="dg1", display_name="compute", matching_rule="new")
    instance = make_dynamic_group(
        module_obj,
        {field: "new"},
        types.SimpleNamespace(
            patch_dynamic_resource_group=lambda **kwargs: calls.append(kwargs)
            or FakeResponse(updated)
        ),
    )
    current = FakeModel(
        id="dg1",
        display_name="old name",
        description="old description",
        matching_rule="old rule",
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    assert instance.needs_update(current) is True
    assert instance.update_resource(current) is updated
    assert set(calls[0]) == {
        "dynamic_resource_group_id",
        "patch_op",
        "attributes",
        "attribute_sets",
    }
    assert calls[0]["dynamic_resource_group_id"] == "dg1"
    assert calls[0]["attributes"] == "matchingRule"
    assert calls[0]["attribute_sets"] == ["default"]
    assert [operation.path for operation in calls[0]["patch_op"].operations] == [
        path
    ]


def test_group_patch_response_kwargs_default_is_unchanged(monkeypatch):
    """Keep existing group PATCH arguments unchanged by the helper extension."""
    install_fake_oci(monkeypatch, model_names=MODELS + ("Group",))
    module_obj = load_collection_module("oci_identity_group")
    instance = make_module_instance(
        module_obj,
        "OciIdentityGroupModule",
        {"name": "operators"},
        client=types.SimpleNamespace(
            patch_group=lambda **kwargs: FakeResponse(FakeModel(id="g1"))
        ),
    )
    current = FakeModel(id="g1", display_name="admins")
    calls = []
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: calls.append(kwargs) or fn(**kwargs),
    )
    instance.update_resource(current)
    assert set(calls[0]) == {"group_id", "patch_op"}


def test_create_and_absent_check_mode_do_not_mutate(monkeypatch):
    """Predict create and delete changes without making SDK mutation calls."""
    module_obj = load_dynamic_group_module(monkeypatch)
    client = types.SimpleNamespace(
        create_dynamic_resource_group=lambda **kwargs: pytest.fail("unexpected create"),
        patch_dynamic_resource_group=lambda **kwargs: pytest.fail("unexpected patch"),
        delete_dynamic_resource_group=lambda **kwargs: pytest.fail("unexpected delete"),
    )
    instance = make_dynamic_group(
        module_obj,
        {"name": "compute", "matching_rule": "rule"},
        client=client,
        check_mode=True,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload == {"changed": True}

    instance.module.params = {"name": "compute", "matching_rule": "new"}
    monkeypatch.setattr(
        instance,
        "resolve_target_resource",
        lambda: FakeModel(id="dg1", display_name="compute", matching_rule="old"),
    )
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload == {"changed": True}

    instance.module.params = {"state": "absent", "dynamic_group_id": "dg1"}
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: FakeModel(id="dg1"))
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload == {"changed": True}


def test_create_delete_and_unchanged_state(monkeypatch):
    """Apply resource mutations once and report unchanged repeated requests."""
    module_obj = load_dynamic_group_module(monkeypatch)
    created = FakeModel(id="dg1", display_name="compute", matching_rule="rule")
    calls = []
    instance = make_dynamic_group(
        module_obj,
        {"name": "compute", "matching_rule": "rule"},
        types.SimpleNamespace(
            create_dynamic_resource_group=lambda **kwargs: calls.append(kwargs)
            or FakeResponse(created),
            delete_dynamic_resource_group=lambda **kwargs: calls.append(kwargs),
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload["changed"] is True
    assert calls[0]["dynamic_resource_group"].matching_rule == "rule"
    assert calls[0]["attributes"] == "matchingRule"

    instance.module.params = {"name": "compute", "matching_rule": "rule"}
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: created)
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload["changed"] is False

    instance.module.params = {"state": "absent", "dynamic_group_id": "dg1"}
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload["changed"] is True
    assert calls[-1] == {"dynamic_resource_group_id": "dg1"}

    instance.module.params = {"state": "absent", "dynamic_group_id": "dg1"}
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload == {"changed": False}
    instance.check_mode = True
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload == {"changed": False}


def test_unchanged_present_normal_and_check_mode(monkeypatch):
    """Return unchanged state for normal and check-mode requests."""
    module_obj = load_dynamic_group_module(monkeypatch)
    instance = make_dynamic_group(
        module_obj,
        {"name": "compute", "matching_rule": "rule"},
        check_mode=False,
    )
    resource = FakeModel(id="dg1", display_name="compute", matching_rule="rule")
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: resource)
    for check_mode in (False, True):
        instance.check_mode = check_mode
        with pytest.raises(ExitJsonCalled) as result:
            instance.execute_resource_module()
        assert result.value.payload["changed"] is False
        assert result.value.payload["resource"]["id"] == "dg1"


def test_get_404_and_other_errors(monkeypatch):
    """Treat a missing dynamic group as absent and re-raise other errors."""
    module_obj = load_dynamic_group_module(monkeypatch)
    instance = make_dynamic_group(module_obj, {"dynamic_group_id": "dg1"})
    error = RuntimeError("missing")
    error.status = 404
    monkeypatch.setattr(instance, "get_resource_response", raising(error))
    assert instance.get_resource_by_id("dg1") is None

    denied = RuntimeError("denied")
    denied.status = 403
    monkeypatch.setattr(instance, "get_resource_response", raising(denied))
    with pytest.raises(RuntimeError, match="denied"):
        instance.get_resource_by_id("dg1")


def test_tag_patch_can_clear_user_tags_and_keeps_oracle_tags(monkeypatch):
    """Clear requested user tags and preserve tags that OCI manages."""
    module_obj = load_dynamic_group_module(monkeypatch)
    instance = make_dynamic_group(
        module_obj,
        {"freeform_tags": {}, "defined_tags": {}},
    )
    current = FakeModel(
        display_name="compute",
        description=None,
        matching_rule="rule",
        urn_ietf_params_scim_schemas_oracle_idcs_extension_oci_tags=FakeModel(
            freeform_tags=[FakeModel(key="team", value="iam")],
            defined_tags=[
                FakeModel(namespace="Oracle-Tags", key="CreatedBy", value="admin")
            ],
        ),
    )
    operations = instance.build_update_plan(current)["operations"]
    helper = sys.modules[module_obj.OciIdentityDomainResourceBase.__module__]
    assert [operation.path for operation in operations] == [
        helper.OCI_TAGS_SCHEMA + ":freeformTags"
    ]
    assert operations[0].value == []
    assert instance.module.params["defined_tags"] == {}

    instance.module.params = {
        "defined_tags": {"Operations": {"CostCenter": "43"}}
    }
    current.urn_ietf_params_scim_schemas_oracle_idcs_extension_oci_tags.defined_tags = [
        FakeModel(namespace="Oracle-Tags", key="CreatedBy", value="admin"),
        FakeModel(namespace="Operations", key="CostCenter", value="42"),
    ]
    operations = instance.build_update_plan(current)["operations"]
    assert len(operations) == 1
    assert [
        (tag.namespace, tag.key, tag.value) for tag in operations[0].value
    ] == [
        ("Operations", "CostCenter", "43"),
        ("Oracle-Tags", "CreatedBy", "admin"),
    ]
