# OKE (Container Engine for Kubernetes) — planned follow-up modules

`oci_oke_cluster` manages the cluster control plane: create, rename, retag,
upgrade the Kubernetes version, reconcile the signed-image verification policy,
and delete. In-place changes it owns all go through the `update_cluster` API.
It intentionally does **not** reconcile attributes that are create-time only
(`options`, `kms_key_id`, `cluster_pod_network_options`) or that are driven by a
distinct OCI API (`endpoint_config`). The remaining follow-up below is kept
separate because it uses its own OCI endpoint-config API rather than
`update_cluster`.

## oci_oke_cluster_network_security_groups

- **Purpose:** Manage the network security groups applied to a cluster's
  control-plane endpoint.
- **OCI SDK:** `ContainerEngineClient.update_cluster_endpoint_config(cluster_id,
  UpdateClusterEndpointConfigDetails(nsg_ids=...))`, driven as an asynchronous
  work request.
- **Behavior:** Reconcile the endpoint `nsg_ids` list (add/remove/replace);
  idempotent when the endpoint already has the desired NSGs. Supports check mode
  and the shared wait options.
- **Why separate:** Endpoint NSG changes use a dedicated endpoint-config API
  distinct from `update_cluster`, so they belong in a focused module rather than
  in `oci_oke_cluster`, which treats `endpoint_config` as create-time only.
