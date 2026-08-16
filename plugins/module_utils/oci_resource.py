"""Base lifecycle helpers for OCI resource-managing modules."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from abc import ABC, abstractmethod

from ansible_collections.oracle.oci.plugins.module_utils.oci_base import (
    OciModuleBase,
    oci,
)
from ansible_collections.oracle.oci.plugins.module_utils.oci_common import (
    DEAD_STATES,
    normalize_enum_values,
    rename_aliased_fields,
    serialize_oci_model,
    values_differ_as_subset,
)


def _resource_wait_complete(module, response, target_states, failure_states, resource_id):
    state = getattr(response.data, "lifecycle_state", None)
    if state in failure_states:
        module.fail_json(
            msg=f"Resource {resource_id} entered failure state: {state}",
        )
    return state in target_states


def _work_request_wait_complete(
    module,
    response,
    target_states,
    failure_states,
    work_request_id,
):
    state = getattr(response.data, "status", None)
    if state in failure_states:
        module.fail_json(
            msg=f"Work request {work_request_id} {state}",
        )
    return state in target_states


def _target_states_include_dead_states(target_states):
    return any(state in DEAD_STATES for state in target_states)


class OciResourceBase(OciModuleBase, ABC):
    """Base class for OCI resource management modules.

    Subclasses declare OCI client metadata and the resource-specific create,
    read, update, and delete hooks. The base class handles common Ansible
    module flow such as check mode, scoped name lookup, update planning, tag
    comparison, serialization, and optional waiter integration.
    """

    client_class = None
    resource_id_param = None
    list_resource_method = None
    common_list_filter_params = ("compartment_id",)
    list_filter_params = ()
    name_lookup_param = "name"
    name_response_field = "display_name"
    create_required_fields = ()
    create_resource_name = "resource"
    enum_keys = frozenset()
    common_update_field_specs = (
        {
            "param_name": "freeform_tags",
            "resource_field": "freeform_tags",
            "update_field": "freeform_tags",
            "is_mutable": True,
        },
        {
            "param_name": "defined_tags",
            "resource_field": "defined_tags",
            "update_field": "defined_tags",
            "is_mutable": True,
        },
    )
    update_field_specs = ()
    update_method_name = None
    update_details_name = None
    update_wait_states = ()

    def __init__(self, module):
        """Initialize the shared OCI resource helper for one module invocation.

        ``module`` is the active Ansible module instance. The constructor
        creates the OCI service client, captures check mode, and prepares the
        per-resource update-plan cache used during this run.
        """
        super(OciResourceBase, self).__init__(module)
        self.check_mode = module.check_mode
        self._update_plan_cache = None

    def resolve_target_resource(self):
        """Return the current resource selected by ID or scoped name lookup.

        If the caller supplied the explicit identifier named by
        ``resource_id_param``, this method resolves that resource directly.
        Otherwise it falls back to the subclass-declared name lookup flow and
        returns ``None`` when no matching resource exists.
        """
        resource_id = self.resource_id
        if resource_id:
            return self.get_resource_by_id(resource_id)
        return self.resolve_resource_by_name()

    @abstractmethod
    def create_resource(self):
        """Create the OCI resource and return the created SDK model.

        Subclasses implement the concrete OCI create call and should return the
        final resource object, not the raw response wrapper.
        """
        pass

    def update_resource(self, resource):
        """Apply the shared update plan and return the updated resource model.

        ``resource`` is the current OCI SDK model. The base implementation uses
        subclass metadata such as ``update_method_name`` and
        ``update_details_name`` to build the update payload, call the OCI SDK,
        and optionally wait for the resource to settle before returning it.
        """
        if self.update_method_name is None:
            raise ValueError(
                f"{type(self).__name__} must define update_method_name or override update_resource()"
            )
        if self.update_details_name is None:
            raise ValueError(
                f"{type(self).__name__} must define update_details_name or override update_resource()"
            )
        if not self.update_wait_states:
            raise ValueError(
                f"{type(self).__name__} must define update_wait_states or override update_resource()"
            )

        update_plan = self.get_update_plan(resource)
        if not update_plan["update_model_fields"]:
            return resource

        update_details = self.build_update_details(update_plan["update_model_fields"])
        response = self.call_with_retry(
            getattr(self.client, self.update_method_name),
            **{
                self.resource_id_param: resource.id,
                self.update_details_name: update_details,
            },
        )
        return self.get_mutation_result(
            response.data,
            resource.id,
            self.update_wait_states,
        )

    def build_update_details(self, update_model_fields):
        """Build the OCI update-details model from planned field changes.

        ``update_model_fields`` contains only the fields that the shared update
        planner determined need to change. Subclasses return the concrete OCI
        SDK details object expected by ``update_method_name``.
        """
        raise ValueError(
            f"{type(self).__name__} must define build_update_details()"
        )

    @abstractmethod
    def delete_resource(self, resource):
        """Delete the OCI resource represented by ``resource``.

        Subclasses implement the concrete OCI delete call and may delegate to
        ``delete_resource_and_wait()`` when the standard wait flow applies.
        """
        pass

    def fail_immutable_field_change(self, field_name, reason=None):
        """Fail the module because the caller attempted an unsupported change.

        ``field_name`` identifies the requested module parameter. ``reason`` is
        appended when the subclass wants to explain why the field is immutable
        for updates of this resource type.
        """
        message = (
            f"Updating {field_name} for an existing {self.create_resource_name} "
            "is not supported"
        )
        if reason:
            message += f" because {reason}"
        message += "."
        self.module.fail_json(msg=message)

    def compare_update_field_values(self, current_value, desired_value, compare=None):
        """Return ``True`` when a planned field value differs from the resource.

        ``compare`` selects the comparison strategy. ``None`` and ``"eq"``
        perform direct inequality checks, while ``"sorted_list"`` compares the
        values as order-insensitive lists.
        """
        if compare in (None, "eq"):
            return current_value != desired_value
        if compare == "sorted_list":
            return sorted(current_value or []) != sorted(desired_value or [])
        if compare == "subset_dict":
            desired_value = normalize_enum_values(desired_value or {}, self.enum_keys)
            return values_differ_as_subset(current_value, desired_value)
        raise ValueError(f"Unsupported update comparison: {compare}")

    def execute_update_field_strategy(
        self,
        strategy,
        spec,
        resource,
        resource_dict,
        desired_value,
    ):
        """Execute a custom update strategy declared in one field spec.

        The named ``strategy`` must resolve to a method on this instance. That
        method receives the current resource context and returns zero or more
        strategy-specific operations to record in the shared update plan.
        """
        if not isinstance(strategy, str):
            raise ValueError(f"Unsupported update strategy: {strategy}")
        return getattr(self, strategy)(resource, resource_dict, spec, desired_value)

    def build_update_plan(self, resource):
        """Compute the shared update plan for a current OCI resource.

        The returned dict records whether an update is needed, which fields
        belong in the OCI update-details model, and any strategy-driven
        operations that subclasses will need to apply outside the simple field
        assignment path.
        """
        resource_dict = serialize_oci_model(resource)
        if not isinstance(resource_dict, dict):
            resource_dict = {}

        update_plan = {
            "update_needed": False,
            "update_model_fields": {},
            "strategy_operations": [],
        }
        for spec in self.get_update_field_specs():
            param_name = spec["param_name"]
            desired_value = self.module.params.get(param_name)
            if desired_value is None:
                continue

            strategy = spec.get("strategy")
            if strategy is not None:
                strategy_operations = self.execute_update_field_strategy(
                    strategy,
                    spec,
                    resource,
                    resource_dict,
                    desired_value,
                )
                if strategy_operations:
                    update_plan["update_needed"] = True
                    update_plan["strategy_operations"].append(
                        {
                            "param_name": param_name,
                            "operations": strategy_operations,
                        }
                    )
                continue

            resource_field = spec.get("resource_field", param_name)
            current_value = resource_dict.get(resource_field)
            compare_desired_value = rename_aliased_fields(
                desired_value, spec.get("desired_key_map")
            )
            if not self.compare_update_field_values(
                current_value,
                compare_desired_value,
                compare=spec.get("compare"),
            ):
                continue

            if spec.get("is_mutable") is False:
                self.fail_immutable_field_change(
                    param_name,
                    reason=spec.get("immutable_reason"),
                )

            update_plan["update_needed"] = True
            update_field = spec.get("update_field", resource_field)
            update_plan["update_model_fields"][update_field] = desired_value

        return update_plan

    def get_update_field_specs(self):
        """Return the full set of field specs used by the update planner.

        Shared specs such as tag handling are prepended to any
        subclass-provided ``update_field_specs`` entries.
        """
        return tuple(self.common_update_field_specs) + tuple(self.update_field_specs)

    def get_update_plan(self, resource):
        """Return the cached or freshly computed update plan for ``resource``.

        The cache key is the Python object identity of the current resource so
        repeated calls during one module run do not rebuild the same plan.
        """
        resource_cache_key = id(resource)
        update_plan_cache = getattr(self, "_update_plan_cache", None)
        if (
            update_plan_cache is not None
            and update_plan_cache["resource_cache_key"] == resource_cache_key
        ):
            return update_plan_cache["update_plan"]

        update_plan = self.build_update_plan(resource)
        self._update_plan_cache = {
            "resource_cache_key": resource_cache_key,
            "update_plan": update_plan,
        }
        return update_plan

    def needs_update(self, resource) -> bool:
        """Return ``True`` when the shared update planner detects drift.

        This is the base class gate for deciding whether the present-state flow
        should call ``update_resource()``.
        """
        return self.get_update_plan(resource)["update_needed"]

    @property
    def tags(self):
        """Return the desired freeform and defined tags from module inputs.

        The tuple order is ``(freeform_tags, defined_tags)``.
        """
        return (
            self.module.params.get("freeform_tags"),
            self.module.params.get("defined_tags"),
        )

    def tags_changed(self, resource) -> bool:
        """Return ``True`` when desired tags differ from the current resource.

        ``None`` tag inputs are treated as unspecified and therefore do not
        trigger drift detection.
        """
        freeform, defined = self.tags
        if freeform is not None and getattr(resource, "freeform_tags", None) != freeform:
            return True
        if defined is not None and getattr(resource, "defined_tags", None) != defined:
            return True
        return False

    def _require_create_fields(self) -> None:
        """Fail if a create request is missing required fields."""
        if not self.create_required_fields:
            return

        missing = [
            field
            for field in self.create_required_fields
            if self.module.params.get(field) is None
        ]
        if missing:
            self.module.fail_json(
                msg=(
                    f"Creating a {self.create_resource_name} requires the "
                    f"following parameters: {', '.join(missing)}"
                )
            )

    def validate_create_request(self) -> None:
        """Validate a create request before issuing the OCI create call.

        The base implementation enforces ``create_required_fields`` and
        subclasses may extend or override it with resource-specific checks.
        """
        self._require_create_fields()

    @property
    def resource_id(self):
        """Return the explicit resource identifier supplied by the caller.

        When ``resource_id_param`` is unset for a subclass, this helper returns
        ``None`` and the base class relies on name-based lookup instead.
        """
        if self.resource_id_param is None:
            return None
        return self.module.params.get(self.resource_id_param)

    @abstractmethod
    def get_resource_response(self, resource_id):
        """Return the raw OCI SDK response wrapper for ``resource_id``.

        Subclasses implement the concrete getter so wait helpers and ID-based
        lookups can reuse the same OCI response shape.
        """
        pass

    def get_resource_by_id(self, resource_id):
        """Return the current resource for ``resource_id`` or ``None`` on 404.

        Non-404 OCI errors are re-raised so the module fails with the original
        SDK exception.
        """
        try:
            return self.get_resource_response(resource_id).data
        except Exception as exc:
            if getattr(exc, "status", None) == 404:
                return None
            raise

    @property
    def supports_name_lookup(self) -> bool:
        """Return ``True`` when the subclass exposes scoped name lookup hooks.

        Name lookup requires both a list operation and the public parameter used
        to receive the desired name from the caller.
        """
        return (
            self.list_resource_method is not None
            and self.name_lookup_param is not None
        )

    @property
    def name_lookup_value(self):
        """Return the caller-supplied name used for scoped lookup.

        If the subclass disables name lookup by clearing ``name_lookup_param``,
        this helper returns ``None``.
        """
        if self.name_lookup_param is None:
            return None
        return self.module.params.get(self.name_lookup_param)

    @property
    def has_name_lookup_request(self) -> bool:
        """Return ``True`` when the caller supplied a scoped lookup name.

        This separates "lookup is supported" from "lookup was requested" so the
        present and absent flows can decide when name-based resolution applies.
        """
        return self.name_lookup_value is not None

    def find_resources_by_name(self):
        """List and locally filter resources for the caller-supplied name.

        This helper returns every matching resource because name collisions can
        be legal for some OCI resource types and must be resolved by the caller
        or by ``allow_duplicate_name`` handling.
        """
        if not self.supports_name_lookup or not self.has_name_lookup_request:
            return []
        if self.list_resource_method is None:
            return []
        self.validate_name_lookup_scope()
        resources = self.list_all_resources(
            getattr(self.client, self.list_resource_method),
            **self.collect_list_filters(
                self.common_list_filter_params,
                self.list_filter_params,
            ),
        )
        name_lookup_value = self.name_lookup_value
        return self.filter_resources_by_display_name(resources, name_lookup_value)

    def validate_name_lookup_scope(self) -> None:
        """Fail when a scoped name lookup omits required list-filter fields."""
        required_scope_params = tuple(self.common_list_filter_params) + tuple(
            self.list_filter_params
        )
        missing_scope_params = [
            param_name
            for param_name in required_scope_params
            if self.module.params.get(param_name) is None
        ]
        if not missing_scope_params:
            return

        self.module.fail_json(
            msg=(
                f"Using name lookup for {self.create_resource_name} requires the following parameters: "
                f"{', '.join(missing_scope_params)}"
            )
        )

    def fail_ambiguous_name_match(self, resources) -> None:
        """Fail the module when scoped name lookup matches multiple resources.

        ``resources`` is only used to report how many matches were found and to
        instruct the caller to disambiguate with the explicit resource ID.
        """
        name_value = self.name_lookup_value
        count = len(resources)
        self.module.fail_json(
            msg=(
                f"Multiple {self.create_resource_name} resources were found for "
                f"{self.name_lookup_param}={name_value}. Provide "
                f"{self.resource_id_param} to distinguish between {count} matches."
            )
        )

    def should_create_duplicate_name_resource(self) -> bool:
        """Return ``True`` when create flow should ignore existing name matches.

        This only applies to ``state=present`` requests that explicitly set
        ``allow_duplicate_name=True``.
        """
        return (
            self.module.params.get("state", "present") == "present"
            and self.module.params.get("allow_duplicate_name", False)
        )

    def resolve_resource_by_name(self):
        """Return a uniquely matched resource from scoped name lookup.

        The method returns ``None`` when there is no match, when duplicate-name
        creation is explicitly allowed, or after failing the module for
        ambiguous matches.
        """
        matches = self.find_resources_by_name()
        if not matches:
            return None
        if self.should_create_duplicate_name_resource():
            return None
        if len(matches) > 1:
            self.fail_ambiguous_name_match(matches)
        return matches[0]

    def wait_for_resource_id(self, resource_id, target_states, failure_states=None):
        """Wait for ``resource_id`` to reach one of ``target_states``.

        The ``wait``, ``wait_timeout``, and ``wait_interval`` settings are read
        from the module parameters. When waiting is disabled this performs one
        immediate lookup and returns its data. Otherwise it polls until the
        resource reaches ``target_states`` or fails into ``failure_states``.
        """
        wait = self.module.params.get("wait", True)
        if not wait:
            return self.get_resource_response(resource_id).data

        timeout = self.module.params.get("wait_timeout", 1200)
        interval = self.module.params.get("wait_interval", 30)

        if failure_states is None:
            failure_states = frozenset({"FAILED"})

        try:
            initial_response = self.get_resource_response(resource_id)
        except Exception as exc:
            if getattr(exc, "status", None) == 404 and _target_states_include_dead_states(target_states):
                return None
            raise

        waiter_result = oci.wait_until(
            self.client,
            initial_response,
            max_interval_seconds=interval,
            max_wait_seconds=timeout,
            succeed_on_not_found=_target_states_include_dead_states(target_states),
            evaluate_response=lambda response: _resource_wait_complete(
                self.module,
                response,
                target_states,
                failure_states,
                resource_id,
            ),
            fetch_func=lambda response=None: self.get_resource_response(resource_id),
        )
        return getattr(waiter_result, "data", None)

    def wait_for_work_request(
        self,
        work_request_client,
        work_request_id,
        get_work_request_fn=None,
        target_states=None,
        failure_states=None,
    ):
        """Wait for an OCI asynchronous work request to finish.

        ``work_request_client`` is the OCI client used to poll the work
        request. The helper polls ``get_work_request_fn`` until the work
        request enters one of ``target_states`` and returns the final OCI work
        request model. If the request enters ``failure_states``, the module
        fails immediately.
        """
        timeout = self.module.params.get("wait_timeout", 1200)
        interval = self.module.params.get("wait_interval", 30)

        if get_work_request_fn is None:
            get_work_request_fn = work_request_client.get_work_request
        if target_states is None:
            target_states = ("SUCCEEDED", "COMPLETED")
        if failure_states is None:
            failure_states = frozenset({"FAILED", "CANCELED"})

        # Work request polling is a long-running GET loop, so it is prone to
        # transient connection drops (e.g. RemoteDisconnected) from the OCI
        # API. Route it through call_with_retry rather than calling
        # get_work_request_fn directly so those drops are retried instead of
        # failing the whole task.
        initial_response = self.call_with_retry(get_work_request_fn, work_request_id)
        waiter_result = oci.wait_until(
            work_request_client,
            initial_response,
            max_interval_seconds=interval,
            max_wait_seconds=timeout,
            evaluate_response=lambda response: _work_request_wait_complete(
                self.module,
                response,
                target_states,
                failure_states,
                work_request_id,
            ),
            fetch_func=lambda response=None: self.call_with_retry(
                get_work_request_fn, work_request_id
            ),
        )
        return getattr(waiter_result, "data", None)

    def get_mutation_result(self, response_data, resource_id, target_states):
        """Return the immediate or waited result for a create/update/delete call.

        ``response_data`` is returned as-is when waiting is disabled or the
        mutation does not yield a follow-up resource identifier. Otherwise the
        helper waits for ``resource_id`` to reach ``target_states`` and returns
        the refreshed resource model.
        """
        if not self.module.params.get("wait", True):
            return response_data
        if not resource_id:
            return response_data
        return self.wait_for_resource_id(resource_id, target_states)

    def delete_resource_and_wait(self, resource, delete_fn, **delete_kwargs):
        """Delete ``resource`` and optionally wait for a dead lifecycle state.

        ``delete_fn`` is the concrete OCI delete method. A 409 response is
        translated into a clearer module failure when dependent resources block
        deletion.
        """
        try:
            response = self.call_with_retry(delete_fn, **delete_kwargs)
        except Exception as exc:
            if getattr(exc, "status", None) == 409:
                self.module.fail_json(
                    msg=(
                        f"Cannot delete {self.create_resource_name} {resource.id} while "
                        f"dependent resources exist: {exc}"
                    )
                )
            raise

        return self.get_mutation_result(
            response.data,
            resource.id,
            tuple(DEAD_STATES),
        )

    def validate_delete_request(self) -> None:
        """Validate that a delete request identifies the target resource.

        Callers must provide either the explicit resource ID or a supported
        scoped name lookup value before the absent-state flow can continue.
        """
        if (
            self.resource_id_param
            and not self.resource_id
            and not self.has_name_lookup_request
        ):
            if self.supports_name_lookup:
                scope_params = tuple(self.common_list_filter_params) + tuple(
                    self.list_filter_params
                )
                msg = (
                    f"Deleting a {self.create_resource_name} requires either "
                    f"{self.resource_id_param} or {self.name_lookup_param} "
                    f"(with {', '.join(scope_params)})"
                )
            else:
                msg = f"Deleting a {self.create_resource_name} requires {self.resource_id_param}"
            self.module.fail_json(msg=msg)

    def fail_missing_update_target(self) -> None:
        """Fail when an explicit update target ID does not resolve to a resource.

        This protects the present-state flow from silently creating a new
        resource when the caller clearly intended to update an existing one.
        """
        resource_id = self.resource_id
        if not self.resource_id_param or not resource_id:
            return

        self.module.fail_json(
            msg=(
                f"No {self.create_resource_name} was found for "
                f"{self.resource_id_param}={resource_id}. Create the "
                f"{self.create_resource_name} without {self.resource_id_param}, "
                f"then use the returned ID for future updates"
            )
        )

    def execute_resource_module(self) -> None:
        """Execute the standard present/absent lifecycle for the module.

        The base flow handles check mode, resource lookup, create/update/delete
        dispatch, and final ``exit_json`` responses. Subclasses supply the
        resource-specific OCI calls through the abstract hooks and metadata.
        """
        state = self.module.params.get("state", "present")

        if state == "absent":
            self.validate_delete_request()
            resource = self.resolve_target_resource()
            if resource is None or getattr(resource, "lifecycle_state", None) in DEAD_STATES:
                self.module.exit_json(changed=False)
            if self.check_mode:
                self.module.exit_json(changed=True)
            self.delete_resource(resource)
            self.module.exit_json(changed=True)

        # state == present
        resource = self.resolve_target_resource()
        if resource is None:
            if self.resource_id:
                self.fail_missing_update_target()
            self.validate_create_request()
            if self.check_mode:
                self.module.exit_json(changed=True)
            resource = self.create_resource()
            self.module.exit_json(
                changed=True,
                resource=self.serialize_result_resource(resource),
            )

        if self.needs_update(resource):
            if self.check_mode:
                self.module.exit_json(changed=True)
            resource = self.update_resource(resource)
            self.module.exit_json(
                changed=True,
                resource=self.serialize_result_resource(resource),
            )

        self.module.exit_json(
            changed=False,
            resource=self.serialize_result_resource(resource),
        )
