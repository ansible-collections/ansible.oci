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
_TLS_PROTOCOL_VALUES = {
    "tlsv1": "TLSv1",
    "tlsv1.1": "TLSv1.1",
    "tlsv1.2": "TLSv1.2",
    "tlsv1.3": "TLSv1.3",
}


def normalize_load_balancer_fields(fields):
    """Normalize known caller-facing enums to the casing expected by OCI.

    Args:
        fields: Load Balancer input or serialized field mapping.

    Returns:
        A recursively normalized copy, with unrelated string values preserved.
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

    return _normalize_tls_protocols(normalized)


def _normalize_tls_protocols(value):
    """Convert known TLS protocol names to OCI spelling.

    Args:
        value: A mapping, list, tuple, or scalar value.

    Returns:
        A copied value with known TLS protocol names converted.
    """
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            if key == "protocols" and isinstance(item, (list, tuple)):
                item = [
                    _TLS_PROTOCOL_VALUES.get(protocol, protocol)
                    if isinstance(protocol, str)
                    else protocol
                    for protocol in item
                ]
            else:
                item = _normalize_tls_protocols(item)
            result[key] = item
        return result
    if isinstance(value, list):
        return [_normalize_tls_protocols(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_normalize_tls_protocols(item) for item in value)
    return value


def _normalize_routing_rule(rule):
    """Normalize action names in one routing rule.

    Args:
        rule: A routing rule mapping.

    Returns:
        A copied rule with supported action names in OCI casing.
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
    """Convert a supported field to its nested SDK model types.

    Args:
        model_name: Name of the containing SDK model class.
        field_name: Name of the supported field.
        value: Field value to convert.

    Returns:
        The converted value, or the original value when no conversion applies.
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
    """Build one SDK model and its supported nested model fields.

    Args:
        model_name: OCI SDK model class name.
        fields: Caller-facing model values.

    Returns:
        The typed OCI SDK model. Unsupported fields and ``None`` values are skipped.
        Create routing policies use condition language V1 when the field is absent.
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
    """Build a typed Load Balancer SDK model from caller or serialized fields.

    The SDK models do not expose a public recursive ``from_dict`` converter,
    so construct the small set of nested Load Balancer model fields explicitly.
    Unknown fields are ignored to keep Ansible-only options out of SDK calls.

    Args:
        model_name: OCI SDK model class name.
        fields: Caller-facing fields used to populate that model.

    Returns:
        An instance of the requested OCI SDK model.
    """
    return _build_model(model_name, normalize_load_balancer_fields(fields))


def merge_load_balancer_fields(current, desired):
    """Merge supplied fields into a current child-resource snapshot.

    Nested dictionaries merge recursively, ``None`` values are omitted, and
    lists replace the current list exactly. This preserves SDK-required fields
    when OCI update models represent a full child-resource configuration.
    """
    current = serialize_oci_model(current)
    desired = serialize_oci_model(desired)

    def merge(existing, supplied):
        if not isinstance(existing, Mapping):
            existing = {}
        if not isinstance(supplied, Mapping):
            return dict(existing)

        result = dict(existing)
        for key, value in supplied.items():
            if value is None:
                continue
            if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
                result[key] = merge(result[key], value)
            else:
                result[key] = value
        return result

    return merge(current, desired)


class OciLoadBalancerSubresourceBase(OciResourceBase):
    """Common create, update, and delete behavior for Load Balancer children."""

    @property
    def client_class(self):
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
        return ()

    @property
    def resource_name(self):
        return self.module.params.get("name")

    def resolve_target_resource(self):
        """Resolve a child by its resource name under the selected load balancer."""
        if self.resource_name is None:
            return None
        return self.get_resource_by_id(self.resource_name)

    def plan_enum_update(self, resource, resource_dict, spec, desired_value):
        """Translate an enum update before comparing with OCI's uppercase value.

        Args:
            resource: Current OCI resource model.
            resource_dict: Serialized resource fields.
            spec: Update field specification declaring the module and OCI fields.
            desired_value: Caller-facing enum choice.

        Returns:
            A strategy operation when the normalized value differs, otherwise an
            empty list. The base planner cannot translate enum casing itself.
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
        """Fold strategy operations into the child update-details fields.

        Args:
            resource: Current OCI resource model.

        Returns:
            The shared plan with enum strategy operations added to its model
            fields, because the base planner stores custom operations separately.
        """
        update_plan = super(OciLoadBalancerSubresourceBase, self).build_update_plan(
            resource
        )
        for strategy_plan in update_plan["strategy_operations"]:
            for operation in strategy_plan["operations"]:
                update_plan["update_model_fields"].update(operation)
        return update_plan

    def compare_update_field_values(self, current_value, desired_value, compare=None):
        """Compare nested input enums in OCI response casing for subset updates.

        OCI returns enum fields uppercase, while module choices commonly arrive
        lowercase, so normalize those known fields before the shared comparison.

        Args:
            current_value: The field value returned by OCI.
            desired_value: The caller's requested field value.
            compare: Shared comparison strategy name.

        Returns:
            Whether the current and desired values differ.
        """
        if compare == "subset_dict":
            desired_value = normalize_load_balancer_fields(desired_value or {})
        return super(OciLoadBalancerSubresourceBase, self).compare_update_field_values(
            current_value, desired_value, compare=compare
        )

    def mutation_kwargs(self, operation):
        """Return the parent-resource arguments shared by child API calls."""
        return {"load_balancer_id": self.module.params.get("load_balancer_id")}

    def _is_waiting(self):
        return self.module.params.get("wait", True)

    def _work_request_id(self, response):
        data = getattr(response, "data", response)
        return (
            getattr(data, "id", None)
            or (getattr(response, "headers", None) or {}).get("opc-work-request-id")
        )

    def _work_request_failure_message(self, response):
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
        """Fail promptly when a waited-on composite operation did not succeed."""
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
        """Call an SDK composite operation with the shared wait policy."""
        composite = oci.load_balancer.LoadBalancerClientCompositeOperations(
            self.client
        )
        waiting = self._is_waiting()
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
        """Read the updated child, allowing an immediate ID/name-only result."""
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
        if self._is_waiting():
            self.module.fail_json(
                msg=(
                    "OCI finished {0} {1}, but the child resource {2} could not "
                    "be retrieved."
                ).format(operation, self.create_resource_name, self.resource_name)
            )
        return {self.name_response_field: self.resource_name}

    def create_resource(self):
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
        if self._is_waiting():
            self._check_work_request_result(response, "create")
        return self._read_after_operation("create")

    def build_update_details(self, update_model_fields, resource=None):
        fields = update_model_fields
        if resource is not None:
            fields = merge_load_balancer_fields(resource, update_model_fields)
        return build_load_balancer_model(self.update_model_name, fields)

    def update_resource(self, resource):
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
        if self._is_waiting():
            self._check_work_request_result(response, "update")
        return self._read_after_operation("update")

    def delete_resource(self, resource):
        if not self.delete_method_name:
            self.module.fail_json(
                msg="Deleting {0} is not supported.".format(self.create_resource_name)
            )
        response = self._composite_call(
            "delete",
            self.delete_method_name,
            **self.mutation_kwargs("delete")
        )
        if self._is_waiting():
            self._check_work_request_result(response, "delete")
        return response
