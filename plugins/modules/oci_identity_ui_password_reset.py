# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_identity_ui_password_reset
short_description: Reset an OCI IAM user console password
description:
  - Resets the specified user's Console password through the OCI Identity service.
  - This module only submits password resets and is not idempotent.
  - Each successful normal invocation submits a new reset and reports a change.
  - In check mode, the module reports a change without calling OCI.
  - "We recommend C(no_log: true) for this task and later tasks that handle returned passwords."
  - Deliver any returned password to the user through a secure channel.
  - A temporary password expires after seven days. The user must change it at the next sign in.
  - For identity domain users, OCI can send a password reset email with a link.
  - The user must reset the password before the link expires. Run this module again if the link expires.
  - This IAM operation can return HTTP 404 for users in non-default identity domains.
version_added: "1.3.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  user_id:
    description:
      - OCID of the user returned as C(resource.ocid) by C(oci_identity_user).
      - Do not use the SCIM C(resource.id) value.
      - The Console login remains the C(user_name) set when the user was created.
    type: str
    required: true
seealso:
  - name: OCI User Credentials
    description: Learn about Console password credentials.
    link: https://docs.oracle.com/en-us/iaas/Content/Identity/usercred/usercredentials.htm
"""

EXAMPLES = r"""
- name: Reset a user's console password
  no_log: true
  ansible.oci.oci_identity_ui_password_reset:
    user_id: "{{ user.resource.ocid }}"
"""

RETURN = r"""
action:
  description: The operation performed or predicted by the task.
  returned: always
  type: str
resource:
  description: Password information returned by OCI. OCI can include a temporary password.
  returned: when the reset succeeds
  type: dict
  contains:
    password:
      description: Temporary password, when OCI returns one.
      type: str
    user_id:
      description: OCID of the user.
      type: str
    time_created:
      description: Time when OCI created the password, in RFC 3339 format.
      type: str
    lifecycle_state:
      description: State of the password. Wait until C(ACTIVE) before the user signs in.
      type: str
    inactive_status:
      description: Inactive status code, when OCI returns one.
      type: int
status:
  description: OCI service error HTTP status code.
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

oci = import_oci_sdk()[0]


class OciIdentityUiPasswordResetModule(OciModuleBase):
    """Reset a user's console password with the OCI Identity client."""

    @property
    def client_class(self):
        """Return the OCI IdentityClient class.

        Returns:
            The OCI IdentityClient class.
        """
        return oci.identity.IdentityClient

    def reset_password(self):
        """Reset the configured user's console password.

        Returns:
            The OCI response with password information.

        Raises:
            Exception: If OCI cannot reset the password.
        """
        return self.client.create_or_reset_ui_password(
            user_id=self.module.params["user_id"],
            retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY,
        )


def main():
    """Run the requested reset and return the OCI response."""
    module = AnsibleModule(
        argument_spec=dict(
            OCI_AUTH_ARGS,
            user_id={"type": "str", "required": True},
        ),
        supports_check_mode=True,
    )
    if module.check_mode:
        module.exit_json(changed=True, action="reset")

    helper = OciIdentityUiPasswordResetModule(module)
    error = None
    try:
        response = helper.reset_password()
    except oci.exceptions.ServiceError as exc:
        error = {
            "msg": "Failed to reset the user's console password",
            "status": exc.status,
            "code": exc.code,
            "request_id": exc.request_id,
        }
    except Exception:
        error = {"msg": "Failed to reset the user's console password"}

    # Call fail_json outside the exception handler to avoid automatic traceback data.
    if error:
        module.fail_json(**error)

    module.exit_json(
        changed=True,
        action="reset",
        resource=helper.serialize_result_resource(response.data),
    )


if __name__ == "__main__":
    main()
