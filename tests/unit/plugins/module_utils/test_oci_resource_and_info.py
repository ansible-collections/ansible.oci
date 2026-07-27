import types

import pytest

from conftest import load_collection_module


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


def test_oci_resource_base_omits_user_known_fields_from_results(monkeypatch):
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
    monkeypatch.setattr(
        oci_resource,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
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

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def build_update_details(self, update_model_fields):
            return FakeUpdateDetails(**update_model_fields)

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    resource = ExampleResource(DummyModule({"name": "updated-name", "wait": False}))

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
        lambda module, client_class: (_ for _ in ()).throw(
            AssertionError("create_service_client should not be called")
        ),
    )

    class ExampleResource(oci_resource.OciResourceBase):
        def resolve_target_resource(self):
            return None

        def create_resource(self):
            return None

        def update_resource(self, resource):
            return resource

        def delete_resource(self, resource):
            return None

    with pytest.raises(TypeError, match="client_class"):
        ExampleResource(DummyModule())


def test_oci_info_base_omits_user_known_fields_from_results(monkeypatch):
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

    assert exc_info.value.payload == {
        "changed": False,
        "resources": [
            {
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
        lambda module, client_class: (_ for _ in ()).throw(
            AssertionError("create_service_client should not be called")
        ),
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
        oci_resource,
        "paginate_all_resources",
        lambda list_fn, **kwargs: paginate_calls.append((list_fn, kwargs)) or [existing_resource],
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        resource.execute_resource_module()

    assert exc_info.value.payload == {
        "changed": True,
        "resource": {
            "id": "ocid1.example.oc1..123",
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
            list_examples=lambda **kwargs: (_ for _ in ()).throw(
                AssertionError("list_examples should not be called")
            )
        ),
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        resource_id_param = "example_id"
        list_resource_method = "list_examples"
        common_list_filter_params = ("compartment_id",)
        list_filter_params = ("parent_id",)
        create_resource_name = "example resource"

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
        oci_resource,
        "paginate_all_resources",
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
        oci_resource,
        "paginate_all_resources",
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
        oci_resource,
        "paginate_all_resources",
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
    monkeypatch.setattr(
        oci_info,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    class ExampleInfo(oci_info.OciInfoBase):
        client_class = object
        resource_id_param = "example_id"
        resource_get_method = "get_example"
        resource_id_kwarg = "example_id"

    info_module = ExampleInfo(DummyModule({"example_id": "ocid1.example.oc1..123"}))

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
        oci_info,
        "paginate_all_resources",
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
        oci_resource,
        "call_with_retry",
        lambda fn, **kwargs: (_ for _ in ()).throw(
            ConflictError(409, "dependency exists")
        ),
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        resource.delete_resource_and_wait(
            types.SimpleNamespace(id="ocid1.example.oc1..123"),
            object(),
            example_id="ocid1.example.oc1..123",
        )

    assert "Cannot delete example resource" in exc_info.value.payload["msg"]
