"""Base info helper for OCI Ansible modules."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from abc import ABC

DOCUMENTATION = r"""
---
module_utils: oci_info
short_description: Base class for OCI info and list modules
description:
 - Provides OciInfoBase, a separate abstraction for info and list modules.
 - Centers list-oriented modules on OCI client calls, shared pagination, and
 serialized OCI-shaped result data without state-driven CRUD orchestration.
author:
 - Steve Fulmer (@stevefulme1)
 - Ron Gershburg (@ronger4)
"""

from ansible_collections.oracle.oci.plugins.module_utils.oci_auth import create_service_client
from ansible_collections.oracle.oci.plugins.module_utils.oci_common import (
    omit_user_known_fields,
    to_dict as serialize_resource_dict,
)
from ansible_collections.oracle.oci.plugins.module_utils.oci_wait import (
    call_with_retry,
    list_all_resources as paginate_all_resources,
)


class OciInfoBase(ABC):
    """Base class for OCI info and list modules."""

    client_class = None
    results_key = "resources"
    resource_id_param = None
    resource_id_kwarg = None
    resource_get_method = None
    list_resource_method = None
    list_filter_params = ()
    known_field_names = ()

    def __init__(self, module):
        if self.client_class is None:
            raise TypeError(
                f"{type(self).__name__} must define client_class"
            )
        self.module = module
        self.client = create_service_client(module, self.client_class)

    def list_resources(self):
        """Return resources via class-declared get/list metadata."""
        resource_id = (
            self.module.params.get(self.resource_id_param)
            if self.resource_id_param
            else None
        )
        if resource_id:
            if self.resource_get_method is None:
                raise NotImplementedError(
                    f"{type(self).__name__} must define list_resources() or class metadata"
                )
            resource_id_kwarg = self.resource_id_kwarg or self.resource_id_param
            return self.get_resource_by_id(
                resource_id,
                getattr(self.client, self.resource_get_method),
                **{resource_id_kwarg: resource_id},
            )

        if self.list_resource_method is None:
            raise NotImplementedError(
                f"{type(self).__name__} must define list_resources() or class metadata"
            )
        return self.paginate(
            getattr(self.client, self.list_resource_method),
            **self.build_list_kwargs(),
        )

    def user_known_fields(self):
        """Return result fields that should be omitted when they match inputs."""
        return self.known_field_names

    def paginate(self, list_fn, *args, **kwargs):
        """Return all records from a paginated OCI list operation."""
        return paginate_all_resources(list_fn, *args, **kwargs)

    def build_list_kwargs(self):
        """Return non-empty list filter parameters from module params."""
        return {
            param_name: self.module.params.get(param_name)
            for param_name in self.list_filter_params
            if self.module.params.get(param_name) is not None
        }

    def get_resource_by_id(self, resource_id, get_fn, **kwargs):
        """Return a single OCI resource as a one-item list or [] on 404."""
        if not resource_id:
            return None

        try:
            response = call_with_retry(get_fn, **kwargs)
            return [response.data]
        except Exception as exc:
            if getattr(exc, "status", None) == 404:
                return []
            raise

    def serialize_resource(self, resource):
        """Convert a resource to an OCI-shaped result payload."""
        resource_dict = serialize_resource_dict(resource)
        if not isinstance(resource_dict, dict):
            return resource_dict

        return omit_user_known_fields(
            resource_dict,
            self.module.params,
            self.user_known_fields(),
        )

    def run(self):
        """List resources and exit with OCI-shaped info data."""
        resources = self.list_resources()
        serialized_resources = [
            self.serialize_resource(resource) for resource in resources
        ]
        self.module.exit_json(
            changed=False,
            **{self.results_key: serialized_resources},
        )
