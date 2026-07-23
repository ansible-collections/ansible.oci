"""OCI authentication utilities supporting multiple auth methods."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module_utils: oci_auth
short_description: OCI authentication and service client creation
description:
 - Provides helpers for authenticating to Oracle Cloud Infrastructure using
 multiple auth methods including API key, instance principal, resource
 principal, and session token.
 - Exports get_oci_config to build OCI config dicts from module params or
 environment variables, and create_service_client to instantiate any OCI
 SDK client with the appropriate signer.
author:
 - Steve Fulmer (@stevefulme1)
 - Ron Gershburg (@ronger4)
"""

import os

from ansible_collections.oracle.oci.plugins.module_utils.oci_common import (
    OCI_SDK_REQUIRED_MSG,
)

try:
    import oci
    HAS_OCI_SDK = True
except ImportError:
    HAS_OCI_SDK = False

VALID_AUTH_TYPES = (
    "api_key",
    "instance_principal",
    "resource_principal",
    "session_token",
)


def get_auth_type(module):
    """Resolve the OCI auth type from module params or environment."""
    auth_type = (
        module.params.get("auth_type")
        or os.environ.get("OCI_AUTH_TYPE")
        or "api_key"
    )
    if auth_type not in VALID_AUTH_TYPES:
        module.fail_json(
            msg=(
                f"Unsupported auth_type '{auth_type}'. Expected one of: "
                f"{', '.join(VALID_AUTH_TYPES)}"
            )
        )
        return None
    return auth_type


def _resolve_setting(module, param_key, env_var, default):
    """Resolve a setting from module params, environment, or fallback."""
    return module.params.get(param_key) or os.environ.get(env_var) or default


def get_oci_config(module):
    """Build OCI config dict from module params or environment."""
    auth_type = get_auth_type(module)

    if auth_type in ("instance_principal", "resource_principal"):
        return {"auth_type": auth_type}

    config_file = _resolve_setting(
        module,
        "config_file_location",
        "OCI_CONFIG_FILE",
        "~/.oci/config",
    )
    config_profile = _resolve_setting(
        module,
        "config_profile_name",
        "OCI_CONFIG_PROFILE",
        "DEFAULT",
    )

    config_file = os.path.expanduser(config_file)

    if os.path.isfile(config_file):
        config = oci.config.from_file(
            file_location=config_file,
            profile_name=config_profile,
        )
    else:
        config = {}

    # Override with explicit params or env vars
    env_map = {
        "tenancy": "OCI_TENANCY_ID",
        "user": "OCI_USER_ID",
        "region": "OCI_REGION",
        "fingerprint": "OCI_USER_FINGERPRINT",
        "key_file": "OCI_USER_KEY_FILE",
    }
    param_map = {
        "tenancy": "tenancy",
        "user": "api_user",
        "region": "region",
        "fingerprint": "api_user_fingerprint",
        "key_file": "api_user_key_file",
    }

    for config_key, env_var in env_map.items():
        param_key = param_map[config_key]
        value = module.params.get(param_key) or os.environ.get(env_var)
        if value:
            config[config_key] = value

    pass_phrase = module.params.get("api_user_key_pass_phrase") or os.environ.get("OCI_USER_KEY_PASS_PHRASE")
    if pass_phrase:
        config["pass_phrase"] = pass_phrase

    return config


def create_service_client(module, client_class):
    """Create an OCI service client with the appropriate auth method."""
    if not HAS_OCI_SDK:
        module.fail_json(
            msg=f"{OCI_SDK_REQUIRED_MSG} Install with: pip install oci"
        )
        return None

    auth_type = get_auth_type(module)

    if auth_type == "instance_principal":
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        return client_class(config={}, signer=signer)

    if auth_type == "resource_principal":
        signer = oci.auth.signers.get_resource_principals_signer()
        return client_class(config={}, signer=signer)

    if auth_type == "session_token":
        config = get_oci_config(module)
        token_file = config.get("security_token_file")
        if not token_file:
            module.fail_json(
                msg=(
                    "Session token auth requires security_token_file "
                    "in the selected OCI config profile."
                )
            )
            return None
        token_file = os.path.expanduser(token_file)
        with open(token_file) as f:
            token = f.read().strip()
        private_key = oci.signer.load_private_key_from_file(config["key_file"])
        signer = oci.auth.signers.SecurityTokenSigner(token, private_key)
        return client_class(config=config, signer=signer)

    # api_key (default)
    config = get_oci_config(module)
    oci.config.validate_config(config)
    return client_class(config)
