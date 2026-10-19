# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_oke_node_pool
short_description: Manage an OCI Container Engine for Kubernetes (OKE) node pool
description:
  - Create, update, and delete managed node pools in an OKE cluster.
version_added: "1.2.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_name_lookup_options
  - ansible.oci.oci_wait_options
  - ansible.oci.oci_tags_options
notes:
  - Node pool create, update, and delete are asynchronous OCI work requests; with
    C(wait=true) the module waits for the work request to succeed before returning.
options:
  state:
    description:
      - The desired state of the node pool.
    type: str
    choices: [present, absent]
    default: present
  node_pool_id:
    description:
      - The OCID of the node pool to manage.
      - Required to distinguish between multiple node pools that share the same
        scoped C(name).
      - Use C(id) as an alias.
    type: str
  name:
    description:
      - The node pool name.
      - Required when creating a node pool.
      - When C(node_pool_id) is omitted, name lookup is scoped by C(compartment_id)
        and C(cluster_id).
      - Renamed in place for an existing node pool.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the node pool.
      - Required when creating a node pool and when looking up by name.
      - The module does not move an existing node pool to another compartment.
    type: str
  cluster_id:
    description:
      - The OCID of the OKE cluster the node pool belongs to.
      - Required when creating a node pool and when looking up by name.
      - Immutable after creation.
    type: str
  kubernetes_version:
    description:
      - The Kubernetes version to run on the nodes in this pool.
      - When omitted while creating a node pool, the module defaults to the parent
        cluster's control-plane Kubernetes version.
      - For an existing node pool, changing this value upgrades the nodes in place.
        Setting it to the pool's current version is idempotent. The requested
        version must be one OCI allows for the pool; an unsupported version fails
        the module through the OCI API.
    type: str
  node_shape:
    description:
      - The compute shape of the nodes in the pool.
      - Required when creating a node pool.
    type: str
  node_shape_config:
    description:
      - The shape configuration for flexible node shapes.
      - Reconciled in place; only the sub-options you set are compared.
    type: dict
    suboptions:
      ocpus:
        description:
          - The number of OCPUs for each node.
        type: float
      memory_in_gbs:
        description:
          - The amount of memory in gigabytes for each node.
        type: float
  node_source_details:
    description:
      - The source image for the nodes in the pool.
      - Required when creating a node pool; OCI does not select a default node
        image. Use M(ansible.oci.oci_oke_node_pool_options_info) to find a
        supported image for the chosen shape, OS, and Kubernetes version.
      - Applied only at create time; the module does not reconcile it afterwards.
    type: dict
    suboptions:
      image_id:
        description:
          - The OCID of the image used to boot each node.
        type: str
      boot_volume_size_in_gbs:
        description:
          - The size of each node's boot volume in gigabytes.
        type: int
  node_config_details:
    description:
      - The placement and node configuration for the pool.
      - Reconciled in place; only the sub-options you set are compared.
    type: dict
    suboptions:
      size:
        description:
          - The number of nodes in the pool.
        type: int
      nsg_ids:
        description:
          - OCIDs of network security groups applied to each node's primary VNIC.
        type: list
        elements: str
      kms_key_id:
        description:
          - The OCID of the KMS key used to encrypt the nodes' boot volumes.
        type: str
      is_pv_encryption_in_transit_enabled:
        description:
          - Whether in-transit encryption is enabled for the nodes' volumes.
        type: bool
      freeform_tags:
        description:
          - Free-form tags applied to the nodes in the pool.
          - "Example: C({\"Department\": \"Finance\"})"
        type: dict
      defined_tags:
        description:
          - Defined tags applied to the nodes in the pool.
          - "Example: C({\"Operations\": {\"CostCenter\": \"42\"}})"
        type: dict
      placement_configs:
        description:
          - The placement configuration for the pool's nodes across availability
            domains and subnets.
        type: list
        elements: dict
        suboptions:
          availability_domain:
            description:
              - The availability domain the nodes are placed in.
            type: str
          subnet_id:
            description:
              - The OCID of the subnet the nodes are placed in.
            type: str
          capacity_reservation_id:
            description:
              - The OCID of the compute capacity reservation the nodes use.
            type: str
          fault_domains:
            description:
              - The fault domains the nodes are placed in.
            type: list
            elements: str
      node_pool_pod_network_option_details:
        description:
          - The CNI and pod networking configuration for the nodes.
        type: dict
        suboptions:
          cni_type:
            description:
              - The CNI used by the node pool.
            type: str
            choices: [oci_vcn_ip_native, flannel_overlay]
          max_pods_per_node:
            description:
              - The maximum number of pods per node.
              - Only used with C(cni_type=oci_vcn_ip_native).
            type: int
          pod_nsg_ids:
            description:
              - OCIDs of network security groups applied to the pods.
              - Only used with C(cni_type=oci_vcn_ip_native).
            type: list
            elements: str
          pod_subnet_ids:
            description:
              - OCIDs of the subnets the pods are placed in.
              - Only used with C(cni_type=oci_vcn_ip_native).
            type: list
            elements: str
  subnet_ids:
    description:
      - OCIDs of the subnets the nodes are placed in.
      - Legacy placement option; prefer C(node_config_details.placement_configs).
      - Reconciled in place; compared order-insensitively.
    type: list
    elements: str
  quantity_per_subnet:
    description:
      - The number of nodes to place in each subnet in C(subnet_ids).
      - Legacy sizing option; prefer C(node_config_details.size).
      - Reconciled in place.
    type: int
  initial_node_labels:
    description:
      - Kubernetes labels applied to each node when it joins the pool.
      - Reconciled in place; compared order-insensitively.
    type: list
    elements: dict
    suboptions:
      key:
        description:
          - The label key.
        type: str
      value:
        description:
          - The label value.
        type: str
  ssh_public_key:
    description:
      - The SSH public key authorized on each node.
      - Reconciled in place.
    type: str
  node_metadata:
    description:
      - Arbitrary key/value metadata applied to each node.
      - Reconciled in place.
    type: dict
  node_eviction_node_pool_settings:
    description:
      - The node eviction settings applied when nodes are terminated.
      - Applied only at create time; the module does not reconcile it afterwards.
    type: dict
    suboptions:
      eviction_grace_duration:
        description:
          - The grace period, as an ISO 8601 duration, before a node is evicted.
        type: str
      is_force_delete_after_grace_duration:
        description:
          - Whether to force delete a node after the grace period elapses.
        type: bool
  node_pool_cycling_details:
    description:
      - The node pool cycling configuration used when nodes are replaced.
      - Applied only at create time; the module does not reconcile it afterwards.
    type: dict
    suboptions:
      is_node_cycling_enabled:
        description:
          - Whether node cycling is enabled for the pool.
        type: bool
      maximum_unavailable:
        description:
          - The maximum number or percentage of nodes that can be unavailable
            during cycling.
        type: str
      maximum_surge:
        description:
          - The maximum number or percentage of extra nodes added during cycling.
        type: str
      cycle_modes:
        description:
          - The cycling modes used when replacing nodes.
        type: list
        elements: str
"""

EXAMPLES = r"""
- name: Create a node pool with a flexible shape
  ansible.oci.oci_oke_node_pool:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    cluster_id: ocid1.cluster.oc1..example
    name: example-pool
    node_shape: VM.Standard.E4.Flex
    node_shape_config:
      ocpus: 2
      memory_in_gbs: 16
    node_source_details:
      image_id: ocid1.image.oc1..example
    node_config_details:
      size: 3
      placement_configs:
        - availability_domain: AD-1
          subnet_id: ocid1.subnet.oc1..nodes
    freeform_tags:
      environment: production
  register: created_pool

- name: Scale the node pool and rename it
  ansible.oci.oci_oke_node_pool:
    node_pool_id: "{{ created_pool.resource.id }}"
    name: example-pool-scaled
    node_config_details:
      size: 5

- name: Upgrade the node pool Kubernetes version
  ansible.oci.oci_oke_node_pool:
    node_pool_id: "{{ created_pool.resource.id }}"
    kubernetes_version: v1.30.1

- name: Delete a node pool by OCID
  ansible.oci.oci_oke_node_pool:
    state: absent
    node_pool_id: "{{ created_pool.resource.id }}"

- name: Delete a uniquely named node pool without providing node_pool_id
  ansible.oci.oci_oke_node_pool:
    state: absent
    compartment_id: ocid1.compartment.oc1..example
    cluster_id: ocid1.cluster.oc1..example
    name: example-pool
"""

RETURN = r"""
resource:
  description:
    - The node pool resource.
    - With C(wait=false), the resource may reflect an operation still in progress,
      or contain only C(id) if OCI has not exposed the node pool yet.
    - Changes predicted in check mode do not return a resource.
  returned: when state is present and no change is predicted in check mode
  type: dict
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
    OCI_COMMON_ARGS,
    build_model,
    filter_none_values,
    import_oci_sdk,
    normalize_enum_values,
    values_differ_as_subset,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

oci = import_oci_sdk()[0]

CREATE_REQUIRED_FIELDS = (
    "compartment_id",
    "cluster_id",
    "name",
    "node_shape",
    "node_source_details",
)
NODE_POOL_ENTITY_TYPE = "nodepool"
WORK_REQUEST_ID_HEADER = "opc-work-request-id"

# Module inputs use lowercase snake_case choices (Ansible convention), while OCI's
# wire format and returned resources use upper-case constants (for example
# "oci_vcn_ip_native" -> "OCI_VCN_IP_NATIVE"). ``main`` normalizes module params
# through normalize_enum_values once, so the model builders and idempotency
# comparisons all see the same upper-case vocabulary as the serialized resource.
ENUM_KEYS = frozenset({"cni_type"})


def _build_node_source_details(node_source_details):
    """Build the OCI node source model from module input.

    Args:
        node_source_details: Node source mapping, or None.

    Returns:
        A NodeSourceViaImageDetails model, or None when unset. Only image
        sources are supported, so the model's ``source_type`` is fixed to
        ``IMAGE`` by the SDK subclass.
    """
    return build_model(
        node_source_details,
        oci.container_engine.models.NodeSourceViaImageDetails,
        ("image_id", "boot_volume_size_in_gbs"),
    )


def _build_node_shape_config(node_shape_config, model_class):
    """Build an OCI node shape config model from module input.

    Args:
        node_shape_config: Shape configuration mapping, or None.
        model_class: The create or update shape-config model class to build.

    Returns:
        A ``model_class`` instance, or None when unset.
    """
    return build_model(
        node_shape_config, model_class, ("ocpus", "memory_in_gbs")
    )


def _build_initial_node_labels(initial_node_labels):
    """Build the OCI initial node label models from module input.

    Args:
        initial_node_labels: List of key/value label mappings, or None.

    Returns:
        A list of KeyValue models, or None when unset.
    """
    if initial_node_labels is None:
        return None
    return [
        oci.container_engine.models.KeyValue(**filter_none_values(label))
        for label in initial_node_labels
    ]


def _build_pod_network_option(pod_network_option):
    """Build the OCI pod network option model from module input.

    The concrete SDK model depends on ``cni_type``: flannel overlay carries no
    extra fields, while OCI VCN-native pod networking carries pod subnet and NSG
    details.

    Args:
        pod_network_option: Pod network option mapping, or None.

    Returns:
        A NodePoolPodNetworkOptionDetails subclass instance, or None when unset.
    """
    if pod_network_option is None:
        return None
    if pod_network_option.get("cni_type") == "FLANNEL_OVERLAY":
        return oci.container_engine.models.FlannelOverlayNodePoolPodNetworkOptionDetails()
    return build_model(
        pod_network_option,
        oci.container_engine.models.OciVcnIpNativeNodePoolPodNetworkOptionDetails,
        ("max_pods_per_node", "pod_nsg_ids", "pod_subnet_ids"),
    )


def _build_placement_configs(placement_configs):
    """Build the OCI placement config models from module input.

    Args:
        placement_configs: List of placement mappings, or None.

    Returns:
        A list of NodePoolPlacementConfigDetails models, or None when unset.
    """
    if placement_configs is None:
        return None
    return [
        build_model(
            placement_config,
            oci.container_engine.models.NodePoolPlacementConfigDetails,
            (
                "availability_domain",
                "subnet_id",
                "capacity_reservation_id",
                "fault_domains",
            ),
        )
        for placement_config in placement_configs
    ]


def _build_node_config_details(node_config_details, model_class):
    """Build an OCI node config details model from module input.

    Args:
        node_config_details: Node configuration mapping, or None.
        model_class: The create or update node-config model class to build.

    Returns:
        A ``model_class`` instance, or None when unset.
    """
    if node_config_details is None:
        return None
    details = filter_none_values(
        {
            "size": node_config_details.get("size"),
            "nsg_ids": node_config_details.get("nsg_ids"),
            "kms_key_id": node_config_details.get("kms_key_id"),
            "is_pv_encryption_in_transit_enabled": node_config_details.get(
                "is_pv_encryption_in_transit_enabled"
            ),
            "freeform_tags": node_config_details.get("freeform_tags"),
            "defined_tags": node_config_details.get("defined_tags"),
            "placement_configs": _build_placement_configs(
                node_config_details.get("placement_configs")
            ),
            "node_pool_pod_network_option_details": _build_pod_network_option(
                node_config_details.get("node_pool_pod_network_option_details")
            ),
        }
    )
    return model_class(**details)


def _build_node_eviction_settings(settings):
    """Build the OCI node eviction settings model from module input.

    Args:
        settings: Node eviction settings mapping, or None.

    Returns:
        A NodeEvictionNodePoolSettings model, or None when unset.
    """
    return build_model(
        settings,
        oci.container_engine.models.NodeEvictionNodePoolSettings,
        ("eviction_grace_duration", "is_force_delete_after_grace_duration"),
    )


def _build_node_pool_cycling_details(cycling_details):
    """Build the OCI node pool cycling details model from module input.

    Args:
        cycling_details: Node pool cycling mapping, or None.

    Returns:
        A NodePoolCyclingDetails model, or None when unset.
    """
    return build_model(
        cycling_details,
        oci.container_engine.models.NodePoolCyclingDetails,
        (
            "is_node_cycling_enabled",
            "maximum_unavailable",
            "maximum_surge",
            "cycle_modes",
        ),
    )


def build_create_node_pool_details(params):
    """Build the OCI create-node-pool model from module parameters.

    Args:
        params: Ansible module parameters for the new node pool.

    Returns:
        A CreateNodePoolDetails model.
    """
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "cluster_id": params.get("cluster_id"),
            "name": params.get("name"),
            "kubernetes_version": params.get("kubernetes_version"),
            "node_shape": params.get("node_shape"),
            "node_shape_config": _build_node_shape_config(
                params.get("node_shape_config"),
                oci.container_engine.models.CreateNodeShapeConfigDetails,
            ),
            "node_source_details": _build_node_source_details(
                params.get("node_source_details")
            ),
            "node_config_details": _build_node_config_details(
                params.get("node_config_details"),
                oci.container_engine.models.CreateNodePoolNodeConfigDetails,
            ),
            "subnet_ids": params.get("subnet_ids"),
            "quantity_per_subnet": params.get("quantity_per_subnet"),
            "initial_node_labels": _build_initial_node_labels(
                params.get("initial_node_labels")
            ),
            "ssh_public_key": params.get("ssh_public_key"),
            "node_metadata": params.get("node_metadata"),
            "node_eviction_node_pool_settings": _build_node_eviction_settings(
                params.get("node_eviction_node_pool_settings")
            ),
            "node_pool_cycling_details": _build_node_pool_cycling_details(
                params.get("node_pool_cycling_details")
            ),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.container_engine.models.CreateNodePoolDetails(**details)


class OciOkeNodePoolModule(OciResourceBase):
    """Concrete resource adapter for OKE node pools."""

    @property
    def client_class(self):
        """Return the Container Engine service client required by this adapter."""
        return oci.container_engine.ContainerEngineClient

    resource_id_param = "node_pool_id"
    list_resource_method = "list_node_pools"
    # Node pools are scoped by cluster in addition to compartment, so name lookup
    # requires both compartment_id (from common_list_filter_params) and cluster_id.
    list_filter_params = ("cluster_id",)
    # The NodePool SDK model exposes its display field as ``name`` rather than the
    # ``display_name`` used by most OCI resources, so scoped name lookup and
    # result serialization must resolve against ``name``.
    name_response_field = "name"
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "node pool"
    update_field_specs = (
        UpdateFieldSpec(param_name="name", is_mutable=True),
        UpdateFieldSpec(param_name="node_metadata", is_mutable=True),
        UpdateFieldSpec(param_name="ssh_public_key", is_mutable=True),
        UpdateFieldSpec(param_name="node_shape", is_mutable=True),
        UpdateFieldSpec(param_name="quantity_per_subnet", is_mutable=True),
        UpdateFieldSpec(
            param_name="subnet_ids",
            is_mutable=True,
            compare="sorted_list",
        ),
        UpdateFieldSpec(
            param_name="compartment_id",
            is_mutable=False,
            immutable_reason="OCI does not move node pools through update",
        ),
        UpdateFieldSpec(
            param_name="cluster_id",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="kubernetes_version",
            is_mutable=True,
            strategy="plan_node_pool_kubernetes_upgrade",
        ),
        UpdateFieldSpec(
            param_name="node_config_details",
            is_mutable=True,
            strategy="plan_node_config_details",
        ),
        UpdateFieldSpec(
            param_name="node_shape_config",
            is_mutable=True,
            strategy="plan_node_shape_config",
        ),
        UpdateFieldSpec(
            param_name="initial_node_labels",
            is_mutable=True,
            strategy="plan_initial_node_labels",
        ),
    )

    def get_resource_response(self, resource_id):
        """Fetch a node pool for base lookups and wait polling.

        This override supplies the concrete SDK getter required by the base
        resource helper.

        Args:
            resource_id: OCI node pool identifier.

        Returns:
            The SDK response from get_node_pool.
        """
        return self.call_with_retry(
            self.client.get_node_pool,
            node_pool_id=resource_id,
        )

    def hydrate_named_resource(self, resource):
        """Re-fetch a name-resolved node pool to return the full model.

        ``list_node_pools`` returns a NodePoolSummary that omits ``node_metadata``
        (which participates in idempotency), so re-fetching with get_node_pool
        yields the full model and avoids spurious update drift.

        Args:
            resource: The NodePoolSummary matched by scoped name lookup.

        Returns:
            The full NodePool model, or the summary if the re-fetch returns None.
        """
        full_resource = self.get_resource_by_id(resource.id)
        return full_resource if full_resource is not None else resource

    def _work_request_id(self, response, operation):
        """Return the work request ID from an async operation response.

        Args:
            response: The SDK response from a create/update/delete call.
            operation: Operation name used in the failure message.

        Returns:
            The work request OCID carried in the response headers.
        """
        work_request_id = (response.headers or {}).get(WORK_REQUEST_ID_HEADER)
        if not work_request_id:
            self.module.fail_json(
                msg=(
                    f"The OCI node pool {operation} response did not include a "
                    "work request ID."
                )
            )
        return work_request_id

    def _node_pool_id_from_work_request(self, work_request):
        """Return the node pool OCID recorded on a work request.

        Args:
            work_request: The work request model to inspect.

        Returns:
            The node pool OCID from the work request resources, or None.
        """
        for resource in getattr(work_request, "resources", None) or []:
            entity_type = getattr(resource, "entity_type", None) or ""
            identifier = getattr(resource, "identifier", None)
            if entity_type.lower() == NODE_POOL_ENTITY_TYPE and identifier:
                return identifier
        return None

    def _get_node_pool_or_id(self, node_pool_id):
        """Return the current node pool model, or an ID-only result.

        Args:
            node_pool_id: OCI node pool identifier.

        Returns:
            The NodePool model, or a dict with only ``id`` when it is unavailable.
        """
        resource = self.get_resource_by_id(node_pool_id)
        return resource if resource is not None else {"id": node_pool_id}

    def _cluster_kubernetes_version(self):
        """Return the parent cluster's control-plane Kubernetes version.

        Used to default ``kubernetes_version`` at create time when the caller
        omits it, so a node pool matches its cluster by default.

        Returns:
            The cluster's Kubernetes version string.
        """
        cluster_id = self.module.params.get("cluster_id")
        response = self.call_with_retry(
            self.client.get_cluster,
            cluster_id=cluster_id,
        )
        version = getattr(response.data, "kubernetes_version", None)
        if not version:
            self.module.fail_json(
                msg=(
                    "Could not determine a default kubernetes_version from "
                    f"cluster {cluster_id}."
                )
            )
        return version

    def create_resource(self):
        """Create a node pool and resolve its result through OCI work requests.

        This override drives the asynchronous create work request and resolves
        the node pool OCID from the work request resources. When the caller omits
        ``kubernetes_version``, it is defaulted to the parent cluster's version.

        Returns:
            The created NodePool model, or an ID-only result when wait=False.
        """
        if self.module.params.get("kubernetes_version") is None:
            self.module.params["kubernetes_version"] = (
                self._cluster_kubernetes_version()
            )
        response = self.call_with_retry(
            self.client.create_node_pool,
            create_node_pool_details=build_create_node_pool_details(
                self.module.params
            ),
        )
        work_request_id = self._work_request_id(response, "create")
        if self.module.params.get("wait", True):
            work_request = self.wait_for_work_request(self.client, work_request_id)
        else:
            work_request = self.call_with_retry(
                self.client.get_work_request, work_request_id
            ).data
        node_pool_id = self._node_pool_id_from_work_request(work_request)
        if not node_pool_id:
            self.module.fail_json(
                msg=(
                    f"Work request {work_request_id} did not include a node pool ID."
                )
            )
        return self._get_node_pool_or_id(node_pool_id)

    def plan_node_pool_kubernetes_upgrade(
        self, resource, resource_dict, spec, desired_value
    ):
        """Plan an in-place node pool Kubernetes upgrade.

        An upgrade is planned only when the requested version differs from the
        pool's current version; requesting the current version is idempotent.
        OCI validates whether the requested version is a legal target.

        Args:
            resource: Current NodePool model.
            resource_dict: Serialized current node pool attributes.
            spec: The kubernetes_version update field spec.
            desired_value: The requested Kubernetes version.

        Returns:
            A list with a single set operation, or an empty list when the pool
            already runs the requested version.
        """
        if desired_value == resource_dict.get("kubernetes_version"):
            return []
        return [("set", desired_value)]

    @staticmethod
    def _placement_configs_differ(current_configs, desired_configs):
        """Return True when the desired placement configs differ from current.

        Placement entries are matched order-insensitively. Each desired entry is
        compared only on the keys that entry actually supplied, so OCI-populated
        extras (for example default ``fault_domains``) never register as drift.
        A key omitted from one desired entry is not required of the others, even
        when a sibling entry supplies it. A differing entry count is always a
        change.

        Args:
            current_configs: Serialized current placement config list.
            desired_configs: Requested placement config list, with ``None``
                placeholders for unset sub-options.

        Returns:
            True when the placement configuration differs, otherwise False.
        """
        if len(current_configs) != len(desired_configs):
            return True

        remaining = list(current_configs)
        for desired in desired_configs:
            provided = {
                key: value for key, value in desired.items() if value is not None
            }
            for index, current in enumerate(remaining):
                if all(
                    current.get(key) == value for key, value in provided.items()
                ):
                    del remaining[index]
                    break
            else:
                return True

        return False

    def plan_node_config_details(self, resource, resource_dict, spec, desired_value):
        """Plan an in-place node config reconcile.

        Only the sub-options the caller provided are compared against the current
        configuration, so an omitted sub-option never forces a change. The
        ``placement_configs`` list and ``nsg_ids`` are compared
        order-insensitively; remaining sub-options use a subset comparison that
        ignores fields the caller did not set.

        Args:
            resource: Current NodePool model.
            resource_dict: Serialized current node pool attributes.
            spec: The node_config_details update field spec.
            desired_value: The requested node configuration mapping.

        Returns:
            A list with a single set operation, or an empty list when the
            configuration already matches the requested values.
        """
        current = resource_dict.get("node_config_details") or {}
        for key, value in desired_value.items():
            if value is None:
                continue

            if key == "placement_configs" and self._placement_configs_differ(
                current.get("placement_configs") or [], value
            ):
                return [("set", desired_value)]

            if key == "nsg_ids" and sorted(current.get("nsg_ids") or []) != sorted(value):
                return [("set", desired_value)]

            if key not in ("placement_configs", "nsg_ids") and values_differ_as_subset(current.get(key), value):
                return [("set", desired_value)]

        return []

    def plan_node_shape_config(self, resource, resource_dict, spec, desired_value):
        """Plan an in-place node shape config reconcile.

        Only the sub-options the caller provided are compared, so an omitted
        sub-option never forces a change.

        Args:
            resource: Current NodePool model.
            resource_dict: Serialized current node pool attributes.
            spec: The node_shape_config update field spec.
            desired_value: The requested shape configuration mapping.

        Returns:
            A list with a single set operation, or an empty list when the shape
            configuration already matches the requested values.
        """
        current = resource_dict.get("node_shape_config") or {}
        if values_differ_as_subset(current, desired_value):
            return [("set", desired_value)]
        return []

    def plan_initial_node_labels(self, resource, resource_dict, spec, desired_value):
        """Plan an in-place initial node label reconcile.

        Labels are compared order-insensitively by key/value pair, so reordering
        the same labels is idempotent.

        Args:
            resource: Current NodePool model.
            resource_dict: Serialized current node pool attributes.
            spec: The initial_node_labels update field spec.
            desired_value: The requested list of label mappings.

        Returns:
            A list with a single set operation, or an empty list when the labels
            already match the requested values.
        """
        current = resource_dict.get("initial_node_labels") or []
        current_pairs = sorted(
            (label.get("key"), label.get("value")) for label in current
        )
        desired_pairs = sorted(
            (label.get("key"), label.get("value")) for label in desired_value
        )
        if current_pairs != desired_pairs:
            return [("set", desired_value)]
        return []

    def build_update_details(self, update_model_fields):
        """Build the OCI update-node-pool model from planned field changes.

        Args:
            update_model_fields: Fields selected by the update planner.

        Returns:
            An UpdateNodePoolDetails model.
        """
        return oci.container_engine.models.UpdateNodePoolDetails(**update_model_fields)

    def update_resource(self, resource):
        """Apply planned node pool updates via a work request.

        This override drives the asynchronous update work request, because the
        update endpoint returns only a work request rather than the node pool.
        Strategy-driven nested changes are folded into the same update-details
        model alongside the simple field assignments.

        Args:
            resource: Current NodePool model.

        Returns:
            The updated NodePool model, or an ID-only result when wait=False.
        """
        update_plan = self.get_update_plan(resource)
        update_fields = dict(update_plan["update_model_fields"])

        for strategy_operation in update_plan["strategy_operations"]:
            param_name = strategy_operation["param_name"]
            value = strategy_operation["operations"][0][1]
            if param_name == "kubernetes_version":
                update_fields["kubernetes_version"] = value
            elif param_name == "node_config_details":
                update_fields["node_config_details"] = _build_node_config_details(
                    value,
                    oci.container_engine.models.UpdateNodePoolNodeConfigDetails,
                )
            elif param_name == "node_shape_config":
                update_fields["node_shape_config"] = _build_node_shape_config(
                    value,
                    oci.container_engine.models.UpdateNodeShapeConfigDetails,
                )
            elif param_name == "initial_node_labels":
                update_fields["initial_node_labels"] = _build_initial_node_labels(
                    value
                )

        if not update_fields:
            return resource

        response = self.call_with_retry(
            self.client.update_node_pool,
            node_pool_id=resource.id,
            update_node_pool_details=self.build_update_details(update_fields),
        )
        if self.module.params.get("wait", True):
            work_request_id = self._work_request_id(response, "update")
            self.wait_for_work_request(self.client, work_request_id)
        return self._get_node_pool_or_id(resource.id)

    def delete_resource(self, resource):
        """Delete the node pool and wait on its delete work request.

        The delete endpoint returns only a work request rather than driving the
        node pool lifecycle state synchronously, so this override waits on the
        work request itself. The shared delete call is reused so a 409 from
        dependent resources is translated into a clearer failure.

        Args:
            resource: NodePool model to delete.

        Returns:
            The deleted NodePool model, or an ID-only result when wait=False.
        """
        response = self.call_delete_fn(
            resource,
            self.client.delete_node_pool,
            node_pool_id=resource.id,
        )
        if self.module.params.get("wait", True):
            work_request_id = self._work_request_id(response, "delete")
            self.wait_for_work_request(self.client, work_request_id)
        return self._get_node_pool_or_id(resource.id)


def main():
    """Build the module argument spec and run the OKE node pool resource module."""
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        node_pool_id=dict(type="str"),
        cluster_id=dict(type="str"),
        kubernetes_version=dict(type="str"),
        node_shape=dict(type="str"),
        node_shape_config=dict(
            type="dict",
            options=dict(
                ocpus=dict(type="float"),
                memory_in_gbs=dict(type="float"),
            ),
        ),
        node_source_details=dict(
            type="dict",
            options=dict(
                image_id=dict(type="str"),
                boot_volume_size_in_gbs=dict(type="int"),
            ),
        ),
        node_config_details=dict(
            type="dict",
            options=dict(
                size=dict(type="int"),
                nsg_ids=dict(type="list", elements="str"),
                kms_key_id=dict(type="str"),
                is_pv_encryption_in_transit_enabled=dict(type="bool"),
                freeform_tags=dict(type="dict"),
                defined_tags=dict(type="dict"),
                placement_configs=dict(
                    type="list",
                    elements="dict",
                    options=dict(
                        availability_domain=dict(type="str"),
                        subnet_id=dict(type="str"),
                        capacity_reservation_id=dict(type="str"),
                        fault_domains=dict(type="list", elements="str"),
                    ),
                ),
                node_pool_pod_network_option_details=dict(
                    type="dict",
                    options=dict(
                        cni_type=dict(
                            type="str",
                            choices=["oci_vcn_ip_native", "flannel_overlay"],
                        ),
                        max_pods_per_node=dict(type="int"),
                        pod_nsg_ids=dict(type="list", elements="str"),
                        pod_subnet_ids=dict(type="list", elements="str"),
                    ),
                ),
            ),
        ),
        subnet_ids=dict(type="list", elements="str"),
        quantity_per_subnet=dict(type="int"),
        initial_node_labels=dict(
            type="list",
            elements="dict",
            options=dict(
                key=dict(type="str", no_log=False),
                value=dict(type="str"),
            ),
        ),
        ssh_public_key=dict(type="str", no_log=False),
        node_metadata=dict(type="dict"),
        node_eviction_node_pool_settings=dict(
            type="dict",
            options=dict(
                eviction_grace_duration=dict(type="str"),
                is_force_delete_after_grace_duration=dict(type="bool"),
            ),
        ),
        node_pool_cycling_details=dict(
            type="dict",
            options=dict(
                is_node_cycling_enabled=dict(type="bool"),
                maximum_unavailable=dict(type="str"),
                maximum_surge=dict(type="str"),
                cycle_modes=dict(type="list", elements="str"),
            ),
        ),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )
    # Convert the lowercase snake_case enum choices to the upper-case constants
    # OCI expects, so the builders and comparisons downstream all work against
    # the SDK vocabulary. See ENUM_KEYS. "cni_type" is normalized at its own
    # path, node_config_details.node_pool_pod_network_option_details, rather
    # than by recursing through all of module.params (or even all of
    # node_config_details) -- node_config_details also carries
    # freeform_tags/defined_tags as siblings, and recursing into those would
    # rewrite user-supplied tag keys/values that happen to match an enum
    # name.
    node_config_details = module.params.get("node_config_details") or {}
    pod_network_option_details = node_config_details.get(
        "node_pool_pod_network_option_details"
    )
    if pod_network_option_details:
        node_config_details["node_pool_pod_network_option_details"] = (
            normalize_enum_values(pod_network_option_details, ENUM_KEYS)
        )
    OciOkeNodePoolModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
