"""OCI authentication helpers used by inventory plugins."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import os

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    import_oci_sdk,
)

oci = import_oci_sdk()[0]


def get_oci_config_from_options(options):
    """Build an OCI SDK config dictionary from inventory plugin options."""
    auth_type = options.get("auth_type")
    if auth_type in ("instance_principal", "resource_principal"):
        return {"auth_type": auth_type}

    config_file = os.path.expanduser(
        options.get("config_file_location", "~/.oci/config")
    )
    config_profile = options.get("config_profile_name", "DEFAULT")
    config = (
        oci.config.from_file(file_location=config_file, profile_name=config_profile)
        if os.path.isfile(config_file)
        else {}
    )
    option_keys = {
        "tenancy": "tenancy",
        "user": "api_user",
        "region": "region",
        "fingerprint": "api_user_fingerprint",
        "key_file": "api_user_key_file",
    }
    for config_key, option_key in option_keys.items():
        if options.get(option_key):
            config[config_key] = options[option_key]

    if options.get("api_user_key_pass_phrase"):
        config["pass_phrase"] = options["api_user_key_pass_phrase"]
    return config


def create_service_client_from_options(options, client_class, region=None):
    """Create an OCI service client from inventory plugin options."""
    auth_type = options.get("auth_type", "api_key")
    if auth_type == "instance_principal":
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        client = client_class(config={}, signer=signer)
    elif auth_type == "resource_principal":
        signer = oci.auth.signers.get_resource_principals_signer()
        client = client_class(config={}, signer=signer)
    elif auth_type == "session_token":
        config = get_oci_config_from_options(options)
        token_file = config.get("security_token_file")
        if not token_file:
            raise ValueError(
                "Session token auth requires security_token_file "
                "in the selected OCI config profile."
            )
        with open(os.path.expanduser(token_file)) as token_handle:
            token = token_handle.read().strip()
        private_key = oci.signer.load_private_key_from_file(config["key_file"])
        client = client_class(
            config=config,
            signer=oci.auth.signers.SecurityTokenSigner(token, private_key),
        )
    else:
        config = get_oci_config_from_options(options)
        oci.config.validate_config(config)
        client = client_class(config)

    if region:
        client.base_client.set_region(region)
    return client
