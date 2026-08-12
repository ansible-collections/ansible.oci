# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_availability_domain_info
short_description: Retrieve Availability Domain information from Oracle Cloud Infrastructure
description:
  - Retrieve the Availability Domains (ADs) available to a compartment.
  - Availability domain names are tenancy-specific (a unique randomized prefix
    per tenancy, for example C(Uocm:PHX-AD-1)), so they should never be
    hardcoded. Use this module to discover the valid names for your tenancy
    and region instead.
  - ADs are a tenancy-wide/regional concept, so C(compartment_id) defaults to
    the caller's tenancy (root compartment) when not supplied; OCI returns
    the same domains regardless of which compartment in the tenancy is used.
  - This is a read-only module and does not modify resources.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - oracle.oci.oci_auth_options
options:
  compartment_id:
    description:
      - The OCID of the compartment to list availability domains from.
      - Defaults to the caller's tenancy OCID (the root compartment) when not
        set, resolved from the C(tenancy) option, the C(OCI_TENANCY_ID)
        environment variable, or the selected OCI config profile, in that
        order.
    type: str
notes:
  - Use this module to discover valid values for C(availability_domain) on
    M(oracle.oci.oci_instance) and M(oracle.oci.oci_shape_info) instead of
    hardcoding tenancy-specific names.
  - Fails with a clear error when C(compartment_id) is omitted and no tenancy
    OCID can be resolved (for example, with C(instance_principal) or
    C(resource_principal) auth and no config profile); pass C(compartment_id)
    explicitly in that case.
"""

EXAMPLES = r"""
- name: List availability domains for the caller's tenancy
  oracle.oci.oci_availability_domain_info: {}

- name: List availability domains for a specific compartment
  oracle.oci.oci_availability_domain_info:
    compartment_id: ocid1.compartment.oc1..example
"""

RETURN = r"""
availability_domains:
  description: List of availability domains available to the compartment.
  returned: always
  type: list
  elements: dict
  contains:
    name:
      description: The name of the availability domain.
      type: str
      returned: always
      sample: Uocm:PHX-AD-1
    id:
      description: The OCID of the availability domain.
      type: str
      returned: always
      sample: ocid1.availabilitydomain.oc1..example
    compartment_id:
      description:
        - The OCID that was used to query this availability domain (the
          explicit C(compartment_id), or the caller's tenancy OCID when
          C(compartment_id) was not set).
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.oracle.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.oracle.oci.plugins.module_utils.oci_info import (
    OciInfoBase,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]


class OciAvailabilityDomainInfoModule(OciInfoBase):
    """Concrete info adapter for OCI Identity availability domains."""

    @property
    def client_class(self):
        return oci.identity.IdentityClient

    results_key = "availability_domains"
    list_resource_method = "list_availability_domains"

    def resolve_compartment_id(self):
        """Return the compartment to query, defaulting to the tenancy OCID.

        Availability domains are a tenancy-wide concept, so this reuses the
        tenancy value already resolved for authentication (explicit
        C(tenancy)/C(OCI_TENANCY_ID), or the selected OCI config profile,
        both already merged into the client's config by
        ``create_service_client()``) instead of requiring callers to look up
        and pass their tenancy OCID a second time.
        """
        compartment_id = self.module.params.get("compartment_id")
        if compartment_id:
            return compartment_id
        base_client = getattr(self.client, "base_client", None)
        base_client_config = getattr(base_client, "config", None) or {}
        return base_client_config.get("tenancy")

    def fetch_resources(self):
        compartment_id = self.resolve_compartment_id()
        if not compartment_id:
            self.module.fail_json(
                msg=(
                    "Unable to determine compartment_id. Set compartment_id "
                    "explicitly, or set tenancy/OCI_TENANCY_ID, or configure "
                    "tenancy in your OCI config profile."
                )
            )
        return self.list_all_resources(
            getattr(self.client, self.list_resource_method),
            compartment_id=compartment_id,
        )


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciAvailabilityDomainInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
