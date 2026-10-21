from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from .conftest import (
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


MODULE_CASES = (
    (
        "oci_identity_group_info",
        "OciIdentityGroupInfoModule",
        "group_id",
        "group_id",
        "get_group",
        "list_groups",
        {},
    ),
    (
        "oci_identity_dynamic_group_info",
        "OciIdentityDynamicGroupInfoModule",
        "dynamic_group_id",
        "dynamic_resource_group_id",
        "get_dynamic_resource_group",
        "list_dynamic_resource_groups",
        {"attributes": "matchingRule", "attribute_sets": ["default"]},
    ),
)

RESOURCE_CASES = (
    ("oci_identity_group", "OciIdentityGroupModule", "list_groups", {}),
    (
        "oci_identity_dynamic_group",
        "OciIdentityDynamicGroupModule",
        "list_dynamic_resource_groups",
        {"attributes": "matchingRule", "attribute_sets": ["default"]},
    ),
)

SHARED_HELPER_MODELS = (
    "ExtensionOCITags",
    "FreeformTags",
    "DefinedTags",
    "PatchOp",
    "Operations",
)


def load_module(monkeypatch, module_name):
    """Load one identity module with fake OCI SDK objects.

    Args:
        monkeypatch: Pytest fixture for temporary module changes.
        module_name: Name of the module to import.

    Returns:
        The imported module.
    """
    install_fake_oci(monkeypatch, model_names=SHARED_HELPER_MODELS)
    return load_collection_module(module_name)


@pytest.mark.parametrize(
    "module_name,class_name,list_method,response_kwargs", RESOURCE_CASES
)
def test_resource_lookup_without_name_does_not_list(
    monkeypatch, module_name, class_name, list_method, response_kwargs
):
    """Skip a resource name lookup when no name was supplied."""
    module_obj = load_module(monkeypatch, module_name)
    instance = make_module_instance(
        module_obj,
        class_name,
        {},
        client=types.SimpleNamespace(**{list_method: object()}),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda *args, **kwargs: pytest.fail("unexpected list call"),
    )
    assert instance.find_resources_by_name() == []


@pytest.mark.parametrize(
    "module_name,class_name,id_param,id_kwarg,get_method,list_method,response_kwargs",
    MODULE_CASES,
)
def test_info_lookup_uses_optional_exact_name_and_id_precedence(
    monkeypatch,
    module_name,
    class_name,
    id_param,
    id_kwarg,
    get_method,
    list_method,
    response_kwargs,
):
    """List all resources without a name and prefer an ID over a name."""
    module_obj = load_module(monkeypatch, module_name)
    list_fn = object()
    get_fn = object()
    instance = make_module_instance(
        module_obj,
        class_name,
        {},
        client=types.SimpleNamespace(**{list_method: list_fn, get_method: get_fn}),
    )
    list_calls = []
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda method, **kwargs: list_calls.append((method, kwargs)) or ["listed"],
    )
    assert instance.fetch_resources() == ["listed"]
    assert list_calls == [(list_fn, response_kwargs)]

    instance.module.params = {"name": ""}
    assert instance.fetch_resources() == ["listed"]
    assert list_calls[-1] == (
        list_fn,
        {**response_kwargs, "filter": 'displayName eq ""'},
    )

    instance.module.params = {id_param: "resource-id", "name": "ignored"}
    get_calls = []
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda method, **kwargs: get_calls.append((method, kwargs))
        or FakeResponse(FakeModel(id="resource-id")),
    )
    assert instance.fetch_resources()[0].id == "resource-id"
    assert get_calls == [
        (get_fn, {id_kwarg: "resource-id", **response_kwargs})
    ]
    assert len(list_calls) == 2


@pytest.mark.parametrize(
    "module_name,class_name,id_param,id_kwarg,get_method,list_method,response_kwargs",
    MODULE_CASES,
)
def test_info_lookup_escapes_quotes_and_backslashes(
    monkeypatch,
    module_name,
    class_name,
    id_param,
    id_kwarg,
    get_method,
    list_method,
    response_kwargs,
):
    """Escape quotes and backslashes in an exact SCIM name filter."""
    module_obj = load_module(monkeypatch, module_name)
    list_fn = object()
    instance = make_module_instance(
        module_obj,
        class_name,
        {"name": 'a\\b"c'},
        client=types.SimpleNamespace(**{list_method: list_fn}),
    )
    calls = []
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda method, **kwargs: calls.append((method, kwargs)) or [],
    )
    assert instance.fetch_resources() == []
    assert calls == [
        (
            list_fn,
            {
                **response_kwargs,
                "filter": 'displayName eq "a\\\\b\\"c"',
            },
        )
    ]


@pytest.mark.parametrize(
    "module_name,class_name,id_param,id_kwarg,get_method,list_method,response_kwargs",
    MODULE_CASES,
)
def test_info_get_404_returns_empty_and_other_errors_raise(
    monkeypatch,
    module_name,
    class_name,
    id_param,
    id_kwarg,
    get_method,
    list_method,
    response_kwargs,
):
    """Return an empty list for 404 and re-raise other get errors."""
    module_obj = load_module(monkeypatch, module_name)
    instance = make_module_instance(
        module_obj,
        class_name,
        {id_param: "missing"},
        client=types.SimpleNamespace(**{get_method: object()}),
    )
    error = RuntimeError("missing")
    error.status = 404
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        raising(error),
    )
    assert instance.fetch_resources() == []

    denied = RuntimeError("denied")
    denied.status = 403
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        raising(denied),
    )
    with pytest.raises(RuntimeError, match="denied"):
        instance.fetch_resources()


@pytest.mark.parametrize(
    "module_name,class_name,list_method,response_kwargs",
    [
        ("oci_identity_group_info", "OciIdentityGroupInfoModule", "list_groups", {}),
        (
            "oci_identity_dynamic_group_info",
            "OciIdentityDynamicGroupInfoModule",
            "list_dynamic_resource_groups",
            {"attributes": "matchingRule", "attribute_sets": ["default"]},
        ),
    ],
)
def test_info_list_keeps_response_kwargs_on_each_page(
    monkeypatch, module_name, class_name, list_method, response_kwargs
):
    """Keep each resource's response fields across all list pages."""
    module_obj = load_module(monkeypatch, module_name)
    instance = make_module_instance(
        module_obj,
        class_name,
        {"name": "compute"},
        client=types.SimpleNamespace(**{list_method: object()}),
    )
    responses = iter(
        [
            FakeResponse(FakeModel(resources=["first"]), {"opc-next-page": "p2"}),
            FakeResponse(FakeModel(resources=["second"])),
        ]
    )
    calls = []
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda method, **kwargs: calls.append(kwargs) or next(responses),
    )
    assert instance.fetch_resources() == ["first", "second"]
    assert calls == [
        {**response_kwargs, "filter": 'displayName eq "compute"'},
        {**response_kwargs, "filter": 'displayName eq "compute"', "page": "p2"},
    ]
