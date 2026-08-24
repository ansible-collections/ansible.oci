from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import types

import pytest
from ansible.module_utils.basic import missing_required_lib

from conftest import load_collection_module, raising


class ExitJsonCalled(Exception):
    def __init__(self, payload):
        self.payload = payload


class FailJsonCalled(Exception):
    def __init__(self, payload):
        self.payload = payload


class DummyModule:
    def __init__(self, params=None):
        self.params = params or {}
        self.check_mode = False

    def fail_json(self, **kwargs):
        raise FailJsonCalled(kwargs)

    def exit_json(self, **kwargs):
        raise ExitJsonCalled(kwargs)


def patch_create_service_client(monkeypatch, module_obj, factory):
    monkeypatch.setitem(
        module_obj.OciModuleBase.__init__.__globals__,
        "create_service_client",
        factory,
    )


def patch_serialize_oci_model(monkeypatch, module_obj, serializer):
    monkeypatch.setitem(
        module_obj.OciModuleBase.serialize_result_resource.__globals__,
        "serialize_oci_model",
        serializer,
    )


def install_fake_oci_sdk(monkeypatch, *, pagination=None, retry=None, wait_until=None):
    """Register a fake ``oci`` module so freshly (re)loaded modules pick it up."""
    oci_module = types.ModuleType("oci")
    exceptions_module = types.ModuleType("oci.exceptions")

    class ServiceError(Exception):
        def __init__(self, status):
            super().__init__(status)
            self.status = status

    exceptions_module.ServiceError = ServiceError
    oci_module.exceptions = exceptions_module
    oci_module.pagination = pagination or types.SimpleNamespace()
    oci_module.retry = retry or types.SimpleNamespace()
    oci_module.wait_until = wait_until

    monkeypatch.setitem(sys.modules, "oci", oci_module)
    monkeypatch.setitem(sys.modules, "oci.exceptions", exceptions_module)

    return ServiceError


class _PassthroughRetryStrategy:
    """Fake OCI retry strategy that just invokes the wrapped call once."""

    def make_retrying_call(self, fn, *args, **kwargs):
        return fn(*args, **kwargs)


class _PassthroughRetryStrategyBuilder:
    """Fake ``oci.retry.RetryStrategyBuilder`` for tests that don't exercise retries."""

    def __init__(self, **kwargs):
        pass

    def get_retry_strategy(self):
        return _PassthroughRetryStrategy()


def passthrough_retry_module():
    """Return a fake ``oci.retry`` module usable with ``call_with_retry``."""
    return types.SimpleNamespace(RetryStrategyBuilder=_PassthroughRetryStrategyBuilder)


def test_oci_resource_base_uses_shared_serializer(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object

        def resolve_target_resource(self):
            raise AssertionError("get_resource should not be called")

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    patch_serialize_oci_model(
        monkeypatch,
        oci_resource,
        lambda resource: {"delegated": True},
    )

    resource = ExampleResource(DummyModule())

    assert resource.serialize_result_resource(object()) == {"delegated": True}


def test_oci_resource_base_renames_aliased_fields_in_results(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        field_param_aliases = {"resource_label": "label"}

        def resolve_target_resource(self):
            raise AssertionError("get_resource should not be called")

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    resource = ExampleResource(DummyModule({"name": "example-resource", "label": "blue"}))

    assert resource.serialize_result_resource(
        types.SimpleNamespace(
            display_name="example-resource",
            resource_label="blue",
            id="ocid1.example.oc1..123",
            lifecycle_state="ACTIVE",
        )
    ) == {
        "id": "ocid1.example.oc1..123",
        "lifecycle_state": "ACTIVE",
        "name": "example-resource",
        "label": "blue",
    }


def test_oci_resource_base_does_not_expose_generic_attribute_update_hook(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object

        def resolve_target_resource(self):
            raise AssertionError("get_resource should not be called")

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    resource = ExampleResource(DummyModule())

    assert not hasattr(resource, "_updatable_attributes")


def test_oci_resource_base_build_update_plan_maps_aliased_mutable_fields(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        update_field_specs = (
            {
                "param_name": "name",
                "resource_field": "display_name",
                "update_field": "display_name",
                "is_mutable": True,
            },
        )

        def resolve_target_resource(self):
            raise AssertionError("get_resource should not be called")

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    resource = ExampleResource(DummyModule({"name": "updated-name"}))

    update_plan = resource.build_update_plan(
        types.SimpleNamespace(display_name="current-name")
    )

    assert update_plan["update_needed"] is True
    assert update_plan["update_model_fields"] == {"display_name": "updated-name"}
    assert update_plan["strategy_operations"] == []


def test_oci_resource_base_build_update_plan_skips_matching_name_alias(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        update_field_specs = (
            {
                "param_name": "name",
                "resource_field": "display_name",
                "update_field": "display_name",
                "is_mutable": True,
            },
        )

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    resource = ExampleResource(DummyModule({"name": "current-name"}))

    update_plan = resource.build_update_plan(
        types.SimpleNamespace(display_name="current-name")
    )

    assert update_plan["update_needed"] is False
    assert update_plan["update_model_fields"] == {}
    assert update_plan["strategy_operations"] == []


def test_oci_resource_base_build_update_plan_rejects_immutable_field_drift(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        create_resource_name = "example resource"
        update_field_specs = (
            {
                "param_name": "dns_label",
                "resource_field": "dns_label",
                "is_mutable": False,
                "immutable_reason": "OCI treats dns_label as immutable after create",
            },
        )

        def resolve_target_resource(self):
            raise AssertionError("get_resource should not be called")

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    resource = ExampleResource(DummyModule({"dns_label": "desired-label"}))

    with pytest.raises(FailJsonCalled) as exc_info:
        resource.build_update_plan(types.SimpleNamespace(dns_label="current-label"))

    assert "Updating dns_label for an existing example resource is not supported" in exc_info.value.payload["msg"]
    assert "OCI treats dns_label as immutable after create" in exc_info.value.payload["msg"]


def test_oci_resource_base_build_update_plan_supports_sorted_list_compare_and_skips_omitted_params(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        update_field_specs = (
            {
                "param_name": "security_list_ids",
                "resource_field": "security_list_ids",
                "update_field": "security_list_ids",
                "is_mutable": True,
                "compare": "sorted_list",
            },
            {
                "param_name": "cidr_block",
                "resource_field": "cidr_block",
                "update_field": "cidr_block",
                "is_mutable": True,
            },
        )

        def resolve_target_resource(self):
            raise AssertionError("get_resource should not be called")

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    resource = ExampleResource(
        DummyModule(
            {
                "security_list_ids": ["ocid1.securitylist.oc1..two", "ocid1.securitylist.oc1..one"],
            }
        )
    )

    update_plan = resource.build_update_plan(
        types.SimpleNamespace(
            security_list_ids=["ocid1.securitylist.oc1..one", "ocid1.securitylist.oc1..two"],
            cidr_block="10.0.0.0/24",
        )
    )

    assert update_plan["update_needed"] is False
    assert update_plan["update_model_fields"] == {}
    assert update_plan["strategy_operations"] == []


def test_oci_resource_base_build_update_plan_subset_dict_recurses_into_nested_dicts(monkeypatch):
    """Regression test: subset_dict must apply subset semantics at every
    nesting level, not just the top level of the suboption. A resource that
    echoes back an extra field several levels deep (here ``routing.priority``)
    should not be treated as drift when the caller never set it, and enum
    casing declared via ``enum_keys`` should normalize at any depth too.
    """
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        enum_keys = {"mode"}
        update_field_specs = (
            {
                "param_name": "network_config",
                "resource_field": "network_config",
                "update_field": "network_config",
                "is_mutable": True,
                "compare": "subset_dict",
            },
        )

        def resolve_target_resource(self):
            raise AssertionError("get_resource should not be called")

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    resource = ExampleResource(
        DummyModule(
            {
                # "priority" is left unset (Ansible fills it with None), and
                # "mode" is lowercase per this module's own convention.
                "network_config": {"routing": {"mode": "active", "priority": None}},
            }
        )
    )

    update_plan = resource.build_update_plan(
        types.SimpleNamespace(
            # The resource echoes back "priority", a field this caller never set.
            network_config={"routing": {"mode": "ACTIVE", "priority": 10}},
        )
    )

    assert update_plan["update_needed"] is False
    assert update_plan["update_model_fields"] == {}

    drifted_plan = resource.build_update_plan(
        types.SimpleNamespace(
            network_config={"routing": {"mode": "PASSIVE", "priority": 10}},
        )
    )

    assert drifted_plan["update_needed"] is True
    assert drifted_plan["update_model_fields"] == {
        "network_config": {"routing": {"mode": "active", "priority": None}},
    }


def test_oci_resource_base_build_update_plan_subset_dict_compares_nested_lists_as_a_whole(
    monkeypatch,
):
    """Nested lists (for example a list of plugin suboptions) are compared as
    a whole after recursively stripping ``None`` placeholders from their
    elements, rather than matching individual elements by key.

    A fully-specified list that matches the resource exactly is correctly
    recognized as no drift, and genuinely different content is still caught.
    A list element that only sets some of its own fields (leaving the rest as
    Ansible's ``None`` placeholder) still counts as drift against a resource
    that has real values for those fields, because whole-list equality -
    unlike the dict case above - does not match elements individually by key.
    This documents that known, unchanged limitation rather than silently
    depending on it.
    """
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        update_field_specs = (
            {
                "param_name": "agent_config",
                "resource_field": "agent_config",
                "update_field": "agent_config",
                "is_mutable": True,
                "compare": "subset_dict",
            },
        )

        def resolve_target_resource(self):
            raise AssertionError("get_resource should not be called")

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    resource = ExampleResource(
        DummyModule(
            {
                "agent_config": {
                    "plugins_config": [{"name": "monitoring", "desired_state": "enabled"}],
                },
            }
        )
    )

    matching_plan = resource.build_update_plan(
        types.SimpleNamespace(
            agent_config={
                "plugins_config": [{"name": "monitoring", "desired_state": "enabled"}],
            },
        )
    )

    assert matching_plan["update_needed"] is False

    drifted_plan = resource.build_update_plan(
        types.SimpleNamespace(
            agent_config={
                "plugins_config": [{"name": "monitoring", "desired_state": "disabled"}],
            },
        )
    )

    assert drifted_plan["update_needed"] is True

    partially_specified_resource = ExampleResource(
        DummyModule(
            {
                "agent_config": {
                    # desired_state is left unset (None); the caller only
                    # wants to reference the plugin by name.
                    "plugins_config": [{"name": "monitoring", "desired_state": None}],
                },
            }
        )
    )

    partial_plan = partially_specified_resource.build_update_plan(
        types.SimpleNamespace(
            agent_config={
                "plugins_config": [{"name": "monitoring", "desired_state": "enabled"}],
            },
        )
    )

    assert partial_plan["update_needed"] is True


def test_oci_resource_base_build_update_plan_applies_desired_key_map_before_compare(
    monkeypatch,
):
    """A field spec's ``desired_key_map`` renames the caller-supplied param's
    keys to the resource's own field names before comparison, so a module can
    expose factual, non-question-style parameter names (for example
    ``all_plugins_disabled``) while the underlying resource reports its own
    vocabulary (for example ``are_all_plugins_disabled``).

    The renamed keys are only used for drift comparison: update_model_fields
    still records the value under the caller's original param keys, since
    that is what downstream update-details builders expect.
    """
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        update_field_specs = (
            {
                "param_name": "agent_config",
                "resource_field": "agent_config",
                "update_field": "agent_config",
                "is_mutable": True,
                "compare": "subset_dict",
                "desired_key_map": {"all_plugins_disabled": "are_all_plugins_disabled"},
            },
        )

        def resolve_target_resource(self):
            raise AssertionError("get_resource should not be called")

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    resource = ExampleResource(
        DummyModule({"agent_config": {"all_plugins_disabled": False}})
    )

    matching_plan = resource.build_update_plan(
        types.SimpleNamespace(agent_config={"are_all_plugins_disabled": False}),
    )

    assert matching_plan["update_needed"] is False

    drifted_plan = resource.build_update_plan(
        types.SimpleNamespace(agent_config={"are_all_plugins_disabled": True}),
    )

    assert drifted_plan["update_needed"] is True
    assert drifted_plan["update_model_fields"] == {
        "agent_config": {"all_plugins_disabled": False},
    }


def test_oci_resource_base_needs_update_uses_shared_update_plan(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        update_field_specs = (
            {
                "param_name": "name",
                "resource_field": "display_name",
                "update_field": "display_name",
                "is_mutable": True,
            },
        )

        def resolve_target_resource(self):
            raise AssertionError("get_resource should not be called")

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    resource = ExampleResource(DummyModule({"name": "updated-name"}))

    assert resource.needs_update(types.SimpleNamespace(display_name="current-name")) is True


def test_oci_resource_base_build_update_plan_includes_common_tag_fields(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object

        def resolve_target_resource(self):
            raise AssertionError("get_resource should not be called")

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    resource = ExampleResource(DummyModule({"freeform_tags": {"env": "prod"}}))

    update_plan = resource.build_update_plan(
        types.SimpleNamespace(freeform_tags={"env": "dev"})
    )

    assert update_plan["update_needed"] is True
    assert update_plan["update_model_fields"] == {"freeform_tags": {"env": "prod"}}


def test_oci_resource_base_caches_shared_update_plan_per_resource_instance(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        update_field_specs = (
            {
                "param_name": "cidr_blocks",
                "resource_field": "cidr_blocks",
                "is_mutable": True,
                "strategy": "plan_cidr_blocks",
            },
        )

        def __init__(self, module):
            super().__init__(module)
            self.strategy_calls = 0

        def plan_cidr_blocks(self, resource, resource_dict, spec, desired_value):
            self.strategy_calls += 1
            if desired_value != resource_dict.get("cidr_blocks"):
                return [("add", "10.1.0.0/16")]
            return []

        def resolve_target_resource(self):
            raise AssertionError("get_resource should not be called")

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    resource = ExampleResource(DummyModule({"cidr_blocks": ["10.0.0.0/16", "10.1.0.0/16"]}))
    current = types.SimpleNamespace(cidr_blocks=["10.0.0.0/16"])

    assert resource.get_update_plan(current)["update_needed"] is True
    assert resource.get_update_plan(current)["update_needed"] is True
    assert resource.strategy_calls == 1


def test_oci_resource_base_default_update_resource_uses_class_metadata(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    update_calls = []
    response = types.SimpleNamespace(data=types.SimpleNamespace(id="ocid1.example.oc1..updated"))

    class FakeUpdateDetails:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    def update_example(example_id, update_example_details):
        update_calls.append((example_id, update_example_details))
        return response

    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: types.SimpleNamespace(update_example=update_example),
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        resource_id_param = "example_id"
        update_method_name = "update_example"
        update_details_name = "update_example_details"
        update_wait_states = ("AVAILABLE",)
        update_field_specs = (
            {
                "param_name": "name",
                "resource_field": "display_name",
                "update_field": "display_name",
                "is_mutable": True,
            },
        )

        def resolve_target_resource(self):
            raise AssertionError("get_resource should not be called")

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def build_update_details(self, update_model_fields):
            return FakeUpdateDetails(**update_model_fields)

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    resource = ExampleResource(DummyModule({"name": "updated-name", "wait": False}))
    monkeypatch.setattr(
        resource,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    updated_resource = resource.update_resource(
        types.SimpleNamespace(id="ocid1.example.oc1..123", display_name="current-name")
    )

    assert update_calls[0][0] == "ocid1.example.oc1..123"
    assert update_calls[0][1].display_name == "updated-name"
    assert updated_resource.id == "ocid1.example.oc1..updated"


def test_incomplete_oci_resource_subclass_cannot_be_instantiated(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: "client",
    )

    class IncompleteResource(oci_resource.OciResourceBase):
        client_class = object

    with pytest.raises(TypeError):
        IncompleteResource(DummyModule())


def test_oci_resource_base_requires_client_class_before_creating_client(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        raising(AssertionError("create_service_client should not be called")),
    )

    class ExampleResource(oci_resource.OciResourceBase):
        def resolve_target_resource(self):
            return None

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            return None

        def update_resource(self, resource):
            return resource

        def delete_resource(self, resource):
            return None

    with pytest.raises(TypeError, match="client_class"):
        ExampleResource(DummyModule())


def test_oci_info_base_renames_common_and_explicitly_aliased_fields(monkeypatch):
    oci_info = load_collection_module("oci_info")

    patch_create_service_client(
        monkeypatch,
        oci_info,
        lambda module, client_class: "client",
    )

    class ExampleInfo(oci_info.OciInfoBase):
        client_class = object
        field_param_aliases = {"resource_label": "label"}

        def fetch_resources(self):
            return [
                types.SimpleNamespace(
                    display_name="example-resource",
                    resource_label="blue",
                    id="ocid1.example.oc1..123",
                    lifecycle_state="ACTIVE",
                )
            ]

    module = DummyModule({"name": "example-resource", "label": "blue"})
    info_module = ExampleInfo(module)

    with pytest.raises(ExitJsonCalled) as exc_info:
        info_module.execute_info_module()

    # display_name is renamed to "name" via the shared common alias, and
    # resource_label is renamed to "label" via ExampleInfo's own
    # field_param_aliases. Neither value is ever dropped, even though both
    # happen to match the query filters used to find the resource.
    assert exc_info.value.payload == {
        "changed": False,
        "resources": [
            {
                "name": "example-resource",
                "label": "blue",
                "id": "ocid1.example.oc1..123",
                "lifecycle_state": "ACTIVE",
            }
        ],
    }


def test_incomplete_oci_info_subclass_cannot_be_instantiated(monkeypatch):
    oci_info = load_collection_module("oci_info")
    patch_create_service_client(
        monkeypatch,
        oci_info,
        lambda module, client_class: "client",
    )

    class IncompleteInfo(oci_info.OciInfoBase):
        client_class = object

    info_module = IncompleteInfo(DummyModule())

    with pytest.raises(NotImplementedError, match="class metadata"):
        info_module.fetch_resources()


def test_oci_info_base_requires_client_class_before_creating_client(monkeypatch):
    oci_info = load_collection_module("oci_info")
    patch_create_service_client(
        monkeypatch,
        oci_info,
        raising(AssertionError("create_service_client should not be called")),
    )

    class ExampleInfo(oci_info.OciInfoBase):
        def fetch_resources(self):
            return []

    with pytest.raises(TypeError, match="client_class"):
        ExampleInfo(DummyModule())


def test_oci_resource_base_treats_dead_state_as_absent(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    delete_calls = []

    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: "client",
    )
    monkeypatch.setattr(
        oci_resource,
        "DEAD_STATES",
        frozenset({"REMOVED"}),
        raising=False,
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object

        def resolve_target_resource(self):
            return types.SimpleNamespace(lifecycle_state="REMOVED")

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            delete_calls.append(resource)

    resource = ExampleResource(DummyModule({"state": "absent"}))

    with pytest.raises(ExitJsonCalled) as exc_info:
        resource.execute_resource_module()

    assert delete_calls == []
    assert exc_info.value.payload == {"changed": False}


def test_oci_resource_base_treats_terminated_id_as_not_found(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        resource_id_param = "example_id"

        def get_resource_response(self, resource_id):
            return types.SimpleNamespace(
                data=types.SimpleNamespace(
                    id=resource_id,
                    lifecycle_state="TERMINATED",
                )
            )

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    resource = ExampleResource(
        DummyModule({"example_id": "ocid1.example.oc1..terminated"})
    )

    assert resource.resolve_target_resource() is None


def test_oci_resource_base_find_resources_by_name_excludes_terminated_matches(
    monkeypatch,
):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: types.SimpleNamespace(
            list_examples="list_examples_method"
        ),
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        resource_id_param = "example_id"
        list_resource_method = "list_examples"
        list_filter_params = ()

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    live_resource = types.SimpleNamespace(
        id="ocid1.example.oc1..live",
        display_name="example",
        lifecycle_state="AVAILABLE",
    )
    terminated_resource = types.SimpleNamespace(
        id="ocid1.example.oc1..terminated",
        display_name="example",
        lifecycle_state="TERMINATED",
    )
    resource = ExampleResource(
        DummyModule(
            {
                "name": "example",
                "compartment_id": "ocid1.compartment.oc1..example",
            }
        )
    )
    monkeypatch.setattr(
        resource,
        "list_all_resources",
        lambda list_fn, **kwargs: [live_resource, terminated_resource],
    )

    assert resource.find_resources_by_name() == [live_resource]


def test_oci_resource_base_fails_present_when_explicit_id_is_terminated(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        resource_id_param = "example_id"
        create_resource_name = "example resource"

        def get_resource_response(self, resource_id):
            return types.SimpleNamespace(
                data=types.SimpleNamespace(
                    id=resource_id,
                    lifecycle_state="TERMINATED",
                )
            )

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    resource = ExampleResource(
        DummyModule(
            {
                "state": "present",
                "example_id": "ocid1.example.oc1..terminated",
            }
        )
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        resource.execute_resource_module()

    assert "example_id" in exc_info.value.payload["msg"]
    assert "ocid1.example.oc1..terminated" in exc_info.value.payload["msg"]


def test_oci_resource_base_present_recreates_when_name_match_is_terminated(
    monkeypatch,
):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: types.SimpleNamespace(
            list_examples="list_examples_method"
        ),
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        resource_id_param = "example_id"
        list_resource_method = "list_examples"
        list_filter_params = ()
        create_required_fields = ()

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    resource = ExampleResource(
        DummyModule(
            {
                "state": "present",
                "name": "example",
                "compartment_id": "ocid1.compartment.oc1..example",
            }
        )
    )
    resource.check_mode = True
    resource.module.check_mode = True
    monkeypatch.setattr(
        resource,
        "list_all_resources",
        lambda list_fn, **kwargs: [
            types.SimpleNamespace(
                id="ocid1.example.oc1..terminated",
                display_name="example",
                lifecycle_state="TERMINATED",
            )
        ],
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        resource.execute_resource_module()

    assert exc_info.value.payload == {"changed": True}


def test_oci_resource_base_validates_create_request_in_check_mode(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object

        def resolve_target_resource(self):
            return None

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

        def _require_create_fields(self):
            self.module.fail_json(msg="missing create fields")

    module = DummyModule({"state": "present"})
    module.check_mode = True
    resource = ExampleResource(module)

    with pytest.raises(FailJsonCalled) as exc_info:
        resource.execute_resource_module()

    assert exc_info.value.payload == {"msg": "missing create fields"}


def test_oci_resource_base_default_create_field_validation_uses_class_metadata(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        create_required_fields = ("compartment_id", "name")
        create_resource_name = "example resource"

        def resolve_target_resource(self):
            return None

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    module = DummyModule({"state": "present", "name": "example"})
    module.check_mode = True
    resource = ExampleResource(module)

    with pytest.raises(FailJsonCalled) as exc_info:
        resource.execute_resource_module()

    assert exc_info.value.payload == {
        "msg": "Creating a example resource requires the following parameters: compartment_id"
    }


def test_oci_resource_base_fails_present_when_explicit_resource_id_is_missing(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        resource_id_param = "example_id"
        create_resource_name = "example resource"

        def resolve_target_resource(self):
            return None

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    module = DummyModule(
        {
            "state": "present",
            "example_id": "ocid1.example.oc1..missing",
        }
    )
    resource = ExampleResource(module)

    with pytest.raises(FailJsonCalled) as exc_info:
        resource.execute_resource_module()

    assert "No example resource was found for example_id=" in exc_info.value.payload["msg"]
    assert "Create the example resource without example_id" in exc_info.value.payload["msg"]


def test_oci_resource_base_uses_unique_name_match_as_update_target(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: types.SimpleNamespace(
            list_examples="list_examples_method"
        ),
    )
    patch_serialize_oci_model(
        monkeypatch,
        oci_resource,
        lambda resource: {
            "id": resource.id,
            "display_name": resource.display_name,
            "freeform_tags": resource.freeform_tags,
        },
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        resource_id_param = "example_id"
        list_resource_method = "list_examples"
        list_filter_params = ()

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            return types.SimpleNamespace(
                id=resource.id,
                display_name=resource.display_name,
                freeform_tags={"env": "prod"},
            )

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    resource = ExampleResource(
        DummyModule(
            {
                "state": "present",
                "name": "example",
                "compartment_id": "ocid1.compartment.oc1..example",
                "freeform_tags": {"env": "prod"},
                "allow_duplicate_name": False,
            }
        )
    )
    existing_resource = types.SimpleNamespace(
        id="ocid1.example.oc1..123",
        display_name="example",
        freeform_tags={"env": "dev"},
    )
    paginate_calls = []
    monkeypatch.setattr(
        resource,
        "list_all_resources",
        lambda list_fn, **kwargs: paginate_calls.append((list_fn, kwargs)) or [existing_resource],
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        resource.execute_resource_module()

    assert exc_info.value.payload == {
        "changed": True,
        "resource": {
            "id": "ocid1.example.oc1..123",
            "name": "example",
            "freeform_tags": {"env": "prod"},
        },
    }
    assert paginate_calls == [
        (
            "list_examples_method",
            {
                "compartment_id": "ocid1.compartment.oc1..example",
            },
        )
    ]


def test_oci_resource_base_requires_scope_fields_for_name_lookup(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: types.SimpleNamespace(
            list_examples=raising(AssertionError("list_examples should not be called"))
        ),
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        resource_id_param = "example_id"
        list_resource_method = "list_examples"
        common_list_filter_params = ("compartment_id",)
        list_filter_params = ("parent_id",)
        create_resource_name = "example resource"

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    resource = ExampleResource(DummyModule({"name": "example"}))

    with pytest.raises(FailJsonCalled) as exc_info:
        resource.resolve_target_resource()

    assert exc_info.value.payload == {
        "msg": "Using name lookup for example resource requires the following parameters: compartment_id, parent_id"
    }


def test_oci_resource_base_deletes_unique_name_match_without_explicit_id(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: types.SimpleNamespace(
            list_examples="list_examples_method"
        ),
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        resource_id_param = "example_id"
        list_resource_method = "list_examples"
        list_filter_params = ()

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            self.deleted_resource = resource

    resource = ExampleResource(
        DummyModule(
            {
                "state": "absent",
                "name": "example",
                "compartment_id": "ocid1.compartment.oc1..example",
            }
        )
    )
    existing_resource = types.SimpleNamespace(
        id="ocid1.example.oc1..123",
        display_name="example",
        lifecycle_state="AVAILABLE",
    )
    monkeypatch.setattr(
        resource,
        "list_all_resources",
        lambda list_fn, **kwargs: [existing_resource],
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        resource.execute_resource_module()

    assert exc_info.value.payload == {"changed": True}
    assert resource.deleted_resource is existing_resource


def test_oci_resource_base_fails_when_name_lookup_is_ambiguous(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: types.SimpleNamespace(
            list_examples="list_examples_method"
        ),
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        resource_id_param = "example_id"
        list_resource_method = "list_examples"
        list_filter_params = ()
        create_resource_name = "example resource"

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    resource = ExampleResource(
        DummyModule(
            {
                "state": "present",
                "name": "example",
                "compartment_id": "ocid1.compartment.oc1..example",
            }
        )
    )
    monkeypatch.setattr(
        resource,
        "list_all_resources",
        lambda list_fn, **kwargs: [
            types.SimpleNamespace(id="ocid1.example.oc1..one", display_name="example"),
            types.SimpleNamespace(id="ocid1.example.oc1..two", display_name="example"),
        ],
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        resource.execute_resource_module()

    assert "Multiple example resource resources were found for name=example." in exc_info.value.payload["msg"]
    assert "Provide example_id to distinguish between 2 matches." in exc_info.value.payload["msg"]


def test_oci_resource_base_creates_duplicate_when_unique_match_opted_in(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: types.SimpleNamespace(
            list_examples="list_examples_method"
        ),
    )
    patch_serialize_oci_model(
        monkeypatch,
        oci_resource,
        lambda resource: {"id": resource.id, "display_name": resource.display_name},
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        resource_id_param = "example_id"
        list_resource_method = "list_examples"
        list_filter_params = ()

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            return types.SimpleNamespace(
                id="ocid1.example.oc1..created",
                display_name="example",
            )

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    resource = ExampleResource(
        DummyModule(
            {
                "state": "present",
                "name": "example",
                "compartment_id": "ocid1.compartment.oc1..example",
                "allow_duplicate_name": True,
            }
        )
    )
    monkeypatch.setattr(
        resource,
        "list_all_resources",
        lambda list_fn, **kwargs: [
            types.SimpleNamespace(id="ocid1.example.oc1..existing", display_name="example")
        ],
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        resource.execute_resource_module()

    assert exc_info.value.payload == {
        "changed": True,
        "resource": {
            "id": "ocid1.example.oc1..created",
            "name": "example",
        },
    }


def test_oci_resource_base_fails_absent_without_resource_id_before_lookup(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        resource_id_param = "example_id"
        create_resource_name = "example resource"

        def resolve_target_resource(self):
            raise AssertionError("get_resource should not be called")

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    module = DummyModule({"state": "absent"})
    resource = ExampleResource(module)

    with pytest.raises(FailJsonCalled) as exc_info:
        resource.execute_resource_module()

    assert exc_info.value.payload == {
        "msg": "Deleting a example resource requires example_id"
    }


def test_oci_resource_base_fails_absent_without_identifier_when_name_lookup_supported(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        resource_id_param = "example_id"
        create_resource_name = "example resource"
        list_resource_method = "list_examples"
        list_filter_params = ()

        def resolve_target_resource(self):
            raise AssertionError("get_resource should not be called")

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    module = DummyModule({"state": "absent"})
    resource = ExampleResource(module)

    with pytest.raises(FailJsonCalled) as exc_info:
        resource.execute_resource_module()

    assert exc_info.value.payload == {
        "msg": (
            "Deleting a example resource requires either example_id or name "
            "(with compartment_id)"
        )
    }


def test_oci_info_base_lists_by_id_using_class_metadata(monkeypatch):
    oci_info = load_collection_module("oci_info")
    patch_create_service_client(
        monkeypatch,
        oci_info,
        lambda module, client_class: types.SimpleNamespace(
            get_example=lambda example_id: types.SimpleNamespace(
                data=types.SimpleNamespace(id=example_id, name="example")
            )
        ),
    )

    class ExampleInfo(oci_info.OciInfoBase):
        client_class = object
        resource_id_param = "example_id"
        resource_get_method = "get_example"
        resource_id_kwarg = "example_id"

    info_module = ExampleInfo(DummyModule({"example_id": "ocid1.example.oc1..123"}))
    monkeypatch.setattr(
        info_module,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    resources = info_module.fetch_resources()

    assert len(resources) == 1
    assert resources[0].id == "ocid1.example.oc1..123"


def test_oci_info_base_lists_with_declared_filter_params(monkeypatch):
    oci_info = load_collection_module("oci_info")
    paginate_calls = []
    patch_create_service_client(
        monkeypatch,
        oci_info,
        lambda module, client_class: types.SimpleNamespace(
            list_examples="list_examples_method",
        ),
    )

    class ExampleInfo(oci_info.OciInfoBase):
        client_class = object
        list_resource_method = "list_examples"
        list_filter_params = ("compartment_id", "display_name", "lifecycle_state")

    info_module = ExampleInfo(
        DummyModule(
            {
                "compartment_id": "ocid1.compartment.oc1..example",
                "name": "example",
                "lifecycle_state": "ACTIVE",
            }
        )
    )
    monkeypatch.setattr(
        info_module,
        "list_all_resources",
        lambda list_fn, **kwargs: paginate_calls.append((list_fn, kwargs)) or [],
    )

    resources = info_module.fetch_resources()

    assert resources == []
    assert paginate_calls == [
        (
            "list_examples_method",
            {
                "compartment_id": "ocid1.compartment.oc1..example",
                "lifecycle_state": "ACTIVE",
            },
        )
    ]


def test_oci_resource_base_uses_response_helper_for_id_lookup(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        resource_id_param = "example_id"

        def get_resource_response(self, resource_id):
            return types.SimpleNamespace(data=types.SimpleNamespace(id=resource_id))

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    resource = ExampleResource(DummyModule({"example_id": "ocid1.example.oc1..123"}))

    current = resource.resolve_target_resource()

    assert current.id == "ocid1.example.oc1..123"


def test_oci_resource_base_delete_helper_fails_on_dependency_conflict(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: "client",
    )

    class ConflictError(Exception):
        def __init__(self, status, message):
            super().__init__(message)
            self.status = status

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        create_resource_name = "example resource"

        def resolve_target_resource(self):
            raise AssertionError("get_resource should not be called")

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    resource = ExampleResource(DummyModule({"wait": True}))
    monkeypatch.setattr(
        resource,
        "call_with_retry",
        raising(ConflictError(409, "dependency exists")),
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        resource.delete_resource_and_wait(
            types.SimpleNamespace(id="ocid1.example.oc1..123"),
            object(),
            example_id="ocid1.example.oc1..123",
        )

    assert "Cannot delete example resource" in exc_info.value.payload["msg"]


def test_oci_module_base_missing_sdk_fails_before_touching_client_class(monkeypatch):
    oci_base = load_collection_module("oci_base", plugin_dir="module_utils")
    monkeypatch.setattr(oci_base, "HAS_OCI_SDK", False)

    class ExampleModule(oci_base.OciModuleBase):
        @property
        def client_class(self):
            raise AssertionError("client_class should not be evaluated")

    with pytest.raises(FailJsonCalled) as exc_info:
        ExampleModule(DummyModule())

    assert exc_info.value.payload["msg"] == missing_required_lib("oci")


def test_oci_module_base_list_all_resources_uses_oci_pagination_helper(monkeypatch):
    recorded_call = {}

    def fake_list_call_get_all_results(list_fn, *args, **kwargs):
        recorded_call["list_fn"] = list_fn
        recorded_call["args"] = args
        recorded_call["kwargs"] = kwargs
        return types.SimpleNamespace(data=["first", "second"])

    install_fake_oci_sdk(
        monkeypatch,
        pagination=types.SimpleNamespace(
            list_call_get_all_results=fake_list_call_get_all_results,
        ),
    )

    oci_base = load_collection_module("oci_base", plugin_dir="module_utils")
    patch_create_service_client(
        monkeypatch,
        oci_base,
        lambda module, client_class: "client",
    )

    class ExampleModule(oci_base.OciModuleBase):
        client_class = object

    instance = ExampleModule(DummyModule())
    list_fn = object()

    results = instance.list_all_resources(list_fn, "compartment-id", limit=25)

    assert results == ["first", "second"]
    assert recorded_call == {
        "list_fn": list_fn,
        "args": ("compartment-id",),
        "kwargs": {"limit": 25},
    }


def test_oci_module_base_call_with_retry_uses_oci_retry_strategy_builder(monkeypatch):
    recorded_call = {}

    class FakeRetryStrategy:
        def make_retrying_call(self, fn, *args, **kwargs):
            recorded_call["fn"] = fn
            recorded_call["args"] = args
            recorded_call["kwargs"] = kwargs
            return fn(*args, **kwargs)

    class FakeRetryStrategyBuilder:
        def __init__(self, **kwargs):
            recorded_call["builder_kwargs"] = kwargs

        def get_retry_strategy(self):
            return FakeRetryStrategy()

    install_fake_oci_sdk(
        monkeypatch,
        retry=types.SimpleNamespace(
            RetryStrategyBuilder=FakeRetryStrategyBuilder,
        ),
    )

    oci_base = load_collection_module("oci_base", plugin_dir="module_utils")
    patch_create_service_client(
        monkeypatch,
        oci_base,
        lambda module, client_class: "client",
    )

    class ExampleModule(oci_base.OciModuleBase):
        client_class = object

    instance = ExampleModule(DummyModule())

    result = instance.call_with_retry(
        lambda value, *, suffix: f"{value}-{suffix}",
        "retry",
        suffix="ok",
        max_retries=4,
        retry_on=(429, 503),
    )

    assert result == "retry-ok"
    assert recorded_call["args"] == ("retry",)
    assert recorded_call["kwargs"] == {"suffix": "ok"}
    assert recorded_call["builder_kwargs"]["max_attempts"] == 5
    assert recorded_call["builder_kwargs"]["service_error_retry_config"] == {
        429: [],
        503: [],
    }


def test_oci_module_base_call_with_retry_defaults_to_eight_attempts(monkeypatch):
    recorded_call = {}

    class FakeRetryStrategy:
        def make_retrying_call(self, fn, *args, **kwargs):
            return fn(*args, **kwargs)

    class FakeRetryStrategyBuilder:
        def __init__(self, **kwargs):
            recorded_call["builder_kwargs"] = kwargs

        def get_retry_strategy(self):
            return FakeRetryStrategy()

    install_fake_oci_sdk(
        monkeypatch,
        retry=types.SimpleNamespace(
            RetryStrategyBuilder=FakeRetryStrategyBuilder,
        ),
    )

    oci_base = load_collection_module("oci_base", plugin_dir="module_utils")
    patch_create_service_client(
        monkeypatch,
        oci_base,
        lambda module, client_class: "client",
    )

    class ExampleModule(oci_base.OciModuleBase):
        client_class = object

    instance = ExampleModule(DummyModule())
    instance.call_with_retry(lambda: "ok")

    assert recorded_call["builder_kwargs"]["max_attempts"] == 8


def _capture_resource_wait_fetch_func(monkeypatch, get_resource_fn):
    """Return wait_until fetch_func after an initial GET succeeds."""
    recorded = {}

    def fake_wait_until(client, response, **kwargs):
        recorded["fetch_func"] = kwargs["fetch_func"]
        return response

    ServiceError = install_fake_oci_sdk(monkeypatch, wait_until=fake_wait_until)
    load_collection_module("oci_base", plugin_dir="module_utils")
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: types.SimpleNamespace(),
    )

    initial_response = types.SimpleNamespace(
        data=types.SimpleNamespace(lifecycle_state="TERMINATING"),
    )
    lookups = {"count": 0}

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object

        def get_resource_response(self, resource_id):
            lookups["count"] += 1
            if lookups["count"] == 1:
                return initial_response
            return get_resource_fn(resource_id)

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    instance = ExampleResource(
        DummyModule({"wait": True, "wait_timeout": 1200, "wait_interval": 30})
    )
    instance.wait_for_resource_id("resource-ocid", ("TERMINATED", "DELETED"))
    return recorded["fetch_func"], ServiceError, initial_response


def test_oci_resource_base_wait_fetch_returns_previous_response_on_429(monkeypatch):
    ServiceErrorHolder = {}

    def get_resource(resource_id):
        raise ServiceErrorHolder["cls"](429)

    fetch_func, ServiceError, previous_response = _capture_resource_wait_fetch_func(
        monkeypatch, get_resource
    )
    ServiceErrorHolder["cls"] = ServiceError

    result = fetch_func(response=previous_response)

    assert result is previous_response


def test_oci_resource_base_wait_fetch_reraises_404(monkeypatch):
    ServiceErrorHolder = {}

    def get_resource(resource_id):
        raise ServiceErrorHolder["cls"](404)

    fetch_func, ServiceError, previous_response = _capture_resource_wait_fetch_func(
        monkeypatch, get_resource
    )
    ServiceErrorHolder["cls"] = ServiceError

    with pytest.raises(ServiceError) as exc_info:
        fetch_func(response=previous_response)

    assert exc_info.value.status == 404


def test_oci_resource_base_wait_fetch_returns_previous_response_on_circuit_breaker(monkeypatch):
    class CircuitBreakerError(Exception):
        pass

    def get_resource(resource_id):
        raise CircuitBreakerError("open")

    fetch_func, _ServiceError, previous_response = _capture_resource_wait_fetch_func(
        monkeypatch, get_resource
    )

    result = fetch_func(response=previous_response)

    assert result is previous_response


def test_oci_resource_base_wait_for_resource_id_uses_oci_wait_until(monkeypatch):
    recorded_call = {}
    final_response = types.SimpleNamespace(
        data=types.SimpleNamespace(lifecycle_state="ACTIVE"),
    )

    def fake_wait_until(client, response, **kwargs):
        recorded_call["client"] = client
        recorded_call["response"] = response
        recorded_call["kwargs"] = kwargs
        return final_response

    install_fake_oci_sdk(monkeypatch, wait_until=fake_wait_until)

    load_collection_module("oci_base", plugin_dir="module_utils")
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: types.SimpleNamespace(),
    )

    initial_response = types.SimpleNamespace(
        data=types.SimpleNamespace(lifecycle_state="CREATING"),
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object

        def get_resource_response(self, resource_id):
            return initial_response

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    instance = ExampleResource(
        DummyModule({"wait": True, "wait_timeout": 900, "wait_interval": 15})
    )

    result = instance.wait_for_resource_id("resource-ocid", ("ACTIVE", "AVAILABLE"))

    assert result is final_response.data
    assert recorded_call["client"] is instance.client
    assert recorded_call["response"] is initial_response
    assert recorded_call["kwargs"]["max_wait_seconds"] == 900
    assert recorded_call["kwargs"]["max_interval_seconds"] == 15
    assert recorded_call["kwargs"]["evaluate_response"](final_response) is True


def test_oci_resource_base_wait_for_work_request_accepts_getter_callback(monkeypatch):
    recorded_call = {}
    final_response = types.SimpleNamespace(
        data=types.SimpleNamespace(status="SUCCEEDED"),
    )

    def fake_wait_until(client, response, **kwargs):
        recorded_call["client"] = client
        recorded_call["response"] = response
        recorded_call["kwargs"] = kwargs
        return final_response

    install_fake_oci_sdk(
        monkeypatch,
        wait_until=fake_wait_until,
        retry=passthrough_retry_module(),
    )

    load_collection_module("oci_base", plugin_dir="module_utils")
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    instance = ExampleResource(
        DummyModule({"wait_timeout": 1200, "wait_interval": 30})
    )

    initial_response = types.SimpleNamespace(
        data=types.SimpleNamespace(status="IN_PROGRESS"),
    )
    requested_ids = []

    def get_work_request(work_request_id):
        requested_ids.append(work_request_id)
        return initial_response

    work_request_client = types.SimpleNamespace()

    result = instance.wait_for_work_request(
        work_request_client,
        "work-request-ocid",
        get_work_request_fn=get_work_request,
    )

    assert result is final_response.data
    assert requested_ids == ["work-request-ocid"]
    assert recorded_call["client"] is work_request_client
    assert recorded_call["response"] is initial_response
    assert recorded_call["kwargs"]["evaluate_response"](final_response) is True


def test_oci_resource_base_wait_for_work_request_retries_transient_connection_errors(monkeypatch):
    """A dropped connection while polling a work request must be retried, not fatal.

    This guards against a regression of the CI failure where a
    ``RemoteDisconnected`` mid-poll on ``GET .../workRequests/{id}`` failed
    the whole task instead of being absorbed by call_with_retry.
    """
    final_response = types.SimpleNamespace(
        data=types.SimpleNamespace(status="SUCCEEDED"),
    )

    install_fake_oci_sdk(
        monkeypatch,
        wait_until=lambda client, response, **kwargs: final_response,
    )

    load_collection_module("oci_base", plugin_dir="module_utils")
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object

        def get_resource_response(self, resource_id):
            raise AssertionError("get_resource_response should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    instance = ExampleResource(
        DummyModule({"wait_timeout": 1200, "wait_interval": 30})
    )

    attempts = {"count": 0}

    def get_work_request(work_request_id):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise ConnectionError("('Connection aborted.', RemoteDisconnected(...))")
        return types.SimpleNamespace(data=types.SimpleNamespace(status="IN_PROGRESS"))

    recorded_call_with_retry = []

    def fake_call_with_retry(fn, *args, **kwargs):
        recorded_call_with_retry.append((fn, args, kwargs))
        try:
            return fn(*args, **kwargs)
        except ConnectionError:
            return fn(*args, **kwargs)

    monkeypatch.setattr(instance, "call_with_retry", fake_call_with_retry)

    result = instance.wait_for_work_request(
        types.SimpleNamespace(),
        "work-request-ocid",
        get_work_request_fn=get_work_request,
    )

    assert result is final_response.data
    assert attempts["count"] == 2
    assert recorded_call_with_retry[0] == (get_work_request, ("work-request-ocid",), {})


def test_oci_resource_base_wait_for_resource_id_uses_dead_states_for_not_found_handling(monkeypatch):
    ServiceError = install_fake_oci_sdk(
        monkeypatch,
        wait_until=lambda client, response, **kwargs: response,
    )

    load_collection_module("oci_base", plugin_dir="module_utils")
    oci_resource = load_collection_module("oci_resource")
    patch_create_service_client(
        monkeypatch,
        oci_resource,
        lambda module, client_class: types.SimpleNamespace(),
    )
    monkeypatch.setattr(
        oci_resource,
        "DEAD_STATES",
        frozenset({"REMOVED"}),
        raising=False,
    )

    def get_resource(resource_id):
        raise ServiceError(404)

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object

        def get_resource_response(self, resource_id):
            return get_resource(resource_id)

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    instance = ExampleResource(
        DummyModule({"wait": True, "wait_timeout": 1200, "wait_interval": 30})
    )

    result = instance.wait_for_resource_id("resource-ocid", ("REMOVED",))

    assert result is None
