"""Shared argument specs, constants, and serializers for OCI helpers."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible.module_utils.common.parameters import env_fallback

OCI_AUTH_ARGS = dict(
    config_file_location=dict(
        type="str",
        default="~/.oci/config",
        fallback=(env_fallback, ["OCI_CONFIG_FILE"]),
    ),
    config_profile_name=dict(
        type="str",
        default="DEFAULT",
        fallback=(env_fallback, ["OCI_CONFIG_PROFILE"]),
    ),
    auth_type=dict(
        type="str",
        default="api_key",
        choices=["api_key", "instance_principal", "resource_principal", "session_token"],
        fallback=(env_fallback, ["OCI_AUTH_TYPE"]),
    ),
    tenancy=dict(type="str", fallback=(env_fallback, ["OCI_TENANCY_ID"])),
    region=dict(type="str", fallback=(env_fallback, ["OCI_REGION"])),
    api_user=dict(type="str", fallback=(env_fallback, ["OCI_USER_ID"])),
    api_user_fingerprint=dict(
        type="str",
        no_log=True,
        fallback=(env_fallback, ["OCI_USER_FINGERPRINT"]),
    ),
    api_user_key_file=dict(type="str", fallback=(env_fallback, ["OCI_USER_KEY_FILE"])),
    api_user_key_pass_phrase=dict(
        type="str",
        no_log=True,
        fallback=(env_fallback, ["OCI_USER_KEY_PASS_PHRASE"]),
    ),
)

OCI_WAIT_ARGS = dict(
    wait=dict(type="bool", default=True),
    wait_timeout=dict(type="int", default=1200),
    wait_interval=dict(type="int", default=30),
)

OCI_TAG_ARGS = dict(
    freeform_tags=dict(type="dict"),
    defined_tags=dict(type="dict"),
)

OCI_NAME_LOOKUP_ARGS = dict(
    name=dict(type="str"),
    compartment_id=dict(type="str"),
    allow_duplicate_name=dict(type="bool", default=False),
)

COMMON_FIELD_PARAM_ALIASES = {
    "display_name": "name",
}

OCI_COMMON_ARGS = dict(
    OCI_AUTH_ARGS,
    **OCI_WAIT_ARGS,
    **OCI_TAG_ARGS,
    **OCI_NAME_LOOKUP_ARGS,
)


def import_oci_sdk():
    """Import the OCI SDK fresh and report whether it is installed.

    This is a function rather than a bare module-level import so that every
    caller re-checks ``sys.modules`` at call time instead of reading a name
    cached once at import time. Tests rely on this: they fake
    ``sys.modules["oci"]`` and reload only the module under test, and that
    module's own call to this helper still needs to observe the fake.
    """
    try:
        import oci
        return oci, True
    except ImportError:
        return None, False


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


def serialize_oci_model(resource):
    """Recursively convert an OCI SDK model into Python container types.

    ``resource`` may be an OCI model instance, a dict, a list, or a primitive
    value. The return value mirrors the input structure but contains only plain
    dictionaries, lists, and scalar values, with ``None`` normalized to ``{}``
    at the top level for missing resources.
    """
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
            return serialize_oci_model(value)
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


def collect_list_filters(module_params, *param_groups):
    """Collect non-None list filter parameters from module inputs."""
    list_filters = {}
    for param_group in param_groups:
        for param_name in param_group:
            param_value = module_params.get(param_name)
            if param_value is not None:
                list_filters[param_name] = param_value
    return list_filters


def filter_resources_by_response_field(resources, response_field, expected_value):
    """Return only resources whose response field matches ``expected_value``."""
    if expected_value is None:
        return resources
    return [
        resource
        for resource in resources
        if getattr(resource, response_field, None) == expected_value
    ]


def rename_aliased_fields(resource_dict, field_aliases):
    """Rename response fields to their caller-facing parameter names.

    ``field_aliases`` maps ``resource_field_name -> module_param_name``. Keys
    present in the mapping are renamed to the aliased name; every other key is
    returned unchanged, so module output vocabulary stays loyal to the
    parameter names callers actually used (e.g. ``display_name`` -> ``name``).
    """
    return {
        field_aliases.get(field_name, field_name): value
        for field_name, value in resource_dict.items()
    }


def filter_none_values(data):
    """Return a shallow copy without keys whose values are ``None``.

    This helper keeps the original dictionary unchanged and only filters the
    first level of keys.
    """
    return {
        key: value for key, value in data.items() if value is not None
    }


def normalize_enum_values(value, enum_keys):
    """Recursively upper-case string values under known OCI enum keys.

    Module inputs commonly use lowercase snake_case choices (Ansible
    convention), while OCI's wire format and returned resources use
    upper-case constants (for example ``RECOVERY_ACTION_STOP_INSTANCE`` ->
    ``"STOP_INSTANCE"``). ``enum_keys`` names the dict keys whose string
    values should be upper-cased; this recurses into nested dicts and lists
    so it can be used directly on a suboption dict (for example
    ``platform_config``) or a list of them (for example
    ``agent_config.plugins_config``).
    """
    if isinstance(value, dict):
        return {
            key: (
                item.upper()
                if key in enum_keys and isinstance(item, str)
                else normalize_enum_values(item, enum_keys)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [normalize_enum_values(item, enum_keys) for item in value]
    return value


def strip_none_values(value):
    """Recursively remove ``None`` entries from nested dicts and lists.

    Unlike ``filter_none_values`` (which only strips the first level),
    this descends into nested dicts and lists. Ansible fills every
    declared suboption of a dict or list-of-dicts type with ``None`` when
    the caller only sets some of them, so this is needed to compare
    caller-supplied values against a fully-populated API response without
    those placeholders causing spurious differences.
    """
    if isinstance(value, dict):
        return {
            key: strip_none_values(item)
            for key, item in value.items()
            if item is not None
        }
    if isinstance(value, list):
        return [strip_none_values(item) for item in value]
    return value


def values_differ_as_subset(current_value, desired_value):
    """Return ``True`` when ``desired_value``'s populated fields differ.

    OCI often echoes back fully populated nested objects that include
    fields the caller never set, so a plain equality check would always
    report drift. This recurses into nested dicts, comparing only the keys
    the caller actually supplied (after dropping ``None`` placeholders, see
    ``strip_none_values``) at every nesting level. Nested lists are compared
    as a whole after stripping ``None`` placeholders from their elements,
    since matching list entries individually (for example by name) isn't
    supported.
    """
    if isinstance(desired_value, dict):
        current_value = current_value or {}
        desired_value = {
            key: item for key, item in desired_value.items() if item is not None
        }
        return any(
            values_differ_as_subset(current_value.get(key), item)
            for key, item in desired_value.items()
        )
    if isinstance(desired_value, list):
        return strip_none_values(current_value or []) != strip_none_values(desired_value)
    return current_value != desired_value
