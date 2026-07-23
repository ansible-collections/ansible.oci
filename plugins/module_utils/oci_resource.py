"""Base resource helper for OCI Ansible modules."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from abc import ABC, abstractmethod

DOCUMENTATION = r"""
---
module_utils: oci_resource
short_description: Base class for OCI resource management modules
description:
 - Provides OciResourceBase, an abstract base class that implements the
 standard create/update/delete lifecycle for OCI resources with built-in
 check mode support, tag comparison, and change detection.
 - Subclasses override get_resource, create_resource, update_resource, and
 delete_resource to manage specific OCI resource types.
author:
 - Steve Fulmer (@stevefulme1)
 - Ron Gershburg (@ronger4)
"""

from ansible_collections.oracle.oci.plugins.module_utils.oci_auth import create_service_client
from ansible_collections.oracle.oci.plugins.module_utils.oci_common import (
    DEAD_STATES,
    omit_user_known_fields,
    to_dict as serialize_resource_dict,
)


class OciResourceBase(ABC):
    """Base class for OCI resource management modules.

    Subclasses must implement:
        - client_class: the OCI SDK client class
        - get_resource(): retrieve current resource state
        - create_resource(): create a new resource
        - update_resource(): update an existing resource
        - delete_resource(): delete a resource
    """

    client_class = None
    resource_id_param = None
    create_required_fields = ()
    create_resource_name = "resource"

    def __init__(self, module):
        if self.client_class is None:
            raise TypeError(
                f"{type(self).__name__} must define client_class"
            )
        self.module = module
        self.client = create_service_client(module, self.client_class)
        self.check_mode = module.check_mode

    @abstractmethod
    def get_resource(self):
        """Return the current resource or None if not found."""
        pass

    @abstractmethod
    def create_resource(self):
        """Create the resource and return it."""
        pass

    @abstractmethod
    def update_resource(self, resource):
        """Update the resource and return it."""
        pass

    @abstractmethod
    def delete_resource(self, resource):
        """Delete the resource."""
        pass

    def user_known_fields(self):
        """Return resource fields that should be omitted when they match inputs."""
        return ()

    def to_dict(self, resource) -> dict:
        """Convert an OCI SDK resource object to a serializable dict."""
        resource_dict = serialize_resource_dict(resource)
        if not isinstance(resource_dict, dict):
            return resource_dict

        return omit_user_known_fields(
            resource_dict,
            self.module.params,
            self.user_known_fields(),
        )

    def needs_update(self, resource) -> bool:
        """Check if resource attributes differ from desired state."""
        for key in self._updatable_attributes():
            desired = self.module.params.get(key)
            if desired is None:
                continue
            current = getattr(resource, key, None)
            if current != desired:
                return True
        return False

    def _updatable_attributes(self):
        """Return list of attribute names that can be updated."""
        return []

    def get_tags(self):
        """Return (freeform_tags, defined_tags) from module params."""
        return (
            self.module.params.get("freeform_tags"),
            self.module.params.get("defined_tags"),
        )

    def tags_changed(self, resource) -> bool:
        """Check if tags differ from current resource."""
        freeform, defined = self.get_tags()
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
        """Allow subclasses to validate create requests before creation."""
        self._require_create_fields()

    def get_resource_id(self):
        """Return the explicit resource identifier supplied by the caller."""
        if self.resource_id_param is None:
            return None
        return self.module.params.get(self.resource_id_param)

    def validate_delete_request(self) -> None:
        """Fail if a delete request omits the resource identifier."""
        if self.resource_id_param and not self.get_resource_id():
            self.module.fail_json(
                msg=f"Deleting a {self.create_resource_name} requires {self.resource_id_param}"
            )

    def fail_missing_update_target(self) -> None:
        """Fail when an explicit resource identifier does not resolve."""
        resource_id = self.get_resource_id()
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

    def run(self) -> None:
        """Main entry point — determine action and execute."""
        state = self.module.params.get("state", "present")

        if state == "absent":
            self.validate_delete_request()
            resource = self.get_resource()
            if resource is None or getattr(resource, "lifecycle_state", None) in DEAD_STATES:
                self.module.exit_json(changed=False)
                return
            if self.check_mode:
                self.module.exit_json(changed=True)
                return
            self.delete_resource(resource)
            self.module.exit_json(changed=True)
            return

        # state == present
        resource = self.get_resource()
        if resource is None:
            if self.get_resource_id():
                self.fail_missing_update_target()
            self.validate_create_request()
            if self.check_mode:
                self.module.exit_json(changed=True)
                return
            resource = self.create_resource()
            self.module.exit_json(changed=True, resource=self.to_dict(resource))
            return

        if self.needs_update(resource) or self.tags_changed(resource):
            if self.check_mode:
                self.module.exit_json(changed=True)
                return
            resource = self.update_resource(resource)
            self.module.exit_json(changed=True, resource=self.to_dict(resource))
            return

        self.module.exit_json(changed=False, resource=self.to_dict(resource))
