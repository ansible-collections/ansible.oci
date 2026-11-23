# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_identity_ui_password_info
short_description: Get OCI IAM user console password information
description:
  - Gets console password information for one OCI IAM user.
version_added: "1.3.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  user_id:
    description:
      - OCID of the user. Do not use the SCIM C(resource.id) value.
    type: str
    required: true
notes:
  - OCI returns an empty list when the user has no password information.
  - This operation does not return the password.
"""

EXAMPLES = r"""
- name: Get console password information
  ansible.oci.oci_identity_ui_password_info:
    user_id: ocid1.user.oc1..example
"""

RETURN = r"""
ui_passwords:
  description: Console password information for the user.
  returned: always
  type: list
  elements: dict
  contains:
    user_id:
      description: OCID of the user.
      type: str
    time_created:
      description: Time when OCI created the current password.
      type: str
    lifecycle_state:
      description: State of the current password.
      type: str
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

oci = import_oci_sdk()[0]


class OciIdentityUiPasswordInfoModule(OciInfoBase):
    """Get password information for one OCI IAM user."""

    results_key = "ui_passwords"
    resource_id_param = "user_id"
    resource_get_method = "get_user_ui_password_information"

    @property
    def client_class(self):
        """Return the OCI IdentityClient class.

        Returns:
            The OCI IdentityClient class.
        """
        return oci.identity.IdentityClient


def main():
    """Validate the user identifier and return password information."""
    module = AnsibleModule(
        argument_spec=dict(OCI_AUTH_ARGS, user_id={"type": "str", "required": True}),
        supports_check_mode=True,
    )
    OciIdentityUiPasswordInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
