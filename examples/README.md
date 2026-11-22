# OCI example playbooks

Each playbook shows one use case for the `ansible.oci` collection. Run the
playbooks in any order. Each creates the infrastructure for its own scenario.

## Set up access to OCI

1. Install `ansible.oci` and the OCI Python SDK in the environment where
   Ansible runs. See the [collection requirements](../README.md#requirements).
2. Set up OCI authentication. The default profile is `DEFAULT` in
   `~/.oci/config`. Select the region in that profile. See
   [authentication defaults](../README.md#authentication-defaults).
3. Set `OCI_EXAMPLE_COMPARTMENT_ID` to the Oracle Cloud Identifier (OCID) of
   your target compartment in the shell where you run the examples.
4. Give the OCI identity permission to read and manage the resources in the
   example. Include delete permission for examples that create resources.

Use a test compartment. OCI can charge for the resources while they exist.
The Compute examples use an Oracle Linux 9 platform image and a Flex shape
with one Oracle CPU (OCPU) and 16 GB of memory. They use the first compatible
platform image and the first availability domain returned by OCI. If the shape
is unavailable, set `example_compute_shape` to another Flex shape that supports
this configuration. The examples inspect the instance through the OCI API.

## Run a playbook

Run the commands from the repository root.

### Discover resources

List the availability domains and the IDs of running instances. The command
can run in an empty compartment.

```sh
ansible-playbook examples/discover_resources.yml -e "oci_compartment_id=$OCI_EXAMPLE_COMPARTMENT_ID"
```

### Create a private network

Create a virtual cloud network (VCN) and a regional subnet. The subnet prevents
public IP assignment.

```sh
ansible-playbook examples/create_private_network.yml -e "oci_compartment_id=$OCI_EXAMPLE_COMPARTMENT_ID"
```

### Launch an instance

Create a private network, launch a Linux instance, and show its ID and state.

```sh
ansible-playbook examples/launch_instance.yml -e "oci_compartment_id=$OCI_EXAMPLE_COMPARTMENT_ID"
```

### Attach a block volume

Create a private Linux instance and attach a new 50 GB block volume. The
playbook shows the attachment state through the OCI API.

```sh
ansible-playbook examples/attach_block_volume.yml -e "oci_compartment_id=$OCI_EXAMPLE_COMPARTMENT_ID"
```

### Upload an object

Write a temporary text file, upload it to a private bucket, and show the
metadata for the uploaded object.

```sh
ansible-playbook examples/upload_object.yml -e "oci_compartment_id=$OCI_EXAMPLE_COMPARTMENT_ID"
```

### Create an Autonomous Database

Create a paid Autonomous Database for transaction processing with a private
endpoint. Supply an administrator password that meets Oracle's requirements.

```bash
read -rs -p 'Autonomous Database administrator password: ' OCI_EXAMPLE_ADB_ADMIN_PASSWORD
export OCI_EXAMPLE_ADB_ADMIN_PASSWORD
ansible-playbook examples/create_autonomous_database.yml -e "oci_compartment_id=$OCI_EXAMPLE_COMPARTMENT_ID"
unset OCI_EXAMPLE_ADB_ADMIN_PASSWORD
```

[Oracle password requirements](https://docs.oracle.com/en/cloud/paas/autonomous-database/serverless/adbsb/manage-users-create.html)

## Cleanup

By default, each provisioning playbook deletes the resources it creates in
an `always` block. Add `-e example_cleanup=false` to keep the OCI resources
for inspection. The upload example removes its temporary local files in
either case.

The playbooks use fixed example names. If you keep resources or a run stops
before cleanup completes, find the resources by name in the OCI Console.
Delete them in the order shown in the playbook before you run it again.
If you mount an example block volume, unmount it before you detach it.
