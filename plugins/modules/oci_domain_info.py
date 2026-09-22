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
version_added: "1.1.0"
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
  contains:
    id:
      description: The OCID of the identity domain.
      type: str
      returned: always
      sample: ocid1.domain.oc1..example
    compartment_id:
      description: The OCID of the compartment containing the identity domain.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    name:
      description: The display name of the identity domain.
      type: str
      returned: always
      sample: example-domain
    description:
      description: The description of the identity domain.
      type: str
      returned: always
      sample: Example identity domain
    url:
      description: The URL of the identity domain.
      type: str
      returned: always
      sample: https://idcs.example.identity.oraclecloud.com:443
    home_region_url:
      description: The identity domain URL in its home region.
      type: str
      returned: always
      sample: https://idcs.example.us-sanjose-idcs-1.identity.us-sanjose-1.oci.oraclecloud.com:443
    home_region:
      description: The OCI region where the identity domain is homed.
      type: str
      returned: always
      sample: us-sanjose-1
    replica_regions:
      description: The regions where the identity domain is replicated.
      type: list
      elements: dict
      returned: always
      contains:
        region:
          description: The replicated region name.
          type: str
          returned: always
          sample: us-phoenix-1
        url:
          description: The identity domain URL for the replicated region.
          type: str
          returned: always
          sample: https://idcs.example.us-phoenix-idcs-1.identity.us-phoenix-1.oci.oraclecloud.com:443
        regional_url:
          description: The regional URL for the replicated identity domain.
          type: str
          returned: always
          sample: https://idcs.example.identity.oraclecloud.com:443
        state:
          description: The lifecycle state of the replicated region.
          type: str
          returned: always
          sample: ACTIVE
    type:
      description: The type of the identity domain.
      type: str
      returned: always
      sample: SECONDARY
    license_type:
      description: The license type of the identity domain.
      type: str
      returned: always
      sample: free
    is_hidden_on_login:
      description: Whether the identity domain is hidden on the sign-in screen.
      type: bool
      returned: always
      sample: false
    lifecycle_state:
      description: The current lifecycle state of the identity domain.
      type: str
      returned: always
      sample: ACTIVE
    lifecycle_details:
      description: Details about the current identity domain lifecycle state.
      type: str
      returned: always
      sample: null
    freeform_tags:
      description: Free-form tags applied to the identity domain.
      type: dict
      returned: always
      sample: {environment: production}
    defined_tags:
      description: Defined tags applied to the identity domain.
      type: dict
      returned: always
      sample: {Operations: {CostCenter: "42"}}
    time_created:
      description: The date and time the identity domain was created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
  sample:
    - id: ocid1.domain.oc1..example
      compartment_id: ocid1.compartment.oc1..example
      name: example-domain
      description: Example identity domain
      home_region: us-sanjose-1
      license_type: free
      is_hidden_on_login: false
      lifecycle_state: ACTIVE
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]


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
