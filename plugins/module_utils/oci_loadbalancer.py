"""Shared lifecycle support for OCI load balancer child resources."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from collections.abc import Mapping

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    import_oci_sdk,
    normalize_enum_values,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_loadbalancer_common import (
    OciLoadBalancerSubresourceBase as OciLoadBalancerSubresourceCommonBase,
    OciLoadBalancerInfoBase as OciLoadBalancerInfoCommonBase,
    build_nested_model,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]


_NESTED_MODEL_NAMES = {
    "health_checker": "HealthCheckerDetails",
    "ssl_configuration": "SSLConfigurationDetails",
    "connection_configuration": "ConnectionConfiguration",
    "session_persistence_configuration": "SessionPersistenceConfigurationDetails",
    "lb_cookie_session_persistence_configuration": (
        "LBCookieSessionPersistenceConfigurationDetails"
    ),
}

_LIST_MODEL_NAMES = {"backends": "BackendDetails", "rules": "RoutingRule"}

_LOAD_BALANCER_ENUM_KEYS = frozenset(
    ("policy", "protocol", "server_order_preference")
)


def normalize_load_balancer_fields(fields):
    """Normalize load balancer enum fields.

    Preserve TLS protocol spelling and unrelated strings.

    Args:
        fields: Input fields or a serialized resource.

    Returns:
        A new mapping with normalized fields.
    """
    normalized = normalize_enum_values(dict(fields or {}), _LOAD_BALANCER_ENUM_KEYS)

    rules = normalized.get("rules")
    if rules is not None:
        normalized["rules"] = [
            _normalize_routing_rule(rule) if isinstance(rule, Mapping) else rule
            for rule in rules
        ]

    return normalized


def _normalize_routing_rule(rule):
    """Normalize action names in one routing rule.

    Args:
        rule: Routing rule fields.

    Returns:
        A copy with action names in OCI spelling.
    """
    result = dict(rule)
    actions = result.get("actions")
    if actions is not None:
        result["actions"] = []
        for action in actions:
            if isinstance(action, Mapping):
                action = dict(action)
                action.setdefault("name", "FORWARD_TO_BACKENDSET")
                action = normalize_enum_values(action, ("name",))
            result["actions"].append(action)
    return result


def _build_routing_actions(field_name, value):
    """Convert supported routing actions to SDK models.

    Args:
        field_name: Field in a routing rule.
        value: Supplied field value.

    Returns:
        Typed forward actions, or the original value for other fields.
    """
    if field_name == "actions":
        return [
            _build_model("ForwardToBackendSet", action)
            if isinstance(action, Mapping)
            and action.get("name") == "FORWARD_TO_BACKENDSET"
            else action
            for action in value
        ]
    return value


def _build_model(model_name, fields):
    """Build an LB model through the shared nested model builder.

    Args:
        model_name: SDK model name.
        fields: Normalized source fields.

    Returns:
        The typed SDK model with routing defaults applied.
    """
    model_fields = dict(fields)
    if model_name == "CreateRoutingPolicyDetails":
        model_fields.setdefault("condition_language_version", "V1")
    return build_nested_model(
        getattr(oci.load_balancer.models, model_name),
        model_fields,
        _NESTED_MODEL_NAMES,
        _LIST_MODEL_NAMES,
        _build_model,
        skip_none_items=("backends",),
        convert_field=_build_routing_actions if model_name == "RoutingRule" else None,
    )


def build_load_balancer_model(model_name, fields):
    """Build a load balancer SDK model with normalized enum fields.

    Args:
        model_name: Name of the SDK model class.
        fields: Input fields or serialized resource fields.

    Returns:
        The requested SDK model with typed nested fields.
    """
    return _build_model(model_name, normalize_load_balancer_fields(fields))


class OciLoadBalancerSubresourceBase(OciLoadBalancerSubresourceCommonBase):
    """Common create, update, and delete behavior for Load Balancer children."""

    @property
    def client_class(self):
        """Return the SDK client class.

        Returns:
            The OCI load balancer client class.
        """
        return oci.load_balancer.LoadBalancerClient

    @staticmethod
    def plan_enum_update(resource, resource_dict, spec, desired_value):
        """Plan an update when an enum value differs.

        Args:
            resource: Current OCI resource model.
            resource_dict: Serialized resource fields.
            spec: Update field specification.
            desired_value: Requested enum value.

        Returns:
            An operation with the normalized value, or an empty list.
        """
        resource_field = spec.resource_field or spec.param_name
        update_field = spec.update_field or resource_field
        normalized_value = normalize_load_balancer_fields(
            {update_field: desired_value}
        )[update_field]
        if resource_dict.get(resource_field) == normalized_value:
            return []
        return [{update_field: normalized_value}]

    def build_update_plan(self, resource):
        """Add enum operations to the update model fields.

        Args:
            resource: Current OCI resource model.

        Returns:
            The shared update plan with enum fields included.
        """
        update_plan = super(OciLoadBalancerSubresourceBase, self).build_update_plan(
            resource
        )
        for strategy_plan in update_plan["strategy_operations"]:
            for operation in strategy_plan["operations"]:
                update_plan["update_model_fields"].update(operation)
        return update_plan

    def compare_update_field_values(self, current_value, desired_value, compare=None):
        """Compare field values with enum normalization for subset updates.

        Args:
            current_value: Value returned by OCI.
            desired_value: Requested field value.
            compare: Comparison strategy, if supplied.

        Returns:
            True if the field values differ.
        """
        if compare == "subset_dict":
            desired_value = normalize_load_balancer_fields(desired_value)
        return super(OciLoadBalancerSubresourceBase, self).compare_update_field_values(
            current_value, desired_value, compare=compare
        )

    def mutation_kwargs(self, operation):
        """Build arguments that identify the parent load balancer.

        Args:
            operation: Create, update, or delete operation.

        Returns:
            The arguments shared by child API calls.
        """
        return {"load_balancer_id": self.module.params["load_balancer_id"]}

    @staticmethod
    def build_resource_model(model_name, fields):
        """Build a load balancer model from supported fields.

        Args:
            model_name: SDK model name.
            fields: Source fields.

        Returns:
            The typed SDK model.
        """
        return build_load_balancer_model(model_name, fields)

    def invoke_resource_operation(self, operation, method_name, **kwargs):
        """Invoke a composite child operation and check its work request.

        Args:
            operation: Lifecycle operation name.
            method_name: Composite operation method name.
            **kwargs: SDK operation arguments.

        Returns:
            The immediate or waited SDK response.
        """
        response = self._composite_call(operation, method_name, **kwargs)
        if self._should_wait:
            self._check_work_request_result(response, operation)
        return response

    @staticmethod
    def _work_request_id(response):
        """Read the work request ID from a response.

        Args:
            response: SDK response.

        Returns:
            The ID from the response data or headers, or None.
        """
        data = response.data
        return (
            getattr(data, "id", None)
            or response.headers.get("opc-work-request-id")
        )

    def _work_request_failure_message(self, response):
        """Build a message for a failed work request.

        Args:
            response: SDK response.

        Returns:
            A message with the request ID and available error details.
        """
        work_request_id = self._work_request_id(response) or "ID unavailable"
        data = response.data
        error_details = data.error_details or []
        messages = []
        for detail in error_details:
            code = detail.error_code
            message = detail.message
            part = ": ".join(item for item in (code, message) if item)
            if part:
                messages.append(part)
        reason = "; ".join(messages) or data.message
        return "Work request {0} failed{1}".format(
            work_request_id,
            ": {0}".format(reason) if reason else "",
        )

    def _check_work_request_result(self, response, operation):
        """Fail if a work request did not succeed.

        Args:
            response: SDK response.
            operation: Create, update, or delete operation.
        """
        data = response.data
        # An immediate composite response can have no work request data.
        state = getattr(data, "lifecycle_state", None)
        work_request_id = self._work_request_id(response)
        if state == "FAILED":
            self.module.fail_json(
                msg="Failed to {0} {1}: {2}".format(
                    operation,
                    self.create_resource_name,
                    self._work_request_failure_message(response),
                )
            )
        if work_request_id and state != "SUCCEEDED":
            self.module.fail_json(
                msg=(
                    "The OCI {0} work request {1} completed in unexpected state "
                    "{2}."
                ).format(operation, work_request_id, state or "unknown")
            )

    def _composite_call(self, operation, method_name, **kwargs):
        """Call an SDK composite operation with the configured wait settings.

        Args:
            operation: Operation name used in error messages.
            method_name: Name of the SDK composite method.
            **kwargs: Arguments for the SDK operation.

        Returns:
            The immediate or waited SDK response.
        """
        composite = oci.load_balancer.LoadBalancerClientCompositeOperations(
            self.client
        )
        waiting = self._should_wait
        wait_states = ["SUCCEEDED", "FAILED"] if waiting else []
        waiter_kwargs = {}
        if waiting:
            waiter_kwargs = {
                "max_wait_seconds": self.module.params.get("wait_timeout", 1200),
                "max_interval_seconds": self.module.params.get("wait_interval", 30),
            }

        operation_kwargs = kwargs.pop("operation_kwargs", {})
        operation_kwargs.setdefault(
            "retry_strategy", oci.retry.DEFAULT_RETRY_STRATEGY
        )
        previous_retry_strategy = self.client.retry_strategy
        self.client.retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY
        try:
            return getattr(composite, method_name)(
                wait_for_states=wait_states,
                waiter_kwargs=waiter_kwargs,
                operation_kwargs=operation_kwargs,
                **kwargs
            )
        except oci.exceptions.CompositeOperationError as exc:
            partial_results = exc.partial_results
            work_request_id = None
            if partial_results:
                work_request_id = partial_results[-1].headers.get("opc-work-request-id")
            cause = exc.cause or exc
            self.module.fail_json(
                msg="Failed to {0} {1}; work request {2}: {3}".format(
                    operation,
                    self.create_resource_name,
                    work_request_id or "ID unavailable",
                    cause,
                )
            )
        except oci.exceptions.MaximumWaitTimeExceeded as exc:
            self.module.fail_json(
                msg="Timed out waiting to {0} {1}: {2}".format(
                    operation, self.create_resource_name, exc
                )
            )
        except oci.exceptions.ServiceError as exc:
            self.module.fail_json(
                msg="Failed to {0} {1}: {2}".format(
                    operation, self.create_resource_name, exc
                )
            )
        finally:
            self.client.retry_strategy = previous_retry_strategy


class OciLoadBalancerInfoBase(OciLoadBalancerInfoCommonBase):
    """Select the SDK client for scoped LB info requests."""

    @property
    def client_class(self):
        """Return the LB SDK client class."""
        return oci.load_balancer.LoadBalancerClient
