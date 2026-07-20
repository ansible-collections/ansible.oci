import types

import pytest

from conftest import load_collection_module


class ExitJsonCalled(Exception):
    def __init__(self, payload):
        self.payload = payload


class DummyModule:
    def __init__(self, params=None):
        self.params = params or {}
        self.check_mode = False

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


def test_oci_facts_base_omits_user_known_fields_from_results(monkeypatch):
    oci_facts = load_collection_module("oci_facts")

    monkeypatch.setattr(
        oci_facts,
        "create_service_client",
        lambda module, client_class: "client",
    )

    class ExampleFacts(oci_facts.OciFactsBase):
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
    facts = ExampleFacts(module)

    with pytest.raises(ExitJsonCalled) as exc_info:
        facts.run()

    assert exc_info.value.payload == {
        "changed": False,
        "resources": [
            {
                "id": "ocid1.example.oc1..123",
                "lifecycle_state": "ACTIVE",
            }
        ],
    }


def test_incomplete_oci_facts_subclass_cannot_be_instantiated(monkeypatch):
    oci_facts = load_collection_module("oci_facts")
    monkeypatch.setattr(
        oci_facts,
        "create_service_client",
        lambda module, client_class: "client",
    )

    class IncompleteFacts(oci_facts.OciFactsBase):
        client_class = object

    with pytest.raises(TypeError):
        IncompleteFacts(DummyModule())


def test_oci_facts_base_requires_client_class_before_creating_client(monkeypatch):
    oci_facts = load_collection_module("oci_facts")
    monkeypatch.setattr(
        oci_facts,
        "create_service_client",
        lambda module, client_class: (_ for _ in ()).throw(
            AssertionError("create_service_client should not be called")
        ),
    )

    class ExampleFacts(oci_facts.OciFactsBase):
        def list_resources(self):
            return []

    with pytest.raises(TypeError, match="client_class"):
        ExampleFacts(DummyModule())


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
