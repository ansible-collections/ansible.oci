"""Shared lifecycle support for OCI load balancer child resources."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from collections.abc import Mapping

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    import_oci_sdk,
    normalize_enum_values,
    serialize_oci_model,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
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

_LOAD_BALANCER_ENUM_KEYS = frozenset(
    ("policy", "protocol", "server_order_preference")
)


def normalize_load_balancer_fields(fields):
    """Normalize load balancer enum fields.

    Preserve TLS protocol spelling and unrelated strings.

    Args:
        fields: Input fields or a serialized resource.

    Returns:
        Normalized fields, or the original value for nonmapping input.
    """
    if not isinstance(fields, Mapping):
        return fields

    normalized = normalize_enum_values(dict(fields), _LOAD_BALANCER_ENUM_KEYS)

    rules = normalized.get("rules")
    if isinstance(rules, (list, tuple)):
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
    if isinstance(actions, (list, tuple)):
        result["actions"] = []
        for action in actions:
            if isinstance(action, Mapping):
                action = dict(action)
                action.setdefault("name", "FORWARD_TO_BACKENDSET")
                action = normalize_enum_values(action, ("name",))
            result["actions"].append(action)
    return result


def _build_model_field(model_name, field_name, value):
    """Build nested SDK models for a supported field.

    Args:
        model_name: Name of the containing SDK model class.
        field_name: Name of the supported field.
        value: Field value to convert.

    Returns:
        The converted value, or the original value if no conversion applies.
    """
    nested_model_name = _NESTED_MODEL_NAMES.get(field_name)
    if nested_model_name and isinstance(value, Mapping):
        value = _build_model(nested_model_name, value)
    elif field_name == "backends" and isinstance(value, (list, tuple)):
        value = [
            _build_model("BackendDetails", backend)
            if isinstance(backend, Mapping)
            else backend
            for backend in value
            if backend is not None
        ]
    elif (
        model_name == "RoutingRule"
        and field_name == "actions"
        and isinstance(value, (list, tuple))
    ):
        value = [
            _build_model("ForwardToBackendSet", action)
            if isinstance(action, Mapping)
            and action.get("name") == "FORWARD_TO_BACKENDSET"
            else action
            for action in value
        ]
    elif field_name == "rules" and isinstance(value, (list, tuple)):
        value = [
            _build_model("RoutingRule", rule) if isinstance(rule, Mapping) else rule
            for rule in value
        ]
    return value


def _build_model(model_name, fields):
    """Build an SDK model from supported fields.

    Skip unsupported fields and None values.
    Use condition language V1 for new routing policies when the field is absent.

    Args:
        model_name: Name of the SDK model class.
        fields: Fields used to build the model.

    Returns:
        The SDK model with supported fields set.
    """
    model_class = getattr(oci.load_balancer.models, model_name)
    model_template = model_class()
    supported_fields = getattr(model_template, "swagger_types", {})
    values = {}

    model_fields = dict(fields or {})
    if model_name == "CreateRoutingPolicyDetails":
        model_fields.setdefault("condition_language_version", "V1")

    for field_name, value in model_fields.items():
        if field_name not in supported_fields or value is None:
            continue

        values[field_name] = _build_model_field(model_name, field_name, value)

    return model_class(**values)


def build_load_balancer_model(model_name, fields):
    """Build a load balancer SDK model with normalized enum fields.

    Args:
        model_name: Name of the SDK model class.
        fields: Input fields or serialized resource fields.

    Returns:
        The requested SDK model with typed nested fields.
    """
    return _build_model(model_name, normalize_load_balancer_fields(fields))


def _merge_load_balancer_mappings(existing, supplied):
    """Merge supplied fields into existing fields.

    Merge nested mappings, skip None values, and replace lists.

    Args:
        existing: Current fields, if available.
        supplied: Fields supplied for the update.

    Returns:
        Merged fields without changes to the input data.
    """
    if not isinstance(existing, Mapping):
        existing = {}
    if not isinstance(supplied, Mapping):
        return dict(existing)

    result = dict(existing)
    for key, value in supplied.items():
        if value is None:
            continue
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = _merge_load_balancer_mappings(result[key], value)
        else:
            result[key] = value
    return result


def merge_load_balancer_fields(current, desired):
    """Serialize and merge resource fields for an update.

    Args:
        current: Current SDK resource or field mapping.
        desired: Requested fields or SDK model.

    Returns:
        Merged fields with omitted settings preserved.
    """
    current = serialize_oci_model(current)
    desired = serialize_oci_model(desired)
    return _merge_load_balancer_mappings(current, desired)


class OciLoadBalancerSubresourceBase(OciResourceBase):
    """Common create, update, and delete behavior for Load Balancer children."""

    @property
    def client_class(self):
        """Return the SDK client class.

        Returns:
            The OCI load balancer client class.
        """
        return oci.load_balancer.LoadBalancerClient

    resource_id_param = None
    name_response_field = "name"
    create_model_name = None
    create_method_name = None
    create_details_name = None
    update_model_name = None
    update_method_name = None
    update_details_name = None
    delete_method_name = None
    common_update_field_specs = ()
    create_resource_name = "load balancer subresource"

    @property
    def update_field_specs(self):
        """Return the default update field specifications.

        Returns:
            An empty tuple; child modules define their update fields.
        """
        return ()

    @property
    def resource_name(self):
        """Return the configured child resource name.

        Returns:
            The name parameter, or None if it is absent.
        """
        return self.module.params.get("name")

    def resolve_target_resource(self):
        """Find the named child resource under the load balancer.

        Returns:
            The child resource, or None if its name or resource is absent.
        """
        if self.resource_name is None:
            return None
        return self.get_resource_by_id(self.resource_name)

    def plan_enum_update(self, resource, resource_dict, spec, desired_value):
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
            desired_value = normalize_load_balancer_fields(desired_value or {})
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
        return {"load_balancer_id": self.module.params.get("load_balancer_id")}

    @property
    def _should_wait(self):
        """Return whether operations should wait for completion.

        Returns:
            The wait setting, or True if the setting is absent.
        """
        return self.module.params.get("wait", True)

    def _work_request_id(self, response):
        """Read the work request ID from a response.

        Args:
            response: SDK response or work request model.

        Returns:
            The ID from the response data or headers, or None.
        """
        data = getattr(response, "data", response)
        return (
            getattr(data, "id", None)
            or (getattr(response, "headers", None) or {}).get("opc-work-request-id")
        )

    def _work_request_failure_message(self, response):
        """Build a message for a failed work request.

        Args:
            response: SDK response or work request model.

        Returns:
            A message with the request ID and available error details.
        """
        work_request_id = self._work_request_id(response) or "ID unavailable"
        data = getattr(response, "data", response)
        error_details = getattr(data, "error_details", None) or []
        messages = []
        for detail in error_details:
            code = getattr(detail, "error_code", None)
            message = getattr(detail, "message", None)
            part = ": ".join(item for item in (code, message) if item)
            if part:
                messages.append(part)
        reason = "; ".join(messages) or getattr(data, "message", None)
        return "Work request {0} failed{1}".format(
            work_request_id,
            ": {0}".format(reason) if reason else "",
        )

    def _check_work_request_result(self, response, operation):
        """Fail if a work request did not succeed.

        Args:
            response: SDK response or work request model.
            operation: Create, update, or delete operation.
        """
        data = getattr(response, "data", response)
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

        operation_kwargs = kwargs.pop("operation_kwargs", {}) or {}
        operation_kwargs.setdefault(
            "retry_strategy", oci.retry.DEFAULT_RETRY_STRATEGY
        )
        previous_retry_strategy = getattr(self.client, "retry_strategy", None)
        self.client.retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY
        try:
            return getattr(composite, method_name)(
                wait_for_states=wait_states,
                waiter_kwargs=waiter_kwargs,
                operation_kwargs=operation_kwargs,
                **kwargs
            )
        except oci.exceptions.CompositeOperationError as exc:
            partial_results = getattr(exc, "partial_results", None) or []
            work_request_id = None
            if partial_results:
                work_request_id = (
                    getattr(partial_results[-1], "headers", None) or {}
                ).get("opc-work-request-id")
            cause = getattr(exc, "cause", None) or exc
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

    def _read_after_operation(self, operation):
        """Read the child resource after a create or update operation.

        Args:
            operation: Operation name used in error messages.

        Returns:
            The resource, or a mapping with its name if it is not visible
            and waiting is disabled.
        """
        try:
            resource = self.get_resource_by_id(self.resource_name)
        except oci.exceptions.ServiceError as exc:
            self.module.fail_json(
                msg="Failed to read {0} after {1}: {2}".format(
                    self.create_resource_name, operation, exc
                )
            )

        if resource is not None:
            return resource
        if self._should_wait:
            self.module.fail_json(
                msg=(
                    "OCI finished {0} {1}, but the child resource {2} could not "
                    "be retrieved."
                ).format(operation, self.create_resource_name, self.resource_name)
            )
        return {self.name_response_field: self.resource_name}

    def create_resource(self):
        """Create the child resource and apply the configured wait settings.

        Returns:
            The resource, or a mapping with its name if it is not visible
            and waiting is disabled.
        """
        if not (
            self.create_model_name
            and self.create_method_name
            and self.create_details_name
        ):
            self.module.fail_json(
                msg="Creating {0} is not supported.".format(self.create_resource_name)
            )
        details = build_load_balancer_model(
            self.create_model_name, self.module.params
        )
        kwargs = self.mutation_kwargs("create")
        kwargs[self.create_details_name] = details
        response = self._composite_call(
            "create", self.create_method_name, **kwargs
        )
        if self._should_wait:
            self._check_work_request_result(response, "create")
        return self._read_after_operation("create")

    def build_update_details(self, update_model_fields, resource=None):
        """Build SDK update details with omitted fields preserved.

        Args:
            update_model_fields: Fields selected for update.
            resource: Current resource, if available.

        Returns:
            The SDK update model.
        """
        fields = update_model_fields
        if resource is not None:
            fields = merge_load_balancer_fields(resource, update_model_fields)
        return build_load_balancer_model(self.update_model_name, fields)

    def update_resource(self, resource):
        """Update the child resource and apply the configured wait settings.

        Args:
            resource: Current child resource.

        Returns:
            The current or updated resource, or a mapping with its name
            if it is not visible and waiting is disabled.
        """
        if not self.update_method_name or not self.update_details_name:
            self.module.fail_json(
                msg="Updating {0} is not supported.".format(self.create_resource_name)
            )
        update_plan = self.get_update_plan(resource)
        update_model_fields = update_plan["update_model_fields"]
        if not update_model_fields:
            return resource

        details = self.build_update_details(update_model_fields, resource)
        kwargs = self.mutation_kwargs("update")
        kwargs[self.update_details_name] = details
        response = self._composite_call(
            "update", self.update_method_name, **kwargs
        )
        if self._should_wait:
            self._check_work_request_result(response, "update")
        return self._read_after_operation("update")

    def delete_resource(self, resource):
        """Delete the child resource and apply the configured wait settings.

        Args:
            resource: Current child resource; deletion uses the configured name.

        Returns:
            The immediate or waited SDK response.
        """
        if not self.delete_method_name:
            self.module.fail_json(
                msg="Deleting {0} is not supported.".format(self.create_resource_name)
            )
        response = self._composite_call(
            "delete",
            self.delete_method_name,
            **self.mutation_kwargs("delete")
        )
        if self._should_wait:
            self._check_work_request_result(response, "delete")
        return response
