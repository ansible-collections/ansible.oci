"""Shared helpers for OCI load balancer resources."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from abc import abstractmethod
from collections.abc import Mapping

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    build_model,
    serialize_oci_model,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    oci,
)


def build_nested_model(
    model_class,
    fields,
    nested_models,
    list_models,
    model_builder,
    skip_none_items=(),
    convert_field=None,
):
    """Build a model with supported fields and typed nested values.

    Args:
        model_class: SDK class for the containing model.
        fields: Source fields, or None for an empty model.
        nested_models: Field names mapped to nested model names.
        list_models: Field names mapped to model names for list items.
        model_builder: Service function that builds a nested model by name.
        skip_none_items: List fields whose None items must be removed.
        convert_field: Optional service conversion for supported field values.

    Returns:
        An SDK model. Existing nested SDK objects retain their identity.
    """
    supported = model_class().swagger_types
    selected = {}
    for name, value in (fields or {}).items():
        if name not in supported or value is None:
            continue
        if name in nested_models and isinstance(value, Mapping):
            value = model_builder(nested_models[name], value)
        elif name in list_models:
            value = [
                (
                    model_builder(list_models[name], item)
                    if isinstance(item, Mapping)
                    else item
                )
                for item in value
                if item is not None or name not in skip_none_items
            ]
        if convert_field is not None:
            value = convert_field(name, value)
        selected[name] = value
    return build_model(selected, model_class)


def _merge_mappings(existing, supplied):
    """Merge supplied mappings into current resource fields.

    Args:
        existing: Current resource fields.
        supplied: Fields requested by the caller.

    Returns:
        Merged fields. Nested mappings merge and lists replace current lists.
    """
    result = dict(existing)
    for key, value in supplied.items():
        if value is None:
            continue
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = _merge_mappings(result[key], value)
        else:
            result[key] = value
    return result


def merge_load_balancer_fields(current, desired):
    """Serialize and merge load balancer fields for a partial update.

    Args:
        current: Current SDK resource or mapping.
        desired: Requested SDK model or mapping.

    Returns:
        Merged fields with omitted settings preserved.
    """
    return _merge_mappings(serialize_oci_model(current), serialize_oci_model(desired))


class OciLoadBalancerSubresourceBase(OciResourceBase):
    """Share child lookup and lifecycle flow across LB services."""

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
    def resource_name(self):
        """Return the configured child name.

        Returns:
            The required child name.
        """
        return self.module.params["name"]

    def resolve_target_resource(self):
        """Find the named child resource.

        Returns:
            The child resource, or None when the resource is absent.
        """
        return self.get_resource_by_id(self.resource_name)

    @staticmethod
    @abstractmethod
    def build_resource_model(model_name, fields):
        """Build a service model from fields.

        Args:
            model_name: SDK model name.
            fields: Source fields.

        Returns:
            The typed SDK model.
        """
        pass

    @abstractmethod
    def invoke_resource_operation(self, operation, method_name, **kwargs):
        """Invoke a service mutation.

        Args:
            operation: Lifecycle operation name.
            method_name: SDK operation name.
            **kwargs: SDK operation arguments.

        Returns:
            The SDK response.
        """
        pass

    @abstractmethod
    def mutation_kwargs(self, operation):
        """Return the identifiers required by a service mutation.

        Args:
            operation: Create, update, or delete operation.

        Returns:
            SDK arguments that identify the parent and child resources.
        """
        pass

    def build_update_details(self, update_model_fields, resource=None):
        """Build update details and preserve omitted current fields.

        Args:
            update_model_fields: Planned update values.
            resource: Current child model.

        Returns:
            The typed update model.
        """
        fields = update_model_fields
        if resource is not None:
            fields = merge_load_balancer_fields(resource, fields)
        return self.build_resource_model(self.update_model_name, fields)

    @property
    def _should_wait(self) -> bool:
        """Return the configured wait setting.

        Returns:
            True when the module should wait for completion.
        """
        return self.module.params.get("wait", True)

    def _read_after_operation(self, operation):
        """Read the child after create or update.

        Args:
            operation: Lifecycle operation name.

        Returns:
            The child model, or a name mapping when waiting is disabled.
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
        """Create the child and return its current representation.

        Returns:
            The child model, or a name mapping when waiting is disabled.
        """
        if not (
            self.create_model_name
            and self.create_method_name
            and self.create_details_name
        ):
            self.module.fail_json(
                msg="Creating {0} is not supported.".format(self.create_resource_name)
            )
        kwargs = self.mutation_kwargs("create")
        kwargs[self.create_details_name] = self.build_resource_model(
            self.create_model_name, self.module.params
        )
        self.invoke_resource_operation("create", self.create_method_name, **kwargs)
        return self._read_after_operation("create")

    def update_resource(self, resource):
        """Update the child and return its current representation.

        Args:
            resource: Current child model.

        Returns:
            The current or updated child model.
        """
        if not self.update_method_name or not self.update_details_name:
            self.module.fail_json(
                msg="Updating {0} is not supported.".format(self.create_resource_name)
            )
        fields = self.get_update_plan(resource)["update_model_fields"]
        if not fields:
            return resource
        kwargs = self.mutation_kwargs("update")
        kwargs[self.update_details_name] = self.build_update_details(fields, resource)
        self.invoke_resource_operation("update", self.update_method_name, **kwargs)
        return self._read_after_operation("update")

    def delete_resource(self, resource):
        """Delete the child and return the SDK response.

        Args:
            resource: Current child model.

        Returns:
            The SDK response from the delete operation.
        """
        if not self.delete_method_name:
            self.module.fail_json(
                msg="Deleting {0} is not supported.".format(self.create_resource_name)
            )
        return self.invoke_resource_operation(
            "delete", self.delete_method_name, **self.mutation_kwargs("delete")
        )


class OciLoadBalancerInfoBase(OciInfoBase):
    """Add parent identifiers to scoped info requests for either LB service."""

    get_scope_params = ()

    def get_resource_by_id(self, resource_id, get_fn, **kwargs):
        """Get a resource with the configured parent identifiers.

        Args:
            resource_id: Resource name or OCID.
            get_fn: SDK getter.
            **kwargs: Explicit getter arguments, which take precedence.

        Returns:
            A list with the resource, or an empty list when it is absent.
        """
        for name in self.get_scope_params:
            value = self.module.params.get(name)
            if value is not None:
                kwargs.setdefault(name, value)
        return super(OciLoadBalancerInfoBase, self).get_resource_by_id(
            resource_id, get_fn, **kwargs
        )

    def fetch_resources(self):
        """Read scoped resources and return an empty list for missing resources.

        Returns:
            Matching SDK resources.

        Raises:
            oci.exceptions.ServiceError: If a request fails with a status other than 404.
        """
        try:
            return super(OciLoadBalancerInfoBase, self).fetch_resources()
        except oci.exceptions.ServiceError as exc:
            if exc.status == 404:
                return []
            raise
