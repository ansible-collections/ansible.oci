# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_oke_cluster
short_description: Manage an OCI Container Engine for Kubernetes (OKE) cluster
description:
  - Create, rename, retag, and delete OKE clusters.
version_added: "1.2.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_name_lookup_options
  - ansible.oci.oci_wait_options
  - ansible.oci.oci_tags_options
notes:
  - Cluster create, update, and delete are asynchronous OCI work requests; with
    C(wait=true) the module waits for the work request to succeed before returning.
options:
  state:
    description:
      - The desired state of the cluster.
    type: str
    choices: [present, absent]
    default: present
  cluster_id:
    description:
      - The OCID of the cluster to manage.
      - Required to distinguish between multiple clusters that share the same
        scoped C(name).
      - Use C(id) as an alias.
    type: str
    aliases: [id]
  name:
    description:
      - The cluster name.
      - Required when creating a cluster.
      - When C(cluster_id) is omitted, name lookup is scoped by C(compartment_id).
      - This is the only cluster attribute this module renames in place.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the cluster.
      - Required when creating a cluster and when looking up by name.
      - The module does not move an existing cluster to another compartment.
    type: str
  vcn_id:
    description:
      - The OCID of the VCN the cluster control plane runs in.
      - Required when creating a cluster and immutable afterwards.
    type: str
  kubernetes_version:
    description:
      - The Kubernetes version to run on the cluster control plane.
      - Required when creating a cluster.
      - For an existing cluster, changing this value upgrades the control plane in
        place. The requested version must be one of the cluster's
        C(available_kubernetes_upgrades); requesting a version outside that allowed
        upgrade path fails the module. Setting it to the cluster's current version
        is idempotent. Downgrades are not supported by OCI.
    type: str
  type:
    description:
      - The cluster type.
      - Set only at create time and immutable afterwards.
    type: str
    choices: [BASIC_CLUSTER, ENHANCED_CLUSTER]
  kms_key_id:
    description:
      - The OCID of the KMS key used for cluster encryption.
      - Applied only at create time; the module does not reconcile it afterwards.
    type: str
  endpoint_config:
    description:
      - The network configuration for the cluster control-plane endpoint.
      - Applied only at create time; the module does not reconcile it afterwards.
        Endpoint network security group changes are planned for a dedicated
        C(oci_oke_cluster_network_security_groups) module.
    type: dict
    suboptions:
      subnet_id:
        description:
          - The OCID of the regional subnet that hosts the cluster endpoint.
        type: str
      nsg_ids:
        description:
          - OCIDs of network security groups applied to the cluster endpoint.
        type: list
        elements: str
      is_public_ip_enabled:
        description:
          - Whether the cluster endpoint is assigned a public IP address.
        type: bool
  image_policy_config:
    description:
      - The signed-image verification policy for the cluster.
      - Reconciled in place for an existing cluster. Only the sub-options you set
        are compared; omitted sub-options are left unchanged. Updating the policy
        is idempotent when it already matches the desired state.
    type: dict
    suboptions:
      is_policy_enabled:
        description:
          - Whether signed-image verification is enabled.
        type: bool
      key_details:
        description:
          - The KMS keys used to verify image signatures.
        type: list
        elements: dict
        suboptions:
          kms_key_id:
            description:
              - The OCID of the KMS key used to verify image signatures.
            type: str
  cluster_pod_network_options:
    description:
      - The available CNI types for node pools created in this cluster.
      - Applied only at create time; the module does not reconcile it afterwards.
    type: list
    elements: dict
    suboptions:
      cni_type:
        description:
          - The CNI used by the node pools of this cluster.
        type: str
        choices: [OCI_VCN_IP_NATIVE, FLANNEL_OVERLAY]
  options:
    description:
      - Optional cluster-creation attributes.
      - Applied only at create time; the module does not reconcile them afterwards.
    type: dict
    suboptions:
      service_lb_subnet_ids:
        description:
          - OCIDs of the subnets used for load balancers created by Kubernetes
            services.
        type: list
        elements: str
      ip_families:
        description:
          - The IP families used for cluster pods and services, for example
            C(IPv4) or C(IPv6).
        type: list
        elements: str
      kubernetes_network_config:
        description:
          - The CIDR ranges used by the cluster network.
        type: dict
        suboptions:
          pods_cidr:
            description:
              - The CIDR block used for Kubernetes pods.
            type: str
          services_cidr:
            description:
              - The CIDR block used for Kubernetes services.
            type: str
      add_ons:
        description:
          - The optional cluster add-ons to enable.
        type: dict
        suboptions:
          is_kubernetes_dashboard_enabled:
            description:
              - Whether the Kubernetes dashboard add-on is enabled.
            type: bool
          is_tiller_enabled:
            description:
              - Whether Tiller (Helm) is enabled.
            type: bool
      admission_controller_options:
        description:
          - The admission controller options for the cluster.
        type: dict
        suboptions:
          is_pod_security_policy_enabled:
            description:
              - Whether the pod security policy admission controller is enabled.
            type: bool
"""

EXAMPLES = r"""
- name: Create a basic OKE cluster
  ansible.oci.oci_oke_cluster:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: example-cluster
    vcn_id: ocid1.vcn.oc1..example
    kubernetes_version: v1.29.1
    type: BASIC_CLUSTER
    endpoint_config:
      subnet_id: ocid1.subnet.oc1..example
      is_public_ip_enabled: true
  register: created_cluster

- name: Create an enhanced cluster with network options and tags
  ansible.oci.oci_oke_cluster:
    compartment_id: ocid1.compartment.oc1..example
    name: example-enhanced
    vcn_id: ocid1.vcn.oc1..example
    kubernetes_version: v1.29.1
    type: ENHANCED_CLUSTER
    endpoint_config:
      subnet_id: ocid1.subnet.oc1..endpoint
    cluster_pod_network_options:
      - cni_type: OCI_VCN_IP_NATIVE
    options:
      service_lb_subnet_ids:
        - ocid1.subnet.oc1..lb
      kubernetes_network_config:
        pods_cidr: 10.244.0.0/16
        services_cidr: 10.96.0.0/16
    freeform_tags:
      environment: production

- name: Rename and retag an existing cluster
  ansible.oci.oci_oke_cluster:
    cluster_id: "{{ created_cluster.resource.id }}"
    name: renamed-cluster
    freeform_tags:
      environment: staging

- name: Upgrade the Kubernetes version of an existing cluster
  ansible.oci.oci_oke_cluster:
    cluster_id: "{{ created_cluster.resource.id }}"
    kubernetes_version: v1.30.1

- name: Enable signed-image verification on an existing cluster
  ansible.oci.oci_oke_cluster:
    cluster_id: "{{ created_cluster.resource.id }}"
    image_policy_config:
      is_policy_enabled: true
      key_details:
        - kms_key_id: ocid1.key.oc1..example

- name: Delete a cluster by OCID
  ansible.oci.oci_oke_cluster:
    state: absent
    cluster_id: "{{ created_cluster.resource.id }}"

- name: Delete a uniquely named cluster without providing cluster_id
  ansible.oci.oci_oke_cluster:
    state: absent
    compartment_id: ocid1.compartment.oc1..example
    name: example-cluster
"""

RETURN = r"""
resource:
  description:
    - The cluster resource.
    - With C(wait=false), the resource may reflect an operation still in progress,
      or contain only C(id) if OCI has not exposed the cluster yet.
    - Changes predicted in check mode do not return a resource.
  returned: when state is present and no change is predicted in check mode
  type: dict
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
    OCI_COMMON_ARGS,
    filter_none_values,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

oci = import_oci_sdk()[0]

CREATE_REQUIRED_FIELDS = (
    "compartment_id",
    "name",
    "vcn_id",
    "kubernetes_version",
)
CLUSTER_ENTITY_TYPE = "cluster"
WORK_REQUEST_ID_HEADER = "opc-work-request-id"


def _build_endpoint_config(endpoint_config):
    """Build the OCI cluster endpoint config model from module input.

    Args:
        endpoint_config: Endpoint configuration mapping, or None.

    Returns:
        A CreateClusterEndpointConfigDetails model, or None when unset.
    """
    if endpoint_config is None:
        return None
    details = filter_none_values(
        {
            "subnet_id": endpoint_config.get("subnet_id"),
            "nsg_ids": endpoint_config.get("nsg_ids"),
            "is_public_ip_enabled": endpoint_config.get("is_public_ip_enabled"),
        }
    )
    return oci.container_engine.models.CreateClusterEndpointConfigDetails(**details)


def _build_image_policy_config(image_policy_config):
    """Build the OCI image policy config model from module input.

    Args:
        image_policy_config: Image policy mapping, or None.

    Returns:
        A CreateImagePolicyConfigDetails model, or None when unset.
    """
    if image_policy_config is None:
        return None
    key_details = image_policy_config.get("key_details")
    details = filter_none_values(
        {
            "is_policy_enabled": image_policy_config.get("is_policy_enabled"),
            "key_details": (
                [
                    oci.container_engine.models.KeyDetails(
                        **filter_none_values(key_detail)
                    )
                    for key_detail in key_details
                ]
                if key_details is not None
                else None
            ),
        }
    )
    return oci.container_engine.models.CreateImagePolicyConfigDetails(**details)


def _build_update_image_policy_config(image_policy_config):
    """Build the OCI update image policy config model from module input.

    Args:
        image_policy_config: Image policy mapping, or None.

    Returns:
        An UpdateImagePolicyConfigDetails model, or None when unset.
    """
    if image_policy_config is None:
        return None
    key_details = image_policy_config.get("key_details")
    details = filter_none_values(
        {
            "is_policy_enabled": image_policy_config.get("is_policy_enabled"),
            "key_details": (
                [
                    oci.container_engine.models.KeyDetails(
                        **filter_none_values(key_detail)
                    )
                    for key_detail in key_details
                ]
                if key_details is not None
                else None
            ),
        }
    )
    return oci.container_engine.models.UpdateImagePolicyConfigDetails(**details)


def _build_cluster_pod_network_options(pod_network_options):
    """Build the OCI cluster pod network option models from module input.

    Args:
        pod_network_options: List of pod network option mappings, or None.

    Returns:
        A list of ClusterPodNetworkOptionDetails models, or None when unset.
    """
    if pod_network_options is None:
        return None
    return [
        oci.container_engine.models.ClusterPodNetworkOptionDetails(
            **filter_none_values(option)
        )
        for option in pod_network_options
    ]


def _build_cluster_create_options(options):
    """Build the OCI cluster create options model from module input.

    Args:
        options: Cluster options mapping, or None.

    Returns:
        A ClusterCreateOptions model, or None when unset.
    """
    if options is None:
        return None
    network_config = options.get("kubernetes_network_config")
    add_ons = options.get("add_ons")
    admission_controller_options = options.get("admission_controller_options")
    details = filter_none_values(
        {
            "service_lb_subnet_ids": options.get("service_lb_subnet_ids"),
            "ip_families": options.get("ip_families"),
            "kubernetes_network_config": (
                oci.container_engine.models.KubernetesNetworkConfig(
                    **filter_none_values(network_config)
                )
                if network_config is not None
                else None
            ),
            "add_ons": (
                oci.container_engine.models.AddOnOptions(
                    **filter_none_values(add_ons)
                )
                if add_ons is not None
                else None
            ),
            "admission_controller_options": (
                oci.container_engine.models.AdmissionControllerOptions(
                    **filter_none_values(admission_controller_options)
                )
                if admission_controller_options is not None
                else None
            ),
        }
    )
    return oci.container_engine.models.ClusterCreateOptions(**details)


def build_create_cluster_details(params):
    """Build the OCI create-cluster model from module parameters.

    Args:
        params: Ansible module parameters for the new cluster.

    Returns:
        A CreateClusterDetails model.
    """
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "name": params.get("name"),
            "vcn_id": params.get("vcn_id"),
            "kubernetes_version": params.get("kubernetes_version"),
            "type": params.get("type"),
            "kms_key_id": params.get("kms_key_id"),
            "endpoint_config": _build_endpoint_config(params.get("endpoint_config")),
            "image_policy_config": _build_image_policy_config(
                params.get("image_policy_config")
            ),
            "cluster_pod_network_options": _build_cluster_pod_network_options(
                params.get("cluster_pod_network_options")
            ),
            "options": _build_cluster_create_options(params.get("options")),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.container_engine.models.CreateClusterDetails(**details)


class OciOkeClusterModule(OciResourceBase):
    """Concrete resource adapter for OKE clusters."""

    @property
    def client_class(self):
        """Return the Container Engine service client required by this adapter."""
        return oci.container_engine.ContainerEngineClient

    resource_id_param = "cluster_id"
    list_resource_method = "list_clusters"
    # The Cluster SDK model exposes its display field as ``name`` rather than the
    # ``display_name`` used by most OCI resources, so scoped name lookup and
    # result serialization must resolve against ``name``.
    name_response_field = "name"
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "cluster"
    update_field_specs = (
        UpdateFieldSpec(
            param_name="name",
            is_mutable=True,
        ),
        UpdateFieldSpec(
            param_name="compartment_id",
            is_mutable=False,
            immutable_reason="OCI does not move clusters through update",
        ),
        UpdateFieldSpec(
            param_name="vcn_id",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="type",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="kubernetes_version",
            is_mutable=True,
            strategy="plan_kubernetes_version_upgrade",
        ),
        UpdateFieldSpec(
            param_name="image_policy_config",
            is_mutable=True,
            strategy="plan_image_policy_config",
        ),
    )

    def get_resource_response(self, resource_id):
        """Fetch a cluster for base lookups and wait polling.

        This override supplies the concrete SDK getter required by the base
        resource helper.

        Args:
            resource_id: OCI cluster identifier.

        Returns:
            The SDK response from get_cluster.
        """
        return self.call_with_retry(
            self.client.get_cluster,
            cluster_id=resource_id,
        )

    def hydrate_named_resource(self, resource):
        """Re-fetch a name-resolved cluster to return the full model.

        ``list_clusters`` returns a ClusterSummary; re-fetching with get_cluster
        yields the full model so results carry the complete attribute set.

        Args:
            resource: The ClusterSummary matched by scoped name lookup.

        Returns:
            The full Cluster model, or the summary if the re-fetch returns None.
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
                msg=f"The OCI {operation} response did not include a work request ID."
            )
        return work_request_id

    def _cluster_id_from_work_request(self, work_request):
        """Return the cluster OCID recorded on a work request.

        Args:
            work_request: The work request model to inspect.

        Returns:
            The cluster OCID from the work request resources, or None.
        """
        for resource in getattr(work_request, "resources", None) or []:
            entity_type = getattr(resource, "entity_type", None) or ""
            identifier = getattr(resource, "identifier", None)
            if entity_type.lower() == CLUSTER_ENTITY_TYPE and identifier:
                return identifier
        return None

    def _get_cluster_or_id(self, cluster_id):
        """Return the current cluster model, or an ID-only result.

        Args:
            cluster_id: OCI cluster identifier.

        Returns:
            The Cluster model, or a dict with only ``id`` when it is unavailable.
        """
        resource = self.get_resource_by_id(cluster_id)
        return resource if resource is not None else {"id": cluster_id}

    def create_resource(self):
        """Create a cluster and resolve its result through OCI work requests.

        This override drives the asynchronous create work request and resolves
        the cluster OCID from the work request resources.

        Returns:
            The created Cluster model, or an ID-only result when wait=False.
        """
        response = self.call_with_retry(
            self.client.create_cluster,
            create_cluster_details=build_create_cluster_details(self.module.params),
        )
        work_request_id = self._work_request_id(response, "create")
        if self.module.params.get("wait", True):
            work_request = self.wait_for_work_request(self.client, work_request_id)
        else:
            work_request = self.call_with_retry(
                self.client.get_work_request, work_request_id
            ).data
        cluster_id = self._cluster_id_from_work_request(work_request)
        if not cluster_id:
            self.module.fail_json(
                msg=(
                    f"Work request {work_request_id} did not include a cluster ID."
                )
            )
        return self._get_cluster_or_id(cluster_id)

    def plan_kubernetes_version_upgrade(
        self, resource, resource_dict, spec, desired_value
    ):
        """Plan an in-place Kubernetes control-plane upgrade.

        An upgrade is planned only when the requested version differs from the
        cluster's current version. Requesting the current version is idempotent,
        and a requested version that is not in the cluster's
        ``available_kubernetes_upgrades`` fails the module rather than letting
        OCI reject an invalid upgrade path.

        Args:
            resource: Current Cluster model.
            resource_dict: Serialized current cluster attributes.
            spec: The kubernetes_version update field spec.
            desired_value: The requested Kubernetes version.

        Returns:
            A list with a single upgrade operation, or an empty list when the
            cluster already runs the requested version.
        """
        current_value = resource_dict.get("kubernetes_version")
        if desired_value == current_value:
            return []
        available_upgrades = resource_dict.get("available_kubernetes_upgrades") or []
        if desired_value not in available_upgrades:
            allowed = ", ".join(available_upgrades) if available_upgrades else "none"
            self.module.fail_json(
                msg=(
                    f"Cannot upgrade {self.create_resource_name} {resource.id} from "
                    f"{current_value} to {desired_value}. The requested version is "
                    f"not an allowed upgrade path; available upgrades: {allowed}."
                )
            )
        return [("upgrade", desired_value)]

    def plan_image_policy_config(self, resource, resource_dict, spec, desired_value):
        """Plan an in-place image policy reconcile.

        Only the sub-options the caller provided are compared against the current
        policy, so an omitted sub-option never forces a change. Key details are
        compared order-insensitively. Returns no operation when the current
        policy already matches the desired values.

        Args:
            resource: Current Cluster model.
            resource_dict: Serialized current cluster attributes.
            spec: The image_policy_config update field spec.
            desired_value: The requested image policy mapping.

        Returns:
            A list with a single set operation, or an empty list when the policy
            already matches the requested values.
        """
        current = resource_dict.get("image_policy_config") or {}

        desired_enabled = desired_value.get("is_policy_enabled")
        if (
            desired_enabled is not None
            and desired_enabled != current.get("is_policy_enabled")
        ):
            return [("set", desired_value)]

        desired_key_details = desired_value.get("key_details")
        if desired_key_details is not None:
            current_keys = sorted(
                key_detail.get("kms_key_id")
                for key_detail in (current.get("key_details") or [])
                if key_detail.get("kms_key_id") is not None
            )
            desired_keys = sorted(
                key_detail.get("kms_key_id")
                for key_detail in desired_key_details
                if key_detail.get("kms_key_id") is not None
            )
            if current_keys != desired_keys:
                return [("set", desired_value)]

        return []

    def build_update_details(self, update_model_fields):
        """Build the OCI update-cluster model from planned field changes.

        Args:
            update_model_fields: Fields selected by the update planner.

        Returns:
            An UpdateClusterDetails model.
        """
        return oci.container_engine.models.UpdateClusterDetails(**update_model_fields)

    def update_resource(self, resource):
        """Apply name, tag, and Kubernetes version updates via a work request.

        This override drives the asynchronous update work request, because the
        update endpoint returns only a work request rather than the cluster. A
        planned Kubernetes upgrade is folded into the same update-details model.

        Args:
            resource: Current Cluster model.

        Returns:
            The updated Cluster model, or an ID-only result when wait=False.
        """
        update_plan = self.get_update_plan(resource)
        update_fields = dict(update_plan["update_model_fields"])

        for strategy_operation in update_plan["strategy_operations"]:
            param_name = strategy_operation["param_name"]
            operations = strategy_operation["operations"]
            if not operations:
                continue
            if param_name == "kubernetes_version":
                update_fields["kubernetes_version"] = operations[0][1]
            elif param_name == "image_policy_config":
                update_fields["image_policy_config"] = (
                    _build_update_image_policy_config(operations[0][1])
                )

        if not update_fields:
            return resource

        response = self.call_with_retry(
            self.client.update_cluster,
            cluster_id=resource.id,
            update_cluster_details=self.build_update_details(update_fields),
        )
        if self.module.params.get("wait", True):
            work_request_id = self._work_request_id(response, "update")
            self.wait_for_work_request(self.client, work_request_id)
        return self._get_cluster_or_id(resource.id)

    def delete_resource(self, resource):
        """Delete the cluster through the shared delete helper.

        The shared helper waits for the cluster to reach a dead state, which the
        delete work request drives.

        Args:
            resource: Cluster model to delete.

        Returns:
            The result from the base delete helper.
        """
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_cluster,
            cluster_id=resource.id,
        )


def main():
    """Build the module argument spec and run the OKE cluster resource module."""
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        cluster_id=dict(type="str", aliases=["id"]),
        vcn_id=dict(type="str"),
        kubernetes_version=dict(type="str"),
        type=dict(type="str", choices=["BASIC_CLUSTER", "ENHANCED_CLUSTER"]),
        kms_key_id=dict(type="str"),
        endpoint_config=dict(
            type="dict",
            options=dict(
                subnet_id=dict(type="str"),
                nsg_ids=dict(type="list", elements="str"),
                is_public_ip_enabled=dict(type="bool"),
            ),
        ),
        image_policy_config=dict(
            type="dict",
            options=dict(
                is_policy_enabled=dict(type="bool"),
                key_details=dict(
                    type="list",
                    elements="dict",
                    no_log=False,
                    options=dict(kms_key_id=dict(type="str")),
                ),
            ),
        ),
        cluster_pod_network_options=dict(
            type="list",
            elements="dict",
            options=dict(
                cni_type=dict(
                    type="str",
                    choices=["OCI_VCN_IP_NATIVE", "FLANNEL_OVERLAY"],
                ),
            ),
        ),
        options=dict(
            type="dict",
            options=dict(
                service_lb_subnet_ids=dict(type="list", elements="str"),
                ip_families=dict(type="list", elements="str"),
                kubernetes_network_config=dict(
                    type="dict",
                    options=dict(
                        pods_cidr=dict(type="str"),
                        services_cidr=dict(type="str"),
                    ),
                ),
                add_ons=dict(
                    type="dict",
                    options=dict(
                        is_kubernetes_dashboard_enabled=dict(type="bool"),
                        is_tiller_enabled=dict(type="bool"),
                    ),
                ),
                admission_controller_options=dict(
                    type="dict",
                    options=dict(
                        is_pod_security_policy_enabled=dict(type="bool"),
                    ),
                ),
            ),
        ),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )
    OciOkeClusterModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
