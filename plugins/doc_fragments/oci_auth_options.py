# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


class ModuleDocFragment(object):
    DOCUMENTATION = r"""
notes:
  - Shared OCI auth options use ansible-core argument-spec fallbacks.
  - >-
    For API key authentication, explicit module parameters override matching
    values from environment variables and from the selected OCI config profile
    when provided.
  - Resolution order for C(auth_type) is module parameter, then C(OCI_AUTH_TYPE), then C(api_key).
  - Resolution order for C(config_file_location) is module parameter, then C(OCI_CONFIG_FILE), then C(~/.oci/config).
  - Resolution order for C(config_profile_name) is module parameter, then C(OCI_CONFIG_PROFILE), then C(DEFAULT).
options:
  auth_type:
    description:
      - The OCI authentication method to use.
    type: str
    default: api_key
    choices: [api_key, instance_principal, resource_principal, session_token]
  config_file_location:
    description:
      - Path to the OCI configuration file.
    type: str
    default: ~/.oci/config
  config_profile_name:
    description:
      - Profile name to load from the OCI configuration file.
    type: str
    default: DEFAULT
  tenancy:
    description:
      - OCI tenancy OCID for API key authentication.
    type: str
  region:
    description:
      - OCI region for API key authentication.
    type: str
  api_user:
    description:
      - OCI user OCID for API key authentication.
    type: str
  api_user_fingerprint:
    description:
      - Fingerprint for the API key used with API key authentication.
    type: str
  api_user_key_file:
    description:
      - Path to the private key file used with API key authentication.
    type: str
  api_user_key_pass_phrase:
    description:
      - Pass phrase for the private key used with API key authentication.
    type: str
"""
