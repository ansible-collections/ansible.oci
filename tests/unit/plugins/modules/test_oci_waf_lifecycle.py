from __future__ import absolute_import, division, print_function

__metaclass__ = type

import types

import pytest

from .conftest import (
    ExitJsonCalled,
    FailJsonCalled,
    FakeModel,
    FakeResponse,
    load_collection_module,
    make_module_instance,
    raising,
)

RESOURCES = (
    (
        "oci_waf_web_app_firewall_policy",
        "OciWafWebAppFirewallPolicyModule",
        "web_app_firewall_policy_id",
        {},
    ),
    (
        "oci_waf_web_app_firewall",
        "OciWafWebAppFirewallModule",
        "web_app_firewall_id",
        {"load_balancer_id": "lb", "web_app_firewall_policy_id": "policy"},
    ),
)


@pytest.mark.parametrize("module_name,class_name,id_param,required", RESOURCES)
@pytest.mark.parametrize("operation", ("create", "update", "delete"))
def test_check_mode_predicts_changes_without_mutations(
    monkeypatch, module_name, class_name, id_param, required, operation
):
    """Predict each lifecycle change without sending a mutation to OCI."""
    module = load_collection_module(module_name)
    params = dict(required, compartment_id="compartment", name="desired")
    if operation == "delete":
        params.update({id_param: "resource", "state": "absent"})
    current = (
        None
        if operation == "create"
        else FakeModel(
            **dict(
                params, id="resource", display_name="current", lifecycle_state="ACTIVE"
            )
        )
    )
    instance = make_module_instance(module, class_name, params, check_mode=True)
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: current)
    for method in ("create_resource", "update_resource", "delete_resource"):
        monkeypatch.setattr(
            instance, method, raising(AssertionError("Check mode sent a mutation"))
        )
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload == {"changed": True}


@pytest.mark.parametrize("module_name,class_name,id_param,required", RESOURCES)
@pytest.mark.parametrize("check_mode", (False, True))
def test_matching_resource_is_unchanged(
    monkeypatch, module_name, class_name, id_param, required, check_mode
):
    """Keep matching resources unchanged in normal and check mode."""
    module = load_collection_module(module_name)
    params = dict(required, compartment_id="compartment", name="desired")
    current = FakeModel(
        **dict(params, id="resource", display_name="desired", lifecycle_state="ACTIVE")
    )
    instance = make_module_instance(module, class_name, params, check_mode=check_mode)
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: current)
    monkeypatch.setattr(
        instance,
        "update_resource",
        raising(AssertionError("Unchanged resource was updated")),
    )
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload["changed"] is False
    assert result.value.payload["resource"]["id"] == "resource"
    assert result.value.payload["resource"]["name"] == "desired"


@pytest.mark.parametrize("module_name,class_name,id_param,required", RESOURCES)
@pytest.mark.parametrize("check_mode", (False, True))
def test_absent_resource_is_unchanged(
    monkeypatch, module_name, class_name, id_param, required, check_mode
):
    """Keep repeated deletion unchanged when the resource is absent."""
    module = load_collection_module(module_name)
    instance = make_module_instance(
        module,
        class_name,
        {id_param: "missing", "state": "absent"},
        check_mode=check_mode,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)
    monkeypatch.setattr(
        instance,
        "delete_resource",
        raising(AssertionError("Missing resource was deleted")),
    )
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload == {"changed": False}


@pytest.mark.parametrize("module_name,class_name,id_param,required", RESOURCES)
def test_missing_explicit_update_target_does_not_create(
    monkeypatch, module_name, class_name, id_param, required
):
    """Fail an explicit update when the target OCID does not exist."""
    module = load_collection_module(module_name)
    instance = make_module_instance(module, class_name, {id_param: "missing"})
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)
    monkeypatch.setattr(
        instance,
        "create_resource",
        raising(AssertionError("Missing update target was created")),
    )
    with pytest.raises(FailJsonCalled) as result:
        instance.execute_resource_module()
    assert "missing" in result.value.payload["msg"]


@pytest.mark.parametrize("module_name,class_name,id_param,required", RESOURCES)
@pytest.mark.parametrize("operation", ("create", "update", "delete"))
def test_failed_work_request_stops_the_operation(
    monkeypatch, module_name, class_name, id_param, required, operation
):
    """Propagate work-request failure for every lifecycle operation."""
    module = load_collection_module(module_name)
    params = dict(required, compartment_id="compartment", name="desired", wait=True)
    current = FakeModel(
        **dict(
            required,
            id="resource",
            display_name="current",
            compartment_id="compartment",
        )
    )
    response = FakeResponse(
        data=FakeModel(id="resource"), headers={"opc-work-request-id": "request"}
    )
    sdk_suffix = module_name.removeprefix("oci_waf_")
    calls = []
    client = types.SimpleNamespace(
        **{operation + "_" + sdk_suffix: lambda **kw: calls.append(kw) or response}
    )
    instance = make_module_instance(module, class_name, params, client=client)
    monkeypatch.setattr(
        instance, "call_with_retry", lambda function, **kw: function(**kw)
    )
    monkeypatch.setattr(
        instance, "wait_for_work_request", raising(RuntimeError("Work request FAILED"))
    )
    monkeypatch.setattr(
        instance,
        "get_resource_response",
        raising(AssertionError("Read after failed work request")),
    )
    if operation == "create":
        with pytest.raises(RuntimeError, match="Work request FAILED"):
            instance.create_resource()
    else:
        with pytest.raises(RuntimeError, match="Work request FAILED"):
            getattr(instance, operation + "_resource")(current)
    assert len(calls) == 1


@pytest.mark.parametrize("module_name,class_name,id_param,required", RESOURCES)
def test_update_without_wait_never_polls(
    monkeypatch, module_name, class_name, id_param, required
):
    """Return a resource ID without polling an asynchronous update."""
    module = load_collection_module(module_name)
    params = {"name": "desired", "wait": False}
    suffix = module_name.removeprefix("oci_waf_")
    client = types.SimpleNamespace(
        **{
            "update_"
            + suffix: lambda **kw: FakeResponse(
                headers={"opc-work-request-id": "request"}
            )
        }
    )
    instance = make_module_instance(module, class_name, params, client=client)
    monkeypatch.setattr(
        instance, "call_with_retry", lambda function, **kw: function(**kw)
    )
    monkeypatch.setattr(
        instance,
        "wait_for_work_request",
        raising(AssertionError("wait=false polled work request")),
    )
    monkeypatch.setattr(
        instance,
        "get_resource_response",
        raising(AssertionError("wait=false polled resource")),
    )
    result = instance.serialize_result_resource(
        instance.update_resource(FakeModel(id="resource", display_name="current"))
    )
    assert result["id"] == "resource"


@pytest.mark.parametrize("module_name,class_name,id_param,required", RESOURCES)
def test_info_get_and_not_found(
    monkeypatch, module_name, class_name, id_param, required
):
    """Retrieve one resource by ID and return an empty list on HTTP 404."""
    module = load_collection_module(module_name + "_info")
    info_class = class_name.removesuffix("Module") + "InfoModule"
    suffix = module_name.removeprefix("oci_waf_")
    calls = []
    resource = FakeModel(id="resource", display_name="MixedCase")
    client = types.SimpleNamespace(
        **{
            "get_" + suffix: lambda **kw: calls.append(kw)
            or FakeResponse(data=resource)
        }
    )
    instance = make_module_instance(
        module, info_class, {id_param: "resource"}, client=client
    )
    monkeypatch.setattr(
        instance, "call_with_retry", lambda function, **kw: function(**kw)
    )
    assert instance.fetch_resources() == [resource]
    assert calls == [{id_param: "resource"}]
    assert instance.serialize_result_resource(resource)["name"] == "MixedCase"
    error = RuntimeError("not found")
    error.status = 404
    monkeypatch.setattr(instance, "call_with_retry", raising(error))
    assert instance.fetch_resources() == []
    error.status = 403
    with pytest.raises(RuntimeError, match="not found"):
        instance.fetch_resources()


@pytest.mark.parametrize("module_name,class_name,id_param,required", RESOURCES)
def test_info_lists_and_filters_exact_names(
    monkeypatch, module_name, class_name, id_param, required
):
    """Pass service filters to pagination and apply exact name filtering."""
    module = load_collection_module(module_name + "_info")
    info_class = class_name.removesuffix("Module") + "InfoModule"
    suffix = module_name.removeprefix("oci_waf_")
    list_method = "list_" + suffix + ("ies" if suffix.endswith("policy") else "s")
    if suffix.endswith("policy"):
        list_method = "list_" + suffix[:-1] + "ies"
    method = object()
    client = types.SimpleNamespace(**{list_method: method})
    params = {
        "compartment_id": "compartment",
        "name": "MixedCase",
        "lifecycle_state": "active",
    }
    instance = make_module_instance(module, info_class, params, client=client)
    match = FakeModel(id="match", display_name="MixedCase")
    calls = []
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda fn, **kw: calls.append((fn, kw))
        or [match, FakeModel(display_name="mixedcase")],
    )
    assert instance.fetch_resources() == [match]
    state = ["ACTIVE"]
    assert calls == [
        (method, {"compartment_id": "compartment", "lifecycle_state": state})
    ]
