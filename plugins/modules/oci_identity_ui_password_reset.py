# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_identity_ui_password_reset
short_description: Reset an OCI Identity Domains user's password
description:
  - Resets a user's password in Default and non-default OCI identity domains.
  - Requires an OCI tenancy with Identity Domains.
  - This operation is not idempotent. Each successful run submits a new reset.
  - OCI can send a password reset email instead of returning a temporary password.
  - "C(no_log: true) is recommended for this task and later tasks that handle returned passwords."
version_added: "1.3.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  domain_id:
    description:
      - OCID of the identity domain. This option cannot be used with C(domain_url) or C(domain_name).
    type: str
  domain_url:
    description:
      - Service endpoint of the identity domain. This option cannot be used with C(domain_id) or C(domain_name).
    type: str
  domain_name:
    description:
      - Exact name of the identity domain. The module uses C(Default) when you omit all domain selectors.
      - This option cannot be used with C(domain_id) or C(domain_url).
    type: str
  compartment_id:
    description:
      - Compartment OCID for the domain name lookup. The module uses the tenancy OCID when you omit this option.
    type: str
  user_id:
    description:
      - SCIM user ID from C(resource.id) in C(oci_identity_user).
      - Do not use the user OCID with this option.
    type: str
  user_ocid:
    description:
      - User OCID from C(resource.ocid) in C(oci_identity_user).
      - Do not use the SCIM user ID with this option.
    type: str
  user_name:
    description:
      - User sign-in name. The module fails when the name matches multiple users.
    type: str
seealso:
  - name: OCI User Credentials
    description: Learn about Console password credentials.
    link: https://docs.oracle.com/en-us/iaas/Content/Identity/usercred/usercredentials.htm
  - name: OCI identity domains
    description: Learn about OCI identity domains.
    link: https://docs.oracle.com/en-us/iaas/Content/Identity/domains/identity-domains.htm
"""

EXAMPLES = r"""
- name: Reset a user's password
  no_log: true
  ansible.oci.oci_identity_ui_password_reset:
    user_id: "{{ user.resource.id }}"

- name: Reset a user's password by OCID
  no_log: true
  ansible.oci.oci_identity_ui_password_reset:
    domain_id: "{{ user.resource.domain_id }}"
    user_ocid: "{{ user.resource.ocid }}"
"""

RETURN = r"""
action:
  description: The operation performed or predicted by the task.
  returned: always
  type: str
resource:
  description: User identifiers and a temporary password, when OCI returns one.
  returned: when the reset succeeds
  type: dict
  contains:
    password:
      description: Temporary password. This field is omitted when OCI returns no password.
      type: str
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

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_base import OciModuleBase
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_identity_domains import (
    IDENTITY_DOMAIN_PASSWORD_ARGS,
    IdentityDomainConfigurationError,
    IdentityDomainUserError,
    OciIdentityDomainsMixin,
    find_identity_domain_user,
    serialize_identity_domain_password_reset,
)

oci = import_oci_sdk()[0]


class OciIdentityDomainUiPasswordResetModule(OciIdentityDomainsMixin, OciModuleBase):
    """Reset a selected user's password through Identity Domains."""

    def find_user(self):
        """Return the selected user with only identifiers.

        Returns:
            The matching Identity Domains user model.

        Raises:
            IdentityDomainUserError: If no user matches the selector.
        """
        user = find_identity_domain_user(
            self.module,
            self.client,
            attributes="id,ocid,userName,domainOcid",
        )
        if user is None:
            raise IdentityDomainUserError("The selected user was not found")
        return user

    def reset_password(self, user):
        """Submit a password reset for the selected SCIM user.

        Args:
            user: The user model returned by Identity Domains.

        Returns:
            The OCI password reset response.

        Raises:
            Exception: If OCI cannot reset the password.
        """
        request = oci.identity_domains.models.UserPasswordResetter(
            schemas=["urn:ietf:params:scim:schemas:oracle:idcs:UserPasswordResetter"]
        )
        return self.client.put_user_password_resetter(
            user_password_resetter_id=user.id,
            user_password_resetter=request,
            retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY,
        )


def main():
    """Run a domain password reset with safe error output."""
    module = AnsibleModule(
        argument_spec=dict(OCI_AUTH_ARGS, **IDENTITY_DOMAIN_PASSWORD_ARGS),
        supports_check_mode=True,
        required_one_of=[["user_id", "user_ocid", "user_name"]],
        mutually_exclusive=[
            ["user_id", "user_ocid", "user_name"],
            ["domain_id", "domain_url", "domain_name"],
        ],
    )
    if module.check_mode:
        module.exit_json(changed=True, action="reset")

    error = None
    resource = None
    try:
        helper = OciIdentityDomainUiPasswordResetModule(module)
        user = helper.find_user()
        response = helper.reset_password(user)
        resource = serialize_identity_domain_password_reset(
            user,
            response.data,
            helper.identity_domain_id,
        )
    except oci.exceptions.ServiceError as exc:
        error = {
            "msg": "Failed to reset the identity-domain user's password",
            "status": getattr(exc, "status", None),
            "code": getattr(exc, "code", None),
            "request_id": getattr(exc, "request_id", None),
        }
    except (IdentityDomainUserError, IdentityDomainConfigurationError) as exc:
        error = {"msg": str(exc)}
    except Exception:
        error = {"msg": "Failed to reset the identity-domain user's password"}

    if error:
        module.fail_json(**error)

    module.exit_json(
        changed=True,
        action="reset",
        resource=resource,
    )


if __name__ == "__main__":
    main()
