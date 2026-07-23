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


def test_oci_resource_base_uses_shared_serializer(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    monkeypatch.setattr(
        oci_resource,
        "create_service_client",
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object

        def get_resource(self):
            raise AssertionError("get_resource should not be called")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    monkeypatch.setattr(
        oci_resource,
        "serialize_resource_dict",
        lambda resource: {"delegated": True},
    )

    resource = ExampleResource(DummyModule())

    assert resource.to_dict(object()) == {"delegated": True}


def test_incomplete_oci_resource_subclass_cannot_be_instantiated(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    monkeypatch.setattr(
        oci_resource,
        "create_service_client",
        lambda module, client_class: "client",
    )

    class IncompleteResource(oci_resource.OciResourceBase):
        client_class = object

    with pytest.raises(TypeError):
        IncompleteResource(DummyModule())


def test_oci_resource_base_requires_client_class_before_creating_client(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    monkeypatch.setattr(
        oci_resource,
        "create_service_client",
        lambda module, client_class: (_ for _ in ()).throw(
            AssertionError("create_service_client should not be called")
        ),
    )

    class ExampleResource(oci_resource.OciResourceBase):
        def get_resource(self):
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

    monkeypatch.setattr(
        oci_info,
        "create_service_client",
        lambda module, client_class: "client",
    )

    class ExampleInfo(oci_info.OciInfoBase):
        client_class = object

        def list_resources(self):
            return [
                types.SimpleNamespace(
                    name="example-resource",
                    id="ocid1.example.oc1..123",
                    lifecycle_state="ACTIVE",
                )
            ]

        def user_known_fields(self):
            return ("name",)

    module = DummyModule({"name": "example-resource"})
    info_module = ExampleInfo(module)

    with pytest.raises(ExitJsonCalled) as exc_info:
        info_module.run()

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
    monkeypatch.setattr(
        oci_info,
        "create_service_client",
        lambda module, client_class: "client",
    )

    class IncompleteInfo(oci_info.OciInfoBase):
        client_class = object

    info_module = IncompleteInfo(DummyModule())

    with pytest.raises(NotImplementedError, match="class metadata"):
        info_module.list_resources()


def test_oci_info_base_requires_client_class_before_creating_client(monkeypatch):
    oci_info = load_collection_module("oci_info")
    monkeypatch.setattr(
        oci_info,
        "create_service_client",
        lambda module, client_class: (_ for _ in ()).throw(
            AssertionError("create_service_client should not be called")
        ),
    )

    class ExampleInfo(oci_info.OciInfoBase):
        def list_resources(self):
            return []

    with pytest.raises(TypeError, match="client_class"):
        ExampleInfo(DummyModule())


def test_oci_resource_base_treats_dead_state_as_absent(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    delete_calls = []

    monkeypatch.setattr(
        oci_resource,
        "create_service_client",
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

        def get_resource(self):
            return types.SimpleNamespace(lifecycle_state="REMOVED")

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            delete_calls.append(resource)

    resource = ExampleResource(DummyModule({"state": "absent"}))

    with pytest.raises(ExitJsonCalled) as exc_info:
        resource.run()

    assert delete_calls == []
    assert exc_info.value.payload == {"changed": False}


def test_oci_resource_base_validates_create_request_in_check_mode(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    monkeypatch.setattr(
        oci_resource,
        "create_service_client",
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object

        def get_resource(self):
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
        resource.run()

    assert exc_info.value.payload == {"msg": "missing create fields"}


def test_oci_resource_base_default_create_field_validation_uses_class_metadata(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    monkeypatch.setattr(
        oci_resource,
        "create_service_client",
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        create_required_fields = ("compartment_id", "display_name")
        create_resource_name = "example resource"

        def get_resource(self):
            return None

        def create_resource(self):
            raise AssertionError("create_resource should not be called")

        def update_resource(self, resource):
            raise AssertionError("update_resource should not be called")

        def delete_resource(self, resource):
            raise AssertionError("delete_resource should not be called")

    module = DummyModule({"state": "present", "display_name": "example"})
    module.check_mode = True
    resource = ExampleResource(module)

    with pytest.raises(FailJsonCalled) as exc_info:
        resource.run()

    assert exc_info.value.payload == {
        "msg": "Creating a example resource requires the following parameters: compartment_id"
    }


def test_oci_resource_base_fails_present_when_explicit_resource_id_is_missing(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    monkeypatch.setattr(
        oci_resource,
        "create_service_client",
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        resource_id_param = "example_id"
        create_resource_name = "example resource"

        def get_resource(self):
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
        resource.run()

    assert "No example resource was found for example_id=" in exc_info.value.payload["msg"]
    assert "Create the example resource without example_id" in exc_info.value.payload["msg"]


def test_oci_resource_base_fails_absent_without_resource_id_before_lookup(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    monkeypatch.setattr(
        oci_resource,
        "create_service_client",
        lambda module, client_class: "client",
    )

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        resource_id_param = "example_id"
        create_resource_name = "example resource"

        def get_resource(self):
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
        resource.run()

    assert exc_info.value.payload == {
        "msg": "Deleting a example resource requires example_id"
    }


def test_oci_info_base_lists_by_id_using_class_metadata(monkeypatch):
    oci_info = load_collection_module("oci_info")
    monkeypatch.setattr(
        oci_info,
        "create_service_client",
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

    resources = info_module.list_resources()

    assert len(resources) == 1
    assert resources[0].id == "ocid1.example.oc1..123"


def test_oci_info_base_lists_with_declared_filter_params(monkeypatch):
    oci_info = load_collection_module("oci_info")
    paginate_calls = []
    monkeypatch.setattr(
        oci_info,
        "create_service_client",
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
                "display_name": "example",
                "lifecycle_state": "ACTIVE",
            }
        )
    )
    monkeypatch.setattr(
        info_module,
        "paginate",
        lambda list_fn, **kwargs: paginate_calls.append((list_fn, kwargs)) or [],
    )

    resources = info_module.list_resources()

    assert resources == []
    assert paginate_calls == [
        (
            "list_examples_method",
            {
                "compartment_id": "ocid1.compartment.oc1..example",
                "display_name": "example",
                "lifecycle_state": "ACTIVE",
            },
        )
    ]


def test_oci_resource_base_uses_response_helper_for_id_lookup(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    monkeypatch.setattr(
        oci_resource,
        "create_service_client",
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

    current = resource.get_resource()

    assert current.id == "ocid1.example.oc1..123"


def test_oci_resource_base_delete_helper_fails_on_dependency_conflict(monkeypatch):
    oci_resource = load_collection_module("oci_resource")
    monkeypatch.setattr(
        oci_resource,
        "create_service_client",
        lambda module, client_class: "client",
    )

    class ConflictError(Exception):
        def __init__(self, status, message):
            super().__init__(message)
            self.status = status

    class ExampleResource(oci_resource.OciResourceBase):
        client_class = object
        create_resource_name = "example resource"

        def get_resource(self):
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
