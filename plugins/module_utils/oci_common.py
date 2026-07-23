"""Common OCI argument specs and constants used across all modules."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module_utils: oci_common
short_description: Shared OCI argument specs and lifecycle constants
description:
 - Defines OCI_COMMON_ARGS, the common argument spec shared by all OCI modules,
 covering authentication, region, wait behavior, and tagging parameters.
 - Provides lifecycle state constants and frozen sets (WAIT_STATES, READY_STATES,
 DEAD_STATES) used for resource state management and polling.
author:
 - Steve Fulmer (@stevefulme1)
 - Ron Gershburg (@ronger4)
"""

OCI_COMMON_ARGS = dict(
    config_file_location=dict(type="str"),
    config_profile_name=dict(type="str"),
    auth_type=dict(
        type="str",
        choices=["api_key", "instance_principal", "resource_principal", "session_token"],
    ),
    tenancy=dict(type="str"),
    region=dict(type="str"),
    api_user=dict(type="str"),
    api_user_fingerprint=dict(type="str", no_log=True),
    api_user_key_file=dict(type="str"),
    api_user_key_pass_phrase=dict(type="str", no_log=True),
    wait=dict(type="bool", default=True),
    wait_timeout=dict(type="int", default=1200),
    wait_interval=dict(type="int", default=30),
    freeform_tags=dict(type="dict"),
    defined_tags=dict(type="dict"),
)

OCI_SDK_REQUIRED_MSG = "The 'oci' Python SDK is required."

LIFECYCLE_ACTIVE = "ACTIVE"
LIFECYCLE_AVAILABLE = "AVAILABLE"
LIFECYCLE_RUNNING = "RUNNING"
LIFECYCLE_PROVISIONING = "PROVISIONING"
LIFECYCLE_CREATING = "CREATING"
LIFECYCLE_DELETED = "DELETED"
LIFECYCLE_DELETING = "DELETING"
LIFECYCLE_TERMINATED = "TERMINATED"
LIFECYCLE_TERMINATING = "TERMINATING"
LIFECYCLE_FAILED = "FAILED"
LIFECYCLE_STOPPED = "STOPPED"

WAIT_STATES = frozenset({
    LIFECYCLE_PROVISIONING,
    LIFECYCLE_CREATING,
    LIFECYCLE_DELETING,
    LIFECYCLE_TERMINATING,
})

READY_STATES = frozenset({
    LIFECYCLE_ACTIVE,
    LIFECYCLE_AVAILABLE,
    LIFECYCLE_RUNNING,
})

DEAD_STATES = frozenset({
    LIFECYCLE_DELETED,
    LIFECYCLE_TERMINATED,
})


def to_dict(resource):
    """Convert an OCI resource object to a plain dictionary."""
    def _serialize_value(value):
        if value is None:
            return None
        if isinstance(value, list):
            return [_serialize_value(item) for item in value]
        if isinstance(value, dict):
            return {
                key: _serialize_value(item_value)
                for key, item_value in value.items()
            }
        if hasattr(value, "__dict__") or getattr(value, "swagger_types", None):
            return to_dict(value)
        return value

    if resource is None:
        return {}
    swagger_types = getattr(resource, "swagger_types", None)
    if swagger_types:
        return {
            key: _serialize_value(getattr(resource, key, None))
            for key in swagger_types
        }
    if isinstance(resource, dict):
        return {
            key: _serialize_value(value)
            for key, value in resource.items()
        }
    if isinstance(resource, list):
        return [_serialize_value(item) for item in resource]
    if hasattr(resource, "__dict__"):
        result = {}
        for key, value in resource.__dict__.items():
            if key.startswith("_") or key in ("swagger_types", "attribute_map"):
                continue
            result[key] = _serialize_value(value)
        return result
    return resource


def omit_user_known_fields(resource_dict, module_params, field_names):
    """Drop result fields whose values exactly match caller-supplied inputs."""
    filtered_resource_dict = dict(resource_dict)

    for field_name in field_names:
        if filtered_resource_dict.get(field_name) == module_params.get(field_name):
            filtered_resource_dict.pop(field_name, None)

    return filtered_resource_dict


def filter_none_values(data):
    """Return a shallow copy without keys whose values are None."""
    return {
        key: value for key, value in data.items() if value is not None
    }
