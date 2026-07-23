import sys
import types

import pytest

from conftest import load_collection_module


class FailJsonCalled(Exception):
    def __init__(self, payload):
        self.payload = payload


class ExitJsonCalled(Exception):
    def __init__(self, payload):
        self.payload = payload


class DummyModule:
    def __init__(self, params=None, check_mode=False):
        self.params = params or {}
        self.check_mode = check_mode

    def fail_json(self, **kwargs):
        raise FailJsonCalled(kwargs)

    def exit_json(self, **kwargs):
        raise ExitJsonCalled(kwargs)


class FakeModel:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeResponse:
    def __init__(self, data=None, headers=None):
        self.data = data
        self.headers = headers or {}


class FakeVirtualNetworkClient:
    pass


class FakeWorkRequestClient:
    pass


def install_fake_oci(monkeypatch):
    oci_module = types.ModuleType("oci")
    exceptions_module = types.ModuleType("oci.exceptions")

    class ServiceError(Exception):
        def __init__(self, status, message="service error"):
            super().__init__(message)
            self.status = status
            self.message = message

    exceptions_module.ServiceError = ServiceError
    oci_module.exceptions = exceptions_module
    oci_module.core = types.SimpleNamespace(
        VirtualNetworkClient=FakeVirtualNetworkClient,
        models=types.SimpleNamespace(
            CreateVcnDetails=FakeModel,
            UpdateVcnDetails=FakeModel,
            AddVcnCidrDetails=FakeModel,
            ModifyVcnCidrDetails=FakeModel,
            RemoveVcnCidrDetails=FakeModel,
        ),
    )
    oci_module.work_requests = types.SimpleNamespace(
        WorkRequestClient=FakeWorkRequestClient,
    )

    monkeypatch.setitem(sys.modules, "oci", oci_module)
    monkeypatch.setitem(sys.modules, "oci.exceptions", exceptions_module)

    return oci_module, ServiceError


def make_vcn_module(module_obj, params, client=None):
    instance = object.__new__(module_obj.OciNetworkVcnModule)
    instance.module = DummyModule(params)
    instance.client = client or types.SimpleNamespace()
    instance.work_request_client = types.SimpleNamespace()
    instance.check_mode = False
    return instance


def test_build_create_vcn_details_includes_dns_label_and_tags(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    details = vcn_module.build_create_vcn_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "cidr_blocks": ["10.0.0.0/16"],
            "display_name": "example-vcn",
            "dns_label": "examplevcn",
            "freeform_tags": {"env": "dev"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        }
    )

    assert isinstance(details, FakeModel)
    assert details.compartment_id == "ocid1.compartment.oc1..example"
    assert details.cidr_blocks == ["10.0.0.0/16"]
    assert details.display_name == "example-vcn"
    assert details.dns_label == "examplevcn"
    assert details.freeform_tags == {"env": "dev"}
    assert details.defined_tags == {"Operations": {"CostCenter": "42"}}


def test_build_update_vcn_details_only_includes_mutable_fields(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    details = vcn_module.build_update_vcn_details(
        {
            "display_name": "updated-vcn",
            "cidr_blocks": ["10.1.0.0/16"],
            "dns_label": "immutablelabel",
            "freeform_tags": {"env": "prod"},
            "defined_tags": {"Operations": {"CostCenter": "43"}},
        }
    )

    assert isinstance(details, FakeModel)
    assert details.display_name == "updated-vcn"
    assert details.freeform_tags == {"env": "prod"}
    assert details.defined_tags == {"Operations": {"CostCenter": "43"}}
    assert not hasattr(details, "cidr_blocks")
    assert not hasattr(details, "dns_label")


def test_build_add_vcn_cidr_details_uses_cidr_block(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    details = vcn_module.build_add_vcn_cidr_details("10.1.0.0/16")

    assert isinstance(details, FakeModel)
    assert details.cidr_block == "10.1.0.0/16"


def test_build_modify_vcn_cidr_details_uses_original_and_new_cidr(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    details = vcn_module.build_modify_vcn_cidr_details(
        "10.0.0.0/16",
        "10.0.0.0/15",
    )

    assert isinstance(details, FakeModel)
    assert details.original_cidr_block == "10.0.0.0/16"
    assert details.new_cidr_block == "10.0.0.0/15"


def test_build_remove_vcn_cidr_details_uses_cidr_block(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    details = vcn_module.build_remove_vcn_cidr_details("10.1.0.0/16")

    assert isinstance(details, FakeModel)
    assert details.cidr_block == "10.1.0.0/16"


def test_plan_vcn_cidr_operations_returns_adds_in_desired_order(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")

    assert vcn_module.plan_vcn_cidr_operations(
        ["10.0.0.0/16"],
        ["10.0.0.0/16", "10.1.0.0/16", "10.2.0.0/16"],
    ) == [
        ("add", "10.1.0.0/16"),
        ("add", "10.2.0.0/16"),
    ]


def test_plan_vcn_cidr_operations_returns_removes_in_current_order(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")

    assert vcn_module.plan_vcn_cidr_operations(
        ["10.0.0.0/16", "10.1.0.0/16", "10.2.0.0/16"],
        ["10.0.0.0/16"],
    ) == [
        ("remove", "10.1.0.0/16"),
        ("remove", "10.2.0.0/16"),
    ]


def test_plan_vcn_cidr_operations_returns_single_modify(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")

    assert vcn_module.plan_vcn_cidr_operations(
        ["10.0.0.0/16"],
        ["10.0.0.0/15"],
    ) == [
        ("modify", "10.0.0.0/16", "10.0.0.0/15"),
    ]


def test_plan_vcn_cidr_operations_rejects_complex_changes(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")

    with pytest.raises(ValueError, match="Complex cidr_blocks changes"):
        vcn_module.plan_vcn_cidr_operations(
            ["10.0.0.0/16", "10.1.0.0/16"],
            ["10.2.0.0/16", "10.3.0.0/16"],
        )


def test_get_resource_prefers_vcn_id_lookup(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    get_calls = []

    def get_vcn(vcn_id):
        get_calls.append(vcn_id)
        return FakeResponse(data=FakeModel(id=vcn_id))

    instance = make_vcn_module(
        vcn_module,
        {"vcn_id": "ocid1.vcn.oc1..example"},
        client=types.SimpleNamespace(get_vcn=get_vcn),
    )
    monkeypatch.setattr(
        vcn_module,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    resource = instance.get_resource()

    assert resource.id == "ocid1.vcn.oc1..example"
    assert get_calls == ["ocid1.vcn.oc1..example"]


def test_get_resource_returns_none_without_vcn_id(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    instance = make_vcn_module(
        vcn_module,
        {
            "display_name": "example-vcn",
            "compartment_id": "ocid1.compartment.oc1..example",
        },
    )

    assert instance.get_resource() is None


def test_run_fails_when_present_uses_missing_vcn_id(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    instance = make_vcn_module(
        vcn_module,
        {
            "state": "present",
            "vcn_id": "ocid1.vcn.oc1..missing",
        },
    )
    monkeypatch.setattr(instance, "get_resource", lambda: None)

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.run()

    assert "No VCN was found for vcn_id=" in exc_info.value.payload["msg"]
    assert "Create the VCN without vcn_id" in exc_info.value.payload["msg"]


def test_run_fails_when_absent_omits_vcn_id(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    instance = make_vcn_module(
        vcn_module,
        {
            "state": "absent",
        },
    )
    monkeypatch.setattr(
        instance,
        "get_resource",
        lambda: (_ for _ in ()).throw(
            AssertionError("get_resource should not be called")
        ),
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.run()

    assert "Deleting a VCN requires vcn_id" in exc_info.value.payload["msg"]


def test_needs_update_treats_cidr_block_order_as_noop(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    instance = make_vcn_module(
        vcn_module,
        {"cidr_blocks": ["10.1.0.0/16", "10.0.0.0/16"]},
    )
    resource = FakeModel(
        id="ocid1.vcn.oc1..example",
        cidr_blocks=["10.0.0.0/16", "10.1.0.0/16"],
    )

    assert instance.needs_update(resource) is False


def test_needs_update_rejects_cidr_updates_without_wait(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    instance = make_vcn_module(
        vcn_module,
        {"cidr_blocks": ["10.1.0.0/16"], "wait": False},
    )
    resource = FakeModel(id="ocid1.vcn.oc1..example", cidr_blocks=["10.0.0.0/16"])

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "wait=true" in exc_info.value.payload["msg"]


def test_needs_update_rejects_complex_cidr_changes(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    instance = make_vcn_module(
        vcn_module,
        {"cidr_blocks": ["10.2.0.0/16", "10.3.0.0/16"]},
    )
    resource = FakeModel(
        id="ocid1.vcn.oc1..example",
        cidr_blocks=["10.0.0.0/16", "10.1.0.0/16"],
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "Complex cidr_blocks changes" in exc_info.value.payload["msg"]


def test_needs_update_rejects_dns_label_drift(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    instance = make_vcn_module(
        vcn_module,
        {"dns_label": "desiredlabel"},
    )
    resource = FakeModel(id="ocid1.vcn.oc1..example", dns_label="currentlabel")

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "dns_label" in exc_info.value.payload["msg"]


def test_create_resource_uses_create_vcn_and_waits(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    create_calls = []
    response = FakeResponse(
        data=FakeModel(id="ocid1.vcn.oc1..example"),
    )

    def create_vcn(create_vcn_details):
        create_calls.append(create_vcn_details)
        return response

    instance = make_vcn_module(
        vcn_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "cidr_blocks": ["10.0.0.0/16"],
            "display_name": "example-vcn",
            "dns_label": "examplevcn",
            "wait": True,
        },
        client=types.SimpleNamespace(create_vcn=create_vcn),
    )
    monkeypatch.setattr(
        vcn_module,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )
    monkeypatch.setattr(
        vcn_module,
        "wait_for_resource",
        lambda module, client, get_fn, resource_id, target_states, **kwargs: FakeModel(
            id=resource_id,
            lifecycle_state="AVAILABLE",
        ),
    )

    resource = instance.create_resource()

    assert create_calls[0].display_name == "example-vcn"
    assert create_calls[0].dns_label == "examplevcn"
    assert resource.id == "ocid1.vcn.oc1..example"
    assert resource.lifecycle_state == "AVAILABLE"


def test_update_resource_uses_update_vcn_details_and_waits(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    update_calls = []
    response = FakeResponse(
        data=FakeModel(id="ocid1.vcn.oc1..example"),
    )

    def update_vcn(vcn_id, update_vcn_details):
        update_calls.append((vcn_id, update_vcn_details))
        return response

    resource = FakeModel(id="ocid1.vcn.oc1..example")
    instance = make_vcn_module(
        vcn_module,
        {
            "display_name": "updated-vcn",
            "freeform_tags": {"env": "prod"},
            "wait": True,
        },
        client=types.SimpleNamespace(update_vcn=update_vcn),
    )
    monkeypatch.setattr(
        vcn_module,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )
    monkeypatch.setattr(
        vcn_module,
        "wait_for_resource",
        lambda module, client, get_fn, resource_id, target_states, **kwargs: FakeModel(
            id=resource_id,
            lifecycle_state="AVAILABLE",
        ),
    )

    updated_resource = instance.update_resource(resource)

    assert update_calls[0][0] == "ocid1.vcn.oc1..example"
    assert update_calls[0][1].display_name == "updated-vcn"
    assert update_calls[0][1].freeform_tags == {"env": "prod"}
    assert updated_resource.id == "ocid1.vcn.oc1..example"


def test_update_resource_adds_vcn_cidr_and_waits_for_work_request(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    add_calls = []
    waited_work_requests = []
    waited_resources = []

    def add_vcn_cidr(vcn_id, add_vcn_cidr_details):
        add_calls.append((vcn_id, add_vcn_cidr_details))
        return FakeResponse(
            data=None,
            headers={"opc-work-request-id": "wr-add-1"},
        )

    resource = FakeModel(
        id="ocid1.vcn.oc1..example",
        cidr_blocks=["10.0.0.0/16"],
    )
    instance = make_vcn_module(
        vcn_module,
        {
            "cidr_blocks": ["10.0.0.0/16", "10.1.0.0/16"],
            "wait": True,
        },
        client=types.SimpleNamespace(add_vcn_cidr=add_vcn_cidr),
    )
    monkeypatch.setattr(
        vcn_module,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )
    monkeypatch.setattr(
        vcn_module,
        "wait_for_work_request",
        lambda module, client, work_request_id, **kwargs: waited_work_requests.append(
            work_request_id
        ) or FakeModel(status="SUCCEEDED"),
    )
    monkeypatch.setattr(
        instance,
        "_wait_for_vcn",
        lambda vcn_id: waited_resources.append(vcn_id)
        or FakeModel(id=vcn_id, cidr_blocks=["10.0.0.0/16", "10.1.0.0/16"]),
    )

    updated_resource = instance.update_resource(resource)

    assert add_calls[0][0] == "ocid1.vcn.oc1..example"
    assert add_calls[0][1].cidr_block == "10.1.0.0/16"
    assert waited_work_requests == ["wr-add-1"]
    assert waited_resources == ["ocid1.vcn.oc1..example"]
    assert updated_resource.cidr_blocks == ["10.0.0.0/16", "10.1.0.0/16"]


def test_update_resource_applies_cidr_changes_before_metadata_update(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    remove_calls = []
    update_calls = []
    waited_work_requests = []
    waited_resources = []

    def remove_vcn_cidr(vcn_id, remove_vcn_cidr_details):
        remove_calls.append((vcn_id, remove_vcn_cidr_details))
        return FakeResponse(
            data=None,
            headers={"opc-work-request-id": "wr-remove-1"},
        )

    def update_vcn(vcn_id, update_vcn_details):
        update_calls.append((vcn_id, update_vcn_details))
        return FakeResponse(data=FakeModel(id=vcn_id))

    resource = FakeModel(
        id="ocid1.vcn.oc1..example",
        cidr_blocks=["10.0.0.0/16", "10.1.0.0/16"],
        display_name="example-vcn",
        freeform_tags={"phase": "create"},
    )
    instance = make_vcn_module(
        vcn_module,
        {
            "cidr_blocks": ["10.0.0.0/16"],
            "display_name": "example-vcn-updated",
            "freeform_tags": {"phase": "update"},
            "wait": True,
        },
        client=types.SimpleNamespace(
            remove_vcn_cidr=remove_vcn_cidr,
            update_vcn=update_vcn,
        ),
    )
    monkeypatch.setattr(
        vcn_module,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )
    monkeypatch.setattr(
        vcn_module,
        "wait_for_work_request",
        lambda module, client, work_request_id, **kwargs: waited_work_requests.append(
            work_request_id
        ) or FakeModel(status="SUCCEEDED"),
    )

    def fake_wait_for_vcn(vcn_id):
        waited_resources.append(vcn_id)
        if len(waited_resources) == 1:
            return FakeModel(
                id=vcn_id,
                cidr_blocks=["10.0.0.0/16"],
                display_name="example-vcn",
                freeform_tags={"phase": "create"},
            )
        return FakeModel(
            id=vcn_id,
            cidr_blocks=["10.0.0.0/16"],
            display_name="example-vcn-updated",
            freeform_tags={"phase": "update"},
        )

    monkeypatch.setattr(instance, "_wait_for_vcn", fake_wait_for_vcn)

    updated_resource = instance.update_resource(resource)

    assert remove_calls[0][0] == "ocid1.vcn.oc1..example"
    assert remove_calls[0][1].cidr_block == "10.1.0.0/16"
    assert waited_work_requests == ["wr-remove-1"]
    assert waited_resources == [
        "ocid1.vcn.oc1..example",
        "ocid1.vcn.oc1..example",
    ]
    assert update_calls[0][0] == "ocid1.vcn.oc1..example"
    assert update_calls[0][1].display_name == "example-vcn-updated"
    assert update_calls[0][1].freeform_tags == {"phase": "update"}
    assert updated_resource.display_name == "example-vcn-updated"


def test_delete_resource_fails_cleanly_when_dependency_exists(monkeypatch):
    _, ServiceError = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    resource = FakeModel(id="ocid1.vcn.oc1..example")

    def delete_vcn(vcn_id):
        raise ServiceError(409, "Subnet dependencies still exist")

    instance = make_vcn_module(
        vcn_module,
        {"wait": True},
        client=types.SimpleNamespace(delete_vcn=delete_vcn),
    )
    monkeypatch.setattr(
        vcn_module,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.delete_resource(resource)

    assert "dependent resources" in exc_info.value.payload["msg"]


def test_run_check_mode_create_fails_when_required_fields_missing(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    instance = make_vcn_module(
        vcn_module,
        {
            "state": "present",
            "display_name": "example-vcn",
        },
    )
    instance.check_mode = True
    monkeypatch.setattr(instance, "get_resource", lambda: None)

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.run()

    assert "Creating a VCN requires" in exc_info.value.payload["msg"]


def test_run_check_mode_create_reports_changed_without_create(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    instance = make_vcn_module(
        vcn_module,
        {
            "state": "present",
            "compartment_id": "ocid1.compartment.oc1..example",
            "cidr_blocks": ["10.0.0.0/16"],
            "display_name": "example-vcn",
        },
    )
    instance.check_mode = True
    monkeypatch.setattr(instance, "get_resource", lambda: None)
    monkeypatch.setattr(
        instance,
        "create_resource",
        lambda: (_ for _ in ()).throw(AssertionError("create_resource should not be called")),
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.run()

    assert exc_info.value.payload == {"changed": True}


def test_run_check_mode_update_reports_changed_when_tags_differ(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    resource = FakeModel(
        id="ocid1.vcn.oc1..example",
        display_name="example-vcn",
        lifecycle_state="AVAILABLE",
        freeform_tags={"env": "dev"},
    )
    instance = make_vcn_module(
        vcn_module,
        {
            "state": "present",
            "display_name": "example-vcn",
            "freeform_tags": {"env": "prod"},
        },
    )
    instance.check_mode = True
    monkeypatch.setattr(instance, "get_resource", lambda: resource)
    monkeypatch.setattr(
        instance,
        "update_resource",
        lambda resource: (_ for _ in ()).throw(
            AssertionError("update_resource should not be called")
        ),
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.run()

    assert exc_info.value.payload == {"changed": True}


def test_run_check_mode_delete_reports_changed_without_delete(monkeypatch):
    _, _ = install_fake_oci(monkeypatch)

    vcn_module = load_collection_module("oci_network_vcn")
    resource = FakeModel(
        id="ocid1.vcn.oc1..example",
        lifecycle_state="AVAILABLE",
    )
    instance = make_vcn_module(
        vcn_module,
        {
            "state": "absent",
            "vcn_id": "ocid1.vcn.oc1..example",
        },
    )
    instance.check_mode = True
    monkeypatch.setattr(instance, "get_resource", lambda: resource)
    monkeypatch.setattr(
        instance,
        "delete_resource",
        lambda resource: (_ for _ in ()).throw(
            AssertionError("delete_resource should not be called")
        ),
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.run()

    assert exc_info.value.payload == {"changed": True}
