from __future__ import absolute_import, division, print_function

__metaclass__ = type

import types

from .conftest import (
    DummyModule,
    FakeModel,
    FakeResponse,
    FailJsonCalled,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)

MODEL_NAMES = ("CreateWebAppFirewallLoadBalancerDetails", "UpdateWebAppFirewallDetails")


def install_fake_oci(monkeypatch):
    """Install a fake OCI SDK with WAF models for unit tests."""
    oci_module = shared_install_fake_oci(monkeypatch, model_names=MODEL_NAMES)[0]
    oci_module.waf = types.SimpleNamespace(
        WafClient=type("FakeWafClient", (), {}),
        models=oci_module.identity.models,
    )
    return oci_module


def make_waf_module(module_obj, params, client=None, check_mode=False):
    """Create a WAF module instance with a test client."""
    return make_module_instance(
        module_obj,
        "OciWafWebAppFirewallModule",
        params,
        client=client,
        check_mode=check_mode,
    )


def test_main_exposes_waf_firewall_arguments(monkeypatch):
    """Verify the WAF firewall argument specification and check mode."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_waf_web_app_firewall")
    captured = {}

    def fake_ansible_module(**kwargs):
        """Capture the module constructor arguments."""
        captured.update(kwargs)
        return DummyModule()

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(
        module_obj,
        "OciWafWebAppFirewallModule",
        lambda module: types.SimpleNamespace(execute_resource_module=lambda: None),
    )
    module_obj.main()

    assert captured["supports_check_mode"] is True
    assert "backend_type" not in captured["argument_spec"]
    assert captured["argument_spec"]["system_tags"] == {"type": "dict"}


def test_build_create_details_sets_backend_type_and_maps_tags(monkeypatch):
    """Verify create details map user fields to the OCI model."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_waf_web_app_firewall")
    details = module_obj.build_create_web_app_firewall_details(
        {
            "name": "example-waf",
            "compartment_id": "compartment",
            "load_balancer_id": "load-balancer",
            "web_app_firewall_policy_id": "policy",
            "freeform_tags": {"env": "test"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
            "system_tags": {"Oracle-Tags": {"CreatedBy": "user"}},
        }
    )
    assert details.display_name == "example-waf"
    assert details.backend_type == "LOAD_BALANCER"
    assert details.load_balancer_id == "load-balancer"
    assert details.freeform_tags == {"env": "test"}
    assert details.system_tags["Oracle-Tags"]["CreatedBy"] == "user"


def test_update_resource_builds_details_and_fetches_after_update(monkeypatch):
    """Verify waited updates fetch the resource after an empty SDK response."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_waf_web_app_firewall")
    calls = []

    def update(**kwargs):
        """Capture the update request and return an empty response body."""
        calls.append(kwargs)
        return FakeResponse(data=None)

    instance = make_waf_module(
        module_obj,
        {"name": "renamed", "wait": True},
        client=types.SimpleNamespace(update_web_app_firewall=update),
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    instance.get_resource_response = lambda resource_id: FakeResponse(
        data=FakeModel(id=resource_id, display_name="renamed", lifecycle_state="ACTIVE")
    )
    waited = []
    instance.wait_for_resource_id = lambda resource_id, states: (
        waited.append((resource_id, states))
        or instance.get_resource_response(resource_id).data
    )
    resource = instance.update_resource(FakeModel(id="waf", display_name="old"))
    assert waited == [("waf", ("ACTIVE",))]

    assert resource.display_name == "renamed"
    assert calls[0]["web_app_firewall_id"] == "waf"
    assert calls[0]["update_web_app_firewall_details"].display_name == "renamed"


def test_update_resource_wait_false_returns_current_snapshot(monkeypatch):
    """Verify updates with wait disabled return the immediate snapshot."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_waf_web_app_firewall")
    instance = make_waf_module(
        module_obj,
        {"web_app_firewall_policy_id": "new-policy", "wait": False},
        client=types.SimpleNamespace(
            update_web_app_firewall=lambda **kwargs: FakeResponse(data=None)
        ),
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    resource = FakeModel(
        id="waf", display_name="old", web_app_firewall_policy_id="old-policy"
    )

    assert instance.update_resource(resource) is resource


def test_immutable_load_balancer_change_fails(monkeypatch):
    """Verify the load balancer association cannot change after creation."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_waf_web_app_firewall")
    instance = make_waf_module(module_obj, {"load_balancer_id": "new-lb"})

    try:
        instance.needs_update(FakeModel(id="waf", load_balancer_id="old-lb"))
    except FailJsonCalled as exc:
        assert "load_balancer_id" in exc.payload["msg"]
    else:
        raise AssertionError("expected immutable field failure")


def test_execute_create_check_mode_reports_change_without_api_call(monkeypatch):
    """Verify check mode predicts creation without calling the create API."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_waf_web_app_firewall")
    instance = make_waf_module(
        module_obj,
        {
            "state": "present",
            "name": "waf",
            "compartment_id": "compartment",
            "load_balancer_id": "lb",
            "web_app_firewall_policy_id": "policy",
        },
        check_mode=True,
    )
    instance.resolve_target_resource = lambda: None
    instance.create_resource = lambda: (item for item in ()).throw(
        AssertionError("called")
    )
    try:
        instance.execute_resource_module()
    except Exception as exc:
        assert exc.__class__.__name__ == "ExitJsonCalled"
        assert exc.payload["changed"] is True
    else:
        raise AssertionError("expected check-mode exit")


def test_execute_update_check_mode_reports_change_without_api_call(monkeypatch):
    """Verify check mode predicts an update without calling the update API."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_waf_web_app_firewall")
    instance = make_waf_module(
        module_obj, {"state": "present", "name": "new"}, check_mode=True
    )
    instance.resolve_target_resource = lambda: FakeModel(id="waf", display_name="old")
    instance.update_resource = lambda resource: (item for item in ()).throw(
        AssertionError("called")
    )
    try:
        instance.execute_resource_module()
    except Exception as exc:
        assert exc.__class__.__name__ == "ExitJsonCalled"
        assert exc.payload["changed"] is True
    else:
        raise AssertionError("expected check-mode exit")


def test_execute_delete_check_mode_reports_change_without_api_call(monkeypatch):
    """Verify check mode predicts deletion without calling the delete API."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_waf_web_app_firewall")
    instance = make_waf_module(
        module_obj,
        {"state": "absent", "web_app_firewall_id": "waf"},
        check_mode=True,
    )
    instance.resolve_target_resource = lambda: FakeModel(id="waf")
    instance.delete_resource = lambda resource: (item for item in ()).throw(
        AssertionError("called")
    )
    try:
        instance.execute_resource_module()
    except Exception as exc:
        assert exc.__class__.__name__ == "ExitJsonCalled"
        assert exc.payload["changed"] is True
    else:
        raise AssertionError("expected check-mode exit")


def test_execute_present_is_idempotent_when_resource_matches(monkeypatch):
    """Verify a matching present request reports no change."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_waf_web_app_firewall")
    instance = make_waf_module(module_obj, {"state": "present", "name": "waf"})
    instance.resolve_target_resource = lambda: FakeModel(
        id="waf", display_name="waf", backend_type="LOAD_BALANCER"
    )
    try:
        instance.execute_resource_module()
    except Exception as exc:
        assert exc.__class__.__name__ == "ExitJsonCalled"
        assert exc.payload["changed"] is False
    else:
        raise AssertionError("expected normal execution exit")


def test_create_waits_for_work_request_and_fetches_resource(monkeypatch):
    """Verify create waits for an OCI work request when the response has one."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_waf_web_app_firewall")
    instance = make_waf_module(
        module_obj, {"wait": True}, client=types.SimpleNamespace()
    )
    instance.call_with_retry = lambda fn, **kwargs: FakeResponse(
        data=FakeModel(id="waf"), headers={"opc-work-request-id": "wr"}
    )
    instance.client.create_web_app_firewall = lambda **kwargs: FakeResponse(
        data=FakeModel(id="waf"), headers={"opc-work-request-id": "wr"}
    )
    waited = []
    instance.wait_for_work_request = lambda client, work_request_id: waited.append(
        work_request_id
    )
    instance.get_resource_response = lambda resource_id: FakeResponse(
        data=FakeModel(id=resource_id)
    )
    result = instance.create_resource()
    assert waited == ["wr"]
    assert result.id == "waf"


def test_delete_waits_for_work_request_and_propagates_failure(monkeypatch):
    """Verify delete passes work request failures to the shared waiter."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_waf_web_app_firewall")
    instance = make_waf_module(
        module_obj,
        {"wait": True},
        client=types.SimpleNamespace(
            delete_web_app_firewall=lambda **kwargs: FakeResponse(
                data=None, headers={"opc-work-request-id": "wr"}
            )
        ),
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    instance.wait_for_work_request = lambda client, work_request_id: (
        item for item in ()
    ).throw(RuntimeError("work request failed"))
    try:
        instance.delete_resource(FakeModel(id="waf"))
    except RuntimeError as exc:
        assert "failed" in str(exc)
    else:
        raise AssertionError("expected work request failure")
