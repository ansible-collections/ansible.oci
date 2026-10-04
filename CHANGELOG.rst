===================================
Oracle OCI Collection Release Notes
===================================

.. contents:: Topics

v1.1.0
======

Release Summary
---------------

Release summary for v1.1.0

Minor Changes
-------------

- oci_blockstorage_volume - add create-time source_details to restore from a volume backup or clone from an existing volume.
- oci_vnic_attachment - add secondary VNIC attachment lifecycle management.
- oci_vnic_attachment_info - add VNIC attachment retrieval and listing.

New Modules
-----------

- ansible.oci.oci_bastion - Manage a Bastion resource in Oracle Cloud Infrastructure.
- ansible.oci.oci_bastion_info - Retrieve bastion information from Oracle Cloud Infrastructure.
- ansible.oci.oci_boot_volume - Manage a boot volume resource in Oracle Cloud Infrastructure.
- ansible.oci.oci_identity_compartment - Manage OCI compartments.
- ansible.oci.oci_identity_compartment_info - Retrieve OCI compartment information.
- ansible.oci.oci_identity_domain - Manage OCI identity domains.
- ansible.oci.oci_identity_domain_info - Retrieve OCI identity domain information.
- ansible.oci.oci_identity_group - Manage a group in an OCI IAM identity domain.
- ansible.oci.oci_identity_group_info - Retrieve groups from an OCI IAM identity domain.
- ansible.oci.oci_identity_user - Manage a user in an OCI IAM identity domain.
- ansible.oci.oci_identity_user_group_membership - Manage a user group membership in an OCI IAM identity domain.
- ansible.oci.oci_identity_user_group_membership_info - Retrieve user group memberships from an OCI IAM identity domain.
- ansible.oci.oci_identity_user_info - Retrieve users from an OCI IAM identity domain.
- ansible.oci.oci_network_private_ip - Manage a Private IP resource in Oracle Cloud Infrastructure.
- ansible.oci.oci_network_public_ip - Manage a Public IP resource in Oracle Cloud Infrastructure.
- ansible.oci.oci_object_lifecycle_policy - Manage an Object Storage bucket lifecycle policy.
- ansible.oci.oci_object_lifecycle_policy_info - Get an Object Storage bucket lifecycle policy from Oracle Cloud Infrastructure.
- ansible.oci.oci_object_storage_bucket - Manage an Object Storage bucket in Oracle Cloud Infrastructure.
- ansible.oci.oci_object_storage_bucket_info - Retrieve Object Storage bucket information from Oracle Cloud Infrastructure.
- ansible.oci.oci_object_storage_object - Upload, download, or delete an Object Storage object.
- ansible.oci.oci_object_storage_object_info - Retrieve Object Storage object information.
- ansible.oci.oci_vnic_attachment - Manage a VNIC attachment resource in Oracle Cloud Infrastructure.
- ansible.oci.oci_vnic_attachment_info - Retrieve VNIC attachment information from Oracle Cloud Infrastructure.
- ansible.oci.oci_volume_backup_policy - Manage a volume backup policy in Oracle Cloud Infrastructure.
- ansible.oci.oci_volume_backup_policy_assignment - Manage an OCI volume backup policy assignment.
- ansible.oci.oci_volume_backup_policy_assignment_info - Retrieve an OCI volume backup policy assignment.
- ansible.oci.oci_volume_backup_policy_info - Retrieve volume backup policy information from Oracle Cloud Infrastructure.
- ansible.oci.oci_volume_group_backup - Manage a volume group backup resource in Oracle Cloud Infrastructure.
- ansible.oci.oci_volume_group_backup_info - Retrieve volume group backup information from Oracle Cloud Infrastructure.

v1.0.0
======

Release Summary
---------------

Release summary for v1.0.0

New Modules
-----------

- ansible.oci.oci_availability_domain_info - Retrieve Availability Domain information from Oracle Cloud Infrastructure.
- ansible.oci.oci_blockstorage_volume - Manage a block volume resource in Oracle Cloud Infrastructure.
- ansible.oci.oci_blockstorage_volume_info - Retrieve block volume information from Oracle Cloud Infrastructure.
- ansible.oci.oci_boot_volume_backup - Manage a boot volume backup resource in Oracle Cloud Infrastructure.
- ansible.oci.oci_boot_volume_backup_info - Retrieve boot volume backup information from Oracle Cloud Infrastructure.
- ansible.oci.oci_boot_volume_info - Retrieve boot volume information from Oracle Cloud Infrastructure.
- ansible.oci.oci_image - Manage a custom Compute image resource in Oracle Cloud Infrastructure.
- ansible.oci.oci_image_info - Retrieve Compute image information from Oracle Cloud Infrastructure.
- ansible.oci.oci_instance - Manage a Compute instance resource in Oracle Cloud Infrastructure.
- ansible.oci.oci_instance_console_connection - Manage a Compute instance console connection resource in Oracle Cloud Infrastructure.
- ansible.oci.oci_instance_console_connection_info - Retrieve Compute instance console connection information from Oracle Cloud Infrastructure.
- ansible.oci.oci_instance_info - Retrieve Compute instance information from Oracle Cloud Infrastructure.
- ansible.oci.oci_network_dhcp_options - Manage a DHCP Options resource in Oracle Cloud Infrastructure.
- ansible.oci.oci_network_dhcp_options_info - Retrieve DHCP Options information from Oracle Cloud Infrastructure.
- ansible.oci.oci_network_drg - Manage a Dynamic Routing Gateway (DRG) resource in Oracle Cloud Infrastructure.
- ansible.oci.oci_network_drg_attachment - Manage a DRG attachment resource in Oracle Cloud Infrastructure.
- ansible.oci.oci_network_drg_attachment_info - Retrieve DRG attachment information from Oracle Cloud Infrastructure.
- ansible.oci.oci_network_drg_info - Retrieve Dynamic Routing Gateway (DRG) information from Oracle Cloud Infrastructure.
- ansible.oci.oci_network_internet_gateway - Manage an Internet Gateway resource in Oracle Cloud Infrastructure.
- ansible.oci.oci_network_internet_gateway_info - Retrieve Internet Gateway information from Oracle Cloud Infrastructure.
- ansible.oci.oci_network_local_peering_gateway - Manage a Local Peering Gateway resource in Oracle Cloud Infrastructure.
- ansible.oci.oci_network_local_peering_gateway_info - Retrieve Local Peering Gateway information from Oracle Cloud Infrastructure.
- ansible.oci.oci_network_nat_gateway - Manage a NAT Gateway resource in Oracle Cloud Infrastructure.
- ansible.oci.oci_network_nat_gateway_info - Retrieve NAT Gateway information from Oracle Cloud Infrastructure.
- ansible.oci.oci_network_route_table - Manage a Route Table resource in Oracle Cloud Infrastructure.
- ansible.oci.oci_network_route_table_info - Retrieve Route Table information from Oracle Cloud Infrastructure.
- ansible.oci.oci_network_security_list - Manage a Security List resource in Oracle Cloud Infrastructure.
- ansible.oci.oci_network_security_list_info - Retrieve Security List information from Oracle Cloud Infrastructure.
- ansible.oci.oci_network_service_gateway - Manage a Service Gateway resource in Oracle Cloud Infrastructure.
- ansible.oci.oci_network_service_gateway_info - Retrieve Service Gateway information from Oracle Cloud Infrastructure.
- ansible.oci.oci_network_subnet - Manage a Subnet resource in Oracle Cloud Infrastructure.
- ansible.oci.oci_network_subnet_info - Retrieve Subnet information from Oracle Cloud Infrastructure.
- ansible.oci.oci_network_vcn - Manage a Virtual Cloud Network resource in Oracle Cloud Infrastructure.
- ansible.oci.oci_network_vcn_info - Retrieve Virtual Cloud Network information from Oracle Cloud Infrastructure.
- ansible.oci.oci_shape_info - Retrieve Compute shape information from Oracle Cloud Infrastructure.
- ansible.oci.oci_volume_attachment - Manage a block volume attachment resource in Oracle Cloud Infrastructure.
- ansible.oci.oci_volume_attachment_info - Retrieve block volume attachment information from Oracle Cloud Infrastructure.
- ansible.oci.oci_volume_backup - Manage a block volume backup resource in Oracle Cloud Infrastructure.
- ansible.oci.oci_volume_backup_info - Retrieve block volume backup information from Oracle Cloud Infrastructure.
- ansible.oci.oci_volume_group - Manage a volume group resource in Oracle Cloud Infrastructure.
- ansible.oci.oci_volume_group_info - Retrieve volume group information from Oracle Cloud Infrastructure.
