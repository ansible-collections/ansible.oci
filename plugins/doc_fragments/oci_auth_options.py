# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


class ModuleDocFragment(object):
    DOCUMENTATION = r"""
options:
  auth_type:
    description:
      - The OCI authentication method to use.
      - Resolution order is module parameter, then C(OCI_AUTH_TYPE), then C(api_key).
    type: str
    choices: [api_key, instance_principal, resource_principal, session_token]
  config_file_location:
    description:
      - Path to the OCI configuration file.
      - Resolution order is module parameter, then C(OCI_CONFIG_FILE), then C(~/.oci/config).
    type: str
  config_profile_name:
    description:
      - Profile name to load from the OCI configuration file.
      - Resolution order is module parameter, then C(OCI_CONFIG_PROFILE), then C(DEFAULT).
    type: str
  tenancy:
    description:
      - OCI tenancy OCID for API key authentication.
      - Overrides the matching value from the selected OCI profile when provided.
    type: str
  region:
    description:
      - OCI region for API key authentication.
      - Overrides the matching value from the selected OCI profile when provided.
    type: str
  api_user:
    description:
      - OCI user OCID for API key authentication.
      - Overrides the matching value from the selected OCI profile when provided.
    type: str
  api_user_fingerprint:
    description:
      - Fingerprint for the API key used with API key authentication.
      - Overrides the matching value from the selected OCI profile when provided.
    type: str
  api_user_key_file:
    description:
      - Path to the private key file used with API key authentication.
      - Overrides the matching value from the selected OCI profile when provided.
    type: str
  api_user_key_pass_phrase:
    description:
      - Pass phrase for the private key used with API key authentication.
      - Overrides the matching value from the selected OCI profile when provided.
    type: str
"""
