# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_identity_api_key_info
short_description: Retrieve OCI IAM identity domain API keys
description:
  - Lists API keys for an identity domain user through the OCI IAM Identity Domains SCIM API.
  - An optional C(fingerprint) filters the result to one API key.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  domain_id:
    description:
      - OCID of the identity domain.
      - Exactly one of C(domain_id) or C(domain_url) is required.
    type: str
  domain_url:
    description:
      - Service endpoint of the identity domain.
      - Exactly one of C(domain_id) or C(domain_url) is required.
    type: str
  user_id:
    description: SCIM identifier of the user.
    type: str
    required: true
  fingerprint:
    description: Optional server-generated API key fingerprint.
    type: str
"""

EXAMPLES = r"""
- name: List a user's identity domain API keys
  ansible.oci.oci_identity_api_key_info:
    domain_id: ocid1.domain.oc1..example
    user_id: 0123456789abcdef

- name: Get one identity domain API key
  ansible.oci.oci_identity_api_key_info:
    domain_url: https://idcs-example.identity.oraclecloud.com
    user_id: 0123456789abcdef
    fingerprint: 12:34:56:78:9A:BC:DE:F0:12:34:56:78:9A:BC:DE:F0
"""

RETURN = r"""
api_keys:
  description: API keys matching the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: SCIM identifier.
      type: str
    ocid:
      description: OCI identifier, when exposed by the identity domain.
      type: str
    domain_id:
      description: OCID of the identity domain.
      type: str
    user_id:
      description: SCIM identifier of the user.
      type: str
    user_ocid:
      description: OCID of the user, when exposed by the identity domain.
      type: str
    key:
      description: RSA public key in PEM format.
      type: str
    fingerprint:
      description: Server-generated API key fingerprint.
      type: str
    time_created:
      description: API key creation time.
      type: str
    time_modified:
      description: API key modification time.
      type: str
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import OCI_AUTH_ARGS
from ansible_collections.ansible.oci.plugins.module_utils.oci_identity_domains import (
    OCI_IDENTITY_DOMAIN_ARGS,
    OciIdentityDomainsMixin,
    build_api_key_filter,
    serialize_api_key,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase


class OciIdentityApiKeyInfoModule(OciIdentityDomainsMixin, OciInfoBase):
    """Retrieve API keys through the OCI Identity Domains client."""

    results_key = "api_keys"

    def serialize_result_resource(self, resource):
        """Return the API key result fields used by this info module.

        The API key result needs a stable field shape that differs from generic
        SDK serialization, so this method uses the shared API key serializer.

        Args:
            resource: OCI API key model.

        Returns:
            A serialized API key dictionary.
        """
        return serialize_api_key(resource)

    def fetch_resources(self):
        """List API keys for the requested user and optional fingerprint.

        The API key endpoint requires a SCIM filter, so this method supplies
        the user and optional fingerprint filters before inherited pagination.

        Returns:
            All matching API key models.
        """
        return self.list_all_resources(
            self.client.list_api_keys,
            filter=build_api_key_filter(
                self.module.params["user_id"], self.module.params.get("fingerprint")
            ),
        )


def main():
    """Run the API key info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_IDENTITY_DOMAIN_ARGS,
        user_id=dict(type="str", required=True),
        fingerprint=dict(type="str"),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["domain_id", "domain_url"]],
        mutually_exclusive=[["domain_id", "domain_url"]],
    )
    OciIdentityApiKeyInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
