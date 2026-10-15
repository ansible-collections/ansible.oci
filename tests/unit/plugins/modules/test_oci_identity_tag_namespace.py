from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    FailJsonCalled,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)

MODEL_NAMES = ("CreateTagNamespaceDetails", "UpdateTagNamespaceDetails")


def install_fake_oci(monkeypatch):
    """Install fake OCI clients and models used by these tests."""
    return shared_install_fake_oci(monkeypatch, model_names=MODEL_NAMES)


def make_namespace_module(module_obj, params, client=None, check_mode=False):
    """Build a resource helper without creating a live OCI client."""
    return make_module_instance(
        module_obj,
        "OciIdentityTagNamespaceModule",
        params,
        client=client,
        check_mode=check_mode,
    )


def test_main_exposes_namespace_arguments(monkeypatch):
    """Verify namespace arguments and lifecycle execution."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_identity_tag_namespace")
    captured = {}

    def fake_ansible_module(**kwargs):
        """Test fake ansible module."""
        captured["argument_spec"] = kwargs["argument_spec"]
        return DummyModule({})

    class FakeNamespaceModule:
        def __init__(self, module):
            """Test   init  ."""
            self.module = module

        def execute_resource_module(self):
            """Test execute resource module."""
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciIdentityTagNamespaceModule", FakeNamespaceModule)
    module_obj.main()

    assert captured["run_called"] is True
    assert captured["argument_spec"]["state"]["default"] == "present"
    assert captured["argument_spec"]["tag_namespace_id"] == {"type": "str"}
    assert captured["argument_spec"]["is_retired"] == {"type": "bool"}
    assert "allow_duplicate_name" not in captured["argument_spec"]


def test_create_details_include_scope_and_tags(monkeypatch):
    """Verify create details preserve the compartment, name, and tags."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_identity_tag_namespace")
    details = module_obj.build_create_tag_namespace_details(
        {
            "compartment_id": "ocid1.tenancy.oc1..example",
            "name": "Operations",
            "description": "Operations tags",
            "freeform_tags": {"owner": "platform"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        }
    )
    assert details.compartment_id == "ocid1.tenancy.oc1..example"
    assert details.name == "Operations"
    assert details.description == "Operations tags"
    assert details.freeform_tags == {"owner": "platform"}
    assert details.defined_tags == {"Operations": {"CostCenter": "42"}}


def test_name_lookup_is_case_insensitive_and_compartment_scoped(monkeypatch):
    """Verify name lookup uses the compartment and ignores letter case."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_identity_tag_namespace")
    namespace = FakeModel(id="ocid1.tagnamespace.oc1..example", name="Operations")
    calls = []
    instance = make_namespace_module(
        module_obj,
        {"compartment_id": "ocid1.tenancy.oc1..example", "name": "OPERATIONS"},
        client=types.SimpleNamespace(list_tag_namespaces="list_method"),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: calls.append((list_fn, kwargs)) or [namespace],
    )
    assert instance.resolve_target_resource() is namespace
    assert calls == [
        ("list_method", {"compartment_id": "ocid1.tenancy.oc1..example"})
    ]


def test_create_requires_compartment_name_and_description(monkeypatch):
    """Verify creation requires the compartment, name, and description."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_identity_tag_namespace")
    instance = make_namespace_module(module_obj, {"name": "Operations"})
    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()
    message = exc_info.value.payload["msg"]
    assert "compartment_id" in message
    assert "description" in message


def test_name_comparison_allows_case_only_difference_and_blocks_change(monkeypatch):
    """Verify letter case does not rename the namespace."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_identity_tag_namespace")
    same = make_namespace_module(module_obj, {"name": "operations"})
    assert same.compare_update_field_values("Operations", "operations", "case_insensitive") is False
    changed = make_namespace_module(module_obj, {"name": "new-name"})
    resource = FakeModel(id="ns", name="Operations")
    with pytest.raises(FailJsonCalled):
        changed.build_update_plan(resource)


def test_update_plan_tracks_mutable_fields_and_retirement_wait_state(monkeypatch):
    """Verify updates select changed fields and correct wait states."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_identity_tag_namespace")
    instance = make_namespace_module(
        module_obj,
        {"description": "New description", "is_retired": True},
    )
    resource = FakeModel(id="ns", description="Old description", is_retired=False)
    plan = instance.build_update_plan(resource)
    assert plan["update_model_fields"] == {
        "description": "New description",
        "is_retired": True,
    }
    assert instance.update_wait_states == ["INACTIVE"]
    instance.module.params["is_retired"] = False
    assert instance.update_wait_states == ["ACTIVE"]
    instance.module.params["is_retired"] = None
    assert instance.update_wait_states == ["ACTIVE", "INACTIVE"]


def test_create_and_update_use_namespace_sdk_methods(monkeypatch):
    """Verify retired creation calls create and update in sequence."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_identity_tag_namespace")
    calls = []

    def create_tag_namespace(create_tag_namespace_details):
        """Test create tag namespace."""
        calls.append(("create", create_tag_namespace_details))
        return FakeResponse(
            FakeModel(
                id="ns",
                compartment_id="ocid1.tenancy.oc1..example",
                name="Operations",
                description="Operations tags",
                is_retired=False,
                lifecycle_state="ACTIVE",
            )
        )

    def update_tag_namespace(tag_namespace_id, update_tag_namespace_details):
        """Test update tag namespace."""
        calls.append(("update", tag_namespace_id, update_tag_namespace_details))
        return FakeResponse(FakeModel(id=tag_namespace_id, lifecycle_state="INACTIVE"))

    instance = make_namespace_module(
        module_obj,
        {
            "compartment_id": "ocid1.tenancy.oc1..example",
            "name": "Operations",
            "description": "Operations tags",
            "is_retired": True,
            "wait": False,
        },
        client=types.SimpleNamespace(
            create_tag_namespace=create_tag_namespace,
            update_tag_namespace=update_tag_namespace,
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(instance, "get_mutation_result", lambda data, resource_id, states: data)
    created = instance.create_resource()
    assert calls[0][0] == "create"
    assert calls[1][0] == "update"
    assert calls[1][2].is_retired is True
    assert created.lifecycle_state == "INACTIVE"


@pytest.mark.parametrize("is_retired", [False, True])
@pytest.mark.parametrize("wait", [False, True])
def test_delete_retires_and_cascades(monkeypatch, is_retired, wait):
    """Verify retirement, cascade deletion, and optional work request waiting."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_identity_tag_namespace")
    calls = []
    response = FakeResponse(None, headers={"opc-work-request-id": "work-request"})

    def update_namespace(**kwargs):
        """Record the retirement request."""
        calls.append(("retire", kwargs))
        return FakeResponse(None)

    def cascade_delete(**kwargs):
        """Record deletion of the namespace and its definitions."""
        calls.append(("cascade", kwargs))
        return response

    client = types.SimpleNamespace(
        update_tag_namespace=update_namespace,
        cascade_delete_tag_namespace=cascade_delete,
        get_tagging_work_request="get_tagging_work_request",
    )
    instance = make_namespace_module(
        module_obj,
        {"wait": wait, "is_retired": False, "description": "Ignore during deletion"},
        client=client,
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "wait_for_work_request",
        lambda *args, **kwargs: calls.append(("wait", args, kwargs)) or "completed",
    )
    result = instance.delete_resource(
        FakeModel(id="ns", is_retired=is_retired, lifecycle_state="INACTIVE" if is_retired else "ACTIVE")
    )
    if not is_retired:
        operation, options = calls.pop(0)
        assert operation == "retire"
        assert options["tag_namespace_id"] == "ns"
        assert options["update_tag_namespace_details"].__dict__ == {"is_retired": True}
    assert calls.pop(0) == ("cascade", {"tag_namespace_id": "ns"})
    if wait:
        assert calls.pop(0) == (
            "wait", (client, "work-request"),
            {"get_work_request_fn": client.get_tagging_work_request},
        )
        assert result == "completed"
    else:
        assert result is response
    assert calls == []


@pytest.mark.parametrize("wait", [False, True])
def test_delete_does_not_restart_pending_deletion(monkeypatch, wait):
    """Verify repeated deletion does not repeat retirement or cascade deletion."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_identity_tag_namespace")
    instance = make_namespace_module(module_obj, {"wait": wait})
    resource = FakeModel(id="ns", lifecycle_state="DELETING", is_retired=True)
    calls = []
    monkeypatch.setattr(
        instance,
        "get_mutation_result",
        lambda *args: calls.append(args) or resource,
    )
    assert instance.delete_resource(resource) is resource
    assert calls[0][:2] == (resource, "ns")
    assert set(calls[0][2]) == instance.dead_states


def test_get_by_id_returns_none_on_404(monkeypatch):
    """Verify a missing namespace returns no resource."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_identity_tag_namespace")
    instance = make_namespace_module(
        module_obj,
        {},
        client=types.SimpleNamespace(get_tag_namespace=lambda **kwargs: None),
    )
    error = RuntimeError("missing")
    error.status = 404
    monkeypatch.setattr(instance, "get_resource_response", raising(error))
    assert instance.get_resource_by_id("missing") is None


def test_present_check_mode_predicts_change_without_sdk_mutation(monkeypatch):
    """Verify check mode predicts creation without a mutation."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_identity_tag_namespace")
    instance = make_namespace_module(
        module_obj,
        {
            "compartment_id": "ocid1.tenancy.oc1..example",
            "name": "Operations",
            "description": "Operations tags",
        },
        check_mode=True,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)
    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()
    assert exc_info.value.payload == {"changed": True}


@pytest.mark.parametrize("is_retired,lifecycle_state", [(False, "ACTIVE"), (True, "INACTIVE")])
def test_present_is_idempotent_for_active_and_retired_namespaces(monkeypatch, is_retired, lifecycle_state):
    """Test normal and check mode when retirement state is unspecified."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_identity_tag_namespace")
    namespace = FakeModel(
        id="ns",
        compartment_id="ocid1.tenancy.oc1..example",
        name="Operations",
        description="Operations tags",
        is_retired=is_retired,
        lifecycle_state=lifecycle_state,
    )
    params = {
        "compartment_id": "ocid1.tenancy.oc1..example",
        "name": "operations",
        "description": "Operations tags",
        "is_retired": None,
    }
    for check_mode in (False, True):
        instance = make_namespace_module(module_obj, params, check_mode=check_mode)
        monkeypatch.setattr(instance, "resolve_target_resource", lambda: namespace)
        with pytest.raises(ExitJsonCalled) as exc_info:
            instance.execute_resource_module()
        assert exc_info.value.payload["changed"] is False


def test_update_check_mode_predicts_change_without_mutation(monkeypatch):
    """Test that check mode detects drift without calling the update method."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_identity_tag_namespace")
    instance = make_namespace_module(
        module_obj,
        {"description": "New description"},
        check_mode=True,
    )
    resource = FakeModel(
        id="ns",
        compartment_id="ocid1.tenancy.oc1..example",
        name="Operations",
        description="Old description",
        is_retired=False,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: resource)
    monkeypatch.setattr(
        instance,
        "update_resource",
        lambda _resource: pytest.fail("check mode must not update the resource"),
    )
    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()
    assert exc_info.value.payload == {"changed": True}


def test_compartment_id_change_is_immutable(monkeypatch):
    """Test that the module rejects a change to the namespace compartment."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_identity_tag_namespace")
    instance = make_namespace_module(
        module_obj,
        {"compartment_id": "ocid1.tenancy.oc1..new"},
    )
    resource = FakeModel(
        id="ns",
        compartment_id="ocid1.tenancy.oc1..old",
        name="Operations",
    )
    with pytest.raises(FailJsonCalled, match="compartment_id"):
        instance.build_update_plan(resource)


def test_delete_check_mode_and_repeated_absent_are_no_ops(monkeypatch):
    """Test delete prediction and the no-op result after deletion."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_identity_tag_namespace")
    resource = FakeModel(id="ns", lifecycle_state="ACTIVE")
    instance = make_namespace_module(
        module_obj,
        {"state": "absent", "tag_namespace_id": "ns"},
        check_mode=True,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: resource)
    monkeypatch.setattr(
        instance,
        "delete_resource",
        lambda _resource: pytest.fail("check mode must not delete the resource"),
    )
    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()
    assert exc_info.value.payload == {"changed": True}

    instance = make_namespace_module(
        module_obj,
        {"state": "absent", "tag_namespace_id": "ns"},
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)
    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_resource_module()
    assert exc_info.value.payload == {"changed": False}


def test_delete_reports_dependency_conflict(monkeypatch):
    """Test that OCI dependency conflicts become a clear module failure."""
    service_error = install_fake_oci(monkeypatch)[1]
    module_obj = load_collection_module("oci_identity_tag_namespace")
    error = service_error(409, "tag deletion already in progress")
    instance = make_namespace_module(
        module_obj,
        {},
        client=types.SimpleNamespace(
            cascade_delete_tag_namespace=raising(error)
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    resource = FakeModel(id="ns", is_retired=True, lifecycle_state="INACTIVE")
    with pytest.raises(FailJsonCalled, match="dependent resources exist"):
        instance.delete_resource(resource)
