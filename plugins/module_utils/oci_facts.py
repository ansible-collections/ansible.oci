"""Base facts helper for OCI Ansible modules."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from abc import ABC, abstractmethod

DOCUMENTATION = r"""
---
module_utils: oci_facts
short_description: Base class for OCI facts and list modules
description:
 - Provides OciFactsBase, a separate abstraction for facts and list modules.
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
    list_all_resources as paginate_all_resources,
)


class OciFactsBase(ABC):
    """Base class for OCI facts and list modules."""

    client_class = None
    results_key = "resources"

    def __init__(self, module):
        if self.client_class is None:
            raise TypeError(
                f"{type(self).__name__} must define client_class"
            )
        self.module = module
        self.client = create_service_client(module, self.client_class)

    @abstractmethod
    def list_resources(self):
        """Return a list of OCI SDK resource objects."""
        pass

    def user_known_fields(self):
        """Return result fields that should be omitted when they match inputs."""
        return ()

    def paginate(self, list_fn, *args, **kwargs):
        """Return all records from a paginated OCI list operation."""
        return paginate_all_resources(list_fn, *args, **kwargs)

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
        """List resources and exit with OCI-shaped facts data."""
        resources = self.list_resources()
        serialized_resources = [
            self.serialize_resource(resource) for resource in resources
        ]
        self.module.exit_json(
            changed=False,
            **{self.results_key: serialized_resources},
        )
