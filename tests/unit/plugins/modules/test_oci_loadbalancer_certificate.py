from __future__ import absolute_import, division, print_function

__metaclass__ = type

import types

import oci
import pytest
from ansible.module_utils.common.arg_spec import ModuleArgumentSpecValidator

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FailJsonCalled,
    FakeModel,
    FakeResponse,
    load_collection_module,
    make_module_instance,
)


def _certificate_module(params, *, check_mode=False, client=None):
    """Create the module with a test client and parameters."""
    module = load_collection_module("oci_loadbalancer_certificate")
    return make_module_instance(
        module,
        "OciLoadBalancerCertificateModule",
        params,
        client=client,
        check_mode=check_mode,
    )


def _certificate(**overrides):
    """Create a certificate model with test values."""
    fields = {
        "certificate_name": "api-cert",
        "public_certificate": "PUBLIC",
        "ca_certificate": "CA",
    }
    fields.update(overrides)
    return oci.load_balancer.models.Certificate(**fields)


def test_main_exposes_certificate_options_and_standard_auth_wait(monkeypatch):
    """Verify the main entry point and its argument options."""
    module = load_collection_module("oci_loadbalancer_certificate")
    captured = {}

    class FakeCertificateModule:
        def __init__(self, active_module):
            self.module = active_module

        def execute_resource_module(self):
            captured["executed"] = True

    monkeypatch.setattr(
        module,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule({}),
    )
    monkeypatch.setattr(
        module, "OciLoadBalancerCertificateModule", FakeCertificateModule
    )
    module.main()

    args = captured["argument_spec"]
    assert captured["supports_check_mode"] is True
    assert args["load_balancer_id"] == {"type": "str", "required": True}
    assert args["name"] == {"type": "str", "required": True}
    assert args["public_certificate"] == {"type": "str"}
    assert args["ca_certificate"] == {"type": "str"}
    assert args["private_key"] == {"type": "str", "no_log": True}
    assert args["passphrase"] == {"type": "str", "no_log": True}
    assert args["state"]["choices"] == ["present", "absent"]
    assert {"wait", "wait_timeout", "wait_interval"} <= set(args)
    assert captured["executed"] is True

    validator = ModuleArgumentSpecValidator(args)
    valid = {
        "load_balancer_id": "lb",
        "name": "api-cert",
        "public_certificate": "PUBLIC",
    }
    assert validator.validate(valid).error_messages == []
    assert validator.validate({"load_balancer_id": "lb", "certificate_name": "api-cert"}).error_messages


def test_certificate_lookup_uses_parent_load_balancer_certificate_map(monkeypatch):
    """Verify that lookup uses the parent and the exact bundle name."""
    certificate = _certificate()

    def get_load_balancer(load_balancer_id):
        assert load_balancer_id == "lb-ocid"
        return FakeResponse(types.SimpleNamespace(certificates={"api-cert": certificate}))

    instance = _certificate_module(
        {"load_balancer_id": "lb-ocid", "name": "api-cert"},
        client=types.SimpleNamespace(get_load_balancer=get_load_balancer),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.resolve_target_resource() is certificate


def test_certificate_model_and_mutation_arguments_are_scoped():
    """Verify that the bundle name and data map to the SDK."""
    params = {
        "load_balancer_id": "lb-ocid",
        "name": "api-cert",
        "public_certificate": "PUBLIC",
        "ca_certificate": "CA",
        "private_key": "PRIVATE",
        "passphrase": "PASSPHRASE",
    }
    adapter = _certificate_module(params)
    details = adapter.build_resource_model("CreateCertificateDetails", params)

    assert isinstance(details, oci.load_balancer.models.CreateCertificateDetails)
    assert details.certificate_name == "api-cert"
    assert details.public_certificate == "PUBLIC"
    assert details.ca_certificate == "CA"
    assert details.private_key == "PRIVATE"
    assert details.passphrase == "PASSPHRASE"
    assert adapter.mutation_kwargs("create") == {"load_balancer_id": "lb-ocid"}
    assert adapter.mutation_kwargs("delete") == {
        "load_balancer_id": "lb-ocid",
        "certificate_name": "api-cert",
    }


def test_create_and_delete_use_certificate_composite_operations():
    """Verify the composite operation and scope for each mutation."""
    params = {
        "load_balancer_id": "lb-ocid",
        "name": "api-cert",
        "public_certificate": "PUBLIC",
        "wait": False,
    }
    adapter = _certificate_module(params)
    calls = []
    adapter._composite_call = lambda operation, method, **kwargs: calls.append(
        (operation, method, kwargs)
    ) or types.SimpleNamespace(data=FakeModel(certificate_name="api-cert"))
    adapter._read_after_operation = lambda *args: FakeModel(certificate_name="api-cert")

    adapter.create_resource()
    assert calls[-1][0:2] == ("create", "create_certificate_and_wait_for_state")
    assert set(calls[-1][2]) == {"load_balancer_id", "create_certificate_details"}
    details = calls[-1][2]["create_certificate_details"]
    assert isinstance(details, oci.load_balancer.models.CreateCertificateDetails)
    assert details.certificate_name == "api-cert"

    adapter.delete_resource(FakeModel(certificate_name="api-cert"))
    assert calls[-1][0:2] == ("delete", "delete_certificate_and_wait_for_state")
    assert calls[-1][2] == {
        "load_balancer_id": "lb-ocid",
        "certificate_name": "api-cert",
    }


def test_missing_public_certificate_fails_before_create():
    """Require a public certificate for creation."""
    adapter = _certificate_module({"load_balancer_id": "lb-ocid", "name": "api-cert"})
    with pytest.raises(FailJsonCalled):
        adapter.validate_create_request()


def test_check_mode_predicts_create_and_delete_without_mutation():
    """Verify that check mode predicts changes without OCI mutations."""
    create = _certificate_module(
        {
            "load_balancer_id": "lb-ocid",
            "name": "api-cert",
            "public_certificate": "PUBLIC",
            "state": "present",
        },
        check_mode=True,
    )
    create.resolve_target_resource = lambda: None
    create.create_resource = lambda: pytest.fail("check mode called create_resource")
    with pytest.raises(ExitJsonCalled) as created:
        create.execute_resource_module()
    assert created.value.payload == {"changed": True}

    delete = _certificate_module(
        {"load_balancer_id": "lb-ocid", "name": "api-cert", "state": "absent"},
        check_mode=True,
    )
    delete.resolve_target_resource = _certificate
    delete.delete_resource = lambda resource: pytest.fail("check mode called delete_resource")
    with pytest.raises(ExitJsonCalled) as deleted:
        delete.execute_resource_module()
    assert deleted.value.payload == {"changed": True}


@pytest.mark.parametrize("check_mode", [False, True])
def test_same_certificate_is_idempotent(check_mode):
    """Verify PEM comparison and the serialized result in both modes."""
    current = _certificate(public_certificate="PUBLIC", ca_certificate="CA")
    same = _certificate_module(
        {
            "load_balancer_id": "lb-ocid",
            "name": "api-cert",
            "public_certificate": "  PUBLIC\n",
            "ca_certificate": "CA\n",
            "state": "present",
        },
        check_mode=check_mode,
    )
    same.resolve_target_resource = lambda: current
    with pytest.raises(ExitJsonCalled) as result:
        same.execute_resource_module()
    assert result.value.payload == {
        "changed": False,
        "resource": {
            "name": "api-cert",
            "public_certificate": "PUBLIC",
            "ca_certificate": "CA",
        },
    }


@pytest.mark.parametrize("field", ["public_certificate", "ca_certificate"])
@pytest.mark.parametrize("check_mode", [False, True])
def test_pem_mismatch_fails(field, check_mode):
    """Reject a change to a public or CA certificate in either mode."""
    params = {"load_balancer_id": "lb-ocid", "name": "api-cert", field: "OTHER"}
    adapter = _certificate_module(params, check_mode=check_mode)
    adapter.resolve_target_resource = _certificate

    with pytest.raises(FailJsonCalled) as failed:
        adapter.execute_resource_module()

    assert field in failed.value.payload["msg"]
    assert "new bundle name" in failed.value.payload["msg"]


def test_create_without_wait_returns_name_before_bundle_is_visible(monkeypatch):
    """Verify the fallback result until OCI exposes the bundle."""
    adapter = _certificate_module(
        {
            "load_balancer_id": "lb-ocid",
            "name": "api-cert",
            "public_certificate": "PUBLIC",
            "wait": False,
        }
    )
    monkeypatch.setattr(adapter, "invoke_resource_operation", lambda *args, **kwargs: None)
    monkeypatch.setattr(adapter, "get_resource_by_id", lambda name: None)

    with pytest.raises(ExitJsonCalled) as result:
        adapter.execute_resource_module()

    assert result.value.payload == {"changed": True, "resource": {"name": "api-cert"}}


def test_return_preserves_an_empty_ca_certificate():
    """Return a null field when OCI supplies a bundle without a CA certificate."""
    adapter = _certificate_module({"load_balancer_id": "lb-ocid", "name": "api-cert"})
    adapter.resolve_target_resource = lambda: _certificate(ca_certificate=None)

    with pytest.raises(ExitJsonCalled) as result:
        adapter.execute_resource_module()

    assert result.value.payload["resource"] == {
        "name": "api-cert",
        "public_certificate": "PUBLIC",
        "ca_certificate": None,
    }
