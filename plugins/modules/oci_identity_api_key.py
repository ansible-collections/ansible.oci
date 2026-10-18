# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_identity_api_key
short_description: Manage an OCI IAM identity domain API key
description:
  - Creates or removes an RSA public API key for an identity domain user.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  state:
    description:
      - C(present) creates the API key when the same key is missing.
      - C(absent) removes the API key with the matching fingerprint.
    type: str
    choices: [present, absent]
    default: present
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
  key:
    description: RSA public key in PEM format. Required when C(state=present).
    type: str
  fingerprint:
    description: Server-generated API key fingerprint. Required when C(state=absent).
    type: str
"""

EXAMPLES = r"""
- name: Create an identity domain API key
  ansible.oci.oci_identity_api_key:
    domain_id: ocid1.domain.oc1..example
    user_id: 0123456789abcdef
    key: "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"

- name: Remove an identity domain API key
  ansible.oci.oci_identity_api_key:
    domain_url: https://idcs-example.identity.oraclecloud.com
    state: absent
    user_id: 0123456789abcdef
    fingerprint: 12:34:56:78:9A:BC:DE:F0:12:34:56:78:9A:BC:DE:F0
"""

RETURN = r"""
resource:
  description: The identity domain API key.
  returned: when state is present and an API key exists
  type: dict
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
      description: RSA public key in PEM format. The value is masked because the input uses no_log.
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

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    build_model,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_identity_domains import (
    API_KEY_SCHEMA,
    OCI_IDENTITY_DOMAIN_ARGS,
    OciIdentityDomainResourceBase,
    build_api_key_filter,
    build_schemas,
    serialize_api_key,
)

oci = import_oci_sdk()[0]


class OciIdentityApiKeyModule(OciIdentityDomainResourceBase):
    """Manage API keys through the OCI Identity Domains client."""

    resource_id_param = None
    name_lookup_param = None
    create_required_fields = ("user_id", "key")
    create_resource_name = "API key"

    def serialize_result_resource(self, resource):
        """Return the API key result fields used by this module.

        The API key result needs a stable field shape that differs from generic
        SDK serialization, so this method uses the shared API key serializer.

        Args:
            resource: OCI API key model.

        Returns:
            A serialized API key dictionary.
        """
        return serialize_api_key(resource)

    def resolve_target_resource(self):
        """Find the requested API key by user and state-specific selector.

        The inherited resolver expects an ID or name. API keys require a key
        comparison for present state and a fingerprint comparison for absent state.

        Returns:
            The matching API key model, or ``None`` when no key matches.
        """
        resources = self.fetch_resources()
        fingerprint = self.module.params.get("fingerprint")
        if self.module.params.get("state") == "absent":
            return next(
                (resource for resource in resources if getattr(resource, "fingerprint", None) == fingerprint),
                None,
            )
        key = self.module.params.get("key")
        return next(
            (
                resource
                for resource in resources
                if getattr(resource, "key", None) == key
            ),
            None,
        )

    def fetch_resources(self):
        """List API keys with the selector required by the current state.

        The resource lifecycle needs a user-scoped list for present state and
        a user-and-fingerprint list for absent state.

        Returns:
            API key models matching the user and absent-state fingerprint.
        """
        fingerprint = self.module.params.get("fingerprint")
        if self.module.params.get("state") != "absent":
            fingerprint = None
        return self.list_all_resources(
            self.client.list_api_keys,
            filter=build_api_key_filter(
                self.module.params["user_id"], fingerprint
            ),
        )

    def validate_create_request(self):
        """Validate the present-state API key input.

        The base validator checks missing fields. This override also rejects a blank key.

        Raises:
            Ansible module failure when the key is empty.
        """
        super(OciIdentityApiKeyModule, self).validate_create_request()
        if not self.module.params["key"].strip():
            self.module.fail_json(msg="Creating an API key requires a nonempty key")

    def validate_delete_request(self):
        """Validate the absent-state API key selector.

        The base validator expects a resource ID. This override validates the fingerprint selector.

        Raises:
            Ansible module failure when the fingerprint is empty.
        """
        fingerprint = self.module.params.get("fingerprint")
        if fingerprint is None or not fingerprint.strip():
            self.module.fail_json(
                msg="Deleting an API key requires a nonempty fingerprint"
            )

    def get_resource_response(self, resource_id):
        """Get one API key by its SCIM identifier.

        Args:
            resource_id: SCIM identifier of the API key.

        Returns:
            OCI response wrapper for the API key.
        """
        return self.call_with_retry(self.client.get_api_key, api_key_id=resource_id)

    def create_resource(self):
        """Create the requested API key for the user.

        Returns:
            The created API key model.
        """
        api_key = build_model(
            {
                "schemas": build_schemas(API_KEY_SCHEMA),
                "key": self.module.params["key"],
                "user": oci.identity_domains.models.ApiKeyUser(
                    value=self.module.params["user_id"]
                ),
            },
            oci.identity_domains.models.ApiKey,
        )
        return self.call_with_retry(self.client.create_api_key, api_key=api_key).data

    def delete_resource(self, resource):
        """Delete the selected API key.

        Args:
            resource: API key model selected by fingerprint.
        """
        self.call_with_retry(self.client.delete_api_key, api_key_id=resource.id)


def main():
    """Run the API key resource module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_IDENTITY_DOMAIN_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        user_id=dict(type="str", required=True),
        key=dict(type="str", no_log=True),
        fingerprint=dict(type="str"),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["domain_id", "domain_url"]],
        mutually_exclusive=[["domain_id", "domain_url"]],
        required_if=[
            ["state", "present", ["key"]],
            ["state", "absent", ["fingerprint"]],
        ],
    )
    OciIdentityApiKeyModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
