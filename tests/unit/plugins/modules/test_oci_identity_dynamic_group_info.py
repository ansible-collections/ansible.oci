from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


def load_dynamic_group_info_module(monkeypatch):
    """Load the info module with fake OCI SDK models.

    Args:
        monkeypatch: Pytest fixture for temporary module changes.

    Returns:
        The imported dynamic group info module.
    """
    install_fake_oci(monkeypatch)
    return load_collection_module("oci_identity_dynamic_group_info")


def test_info_get_list_and_serialization(monkeypatch):
    """Check ID lookup, exact name filters, response fields, and output."""
    module_obj = load_dynamic_group_info_module(monkeypatch)
    module_class = module_obj.OciIdentityDynamicGroupInfoModule
    captured = {}
    monkeypatch.setattr(
        module_obj,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule({}),
    )
    monkeypatch.setattr(
        module_obj,
        "OciIdentityDynamicGroupInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )
    module_obj.main()
    assert captured["required_one_of"] == [["domain_id", "domain_url"]]
    assert captured["argument_spec"]["dynamic_group_id"] == {"type": "str"}
    monkeypatch.setattr(module_obj, "OciIdentityDynamicGroupInfoModule", module_class)

    group = FakeModel(
        id="dg1",
        ocid="ocid1.dynamicgroup.example",
        domain_ocid="ocid1.domain.example",
        display_name="compute",
        description="Compute instances",
        matching_rule="instance.compartment.id = 'ocid1.compartment.example'",
        meta=FakeModel(created="created", last_modified="modified"),
        urn_ietf_params_scim_schemas_oracle_idcs_extension_oci_tags=FakeModel(
            freeform_tags=[FakeModel(key="team", value="iam")],
            defined_tags=[],
        ),
    )
    client = types.SimpleNamespace(
        get_dynamic_resource_group=object(), list_dynamic_resource_groups=object()
    )
    instance = make_module_instance(
        module_obj,
        "OciIdentityDynamicGroupInfoModule",
        {"dynamic_group_id": "dg1"},
        client=client,
    )
    calls = []
    monkeypatch.setattr(
        instance,
        "get_resource_by_id",
        lambda resource_id, method, **kwargs: calls.append((resource_id, method, kwargs))
        or [group],
    )
    assert instance.fetch_resources() == [group]
    assert calls == [
        (
            "dg1",
            client.get_dynamic_resource_group,
            {
                "dynamic_resource_group_id": "dg1",
                "attributes": "matchingRule",
                "attribute_sets": ["default"],
            },
        )
    ]
    assert instance.serialize_result_resource(group) == {
        "id": "dg1",
        "ocid": "ocid1.dynamicgroup.example",
        "domain_id": "ocid1.domain.example",
        "name": "compute",
        "freeform_tags": {"team": "iam"},
        "defined_tags": {},
        "time_created": "created",
        "time_modified": "modified",
        "description": "Compute instances",
        "matching_rule": "instance.compartment.id = 'ocid1.compartment.example'",
    }

    instance.module.params = {"name": 'compute\\"prod'}
    list_calls = []
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda method, **kwargs: list_calls.append((method, kwargs)) or [group],
    )
    assert instance.fetch_resources() == [group]
    assert list_calls == [
        (
            client.list_dynamic_resource_groups,
            {
                "attributes": "matchingRule",
                "attribute_sets": ["default"],
                "filter": 'displayName eq "compute\\\\\\"prod"',
            },
        )
    ]


def test_info_list_paginates_resources(monkeypatch):
    """Read every SCIM list page and preserve matching-rule response options."""
    module_obj = load_dynamic_group_info_module(monkeypatch)
    instance = make_module_instance(
        module_obj,
        "OciIdentityDynamicGroupInfoModule",
        {"name": "compute"},
        client=types.SimpleNamespace(list_dynamic_resource_groups=object()),
    )
    responses = iter(
        [
            FakeResponse(FakeModel(resources=["first"]), {"opc-next-page": "page2"}),
            FakeResponse(FakeModel(resources=["second"])),
        ]
    )
    calls = []
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda method, **kwargs: calls.append(kwargs) or next(responses),
    )
    assert instance.list_all_resources(
        instance.client.list_dynamic_resource_groups,
        **instance.get_scim_response_kwargs(),
    ) == ["first", "second"]
    assert calls == [
        {"attributes": "matchingRule", "attribute_sets": ["default"]},
        {
            "attributes": "matchingRule",
            "attribute_sets": ["default"],
            "page": "page2",
        },
    ]


def test_info_execute_returns_unchanged_results_and_404_list(monkeypatch):
    """Return serialized results and an empty list for a missing resource."""
    module_obj = load_dynamic_group_info_module(monkeypatch)
    instance = make_module_instance(
        module_obj,
        "OciIdentityDynamicGroupInfoModule",
        {"name": "compute"},
        client=types.SimpleNamespace(get_dynamic_resource_group=object()),
    )
    group = FakeModel(id="dg1", display_name="compute", matching_rule="rule")
    monkeypatch.setattr(instance, "fetch_resources", lambda: [group])
    try:
        instance.execute_info_module()
    except ExitJsonCalled as result:
        assert result.payload["changed"] is False
        assert result.payload["dynamic_groups"] == [
            {
                "id": "dg1",
                "ocid": None,
                "domain_id": None,
                "name": "compute",
                "freeform_tags": {},
                "defined_tags": {},
                "time_created": None,
                "time_modified": None,
                "description": None,
                "matching_rule": "rule",
            }
        ]
    else:
        raise AssertionError("execute_info_module did not exit")

    error = RuntimeError("missing")
    error.status = 404
    missing_instance = make_module_instance(
        module_obj,
        "OciIdentityDynamicGroupInfoModule",
        {"dynamic_group_id": "missing"},
        client=types.SimpleNamespace(get_dynamic_resource_group=object()),
    )
    monkeypatch.setattr(missing_instance, "call_with_retry", raising(error))
    assert missing_instance.fetch_resources() == []
