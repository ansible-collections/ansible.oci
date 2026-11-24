# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_identity_ui_password_info
short_description: Get a user's password state from OCI Identity Domains
description:
  - Gets password state for a user in a Default or non-default OCI identity domain.
  - Requires an OCI tenancy with Identity Domains.
  - Returns an empty C(ui_passwords) list when no user matches.
  - For a matching user without password metadata, C(password_state) is an empty dictionary.
  - This module does not return passwords.
version_added: "1.3.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_identity_password_options
"""

EXAMPLES = r"""
- name: Get console password information
  ansible.oci.oci_identity_ui_password_info:
    user_id: "{{ user.resource.id }}"

- name: Get password state by user OCID
  ansible.oci.oci_identity_ui_password_info:
    domain_id: "{{ user.resource.domain_id }}"
    user_ocid: "{{ user.resource.ocid }}"
"""

RETURN = r"""
ui_passwords:
  description: User identifiers and password state fields from OCI Identity Domains.
  returned: always
  type: list
  elements: dict
  contains:
    user_id:
      description: SCIM user ID.
      type: str
    user_ocid:
      description: OCID of the user.
      type: str
    user_name:
      description: Sign-in name of the user.
      type: str
    domain_id:
      description: OCID of the identity domain.
      type: str
    password_state:
      description: Password state fields. This dictionary is empty when OCI returns no password state.
      type: dict
      contains:
        cant_change:
          description: Whether password changes are prohibited.
          type: bool
        cant_expire:
          description: Whether password expiry is disabled.
          type: bool
        must_change:
          description: Whether the user must change the password.
          type: bool
        expired:
          description: Whether the password is expired.
          type: bool
        last_successful_set_date:
          description: Date when the password was last set successfully.
          type: str
status:
  description: OCI service error status.
  returned: on OCI service error
  type: int
code:
  description: OCI service error code.
  returned: on OCI service error
  type: str
request_id:
  description: OCI request identifier for the service error.
  returned: on OCI service error
  type: str
"""

from ansible.module_utils.basic import AnsibleModule, missing_required_lib

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase
from ansible_collections.ansible.oci.plugins.module_utils.oci_identity_domains import (
    IDENTITY_DOMAIN_PASSWORD_ARGS,
    IdentityDomainConfigurationError,
    IdentityDomainUserError,
    OciIdentityDomainsMixin,
    PASSWORD_STATE_SCHEMA,
    find_identity_domain_user,
    serialize_identity_domain_password_user,
)

oci = import_oci_sdk()[0]


class OciIdentityUiPasswordInfoModule(OciIdentityDomainsMixin, OciInfoBase):
    """Get selected password state from one identity domain."""

    results_key = "ui_passwords"

    def fetch_resources(self):
        """Find the user and return an empty list when no user matches.

        Returns:
            A list with the matching user, or an empty list.
        """
        attributes = "id,ocid,userName,domainOcid," + PASSWORD_STATE_SCHEMA
        user = find_identity_domain_user(self.module, self.client, attributes=attributes)
        return [user] if user is not None else []

    def serialize_result_resource(self, resource):
        """Return user identifiers and password state fields.

        Args:
            resource: The Identity Domains user model.

        Returns:
            A dictionary with selected identifiers and password state fields.
        """
        return serialize_identity_domain_password_user(
            resource,
            self.identity_domain_id,
        )


def main():
    """Run an identity-domain password state lookup with safe error output."""
    module = AnsibleModule(
        argument_spec=dict(OCI_AUTH_ARGS, **IDENTITY_DOMAIN_PASSWORD_ARGS),
        supports_check_mode=True,
        required_one_of=[["user_id", "user_ocid", "user_name"]],
        mutually_exclusive=[
            ["user_id", "user_ocid", "user_name"],
            ["domain_id", "domain_url", "domain_name"],
        ],
    )
    if oci is None:
        module.fail_json(msg=missing_required_lib("oci"))

    error = None
    try:
        OciIdentityUiPasswordInfoModule(module).execute_info_module()
    except oci.exceptions.ServiceError as exc:
        error = {
            "msg": "Failed to get identity-domain password information",
            "status": getattr(exc, "status", None),
            "code": getattr(exc, "code", None),
            "request_id": getattr(exc, "request_id", None),
        }
    except (IdentityDomainUserError, IdentityDomainConfigurationError) as exc:
        error = {"msg": str(exc)}
    except Exception:
        error = {"msg": "Failed to get identity-domain password information"}

    if error:
        module.fail_json(**error)


if __name__ == "__main__":
    main()
