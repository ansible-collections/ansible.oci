# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_oke_node_pool_info
short_description: Retrieve OKE node pool information from OCI
description:
  - Retrieve one OKE node pool or list node pools in a compartment or cluster.
version_added: "1.2.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_info_filter_options
options:
  node_pool_id:
    description:
      - The OCID of one node pool to retrieve.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment to list node pools from.
    type: str
  cluster_id:
    description:
      - The OCID of the cluster to list node pools from.
      - Only used when C(compartment_id) is provided.
    type: str
"""

EXAMPLES = r"""
- name: List active node pools in a compartment
  ansible.oci.oci_oke_node_pool_info:
    compartment_id: ocid1.compartment.oc1..example
    lifecycle_state: ACTIVE

- name: List node pools in a specific cluster
  ansible.oci.oci_oke_node_pool_info:
    compartment_id: ocid1.compartment.oc1..example
    cluster_id: ocid1.cluster.oc1..example

- name: Get a node pool by OCID
  ansible.oci.oci_oke_node_pool_info:
    node_pool_id: ocid1.nodepool.oc1..example
"""

RETURN = r"""
node_pools:
  description: Node pools that matched the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the node pool.
      type: str
      returned: when available
    name:
      description: The node pool name.
      type: str
      returned: when available
    compartment_id:
      description: The OCID of the containing compartment.
      type: str
      returned: when available
    cluster_id:
      description: The OCID of the cluster the node pool belongs to.
      type: str
      returned: when available
    kubernetes_version:
      description: The Kubernetes version running on the nodes.
      type: str
      returned: when available
    lifecycle_state:
      description: The current lifecycle state of the node pool.
      type: str
      returned: when available
    node_shape:
      description: The compute shape of the nodes.
      type: str
      returned: when available
    node_shape_config:
      description: The shape configuration of the nodes.
      type: dict
      returned: when available
    node_source_details:
      description: The source image configuration of the nodes.
      type: dict
      returned: when available
    node_config_details:
      description: The placement and node configuration of the pool.
      type: dict
      returned: when available
    subnet_ids:
      description: The subnets the nodes are placed in.
      type: list
      elements: str
      returned: when available
    initial_node_labels:
      description: The Kubernetes labels applied to each node.
      type: list
      elements: dict
      returned: when available
    nodes:
      description: The nodes currently in the pool.
      type: list
      elements: dict
      returned: when available
    freeform_tags:
      description: Free-form tags applied to the node pool.
      type: dict
      returned: when available
    defined_tags:
      description: Defined tags applied to the node pool.
      type: dict
      returned: when available
    system_tags:
      description: System tags returned by OCI.
      type: dict
      returned: when available
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

oci = import_oci_sdk()[0]


class OciOkeNodePoolInfoModule(OciInfoBase):
    """Concrete info adapter for OKE node pools."""

    @property
    def client_class(self):
        """Return the Container Engine service client required by this adapter."""
        return oci.container_engine.ContainerEngineClient

    results_key = "node_pools"
    resource_id_param = "node_pool_id"
    resource_get_method = "get_node_pool"
    list_resource_method = "list_node_pools"
    list_filter_params = ("compartment_id", "cluster_id", "lifecycle_state")
    # The NodePool SDK model exposes its display field as ``name`` rather than the
    # ``display_name`` used by most OCI resources, so the local name filter must
    # resolve against ``name``.
    name_response_field = "name"

    def collect_list_filters(self, *param_groups):
        """Collect list filters, adapting ``lifecycle_state`` to the SDK shape.

        Like ``list_clusters``, ``ContainerEngineClient.list_node_pools`` takes
        ``lifecycle_state`` as a list of states and validates each entry against
        the allowed enum. The shared module interface exposes a single string, so
        wrap it in a one-item list before the SDK call; otherwise the SDK iterates
        the string character-by-character and rejects each char.

        Args:
            param_groups: Groups of parameter names to collect filters from.

        Returns:
            The collected list filters with ``lifecycle_state`` normalized to a
            one-item list when it was supplied as a string.
        """
        filters = super().collect_list_filters(*param_groups)
        lifecycle_state = filters.get("lifecycle_state")
        if isinstance(lifecycle_state, str):
            filters["lifecycle_state"] = [lifecycle_state]
        return filters


def main():
    """Build the info argument spec and run the OKE node pool info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        node_pool_id=dict(type="str"),
        compartment_id=dict(type="str"),
        cluster_id=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(type="str"),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["node_pool_id", "compartment_id"]],
    )
    OciOkeNodePoolInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
