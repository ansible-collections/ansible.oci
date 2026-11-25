# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


class ModuleDocFragment(object):
    DOCUMENTATION = r"""
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
"""
