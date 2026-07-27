"""Shared client and result helpers for OCI module helper bases."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from abc import ABC

from ansible_collections.oracle.oci.plugins.module_utils.oci_auth import create_service_client
from ansible_collections.oracle.oci.plugins.module_utils.oci_common import (
    COMMON_FIELD_PARAM_ALIASES,
    build_result_field_aliases,
    collect_list_filters,
    filter_resources_by_response_field,
    omit_user_known_fields,
    serialize_oci_model,
)


class OciModuleBase(ABC):
    """Thin shared base for OCI resource and info helper classes."""

    client_class = None
    common_field_param_aliases = COMMON_FIELD_PARAM_ALIASES
    field_param_aliases = {}
    known_field_names = ()
    name_response_field = "display_name"

    def __init__(self, module):
        """Store the active module and create the configured OCI client."""
        if self.client_class is None:
            raise TypeError(
                f"{type(self).__name__} must define client_class"
            )
        self.module = module
        self.client = create_service_client(module, self.client_class)

    def build_result_field_aliases(self):
        """Return OCI-to-module field aliases for echo suppression."""
        return build_result_field_aliases(
            self.common_field_param_aliases,
            self.field_param_aliases,
            self.known_field_names,
        )

    def collect_list_filters(self, *param_groups):
        """Collect non-None list filters from the active module params."""
        return collect_list_filters(self.module.params, *param_groups)

    def filter_resources_by_display_name(self, resources, name_value):
        """Filter resources against the configured response field."""
        return filter_resources_by_response_field(
            resources,
            self.name_response_field,
            name_value,
        )

    def serialize_result_resource(self, resource):
        """Serialize one OCI resource into the module result shape."""
        resource_dict = serialize_oci_model(resource)
        if not isinstance(resource_dict, dict):
            return resource_dict

        return omit_user_known_fields(
            resource_dict,
            self.module.params,
            self.build_result_field_aliases(),
        )
