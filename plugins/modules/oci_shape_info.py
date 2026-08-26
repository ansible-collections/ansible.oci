# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_shape_info
short_description: Retrieve Compute shape information from Oracle Cloud Infrastructure
description:
  - Retrieve one or more OCI Compute shapes available in a compartment.
  - OCI shapes do not have OCIDs; the returned C(shape) value is the shape name
    that can be passed directly to C(ansible.oci.oci_instance).
  - This is a read-only module and does not modify resources.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  compartment_id:
    description:
      - The OCID of the compartment to list shapes from.
      - Required for all shape queries.
    type: str
    required: true
  availability_domain:
    description:
      - Filter listed shapes by availability domain.
      - Exact availability domain names are tenancy-specific, for example
        C(Uocm:PHX-AD-1).
    type: str
  image_id:
    description:
      - Filter listed shapes by compatibility with an image OCID.
    type: str
  shape:
    description:
      - Filter listed shapes by exact shape name.
      - This expects the exact OCI shape name returned by C(oci_shape_info), for
        example C(VM.Standard.E4.Flex).
    type: str
notes:
  - Use C(image_id) together with this module to discover which shapes are
    compatible with a chosen image.
  - Use an unfiltered C(oci_shape_info) query first if you need to discover the
    current shape names available in your region, compartment, and availability
    domain.
  - Use M(ansible.oci.oci_availability_domain_info) to discover valid
    C(availability_domain) values instead of hardcoding tenancy-specific names.
"""

EXAMPLES = r"""
- name: List all shapes available in a compartment
  ansible.oci.oci_shape_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List shapes compatible with a specific image
  ansible.oci.oci_shape_info:
    compartment_id: ocid1.compartment.oc1..example
    image_id: ocid1.image.oc1..example

- name: Filter the list down to one shape definition by exact name
  ansible.oci.oci_shape_info:
    compartment_id: ocid1.compartment.oc1..example
    shape: VM.Standard.E4.Flex
"""

RETURN = r"""
shapes:
  description: List of shapes that matched the query.
  returned: always
  type: list
  elements: dict
  contains:
    shape:
      description: The shape name that can be forwarded to C(ansible.oci.oci_instance).
      type: str
      returned: always
      sample: VM.Standard.E4.Flex
    ocpus:
      description: The default number of OCPUs available to the shape.
      type: float
      returned: when supported
      sample: 1
    memory_in_gbs:
      description: The default memory available to the shape, in GBs.
      type: float
      returned: when supported
      sample: 16
    processor_description:
      description: The processor description for the shape.
      type: str
      returned: when supported
      sample: AMD EPYC
    gpus:
      description: The number of GPUs available to the shape.
      type: int
      returned: when supported
      sample: 0
    gpu_description:
      description: The GPU description for the shape.
      type: str
      returned: when supported
      sample: null
    is_flexible:
      description: Whether the shape supports flexible OCPU and memory configuration.
      type: bool
      returned: when supported
      sample: true
    ocpu_options:
      description: Flexible OCPU configuration details for the shape.
      type: dict
      returned: when supported
    memory_options:
      description: Flexible memory configuration details for the shape.
      type: dict
      returned: when supported
    networking_bandwidth_in_gbps:
      description: The default networking bandwidth for the shape.
      type: float
      returned: when supported
      sample: 1
    max_vnic_attachments:
      description: The maximum number of VNIC attachments supported by the shape.
      type: int
      returned: when supported
      sample: 2
    platform_config_options:
      description:
        - The platform configuration options supported by the shape, if any.
        - Use C(platform_config_options.type) as the C(platform_config.type)
          value in M(ansible.oci.oci_instance) for an instance launched with
          this shape. Shapes that don't support C(platform_config) (for
          example Ampere/ARM shapes) omit this field.
      type: dict
      returned: when supported
      sample: {"type": "AMD_VM"}
    is_billed_for_stopped_instance:
      description: Whether the shape continues to be billed while the instance is stopped.
      type: bool
      returned: when supported
      sample: false
    billing_type:
      description: The billing category of the shape.
      type: str
      returned: when supported
      sample: PAID
    quota_names:
      description: The names of the quotas and limits that apply to this shape.
      type: list
      elements: str
      returned: when supported
      sample: ["standard-e6-core-count", "standard-e6-memory-count"]
    is_subcore:
      description: Whether the shape is a subcore (burstable) shape.
      type: bool
      returned: when supported
      sample: false
    baseline_ocpu_utilizations:
      description:
        - For subcore (burstable) shapes, the allowed baseline OCPU
          utilization values.
      type: list
      elements: str
      returned: when supported
      sample: null
    min_total_baseline_ocpus_required:
      description:
        - For subcore (burstable) shapes, the minimum total baseline OCPUs
          required for the instance.
      type: float
      returned: when supported
      sample: null
    is_live_migration_supported:
      description: Whether the shape supports live migration.
      type: bool
      returned: when supported
      sample: true
    network_ports:
      description: The number of physical network ports available to the shape.
      type: int
      returned: when supported
      sample: 1
    networking_bandwidth_options:
      description: Flexible networking bandwidth configuration details for the shape.
      type: dict
      returned: when supported
    max_vnic_attachment_options:
      description: Flexible maximum VNIC attachment configuration details for the shape.
      type: dict
      returned: when supported
    local_disks:
      description: The number of local (NVMe) disks available to the shape.
      type: int
      returned: when supported
      sample: 0
    local_disks_total_size_in_gbs:
      description: The total size of the local disks available to the shape, in GBs.
      type: float
      returned: when supported
      sample: null
    local_disk_description:
      description: A short description of the local disks available to the shape.
      type: str
      returned: when supported
      sample: null
    rdma_ports:
      description: The number of RDMA (cluster network) ports available to the shape.
      type: int
      returned: when supported
      sample: 0
    rdma_bandwidth_in_gbps:
      description: The networking bandwidth available for RDMA traffic, in Gbps.
      type: int
      returned: when supported
      sample: 0
    resize_compatible_shapes:
      description: Shape names that this shape's instances can be resized to or from.
      type: list
      elements: str
      returned: when supported
    recommended_alternatives:
      description: Alternative shapes recommended in place of this shape, if any.
      type: list
      elements: dict
      returned: when supported
      sample: null
    platform_names:
      description: The platform names supported by the shape, if any.
      type: list
      elements: str
      returned: when supported
      sample: []
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import (
    OciInfoBase,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]


class OciShapeInfoModule(OciInfoBase):
    """Concrete info adapter for OCI Compute shapes."""

    @property
    def client_class(self):
        return oci.core.ComputeClient

    results_key = "shapes"
    list_resource_method = "list_shapes"
    list_filter_params = [
        "compartment_id",
        "availability_domain",
        "image_id",
        "shape",
    ]


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str", required=True),
        availability_domain=dict(type="str"),
        image_id=dict(type="str"),
        shape=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciShapeInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
