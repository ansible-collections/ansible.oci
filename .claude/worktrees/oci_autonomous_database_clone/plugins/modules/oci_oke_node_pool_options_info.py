# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_oke_node_pool_options_info
short_description: Retrieve available OKE node pool options from OCI
description:
  - Retrieve the worker-node images, shapes, and Kubernetes versions available for
    OKE node pools.
  - Use this to discover a supported image OCID to pass to
    M(ansible.oci.oci_oke_node_pool) as C(node_source_details.image_id).
version_added: "1.2.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  node_pool_option_id:
    description:
      - The option set to retrieve.
      - Use the literal C(all) to get every available option, or a cluster OCID to get
        the options valid for that cluster's Kubernetes version.
    type: str
    default: all
  compartment_id:
    description:
      - The OCID of the compartment to scope the options to.
    type: str
  node_pool_os_type:
    description:
      - Restrict the returned images to this operating system.
    type: str
    choices:
      - OL7
      - OL8
      - UBUNTU
  node_pool_os_arch:
    description:
      - Restrict the returned images to this operating system architecture.
      - The architecture also determines which C(shapes) an image can run on.
    type: str
    choices:
      - X86_64
      - AARCH64
  node_pool_k8s_version:
    description:
      - Restrict the returned images to those built for this Kubernetes version.
    type: str
"""

EXAMPLES = r"""
- name: List every available node pool option
  ansible.oci.oci_oke_node_pool_options_info:
    node_pool_option_id: all

- name: List the images valid for a specific cluster
  ansible.oci.oci_oke_node_pool_options_info:
    node_pool_option_id: ocid1.cluster.oc1..example

- name: Narrow images to an architecture and Kubernetes version
  ansible.oci.oci_oke_node_pool_options_info:
    node_pool_option_id: all
    compartment_id: ocid1.compartment.oc1..example
    node_pool_os_arch: AARCH64
    node_pool_k8s_version: v1.29.1
"""

RETURN = r"""
node_pool_options:
  description:
    - The matching node pool option set.
    - Always a single-element list, mirroring the other info modules.
  returned: always
  type: list
  elements: dict
  contains:
    sources:
      description:
        - The available worker-node image sources.
        - The C(image_id) of a source is the value to pass to
          M(ansible.oci.oci_oke_node_pool) as C(node_source_details.image_id).
      type: list
      elements: dict
      returned: when available
      contains:
        source_type:
          description: The source type, for example C(IMAGE).
          type: str
          returned: when available
        source_name:
          description: The human-readable source name, which embeds the OS and
            Kubernetes version.
          type: str
          returned: when available
        image_id:
          description: The OCID of the worker-node image.
          type: str
          returned: when available
    images:
      description: The legacy flat list of available image names.
      type: list
      elements: str
      returned: when available
    shapes:
      description: The compute shapes available for node pools.
      type: list
      elements: str
      returned: when available
    kubernetes_versions:
      description: The Kubernetes versions available for node pools.
      type: list
      elements: str
      returned: when available
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

oci = import_oci_sdk()[0]


class OciOkeNodePoolOptionsInfoModule(OciInfoBase):
    """Concrete info adapter for OKE node pool options."""

    results_key = "node_pool_options"
    # Optional request-side filters that narrow the returned images. They are passed
    # straight through to get_node_pool_options as keyword arguments.
    OPTIONAL_FILTER_PARAMS = (
        "compartment_id",
        "node_pool_os_type",
        "node_pool_os_arch",
        "node_pool_k8s_version",
    )

    @property
    def client_class(self):
        """Return the Container Engine service client required by this adapter."""
        return oci.container_engine.ContainerEngineClient

    def fetch_resources(self):
        """Fetch the node pool options for the requested option set.

        ``get_node_pool_options`` is a single-object GET rather than a paginated
        list, so the base ``list_resource_method`` path does not apply. This reuses
        ``get_resource_by_id`` for its retry and 404-to-empty-list handling, passing
        ``node_pool_option_id`` plus any supplied (non-None) narrowing filters.

        Returns:
            A one-item list holding the ``NodePoolOptions`` model, or an empty list
            when the option set (for example an unknown cluster OCID) is not found.
        """
        option_id = self.module.params["node_pool_option_id"]
        filters = self.collect_list_filters(self.OPTIONAL_FILTER_PARAMS)
        return self.get_resource_by_id(
            option_id,
            self.client.get_node_pool_options,
            node_pool_option_id=option_id,
            **filters,
        )


def main():
    """Build the argument spec and run the OKE node pool options info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        node_pool_option_id=dict(type="str", default="all"),
        compartment_id=dict(type="str"),
        node_pool_os_type=dict(type="str", choices=["OL7", "OL8", "UBUNTU"]),
        node_pool_os_arch=dict(type="str", choices=["X86_64", "AARCH64"]),
        node_pool_k8s_version=dict(type="str"),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )
    OciOkeNodePoolOptionsInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
