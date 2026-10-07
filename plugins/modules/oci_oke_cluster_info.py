# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_oke_cluster_info
short_description: Retrieve OKE cluster information from OCI
description:
  - Retrieve one OKE cluster or list clusters in a compartment.
version_added: "1.2.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_info_filter_options
options:
  cluster_id:
    description:
      - The OCID of one cluster to retrieve.
      - Use C(id) as an alias.
    type: str
    aliases: [id]
  compartment_id:
    description:
      - The OCID of the compartment to list clusters from.
    type: str
"""

EXAMPLES = r"""
- name: List active clusters in a compartment
  ansible.oci.oci_oke_cluster_info:
    compartment_id: ocid1.compartment.oc1..example
    lifecycle_state: ACTIVE

- name: Get a cluster by OCID
  ansible.oci.oci_oke_cluster_info:
    cluster_id: ocid1.cluster.oc1..example
"""

RETURN = r"""
clusters:
  description: Clusters that matched the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the cluster.
      type: str
      returned: when available
    name:
      description: The cluster name.
      type: str
      returned: when available
    compartment_id:
      description: The OCID of the containing compartment.
      type: str
      returned: when available
    vcn_id:
      description: The OCID of the VCN the cluster runs in.
      type: str
      returned: when available
    kubernetes_version:
      description: The Kubernetes version of the cluster control plane.
      type: str
      returned: when available
    type:
      description: The cluster type, such as BASIC_CLUSTER or ENHANCED_CLUSTER.
      type: str
      returned: when available
    lifecycle_state:
      description: The current lifecycle state of the cluster.
      type: str
      returned: when available
    endpoint_config:
      description: The cluster endpoint network configuration.
      type: dict
      returned: when available
    endpoints:
      description: The cluster endpoints.
      type: dict
      returned: when available
    options:
      description: The cluster creation options.
      type: dict
      returned: when available
    image_policy_config:
      description: The signed-image verification policy.
      type: dict
      returned: when available
    cluster_pod_network_options:
      description: The available CNI types for node pools.
      type: list
      elements: dict
      returned: when available
    available_kubernetes_upgrades:
      description: The Kubernetes versions the cluster can be upgraded to.
      type: list
      elements: str
      returned: when available
    metadata:
      description: Cluster lifecycle metadata.
      type: dict
      returned: when available
    freeform_tags:
      description: Free-form tags applied to the cluster.
      type: dict
      returned: when available
    defined_tags:
      description: Defined tags applied to the cluster.
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


class OciOkeClusterInfoModule(OciInfoBase):
    """Concrete info adapter for OKE clusters."""

    @property
    def client_class(self):
        """Return the Container Engine service client required by this adapter."""
        return oci.container_engine.ContainerEngineClient

    results_key = "clusters"
    resource_id_param = "cluster_id"
    resource_get_method = "get_cluster"
    list_resource_method = "list_clusters"
    list_filter_params = ("compartment_id", "lifecycle_state")
    # The Cluster SDK model exposes its display field as ``name`` rather than the
    # ``display_name`` used by most OCI resources, so the local name filter must
    # resolve against ``name``.
    name_response_field = "name"


def main():
    """Build the info argument spec and run the OKE cluster info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        cluster_id=dict(type="str", aliases=["id"]),
        compartment_id=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(type="str"),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["cluster_id", "compartment_id"]],
    )
    OciOkeClusterInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
