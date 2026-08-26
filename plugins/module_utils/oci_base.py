"""Shared client and result helpers for OCI module helper bases."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from abc import ABC

from ansible.module_utils.basic import missing_required_lib

from ansible_collections.ansible.oci.plugins.module_utils.oci_auth import create_service_client
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    COMMON_FIELD_PARAM_ALIASES,
    collect_list_filters,
    filter_resources_by_response_field,
    import_oci_sdk,
    rename_aliased_fields,
    serialize_oci_model,
)

oci, HAS_OCI_SDK = import_oci_sdk()


class OciModuleBase(ABC):
    """Thin shared base for OCI resource and info helper classes."""

    client_class = None
    common_field_param_aliases = COMMON_FIELD_PARAM_ALIASES
    field_param_aliases = {}
    name_response_field = "display_name"
    redacted_result_keys = ()

    def __init__(self, module):
        """Store the active module and create the configured OCI client."""
        if not HAS_OCI_SDK:
            module.fail_json(msg=missing_required_lib("oci"))
        if self.client_class is None:
            raise TypeError(
                f"{type(self).__name__} must define client_class"
            )
        self.module = module
        self.client = create_service_client(module, self.client_class)

    def list_all_resources(self, list_fn, *args, **kwargs):
        """Return every record from an OCI paginated list operation.

        ``list_fn`` is an OCI SDK list method. The caller's OCI client is
        already guaranteed to exist by the time this is called, so no
        additional SDK-presence check is needed here.
        """
        return oci.pagination.list_call_get_all_results(list_fn, *args, **kwargs).data

    def call_with_retry(self, fn, *args, max_retries=7, retry_on=(429, 500, 503), **kwargs):
        """Call an OCI SDK function with retry handling for transient failures.

        ``fn`` receives the provided positional and keyword arguments through
        the OCI retry strategy. The return value is whatever the wrapped OCI
        call returns after succeeding or exhausting the configured retry
        attempts.
        """
        retry_strategy = oci.retry.RetryStrategyBuilder(
            max_attempts_check=True,
            max_attempts=max_retries + 1,
            service_error_check=True,
            service_error_retry_config={status: [] for status in retry_on},
        ).get_retry_strategy()

        return retry_strategy.make_retrying_call(fn, *args, **kwargs)

    def build_result_field_aliases(self):
        """Return OCI-to-module field aliases used to rename result keys."""
        return dict(self.common_field_param_aliases, **self.field_param_aliases)

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
        """Serialize one OCI resource into the module result shape.

        Response fields whose OCI name differs from the module parameter the
        caller used (e.g. ``display_name`` vs ``name``) are renamed so the
        result vocabulary stays loyal to the input the caller provided.
        Keys listed on ``redacted_result_keys`` are dropped so secrets such as
        iSCSI CHAP credentials never appear in module results or logs.
        """
        resource_dict = serialize_oci_model(resource)
        resource_dict = rename_aliased_fields(
            resource_dict, self.build_result_field_aliases()
        )
        if not isinstance(resource_dict, dict) or not self.redacted_result_keys:
            return resource_dict
        return {
            key: value
            for key, value in resource_dict.items()
            if key not in self.redacted_result_keys
        }
