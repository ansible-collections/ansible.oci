from __future__ import absolute_import, division, print_function

__metaclass__ = type

import types

import oci

from .conftest import load_collection_module


def _load_helper(monkeypatch):
    """Load the helper with the installed OCI SDK models."""
    helper = load_collection_module("oci_network_loadbalancer")
    monkeypatch.setattr(helper, "oci", oci)
    return helper


def test_build_model_types_nested_health_checker_backends_and_reserved_ips(monkeypatch):
    """Build supported nested models and preserve arbitrary tag values."""
    helper = _load_helper(monkeypatch)
    fields = {
        "policy": "five_tuple",
        "freeform_tags": {"protocol": "KeepCase", "Owner": "MixedCase"},
        "health_checker": {
            "protocol": "dns",
            "dns": {
                "transport_protocol": "udp",
                "query_type": "a",
                "rcodes": ["noerror"],
                "domain_name": "MiXeD.example",
            },
        },
        "backends": [{"ip_address": "10.0.0.4", "port": 443}],
        "unknown_field": "ignored",
    }

    model = helper.build_network_load_balancer_model("CreateBackendSetDetails", fields)

    assert isinstance(model, oci.network_load_balancer.models.CreateBackendSetDetails)
    assert model.policy == "FIVE_TUPLE"
    assert model.health_checker.protocol == "DNS"
    assert isinstance(
        model.health_checker.dns,
        oci.network_load_balancer.models.DnsHealthCheckerDetails,
    )
    assert model.health_checker.dns.transport_protocol == "UDP"
    assert model.health_checker.dns.query_type == "A"
    assert model.health_checker.dns.domain_name == "MiXeD.example"
    assert model.backends[0].ip_address == "10.0.0.4"
    assert isinstance(
        model.backends[0], oci.network_load_balancer.models.BackendDetails
    )
    assert not hasattr(model, "unknown_field")

    network = helper.build_network_load_balancer_model(
        "CreateNetworkLoadBalancerDetails",
        {
            "reserved_ips": [{"id": "ocid1.reservedip"}],
            "freeform_tags": fields["freeform_tags"],
        },
    )
    assert isinstance(
        network.reserved_ips[0], oci.network_load_balancer.models.ReservedIP
    )
    assert network.freeform_tags == fields["freeform_tags"]


def test_mutation_wait_uses_status_work_request_and_returns_original_response(
    monkeypatch,
):
    """Wait on the work request header and return the original response."""
    helper_module = _load_helper(monkeypatch)
    calls = []
    response = types.SimpleNamespace(
        data=types.SimpleNamespace(id="wr1", status="ACCEPTED"),
        headers={"opc-work-request-id": "wr1"},
    )
    helper = types.SimpleNamespace(
        client=types.SimpleNamespace(create_backend_set=lambda **kwargs: response),
        module=types.SimpleNamespace(params={"wait": True}),
        call_with_retry=lambda fn, **kwargs: fn(**kwargs),
        wait_for_work_request=lambda client, request_id: calls.append(
            (client, request_id)
        ),
    )

    result = helper_module.call_network_load_balancer_mutation(
        helper, "create_backend_set", network_load_balancer_id="nlb1"
    )

    assert result is response
    assert calls == [(helper.client, "wr1")]


def test_mutation_without_wait_does_not_poll_and_returns_original_response(monkeypatch):
    """Skip work request polling when wait is false."""
    helper_module = _load_helper(monkeypatch)
    calls = []
    response = types.SimpleNamespace(
        data=types.SimpleNamespace(id="resource-id"), headers={}
    )
    helper = types.SimpleNamespace(
        client=types.SimpleNamespace(delete_backend=lambda **kwargs: response),
        module=types.SimpleNamespace(params={"wait": False}),
        call_with_retry=lambda fn, **kwargs: fn(**kwargs),
        wait_for_work_request=lambda *args: calls.append(args),
    )

    result = helper_module.call_network_load_balancer_mutation(
        helper, "delete_backend", network_load_balancer_id="nlb1"
    )

    assert result is response
    assert calls == []


def test_update_details_preserve_omitted_nested_backend_set_fields(monkeypatch):
    """Keep omitted nested backend set fields during an update."""
    helper = _load_helper(monkeypatch)
    subresource = types.SimpleNamespace(
        update_model_name="UpdateBackendSetDetails",
        build_resource_model=helper.build_network_load_balancer_model,
    )
    current = oci.network_load_balancer.models.BackendSetDetails(
        policy="FIVE_TUPLE",
        health_checker=oci.network_load_balancer.models.HealthChecker(
            protocol="HTTP", port=80, url_path="/old"
        ),
        backends=[
            oci.network_load_balancer.models.Backend(
                ip_address="10.0.0.7", port=80, weight=2
            )
        ],
    )

    details = helper.OciNetworkLoadBalancerSubresourceBase.build_update_details(
        subresource, {"health_checker": {"url_path": "/ready"}}, current
    )

    assert details.policy == "FIVE_TUPLE"
    assert details.health_checker.protocol == "HTTP"
    assert details.health_checker.port == 80
    assert details.health_checker.url_path == "/ready"
    assert details.backends[0].ip_address == "10.0.0.7"


def test_nested_enum_comparisons_are_schema_scoped():
    """Compare direct health checker and DNS schemas without case drift."""
    helper_module = load_collection_module("oci_network_loadbalancer")

    class ConcreteSubresource(helper_module.OciNetworkLoadBalancerSubresourceBase):
        """Provide the abstract resource hooks for comparison testing."""

        @property
        def update_field_specs(self):
            """Return an empty update specification."""
            return ()

        def get_resource_response(self, resource_id):
            """Return no resource for this isolated comparison test."""
            return None

    subresource = object.__new__(ConcreteSubresource)
    assert not subresource.compare_update_field_values(
        {"protocol": "DNS", "dns": {"query_type": "A", "rcodes": ["NOERROR"]}},
        {"protocol": "dns", "dns": {"query_type": "a", "rcodes": ["noerror"]}},
        compare="nlb_health_checker",
    )
    assert not subresource.compare_update_field_values(
        {"query_type": "A", "rcodes": ["NOERROR"], "domain_name": "MiXeD.example"},
        {"query_type": "a", "rcodes": ["noerror"], "domain_name": "MiXeD.example"},
        compare="nlb_dns",
    )


def test_mutation_without_work_request_header_does_not_poll(monkeypatch):
    """Keep successful SDK responses that have no work request header."""
    helper_module = _load_helper(monkeypatch)
    response = oci.response.Response(204, {}, None, None)
    helper = types.SimpleNamespace(
        client=types.SimpleNamespace(delete_backend=lambda **kwargs: response),
        module=types.SimpleNamespace(params={"wait": True}),
        call_with_retry=lambda fn, **kwargs: fn(**kwargs),
    )

    def unexpected_wait(*args):
        raise AssertionError("An absent work request must not be polled.")

    helper.wait_for_work_request = unexpected_wait
    assert helper_module.call_network_load_balancer_mutation(
        helper, "delete_backend", network_load_balancer_id="nlb1"
    ) is response
