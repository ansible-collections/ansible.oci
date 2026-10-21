"""Shared lifecycle and model helpers for OCI Network Load Balancer."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    import_oci_sdk,
    serialize_oci_model,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_loadbalancer_common import (
    OciLoadBalancerSubresourceBase,
    build_nested_model,
    OciLoadBalancerInfoBase as OciLoadBalancerInfoCommonBase,
)

oci = import_oci_sdk()[0]

_NLB_ENUM_FIELDS = frozenset(
    (
        "policy",
        "protocol",
        "transport_protocol",
        "query_class",
        "query_type",
        "ip_version",
        "nlb_ip_version",
    )
)

_NESTED_MODEL_NAMES = {
    "health_checker": "HealthCheckerDetails",
    "dns": "DnsHealthCheckerDetails",
}
_LIST_MODEL_NAMES = {"backends": "BackendDetails", "reserved_ips": "ReservedIP"}

NETWORK_LOAD_BALANCER_BACKEND_ARGUMENT_SPEC = {
    "name": dict(type="str"),
    "ip_address": dict(type="str"),
    "target_id": dict(type="str"),
    "port": dict(type="int"),
    "weight": dict(type="int"),
    "is_backup": dict(type="bool"),
    "is_drain": dict(type="bool"),
    "is_offline": dict(type="bool"),
}

NETWORK_LOAD_BALANCER_DNS_ARGUMENT_SPEC = {
    "transport_protocol": dict(type="str", choices=["udp", "tcp"]),
    "domain_name": dict(type="str"),
    "query_class": dict(type="str", choices=["in", "ch"]),
    "query_type": dict(type="str", choices=["a", "txt", "aaaa"]),
    "rcodes": dict(
        type="list",
        elements="str",
        choices=["noerror", "servfail", "nxdomain", "refused"],
    ),
}

NETWORK_LOAD_BALANCER_HEALTH_CHECKER_ARGUMENT_SPEC = {
    "protocol": dict(type="str"),
    "port": dict(type="int"),
    "retries": dict(type="int"),
    "timeout_in_millis": dict(type="int"),
    "interval_in_millis": dict(type="int"),
    "url_path": dict(type="str"),
    "response_body_regex": dict(type="str"),
    "return_code": dict(type="int"),
    "request_data": dict(type="str"),
    "response_data": dict(type="str"),
    "dns": dict(type="dict", options=NETWORK_LOAD_BALANCER_DNS_ARGUMENT_SPEC),
}


def validate_network_load_balancer_backend(module, fields):
    """Validate the locator and port for a new backend.

    Args:
        module: Active Ansible module used to report invalid input.
        fields: Requested backend fields.
    """
    missing = []
    if fields.get("port") is None:
        missing.append("port")
    if not (fields.get("ip_address") or fields.get("target_id")):
        missing.append("ip_address or target_id")
    if missing:
        module.fail_json(
            msg="Backend {0} requires {1}.".format(
                fields.get("name"), " and ".join(missing)
            )
        )


def _normalize_model_field(name, value):
    """Normalize one supported NLB field without changing arbitrary mappings.

    Args:
        name: Supported SDK field name.
        value: Supplied field value.

    Returns:
        The normalized enum value, or the original value.
    """
    if name in _NLB_ENUM_FIELDS:
        return value.upper()
    if name == "rcodes":
        return [item.upper() for item in value]
    return value


def build_network_load_balancer_model(model_name, fields):
    """Build an NLB model through the shared nested model builder.

    Args:
        model_name: NLB SDK model name.
        fields: Source fields.

    Returns:
        The SDK model created through ``oci_common.build_model``.
    """
    return build_nested_model(
        getattr(oci.network_load_balancer.models, model_name),
        fields,
        _NESTED_MODEL_NAMES,
        _LIST_MODEL_NAMES,
        build_network_load_balancer_model,
        skip_none_items=("backends", "reserved_ips"),
        convert_field=_normalize_model_field,
    )


def call_network_load_balancer_mutation(helper, method_name, wait=None, **kwargs):
    """Call one NLB mutation and optionally wait for its work request.

    Args:
        helper: Resource helper with retry and work-request methods.
        method_name: Raw SDK mutation method name.
        wait: Whether to wait. The module setting is used when this is None.
        **kwargs: SDK operation arguments.

    Returns:
        The original SDK response.
    """
    operation = getattr(helper.client, method_name)
    response = helper.call_with_retry(operation, **kwargs)
    should_wait = helper.module.params.get("wait", True) if wait is None else wait
    work_request_id = response.headers.get("opc-work-request-id")
    if should_wait and work_request_id:
        helper.wait_for_work_request(helper.client, work_request_id)
    return response


class OciNetworkLoadBalancerSubresourceBase(OciLoadBalancerSubresourceBase):
    """Provide common model and mutation behavior for NLB child resources."""

    @property
    def client_class(self):
        """Return the NLB SDK client class."""
        return oci.network_load_balancer.NetworkLoadBalancerClient

    @staticmethod
    def build_resource_model(model_name, fields):
        """Build an NLB model from supported fields.

        Args:
            model_name: SDK model name.
            fields: Source fields.

        Returns:
            The typed SDK model.
        """
        return build_network_load_balancer_model(model_name, fields)

    def invoke_resource_operation(self, operation, method_name, **kwargs):
        """Invoke an NLB mutation and wait through the shared work-request helper.

        Args:
            operation: Lifecycle operation name.
            method_name: Raw SDK operation name.
            **kwargs: SDK operation arguments.

        Returns:
            The SDK response.
        """
        return call_network_load_balancer_mutation(self, method_name, **kwargs)

    def mutation_kwargs(self, operation):
        """Return the parent ID for a child mutation.

        Args:
            operation: Mutation name.

        Returns:
            SDK arguments shared by child mutations.
        """
        return {
            "network_load_balancer_id": self.module.params["network_load_balancer_id"]
        }

    def compare_update_field_values(self, current_value, desired_value, compare=None):
        """Compare NLB enums and nested fields by their schema values.

        Args:
            current_value: Value returned by OCI.
            desired_value: Value requested by the module.
            compare: Comparison strategy from the update field spec.

        Returns:
            True when the current and desired values differ.
        """
        if compare == "enum":
            desired_value = desired_value.upper()
            compare = None
        elif compare in ("nlb_health_checker", "nlb_dns"):
            model_name = (
                "HealthCheckerDetails"
                if compare == "nlb_health_checker"
                else "DnsHealthCheckerDetails"
            )
            desired_value = serialize_oci_model(
                build_network_load_balancer_model(model_name, desired_value)
            )
            compare = "subset_dict"
        return super(
            OciNetworkLoadBalancerSubresourceBase, self
        ).compare_update_field_values(current_value, desired_value, compare=compare)


class OciNetworkLoadBalancerInfoBase(OciLoadBalancerInfoCommonBase):
    """Select the SDK client for scoped NLB info requests."""

    @property
    def client_class(self):
        """Return the NLB SDK client class."""
        return oci.network_load_balancer.NetworkLoadBalancerClient
