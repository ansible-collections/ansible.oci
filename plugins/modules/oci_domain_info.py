# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_domain_info
short_description: Retrieve OCI identity domain information
description:
  - Retrieve details about one or more OCI identity domains.
  - Use C(domain_id) to retrieve one domain, or C(compartment_id) to list domains.
  - This is a read-only module and does not modify resources.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  domain_id:
    description:
      - The OCID of a specific identity domain to retrieve.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment whose identity domains are listed.
    type: str
  name:
    description:
      - Filter listed identity domains by display name.
    type: str
  lifecycle_state:
    description:
      - Filter listed identity domains by lifecycle state.
    type: str
"""

EXAMPLES = r"""
- name: List identity domains in a compartment
  ansible.oci.oci_domain_info:
    compartment_id: ocid1.compartment.oc1..example

- name: Get an identity domain
  ansible.oci.oci_domain_info:
    domain_id: ocid1.domain.oc1..example
"""

RETURN = r"""
domains:
  description: List of identity domains that matched the query.
  returned: always
  type: list
  elements: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

oci, HAS_OCI_SDK = import_oci_sdk()


class OciDomainInfoModule(OciInfoBase):
    """Concrete info adapter for OCI identity domains."""

    @property
    def client_class(self):
        return oci.identity.IdentityClient

    results_key = "domains"
    resource_id_param = "domain_id"
    resource_get_method = "get_domain"
    list_resource_method = "list_domains"
    list_filter_params = ["compartment_id", "lifecycle_state"]


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        domain_id=dict(type="str"),
        compartment_id=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["domain_id", "compartment_id"]],
    )

    OciDomainInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
