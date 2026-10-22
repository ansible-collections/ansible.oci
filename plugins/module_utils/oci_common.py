"""Shared argument specs, constants, and serializers for OCI helpers."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor

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


def threaded_map(function, items, max_workers=50):
    """Apply a function concurrently and wait for all submitted work.

    Worker errors propagate after all submitted tasks finish.

    Args:
        function: Callable accepting one item.
        items: Iterable of work items.
        max_workers: Maximum number of concurrent workers.

    Returns:
        Results in input order, or an empty list for empty input.
    """
    items = list(items)
    if not items:
        return []
    with ThreadPoolExecutor(max_workers=min(max_workers, len(items))) as executor:
        futures = [executor.submit(function, item) for item in items]
        return [future.result() for future in futures]


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


def merge_mappings(existing, supplied):
    """Merge supplied mappings without modifying either input.

    Ignore supplied None values. Preserve explicit False, zero, and empty values.

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
            result[key] = merge_mappings(result[key], value)
        else:
            result[key] = value
    return result


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
    """Return a shallow copy of ``resource_dict`` with keys renamed via
    ``field_aliases``.

    This is used in both directions: renaming OCI response fields to their
    caller-facing parameter names (e.g. ``display_name`` -> ``name``, so
    module output vocabulary stays loyal to the parameter names callers
    actually used), and renaming a caller-facing parameter's keys to the
    names a downstream consumer actually uses (e.g. Ansible's
    ``all_plugins_disabled`` -> OCI's ``are_all_plugins_disabled``, before
    building an SDK model or comparing against a resource). Keys absent from
    ``field_aliases`` are left unchanged. A falsy ``field_aliases`` or a
    non-dict ``resource_dict`` is returned unchanged, so callers can pass
    optional, not-always-present mappings without guarding first.
    """
    if not field_aliases or not isinstance(resource_dict, dict):
        return resource_dict
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


def build_model(source, model_class, keys=None, enum_keys=None):
    """Build an OCI ``model_class`` from the mapping ``source``.

    Collapses the shared model-builder boilerplate used across modules: skip when
    the input mapping is unset, select the fields to carry over, upper-case any
    enum values, drop the ones the caller left unset, and instantiate the model.

    Args:
        source: The module-input mapping, or None.
        model_class: The SDK model class to instantiate.
        keys: The ``source`` keys to copy onto the model; unset keys are dropped.
            When None, every key of ``source`` is used.
        enum_keys: When given, passed to ``normalize_enum_values`` to upper-case
            the string values under these keys before the model is built.

    Returns:
        A ``model_class`` instance, or None when ``source`` is None.
    """
    if source is None:
        return None
    selected = source if keys is None else {key: source.get(key) for key in keys}
    if enum_keys is not None:
        selected = normalize_enum_values(selected, enum_keys)
    return model_class(**filter_none_values(selected))


def choice_values(value_map):
    """Return lowercase choices and legacy spellings for the transition."""
    return list(dict.fromkeys(list(value_map) + list(value_map.values())))


def _choice_containers(params, path):
    """Return dictionaries that contain the selected choice field."""
    containers = [params]
    for key in path[:-1]:
        children = []
        for container in containers:
            value = container.get(key)
            if isinstance(value, dict):
                children.append(value)
            elif isinstance(value, list):
                children.extend(value)
        containers = children
    return containers


def normalize_choice_parameters(module, choice_maps):
    """Warn about legacy choices and convert selected parameters to OCI values.

    Each tuple in choice_maps identifies a parameter path.
    Lists of dictionaries can occur along that path.
    Each mapping contains lowercase choices and their exact OCI values.
    Call this function once after Ansible validates the arguments.
    """
    for path, value_map in choice_maps.items():
        legacy_values = {
            value: name for name, value in value_map.items() if name != value
        }
        warned_values = set()

        key = path[-1]
        for container in _choice_containers(module.params, path):
            value = container.get(key)
            if value in legacy_values and value not in warned_values:
                module.deprecate(
                    "The choice '%s' for '%s' is deprecated. Use '%s' instead."
                    % (value, ".".join(path), legacy_values[value]),
                    version="2.0.0",
                    collection_name="ansible.oci",
                )
                warned_values.add(value)
            if value in value_map:
                container[key] = value_map[value]


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
