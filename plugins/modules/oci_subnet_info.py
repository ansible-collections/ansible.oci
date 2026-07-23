"""Retrieve OCI Subnet information."""

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
module: oci_subnet_info
short_description: Retrieve Subnet information from Oracle Cloud Infrastructure
description:
  - Retrieve details about one or more OCI subnets.
  - Use C(subnet_id) to fetch a single subnet, or C(compartment_id) to list
    subnets in a compartment.
  - This is a read-only module and does not modify resources.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
options:
  compartment_id:
    description:
      - The OCID of the compartment to list subnets from.
      - Required when listing resources.
    type: str
  subnet_id:
    description:
      - The OCID of a specific subnet to retrieve.
      - When specified, returns a single resource instead of a list.
    type: str
  vcn_id:
    description:
      - Filter listed subnets by VCN.
      - Only used when C(compartment_id) is provided.
    type: str
  display_name:
    description:
      - Filter listed subnets by display name.
      - Only used when C(compartment_id) is provided.
    type: str
  lifecycle_state:
    description:
      - Filter listed subnets by lifecycle state.
      - Only used when C(compartment_id) is provided.
    type: str
"""

EXAMPLES = r"""
- name: List all subnets in a compartment
  oracle.oci.oci_subnet_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List subnets in a VCN by display name
  oracle.oci.oci_subnet_info:
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    display_name: example-subnet

- name: Get a specific subnet
  oracle.oci.oci_subnet_info:
    subnet_id: ocid1.subnet.oc1..example
"""

RETURN = r"""
subnets:
  description: List of subnets that matched the query.
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


class OciSubnetInfoModule(OciInfoBase):
    """Concrete info adapter for OCI subnets."""

    client_class = oci.core.VirtualNetworkClient if HAS_OCI_SDK else object()
    results_key = "subnets"

    def user_known_fields(self):
        return ("display_name",)

    def list_resources(self):
        subnet_id = self.module.params.get("subnet_id")
        if subnet_id:
            try:
                response = call_with_retry(
                    self.client.get_subnet,
                    subnet_id=subnet_id,
                )
                return [response.data]
            except ServiceError as exc:
                if exc.status == 404:
                    return []
                raise

        list_kwargs = {
            "compartment_id": self.module.params.get("compartment_id"),
        }
        if self.module.params.get("vcn_id"):
            list_kwargs["vcn_id"] = self.module.params.get("vcn_id")
        if self.module.params.get("display_name"):
            list_kwargs["display_name"] = self.module.params.get("display_name")
        if self.module.params.get("lifecycle_state"):
            list_kwargs["lifecycle_state"] = self.module.params.get("lifecycle_state")

        return self.paginate(self.client.list_subnets, **list_kwargs)


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        compartment_id=dict(type="str"),
        subnet_id=dict(type="str"),
        vcn_id=dict(type="str"),
        display_name=dict(type="str"),
        lifecycle_state=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[("compartment_id", "subnet_id")],
    )

    OciSubnetInfoModule(module).run()


if __name__ == "__main__":
    main()
