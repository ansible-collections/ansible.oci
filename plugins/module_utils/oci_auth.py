"""OCI authentication helpers for internal collection code."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import os

from ansible.module_utils.basic import missing_required_lib

try:
    import oci
    HAS_OCI_SDK = True
except ImportError:
    HAS_OCI_SDK = False


def get_auth_type(module):
    """Return the resolved OCI auth mode from module parameters.

    The module argument spec and environment fallbacks have already normalized
    this value before helpers call into the OCI SDK.
    """
    return module.params.get("auth_type")


def get_oci_config(module):
    """Build the OCI SDK config dictionary for the selected auth mode.

    For instance and resource principal auth, the SDK only needs the auth mode
    marker and does not require a config file. For API key and session token
    auth, this helper loads the selected OCI profile when it exists and then
    overlays any explicit module parameters before returning the config dict.
    """
    auth_type = get_auth_type(module)

    if auth_type in ("instance_principal", "resource_principal"):
        return {"auth_type": auth_type}

    config_file = module.params.get("config_file_location")
    config_profile = module.params.get("config_profile_name")

    config_file = os.path.expanduser(config_file)

    if os.path.isfile(config_file):
        config = oci.config.from_file(
            file_location=config_file,
            profile_name=config_profile,
        )
    else:
        config = {}

    # Override with explicit module params after loading the selected profile.
    env_map = {
        "tenancy": "tenancy",
        "user": "api_user",
        "region": "region",
        "fingerprint": "api_user_fingerprint",
        "key_file": "api_user_key_file",
    }

    for config_key, param_key in env_map.items():
        value = module.params.get(param_key)
        if value:
            config[config_key] = value

    pass_phrase = module.params.get("api_user_key_pass_phrase")
    if pass_phrase:
        config["pass_phrase"] = pass_phrase

    return config


def create_service_client(module, client_class):
    """Instantiate an OCI service client with the correct signer or config.

    The returned object is an instance of ``client_class`` configured for the
    caller's auth mode. This helper can fail the module when the OCI SDK is not
    installed or when session token auth is missing required profile data.
    """
    if not HAS_OCI_SDK:
        module.fail_json(msg=missing_required_lib("oci"))

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
