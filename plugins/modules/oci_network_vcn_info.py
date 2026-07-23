"""Retrieve OCI Virtual Cloud Network information."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.oracle.oci.plugins.module_utils.oci_common import (
    OCI_COMMON_ARGS,
)
from ansible_collections.oracle.oci.plugins.module_utils.oci_info import (
    OciInfoBase,
)
from ansible_collections.oracle.oci.plugins.module_utils.oci_wait import (
    call_with_retry,
)

DOCUMENTATION = r"""
---
module: oci_network_vcn_info
short_description: Retrieve Virtual Cloud Network information from Oracle Cloud Infrastructure
description:
  - Retrieve details about one or more OCI Virtual Cloud Networks (VCNs).
  - Use C(vcn_id) to fetch a single VCN, or C(compartment_id) to list VCNs in a compartment.
  - This is a read-only module and does not modify resources.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
options:
  compartment_id:
    description:
      - The OCID of the compartment to list VCNs from.
      - Required when listing resources.
    type: str
  vcn_id:
    description:
      - The OCID of a specific VCN to retrieve.
      - When specified, returns a single resource instead of a list.
    type: str
  display_name:
    description:
      - Filter listed VCNs by display name.
      - Only used when C(compartment_id) is provided.
    type: str
  lifecycle_state:
    description:
      - Filter listed VCNs by lifecycle state.
      - Only used when C(compartment_id) is provided.
    type: str
"""

EXAMPLES = r"""
- name: List all VCNs in a compartment
  oracle.oci.oci_network_vcn_info:
    compartment_id: ocid1.compartment.oc1..example

- name: Get a specific VCN
  oracle.oci.oci_network_vcn_info:
    vcn_id: ocid1.vcn.oc1..example
"""

RETURN = r"""
vcns:
  description: List of VCNs that matched the query.
  returned: always
  type: list
  elements: dict
"""

try:
    import oci
    from oci.exceptions import ServiceError

    HAS_OCI_SDK = True
except ImportError:
    HAS_OCI_SDK = False
    ServiceError = None
    oci = None


class OciNetworkVcnInfoModule(OciInfoBase):
    """Concrete info adapter for OCI VCNs."""

    client_class = oci.core.VirtualNetworkClient if HAS_OCI_SDK else object()
    results_key = "vcns"

    def user_known_fields(self):
        return ("display_name",)

    def list_resources(self):
        vcn_id = self.module.params.get("vcn_id")
        if vcn_id:
            try:
                response = call_with_retry(
                    self.client.get_vcn,
                    vcn_id=vcn_id,
                )
                return [response.data]
            except ServiceError as exc:
                if exc.status == 404:
                    return []
                raise

        list_kwargs = {
            "compartment_id": self.module.params.get("compartment_id"),
        }
        if self.module.params.get("display_name"):
            list_kwargs["display_name"] = self.module.params.get("display_name")
        if self.module.params.get("lifecycle_state"):
            list_kwargs["lifecycle_state"] = self.module.params.get("lifecycle_state")

        return self.paginate(self.client.list_vcns, **list_kwargs)


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        compartment_id=dict(type="str"),
        vcn_id=dict(type="str"),
        display_name=dict(type="str"),
        lifecycle_state=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[("compartment_id", "vcn_id")],
    )

    OciNetworkVcnInfoModule(module).run()


if __name__ == "__main__":
    main()
