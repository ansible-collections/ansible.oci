===================================
Oracle OCI Collection Release Notes
===================================

.. contents:: Topics

v1.2.0
======

Release Summary
---------------

Release summary for v1.2.0

Minor Changes
-------------

- Modules now accept lowercase choice values for bastion DNS status, volume sources, network rules, bucket settings, and OKE image filters.

Deprecated Features
-------------------

- Uppercase and mixed-case choice values in these fields are deprecated and will be removed in ansible.oci 2.0.0. Use lowercase choices instead.

New Modules
-----------

- ansible.oci.oci_alarm - Manage an alarm in Oracle Cloud Infrastructure Monitoring.
- ansible.oci.oci_alarm_info - Retrieve alarm information from Oracle Cloud Infrastructure.
- ansible.oci.oci_autonomous_database - Manage an Autonomous Database in Oracle Cloud Infrastructure.
- ansible.oci.oci_autonomous_database_clone - Manage a clone of an Autonomous Database in Oracle Cloud Infrastructure.
- ansible.oci.oci_autonomous_database_clone_info - List the clones of an Autonomous Database in Oracle Cloud Infrastructure.
- ansible.oci.oci_autonomous_database_info - Retrieve Autonomous Database information from Oracle Cloud Infrastructure.
- ansible.oci.oci_autonomous_database_wallet - Download the wallet for an Autonomous Database in Oracle Cloud Infrastructure.
- ansible.oci.oci_dns_domain_records - Manage DNS records in an OCI domain.
- ansible.oci.oci_dns_domain_records_info - Retrieve records from an OCI DNS domain.
- ansible.oci.oci_dns_record_set - Manage one OCI DNS record set.
- ansible.oci.oci_dns_record_set_info - Retrieve one OCI DNS record set.
- ansible.oci.oci_dns_resolver - Update a DNS resolver in Oracle Cloud Infrastructure.
- ansible.oci.oci_dns_resolver_endpoint - Manage a DNS resolver endpoint in Oracle Cloud Infrastructure.
- ansible.oci.oci_dns_resolver_endpoint_info - Get information about DNS resolver endpoints.
- ansible.oci.oci_dns_resolver_info - Get DNS resolver information from Oracle Cloud Infrastructure.
- ansible.oci.oci_dns_zone_records - Manage DNS records in an OCI zone.
- ansible.oci.oci_dns_zone_records_info - Retrieve records from an OCI DNS zone.
- ansible.oci.oci_identity_api_key - Manage an OCI IAM identity domain API key.
- ansible.oci.oci_identity_api_key_info - Retrieve OCI IAM identity domain API keys.
- ansible.oci.oci_identity_dynamic_group - Manage a dynamic group in an OCI IAM identity domain.
- ansible.oci.oci_identity_dynamic_group_info - Retrieve dynamic groups from an OCI IAM identity domain.
- ansible.oci.oci_identity_policy - Manage an OCI identity policy.
- ansible.oci.oci_identity_policy_info - Retrieve OCI identity policy information.
- ansible.oci.oci_identity_tag - Manage a tag definition in an OCI tag namespace.
- ansible.oci.oci_identity_tag_info - Get tag definitions from an OCI tag namespace.
- ansible.oci.oci_identity_tag_namespace - Manage OCI tag namespaces.
- ansible.oci.oci_identity_tag_namespace_info - Retrieve OCI tag namespace information.
- ansible.oci.oci_loadbalancer - Manage an OCI load balancer.
- ansible.oci.oci_loadbalancer_backend - Manage a backend server in an OCI load balancer backend set.
- ansible.oci.oci_loadbalancer_backend_info - Retrieve backend server information from an OCI load balancer.
- ansible.oci.oci_loadbalancer_backend_set - Manage a backend set on an OCI load balancer.
- ansible.oci.oci_loadbalancer_backend_set_info - Retrieve backend set information from an OCI load balancer.
- ansible.oci.oci_loadbalancer_health_checker - Update a Load Balancer backend set health checker.
- ansible.oci.oci_loadbalancer_health_checker_info - Get the health checker for an OCI Load Balancer backend set.
- ansible.oci.oci_loadbalancer_info - Retrieve load balancer information from OCI.
- ansible.oci.oci_loadbalancer_listener - Manage a Load Balancer listener in Oracle Cloud Infrastructure.
- ansible.oci.oci_loadbalancer_listener_info - Get listeners from an OCI Load Balancer.
- ansible.oci.oci_loadbalancer_routing_policy - Manage a Load Balancer routing policy.
- ansible.oci.oci_loadbalancer_routing_policy_info - Get routing policies from an OCI Load Balancer.
- ansible.oci.oci_network_cpe - Manage an OCI customer\-premises equipment object.
- ansible.oci.oci_network_cpe_info - Retrieve OCI customer\-premises equipment information.
- ansible.oci.oci_network_firewall - Manage an OCI Network Firewall.
- ansible.oci.oci_network_firewall_info - Retrieve OCI Network Firewall information.
- ansible.oci.oci_network_firewall_policy - Manage an OCI Network Firewall policy.
- ansible.oci.oci_network_firewall_policy_info - Retrieve OCI Network Firewall policy information.
- ansible.oci.oci_network_ipsec_connection - Manage an OCI IPSec connection and its tunnels.
- ansible.oci.oci_network_ipsec_connection_info - Retrieve OCI IPSec connections and optional tunnel data.
- ansible.oci.oci_network_loadbalancer - Manage an OCI network load balancer.
- ansible.oci.oci_network_loadbalancer_backend - Manage an OCI Network Load Balancer backend.
- ansible.oci.oci_network_loadbalancer_backend_info - Get OCI Network Load Balancer backend details.
- ansible.oci.oci_network_loadbalancer_backend_set - Manage an OCI Network Load Balancer backend set.
- ansible.oci.oci_network_loadbalancer_backend_set_info - Get OCI Network Load Balancer backend set details.
- ansible.oci.oci_network_loadbalancer_health_checker - Manage an OCI Network Load Balancer backend set health checker.
- ansible.oci.oci_network_loadbalancer_health_checker_info - Get OCI Network Load Balancer health checker details.
- ansible.oci.oci_network_loadbalancer_info - Retrieve OCI network load balancer information.
- ansible.oci.oci_network_loadbalancer_listener - Manage an OCI Network Load Balancer listener.
- ansible.oci.oci_network_loadbalancer_listener_info - Get OCI Network Load Balancer listener details.
- ansible.oci.oci_network_vnic_info - Gather information about a VNIC.
- ansible.oci.oci_network_vnic_update - Update a VNIC in Oracle Cloud Infrastructure.
- ansible.oci.oci_notification_topic - Manage an OCI Notifications topic.
- ansible.oci.oci_notification_topic_info - Retrieve OCI Notifications topic information.
- ansible.oci.oci_oke_cluster - Manage an OCI Container Engine for Kubernetes (OKE) cluster.
- ansible.oci.oci_oke_cluster_info - Retrieve OKE cluster information from OCI.
- ansible.oci.oci_oke_node_pool - Manage an OCI Container Engine for Kubernetes (OKE) node pool.
- ansible.oci.oci_oke_node_pool_info - Retrieve OKE node pool information from OCI.
- ansible.oci.oci_oke_node_pool_options_info - Retrieve available OKE node pool options from OCI.
- ansible.oci.oci_waf_web_app_firewall - Manage an OCI Web Application Firewall.
- ansible.oci.oci_waf_web_app_firewall_info - Retrieve OCI Web Application Firewall information.
- ansible.oci.oci_waf_web_app_firewall_policy - Manage an OCI Web Application Firewall policy.
- ansible.oci.oci_waf_web_app_firewall_policy_info - Retrieve OCI Web Application Firewall policies.

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
