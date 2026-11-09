# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_instance_configuration
short_description: Manage an OCI Compute instance configuration
description:
- Create, update, and delete OCI Compute instance configurations.
version_added: 1.3.0
author:
- Ron Gershburg (@ronger4)
extends_documentation_fragment:
- ansible.oci.oci_auth_options
- ansible.oci.oci_name_lookup_options
- ansible.oci.oci_wait_options
- ansible.oci.oci_tags_options
options:
  state:
    description:
    - Select whether to create, update, or delete the configuration.
    type: str
    choices: [present, absent]
    default: present
  instance_configuration_id:
    description:
    - The OCID of the configuration to update or delete.
    - When you omit this option, the module finds a configuration by compartment and name.
    type: str
  source:
    description:
    - Select the source for a new configuration.
    - Select C(none) to create from C(instance_details) or C(instance) to copy an existing instance.
    - This option applies only during creation.
    type: str
    choices: [none, instance]
    default: none
  instance_id:
    description:
    - The OCID of the instance to copy into a new configuration.
    - Set this option when C(source) is C(instance). This option applies only during creation.
    type: str
  instance_details:
    description:
    - The launch template for a configuration created with C(source) set to C(none).
    - OCI does not allow changes to the template after configuration creation.
    - Supply required deferred settings when launching an instance from this configuration.
    type: dict
    suboptions:
      instance_type:
        description:
        - Select the instance template type.
        type: str
        choices: [compute, instance_options]
        default: compute
      block_volumes:
        description:
        - Define data volumes to attach or create when an instance launches from this template.
        type: list
        elements: dict
        suboptions:
          attach_details:
            description:
            - Set the attachment options for an existing volume.
            type: dict
            suboptions:
              use_chap:
                description:
                - Enable CHAP authentication for an iSCSI volume attachment.
                type: bool
              name:
                description:
                - Set the display name for the volume attachment.
                type: str
              is_read_only:
                description:
                - Attach the volume in read-only mode.
                type: bool
              device:
                description:
                - Set the device path for the volume attachment.
                type: str
              is_shareable:
                description:
                - Allow the volume to attach to more than one instance.
                type: bool
              type:
                description:
                - Select the attachment protocol for the volume.
                type: str
                choices: [iscsi, paravirtualized]
                required: true
              is_pv_encryption_in_transit_enabled:
                description:
                - Enable encryption in transit for a paravirtualized volume attachment.
                type: bool
          create_details:
            description:
            - Set the properties for a new data volume.
            type: dict
            suboptions:
              availability_domain:
                description:
                - Select the availability domain for the volume.
                type: str
              backup_policy_id:
                description:
                - The OCID of the backup policy to assign to the volume.
                type: str
              compartment_id:
                description:
                - The OCID of the compartment that contains the volume.
                type: str
              is_auto_tune_enabled:
                description:
                - Enable performance autotuning for the volume.
                type: bool
              block_volume_replicas:
                description:
                - Define replicas for the volume in destination availability domains.
                type: list
                elements: dict
                suboptions:
                  name:
                    description:
                    - Set the display name for the volume replica.
                    type: str
                  availability_domain:
                    description:
                    - Select the destination availability domain for the replica.
                    - This value is required for instance options templates.
                    type: str
                    required: true
              defined_tags:
                description:
                - Set defined tags for the volume
                - grouped by namespace.
                type: dict
              name:
                description:
                - Set the display name for the volume.
                type: str
              freeform_tags:
                description:
                - Set free-form tags for the volume.
                type: dict
              kms_key_id:
                description:
                - The OCID of the Vault key used to encrypt the volume.
                type: str
              vpus_per_gb:
                description:
                - The volume performance units (VPUs) per GB for the volume.
                - Use C(0) for Lower Cost, C(10) for Balanced, or C(20) for Higher Performance.
                - Use C(30) through C(120) for Ultra High Performance.
                - With performance autotuning, this value sets the minimum performance level.
                type: int
              size_in_gbs:
                description:
                - Set the volume size in gigabytes.
                type: int
              source_details:
                description:
                - Select a source volume or volume backup for the new volume.
                type: dict
                suboptions:
                  type:
                    description:
                    - Select whether the source is a volume or a volume backup.
                    type: str
                    choices: [volume_backup, volume]
                    required: true
                  id:
                    description:
                    - The OCID of the source volume or volume backup.
                    type: str
              autotune_policies:
                description:
                - Set performance or detached-volume autotuning policies.
                type: list
                elements: dict
                suboptions:
                  max_vpus_per_gb:
                    description:
                    - Set the maximum VPUs per GB for performance-based autotuning.
                    - Set this value when C(autotune_type) is C(performance_based).
                    type: int
                  autotune_type:
                    description:
                    - Select the volume autotuning policy type.
                    type: str
                    choices: [performance_based, detached_volume]
                    required: true
          volume_id:
            description:
            - The OCID of an existing volume to attach.
            type: str
      launch_details:
        description:
        - Set the compute launch properties for the instance template.
        type: dict
        suboptions:
          availability_domain:
            description:
            - Select the availability domain for the instance.
            type: str
          capacity_reservation_id:
            description:
            - The OCID of the capacity reservation for the instance.
            type: str
          compartment_id:
            description:
            - The OCID of the compartment that contains the instance.
            type: str
          create_vnic_details:
            description:
            - Set the primary VNIC properties for the instance.
            type: dict
            suboptions:
              assign_public_ip:
                description:
                - Assign a public IP address to the primary VNIC.
                type: bool
              assign_private_dns_record:
                description:
                - Create a private DNS record for the primary VNIC.
                type: bool
              defined_tags:
                description:
                - Set defined tags for the primary VNIC
                - grouped by namespace.
                type: dict
              name:
                description:
                - Set the display name for the primary VNIC.
                type: str
              freeform_tags:
                description:
                - Set free-form tags for the primary VNIC.
                type: dict
              hostname_label:
                description:
                - Set the hostname label for the primary private IP address.
                type: str
              nsg_ids:
                description:
                - The OCIDs of network security groups to add to the primary VNIC.
                type: list
                elements: str
              private_ip:
                description:
                - Set the private IP address for the primary VNIC.
                type: str
              skip_source_dest_check:
                description:
                - Disable the source and destination check for the primary VNIC.
                type: bool
              subnet_id:
                description:
                - The OCID of the subnet for the primary VNIC.
                type: str
          defined_tags:
            description:
            - Set defined tags for the instance
            - grouped by namespace.
            type: dict
          name:
            description:
            - Set the display name for the instance.
            type: str
          extended_metadata:
            description:
            - Set nested JSON metadata values for the instance.
            type: dict
          freeform_tags:
            description:
            - Set free-form tags for the instance.
            type: dict
          ipxe_script:
            description:
            - Set the iPXE script that the instance runs during boot.
            type: str
          metadata:
            description:
            - Set string metadata values for the instance
            - such as SSH public keys or cloud-init data.
            type: dict
          shape:
            description:
            - Select the compute shape for the instance.
            type: str
          shape_config:
            description:
            - Set the CPU
            - memory
            - and local storage resources for a flexible shape.
            type: dict
            suboptions:
              ocpus:
                description:
                - Set the number of OCPUs for the instance.
                type: float
              vcpus:
                description:
                - Set the number of virtual CPUs for the instance.
                type: int
              memory_in_gbs:
                description:
                - Set the instance memory in gigabytes.
                type: float
              baseline_ocpu_utilization:
                description:
                - Select the baseline OCPU utilization for a burstable VM shape.
                type: str
                choices: [baseline_1_8, baseline_1_2, baseline_1_1]
              nvmes:
                description:
                - Set the number of NVMe drives for the instance.
                type: int
          platform_config:
            description:
            - Set platform-specific CPU
            - security
            - and firmware options.
            type: dict
            suboptions:
              percentage_of_cores_enabled:
                description:
                - Set the percentage of processor cores to enable.
                type: int
              numa_nodes_per_socket:
                description:
                - Select the number of NUMA nodes per socket.
                type: str
                choices: [nps0, nps1, nps2, nps4]
              is_symmetric_multi_threading_enabled:
                description:
                - Enable symmetric multi-threading for the instance.
                type: bool
              is_access_control_service_enabled:
                description:
                - Enable PCIe device isolation for device pass-through.
                type: bool
              are_virtual_instructions_enabled:
                description:
                - Expose hardware virtualization instructions to the instance.
                type: bool
              is_input_output_memory_management_unit_enabled:
                description:
                - Enable the input-output memory management unit.
                type: bool
              type:
                description:
                - The platform family to configure.
                - Examples include C(amd_vm), C(intel_vm), C(amd_milan_bm), and C(amd_milan_bm_gpu).
                - Other examples include C(amd_rome_bm), C(amd_rome_bm_gpu), C(intel_icelake_bm),
                  C(intel_skylake_bm), and C(generic_bm).
                - Use a value supported by the installed OCI SDK and the selected shape.
                - The module converts this value to uppercase for OCI.
                - See L(Oracle platform types,
                  https://docs.oracle.com/iaas/tools/python/latest/api/core/models/oci.core.models.InstanceConfigurationLaunchInstancePlatformConfig.html)
                  for supported values.
                type: str
                required: true
              is_secure_boot_enabled:
                description:
                - Enable Secure Boot for the instance.
                type: bool
              is_trusted_platform_module_enabled:
                description:
                - Enable the Trusted Platform Module for the instance.
                type: bool
              is_measured_boot_enabled:
                description:
                - Enable measured boot for the instance.
                type: bool
              is_memory_encryption_enabled:
                description:
                - Enable memory encryption for the instance.
                type: bool
          source_details:
            description:
            - Select the image or boot volume used to launch the instance.
            type: dict
            suboptions:
              boot_volume_size_in_gbs:
                description:
                - Set the boot volume size in gigabytes.
                type: int
              image_id:
                description:
                - The OCID of the image used to launch the instance.
                type: str
              kms_key_id:
                description:
                - The OCID of the Vault key used to encrypt the boot volume.
                type: str
              boot_volume_vpus_per_gb:
                description:
                - The boot volume performance units (VPUs) per GB.
                - Use C(10) for Balanced or C(20) for Higher Performance.
                - Use C(30) through C(120) for Ultra High Performance.
                - With performance autotuning, this value sets the minimum performance level.
                type: int
              instance_source_image_filter_details:
                description:
                - Filter images by compartment
                - tags
                - operating system
                - and version.
                type: dict
                suboptions:
                  compartment_id:
                    description:
                    - The OCID of the compartment to search for images.
                    type: str
                  defined_tags_filter:
                    description:
                    - Select images that match these defined tags.
                    type: dict
                  operating_system:
                    description:
                    - Select images by operating system name.
                    type: str
                  operating_system_version:
                    description:
                    - Select images by operating system version.
                    type: str
              source_type:
                description:
                - Select whether to launch from an image or a boot volume.
                type: str
                choices: [image, boot_volume]
                required: true
              boot_volume_id:
                description:
                - The OCID of the boot volume used to launch the instance.
                type: str
          fault_domain:
            description:
            - Select the fault domain for the instance.
            type: str
          dedicated_vm_host_id:
            description:
            - The OCID of the dedicated VM host for the instance.
            type: str
          launch_mode:
            description:
            - Select the launch mode used to boot the instance.
            type: str
            choices: [native, emulated, paravirtualized, custom]
          launch_options:
            description:
            - Set the firmware
            - network
            - and volume device options for the instance.
            type: dict
            suboptions:
              boot_volume_type:
                description:
                - Select the device type for the boot volume.
                type: str
                choices: [ide, iscsi, paravirtualized, scsi, vfio]
              firmware:
                description:
                - Select the firmware type used to boot the instance.
                type: str
                choices: [bios, uefi_64]
              network_type:
                description:
                - Select the network device type for the instance.
                type: str
                choices: [acceleratedpv, e1000, paravirtualized, vfio]
              remote_data_volume_type:
                description:
                - Select the device type for remote data volumes.
                type: str
                choices: [ide, iscsi, paravirtualized, scsi, vfio]
              is_pv_encryption_in_transit_enabled:
                description:
                - Deprecated. Use the instance-level encryption option instead.
                type: bool
              is_consistent_volume_naming_enabled:
                description:
                - Enable consistent device names for attached volumes.
                type: bool
          agent_config:
            description:
            - Set Oracle Cloud Agent and plugin settings for the instance.
            type: dict
            suboptions:
              all_plugins_disabled:
                description:
                - Disable all Oracle Cloud Agent plugins.
                type: bool
              management_disabled:
                description:
                - Disable Oracle Cloud Agent management plugins.
                type: bool
              monitoring_disabled:
                description:
                - Disable Oracle Cloud Agent monitoring plugins.
                type: bool
              plugins_config:
                description:
                - Set the desired state for individual Oracle Cloud Agent plugins.
                type: list
                elements: dict
                suboptions:
                  name:
                    description:
                    - The name of the Oracle Cloud Agent plugin.
                    - This value is required for compute instance templates.
                    type: str
                    required: true
                  desired_state:
                    description:
                    - Select whether to enable or disable the plugin.
                    - This value is required for compute instance templates.
                    type: str
                    choices: [enabled, disabled]
                    required: true
          is_pv_encryption_in_transit_enabled:
            description:
            - Enable encryption in transit for paravirtualized data volume attachments.
            type: bool
          preferred_maintenance_action:
            description:
            - Select the action to use during scheduled maintenance.
            type: str
            choices: [live_migrate, reboot]
          instance_options:
            description:
            - Set instance behavior options.
            type: dict
            suboptions:
              are_legacy_imds_endpoints_disabled:
                description:
                - Disable access to legacy instance metadata service endpoints.
                type: bool
          availability_config:
            description:
            - Set live migration and recovery behavior for the instance.
            type: dict
            suboptions:
              is_live_migration_preferred:
                description:
                - Prefer live migration during maintenance when available.
                type: bool
              recovery_action:
                description:
                - Select the action to take after an instance recovery event.
                type: str
                choices: [restore_instance, stop_instance]
          preemptible_instance_config:
            description:
            - Set behavior for a preemptible instance.
            type: dict
            suboptions:
              preemption_action:
                description:
                - The settings used when OCI reclaims the instance.
                - OCI terminates the instance; set C(preserve_boot_volume) to retain its boot
                  volume.
                type: dict
                required: true
                suboptions:
                  preserve_boot_volume:
                    description:
                    - Preserve the boot volume when OCI terminates the instance.
                    type: bool
      secondary_vnics:
        description:
        - Define secondary VNICs for the instance.
        type: list
        elements: dict
        suboptions:
          create_vnic_details:
            description:
            - Set the properties for a secondary VNIC.
            type: dict
            suboptions:
              assign_public_ip:
                description:
                - Assign a public IP address to the secondary VNIC.
                type: bool
              assign_private_dns_record:
                description:
                - Create a private DNS record for the secondary VNIC.
                type: bool
              defined_tags:
                description:
                - Set defined tags for the secondary VNIC
                - grouped by namespace.
                type: dict
              name:
                description:
                - Set the display name for the secondary VNIC.
                type: str
              freeform_tags:
                description:
                - Set free-form tags for the secondary VNIC.
                type: dict
              hostname_label:
                description:
                - Set the hostname label for the secondary VNIC private IP address.
                type: str
              nsg_ids:
                description:
                - The OCIDs of network security groups to add to the secondary VNIC.
                type: list
                elements: str
              private_ip:
                description:
                - Set the private IP address for the secondary VNIC.
                type: str
              skip_source_dest_check:
                description:
                - Disable the source and destination check for the secondary VNIC.
                type: bool
              subnet_id:
                description:
                - The OCID of the subnet for the secondary VNIC.
                type: str
          name:
            description:
            - Set the display name for the secondary VNIC entry.
            type: str
          nic_index:
            description:
            - Set the NIC index for the secondary VNIC.
            type: int
      options:
        description:
        - Define additional option details for the instance configuration.
        type: list
        elements: dict
        suboptions:
          instance_type:
            description:
            - Select the type of instance details in this option entry.
            type: str
            choices: [compute]
            required: true
          block_volumes:
            description:
            - Define data volumes to attach or create for this option entry.
            type: list
            elements: dict
            suboptions:
              attach_details:
                description:
                - Set the attachment options for an existing volume.
                type: dict
                suboptions:
                  use_chap:
                    description:
                    - Enable CHAP authentication for an iSCSI volume attachment.
                    type: bool
                  name:
                    description:
                    - Set the display name for the volume attachment.
                    type: str
                  is_read_only:
                    description:
                    - Attach the volume in read-only mode.
                    type: bool
                  device:
                    description:
                    - Set the device path for the volume attachment.
                    type: str
                  is_shareable:
                    description:
                    - Allow the volume to attach to more than one instance.
                    type: bool
                  type:
                    description:
                    - Select the attachment protocol for the volume.
                    type: str
                    choices: [iscsi, paravirtualized]
                    required: true
                  is_pv_encryption_in_transit_enabled:
                    description:
                    - Enable encryption in transit for a paravirtualized volume attachment.
                    type: bool
              create_details:
                description:
                - Set the properties for a new data volume.
                type: dict
                suboptions:
                  availability_domain:
                    description:
                    - Select the availability domain for the volume.
                    type: str
                  backup_policy_id:
                    description:
                    - The OCID of the backup policy to assign to the volume.
                    type: str
                  compartment_id:
                    description:
                    - The OCID of the compartment that contains the volume.
                    type: str
                  is_auto_tune_enabled:
                    description:
                    - Enable performance autotuning for the volume.
                    type: bool
                  block_volume_replicas:
                    description:
                    - Define replicas for the volume in destination availability domains.
                    type: list
                    elements: dict
                    suboptions:
                      name:
                        description:
                        - Set the display name for the volume replica.
                        type: str
                      availability_domain:
                        description:
                        - Select the destination availability domain for the replica.
                        type: str
                        required: true
                  defined_tags:
                    description:
                    - Set defined tags for the volume
                    - grouped by namespace.
                    type: dict
                  name:
                    description:
                    - Set the display name for the volume.
                    type: str
                  freeform_tags:
                    description:
                    - Set free-form tags for the volume.
                    type: dict
                  kms_key_id:
                    description:
                    - The OCID of the Vault key used to encrypt the volume.
                    type: str
                  vpus_per_gb:
                    description:
                    - The volume performance units (VPUs) per GB for the volume.
                    - Use C(0) for Lower Cost, C(10) for Balanced, or C(20) for Higher Performance.
                    - Use C(30) through C(120) for Ultra High Performance.
                    - With performance autotuning, this value sets the minimum performance level.
                    type: int
                  size_in_gbs:
                    description:
                    - Set the volume size in gigabytes.
                    type: int
                  source_details:
                    description:
                    - Select a source volume or volume backup for the new volume.
                    type: dict
                    suboptions:
                      type:
                        description:
                        - Select whether the source is a volume or a volume backup.
                        type: str
                        choices: [volume_backup, volume]
                        required: true
                      id:
                        description:
                        - The OCID of the source volume or volume backup.
                        type: str
                  autotune_policies:
                    description:
                    - Set performance or detached-volume autotuning policies.
                    type: list
                    elements: dict
                    suboptions:
                      max_vpus_per_gb:
                        description:
                        - Set the maximum VPUs per GB for performance-based autotuning.
                        type: int
                      autotune_type:
                        description:
                        - Select the volume autotuning policy type.
                        type: str
                        choices: [performance_based, detached_volume]
                        required: true
              volume_id:
                description:
                - The OCID of an existing volume to attach.
                type: str
          launch_details:
            description:
            - Set the compute launch properties for this option entry.
            type: dict
            suboptions:
              availability_domain:
                description:
                - Select the availability domain for the instance.
                type: str
              capacity_reservation_id:
                description:
                - The OCID of the capacity reservation for the instance.
                type: str
              compartment_id:
                description:
                - The OCID of the compartment that contains the instance.
                type: str
              create_vnic_details:
                description:
                - Set the primary VNIC properties for the instance.
                type: dict
                suboptions:
                  assign_public_ip:
                    description:
                    - Assign a public IP address to the primary VNIC.
                    type: bool
                  assign_private_dns_record:
                    description:
                    - Create a private DNS record for the primary VNIC.
                    type: bool
                  defined_tags:
                    description:
                    - Set defined tags for the primary VNIC
                    - grouped by namespace.
                    type: dict
                  name:
                    description:
                    - Set the display name for the primary VNIC.
                    type: str
                  freeform_tags:
                    description:
                    - Set free-form tags for the primary VNIC.
                    type: dict
                  hostname_label:
                    description:
                    - Set the hostname label for the primary private IP address.
                    type: str
                  nsg_ids:
                    description:
                    - The OCIDs of network security groups to add to the primary VNIC.
                    type: list
                    elements: str
                  private_ip:
                    description:
                    - Set the private IP address for the primary VNIC.
                    type: str
                  skip_source_dest_check:
                    description:
                    - Disable the source and destination check for the primary VNIC.
                    type: bool
                  subnet_id:
                    description:
                    - The OCID of the subnet for the primary VNIC.
                    type: str
              defined_tags:
                description:
                - Set defined tags for the instance
                - grouped by namespace.
                type: dict
              name:
                description:
                - Set the display name for the instance.
                type: str
              extended_metadata:
                description:
                - Set nested JSON metadata values for the instance.
                type: dict
              freeform_tags:
                description:
                - Set free-form tags for the instance.
                type: dict
              ipxe_script:
                description:
                - Set the iPXE script that the instance runs during boot.
                type: str
              metadata:
                description:
                - Set string metadata values for the instance
                - such as SSH public keys or cloud-init data.
                type: dict
              shape:
                description:
                - Select the compute shape for the instance.
                type: str
              shape_config:
                description:
                - Set the CPU
                - memory
                - and local storage resources for a flexible shape.
                type: dict
                suboptions:
                  ocpus:
                    description:
                    - Set the number of OCPUs for the instance.
                    type: float
                  vcpus:
                    description:
                    - Set the number of virtual CPUs for the instance.
                    type: int
                  memory_in_gbs:
                    description:
                    - Set the instance memory in gigabytes.
                    type: float
                  baseline_ocpu_utilization:
                    description:
                    - Select the baseline OCPU utilization for a burstable VM shape.
                    type: str
                    choices: [baseline_1_8, baseline_1_2, baseline_1_1]
                  nvmes:
                    description:
                    - Set the number of NVMe drives for the instance.
                    type: int
              platform_config:
                description:
                - Set platform-specific CPU
                - security
                - and firmware options.
                type: dict
                suboptions:
                  percentage_of_cores_enabled:
                    description:
                    - Set the percentage of processor cores to enable.
                    type: int
                  numa_nodes_per_socket:
                    description:
                    - Select the number of NUMA nodes per socket.
                    type: str
                    choices: [nps0, nps1, nps2, nps4]
                  is_symmetric_multi_threading_enabled:
                    description:
                    - Enable symmetric multi-threading for the instance.
                    type: bool
                  is_access_control_service_enabled:
                    description:
                    - Enable PCIe device isolation for device pass-through.
                    type: bool
                  are_virtual_instructions_enabled:
                    description:
                    - Expose hardware virtualization instructions to the instance.
                    type: bool
                  is_input_output_memory_management_unit_enabled:
                    description:
                    - Enable the input-output memory management unit.
                    type: bool
                  type:
                    description:
                    - The platform family to configure.
                    - Examples include C(amd_vm), C(intel_vm), C(amd_milan_bm), and C(amd_milan_bm_gpu).
                    - Other examples include C(amd_rome_bm), C(amd_rome_bm_gpu), C(intel_icelake_bm),
                      C(intel_skylake_bm), and C(generic_bm).
                    - Use a value supported by the installed OCI SDK and the selected shape.
                    - The module converts this value to uppercase for OCI.
                    - See L(Oracle platform types,
                      https://docs.oracle.com/iaas/tools/python/latest/api/core/models/oci.core.models.InstanceConfigurationLaunchInstancePlatformConfig.html)
                      for supported values.
                    type: str
                    required: true
                  is_secure_boot_enabled:
                    description:
                    - Enable Secure Boot for the instance.
                    type: bool
                  is_trusted_platform_module_enabled:
                    description:
                    - Enable the Trusted Platform Module for the instance.
                    type: bool
                  is_measured_boot_enabled:
                    description:
                    - Enable measured boot for the instance.
                    type: bool
                  is_memory_encryption_enabled:
                    description:
                    - Enable memory encryption for the instance.
                    type: bool
              source_details:
                description:
                - Select the image or boot volume used to launch the instance.
                type: dict
                suboptions:
                  boot_volume_size_in_gbs:
                    description:
                    - Set the boot volume size in gigabytes.
                    type: int
                  image_id:
                    description:
                    - The OCID of the image used to launch the instance.
                    type: str
                  kms_key_id:
                    description:
                    - The OCID of the Vault key used to encrypt the boot volume.
                    type: str
                  boot_volume_vpus_per_gb:
                    description:
                    - The boot volume performance units (VPUs) per GB.
                    - Use C(10) for Balanced or C(20) for Higher Performance.
                    - Use C(30) through C(120) for Ultra High Performance.
                    - With performance autotuning, this value sets the minimum performance level.
                    type: int
                  instance_source_image_filter_details:
                    description:
                    - Filter images by compartment
                    - tags
                    - operating system
                    - and version.
                    type: dict
                    suboptions:
                      compartment_id:
                        description:
                        - The OCID of the compartment to search for images.
                        type: str
                      defined_tags_filter:
                        description:
                        - Select images that match these defined tags.
                        type: dict
                      operating_system:
                        description:
                        - Select images by operating system name.
                        type: str
                      operating_system_version:
                        description:
                        - Select images by operating system version.
                        type: str
                  source_type:
                    description:
                    - Select whether to launch from an image or a boot volume.
                    type: str
                    choices: [image, boot_volume]
                    required: true
                  boot_volume_id:
                    description:
                    - The OCID of the boot volume used to launch the instance.
                    type: str
              fault_domain:
                description:
                - Select the fault domain for the instance.
                type: str
              dedicated_vm_host_id:
                description:
                - The OCID of the dedicated VM host for the instance.
                type: str
              launch_mode:
                description:
                - Select the launch mode used to boot the instance.
                type: str
                choices: [native, emulated, paravirtualized, custom]
              launch_options:
                description:
                - Set the firmware
                - network
                - and volume device options for the instance.
                type: dict
                suboptions:
                  boot_volume_type:
                    description:
                    - Select the device type for the boot volume.
                    type: str
                    choices: [ide, iscsi, paravirtualized, scsi, vfio]
                  firmware:
                    description:
                    - Select the firmware type used to boot the instance.
                    type: str
                    choices: [bios, uefi_64]
                  network_type:
                    description:
                    - Select the network device type for the instance.
                    type: str
                    choices: [acceleratedpv, e1000, paravirtualized, vfio]
                  remote_data_volume_type:
                    description:
                    - Select the device type for remote data volumes.
                    type: str
                    choices: [ide, iscsi, paravirtualized, scsi, vfio]
                  is_pv_encryption_in_transit_enabled:
                    description:
                    - Deprecated. Use the instance-level encryption option instead.
                    type: bool
                  is_consistent_volume_naming_enabled:
                    description:
                    - Enable consistent device names for attached volumes.
                    type: bool
              agent_config:
                description:
                - Set Oracle Cloud Agent and plugin settings for the instance.
                type: dict
                suboptions:
                  all_plugins_disabled:
                    description:
                    - Disable all Oracle Cloud Agent plugins.
                    type: bool
                  management_disabled:
                    description:
                    - Disable Oracle Cloud Agent management plugins.
                    type: bool
                  monitoring_disabled:
                    description:
                    - Disable Oracle Cloud Agent monitoring plugins.
                    type: bool
                  plugins_config:
                    description:
                    - Set the desired state for individual Oracle Cloud Agent plugins.
                    type: list
                    elements: dict
                    suboptions:
                      name:
                        description:
                        - The name of the Oracle Cloud Agent plugin.
                        - This value is required for instance options templates.
                        type: str
                        required: true
                      desired_state:
                        description:
                        - Select whether to enable or disable the plugin.
                        - This value is required for instance options templates.
                        type: str
                        choices: [enabled, disabled]
                        required: true
              is_pv_encryption_in_transit_enabled:
                description:
                - Enable encryption in transit for paravirtualized data volume attachments.
                type: bool
              preferred_maintenance_action:
                description:
                - Select the action to use during scheduled maintenance.
                type: str
                choices: [live_migrate, reboot]
              instance_options:
                description:
                - Set instance behavior options.
                type: dict
                suboptions:
                  are_legacy_imds_endpoints_disabled:
                    description:
                    - Disable access to legacy instance metadata service endpoints.
                    type: bool
              availability_config:
                description:
                - Set live migration and recovery behavior for the instance.
                type: dict
                suboptions:
                  is_live_migration_preferred:
                    description:
                    - Prefer live migration during maintenance when available.
                    type: bool
                  recovery_action:
                    description:
                    - Select the action to take after an instance recovery event.
                    type: str
                    choices: [restore_instance, stop_instance]
              preemptible_instance_config:
                description:
                - Set behavior for a preemptible instance.
                type: dict
                suboptions:
                  preemption_action:
                    description:
                    - The settings used when OCI reclaims the instance.
                    - OCI terminates the instance; set C(preserve_boot_volume) to retain its
                      boot volume.
                    type: dict
                    required: true
                    suboptions:
                      preserve_boot_volume:
                        description:
                        - Preserve the boot volume when OCI terminates the instance.
                        type: bool
          secondary_vnics:
            description:
            - Define secondary VNICs for the instance.
            type: list
            elements: dict
            suboptions:
              create_vnic_details:
                description:
                - Set the properties for a secondary VNIC.
                type: dict
                suboptions:
                  assign_public_ip:
                    description:
                    - Assign a public IP address to the secondary VNIC.
                    type: bool
                  assign_private_dns_record:
                    description:
                    - Create a private DNS record for the secondary VNIC.
                    type: bool
                  defined_tags:
                    description:
                    - Set defined tags for the secondary VNIC
                    - grouped by namespace.
                    type: dict
                  name:
                    description:
                    - Set the display name for the secondary VNIC.
                    type: str
                  freeform_tags:
                    description:
                    - Set free-form tags for the secondary VNIC.
                    type: dict
                  hostname_label:
                    description:
                    - Set the hostname label for the secondary VNIC private IP address.
                    type: str
                  nsg_ids:
                    description:
                    - The OCIDs of network security groups to add to the secondary VNIC.
                    type: list
                    elements: str
                  private_ip:
                    description:
                    - Set the private IP address for the secondary VNIC.
                    type: str
                  skip_source_dest_check:
                    description:
                    - Disable the source and destination check for the secondary VNIC.
                    type: bool
                  subnet_id:
                    description:
                    - The OCID of the subnet for the secondary VNIC.
                    type: str
              name:
                description:
                - Set the display name for the secondary VNIC entry.
                type: str
              nic_index:
                description:
                - Set the NIC index for the secondary VNIC.
                type: int
  name:
    description:
    - The name of the configuration.
    - Creation requires this option.
    - Without C(instance_configuration_id), the module searches by C(compartment_id) and C(name).
    type: str
  compartment_id:
    description:
    - The OCID of the compartment that contains the configuration.
    - Creation and name lookup require this option.
    - This module does not move existing configurations between compartments.
    type: str
notes:
- OCI returns synchronous create and update results without lifecycle states.
- The wait options control confirmation of deletion through HTTP 404.
"""

EXAMPLES = r"""
- name: Create a configuration with a flexible compute shape
  ansible.oci.oci_instance_configuration:
    compartment_id: ocid1.compartment.oc1..example
    name: app-template
    source: none
    instance_details:
      instance_type: compute
      launch_details:
        shape: VM.Standard.E4.Flex
        shape_config:
          ocpus: 2
          memory_in_gbs: 16
        source_details:
          source_type: image
          image_id: ocid1.image.oc1..example
  register: configuration

- name: Update a configuration name by its OCID
  ansible.oci.oci_instance_configuration:
    instance_configuration_id: ocid1.instanceconfiguration.oc1..example
    name: app-template-updated
    compartment_id: ocid1.compartment.oc1..example

- name: Create a configuration from an existing instance
  ansible.oci.oci_instance_configuration:
    compartment_id: ocid1.compartment.oc1..example
    name: copied-instance-template
    source: instance
    instance_id: ocid1.instance.oc1..example

- name: Get information about a configuration
  ansible.oci.oci_instance_configuration_info:
    instance_configuration_id: "{{ configuration.resource.id }}"
  register: configuration_info

- name: Delete a configuration by its OCID
  ansible.oci.oci_instance_configuration:
    instance_configuration_id: ocid1.instanceconfiguration.oc1..example
    state: absent
"""

RETURN = r"""
resource:
  description: The instance configuration. Unset fields can be null.
  returned: when state=present and a resource is available
  type: dict
  contains:
    id:
      description: The OCID of the resource.
      type: str
      returned: always
    name:
      description: The name of the configuration.
      type: str
      returned: always
    compartment_id:
      description: The OCID of the compartment that contains this resource.
      type: str
      returned: always
    instance_details:
      description: The Compute template stored in the configuration.
      type: dict
      returned: when a complete configuration is returned
    deferred_fields:
      description: The omitted settings that OCI requires when launching an instance.
      type: list
      returned: when a complete configuration is returned
      elements: str
    freeform_tags:
      description: The free-form tags assigned to this resource.
      type: dict
      returned: always
    defined_tags:
      description: The defined tags, grouped by tag namespace.
      type: dict
      returned: always
    time_created:
      description: The creation time in RFC 3339 format.
      type: str
      returned: always
  sample:
    id: ocid1.instanceconfiguration.oc1..example
    name: application-template
    compartment_id: ocid1.compartment.oc1..example
    instance_details:
      instance_type: compute
      launch_details:
        shape: VM.Standard.E4.Flex
"""

from copy import deepcopy

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_COMMON_ARGS,
    import_oci_sdk,
    serialize_oci_model,
    values_differ_as_subset,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_instance import (
    INSTANCE_CONFIGURATION_BLOCK_VOLUME_ARGS,
    INSTANCE_CONFIGURATION_LAUNCH_ARGS,
    INSTANCE_CONFIGURATION_SECONDARY_VNIC_ARGS,
    build_instance_configuration_details,
)

oci = import_oci_sdk()[0]

COMPUTE_CONFIGURATION_ENTRY_ARGS = dict(
    instance_type=dict(type="str", choices=["compute"], required=True),
    block_volumes=dict(
        type="list", elements="dict", options=INSTANCE_CONFIGURATION_BLOCK_VOLUME_ARGS
    ),
    launch_details=dict(type="dict", options=INSTANCE_CONFIGURATION_LAUNCH_ARGS),
    secondary_vnics=dict(
        type="list",
        elements="dict",
        options=INSTANCE_CONFIGURATION_SECONDARY_VNIC_ARGS,
    ),
)


class OciInstanceConfigurationModule(OciResourceBase):
    """Resource adapter for OCI Compute instance configurations."""

    @property
    def client_class(self):
        """Return the Compute Management client class.

        Returns:
            The OCI SDK client class.
        """
        return oci.core.ComputeManagementClient

    resource_id_param = "instance_configuration_id"
    list_resource_method = "list_instance_configurations"
    list_filter_params = ()
    resource_get_method = "get_instance_configuration"
    name_response_field = "display_name"
    create_required_fields = ("compartment_id", "name")
    create_resource_name = "instance configuration"
    update_method_name = "update_instance_configuration"
    update_details_name = "update_instance_configuration_details"
    update_wait_states = None
    update_field_specs = (
        UpdateFieldSpec(param_name="name", resource_field="display_name", is_mutable=True),
        UpdateFieldSpec(
            param_name="compartment_id",
            is_mutable=False,
            immutable_reason=(
                "This module does not move configurations between compartments; "
                "OCI provides a separate compartment change operation"
            ),
        ),
        UpdateFieldSpec(
            param_name="instance_details",
            resource_field="instance_details",
            is_mutable=False,
            compare="subset_dict",
            immutable_reason="OCI instance configuration templates are immutable",
        ),
    )

    def get_resource_response(self, resource_id):
        """Return the SDK response for one configuration.

        Args:
            resource_id: The configuration OCID.

        Returns:
            The OCI SDK response.
        """
        return self.call_with_retry(
            self.client.get_instance_configuration,
            instance_configuration_id=resource_id,
        )

    def hydrate_named_resource(self, resource):
        """Fetch full configuration details after a name lookup.

        The list response omits template details, so the base implementation
        cannot compare immutable template inputs after a name lookup.

        Args:
            resource: The summary model returned by the list operation.

        Returns:
            The full configuration model.
        """
        return self.get_resource_by_id(resource.id)

    def validate_create_request(self):
        """Validate creation because templates permit deferred launch fields.

        Raises:
            AnsibleFailJson: If the selected source has missing or conflicting inputs.
        """
        super().validate_create_request()
        source = self.module.params.get("source") or "none"
        instance_id = self.module.params.get("instance_id")
        instance_details = self.module.params.get("instance_details")
        if source == "none" and instance_id:
            self.module.fail_json(msg="instance_id is only valid when source=instance")
        if source == "instance" and instance_details:
            self.module.fail_json(msg="instance_details is only valid when source=none")
        if source == "none" and not instance_details:
            self.module.fail_json(msg="Creating with source=none requires instance_details")
        if source == "instance" and not self.module.params.get("instance_id"):
            self.module.fail_json(msg="Creating with source=instance requires instance_id")
        if instance_details:
            details_type = instance_details.get("instance_type", "compute")
            direct_compute_fields = (
                "block_volumes",
                "launch_details",
                "secondary_vnics",
            )
            if details_type == "compute" and instance_details.get("options"):
                self.module.fail_json(
                    msg=(
                        "instance_details.options is only valid when "
                        "instance_type=instance_options"
                    )
                )
            if details_type == "instance_options" and any(
                instance_details.get(field) is not None for field in direct_compute_fields
            ):
                self.module.fail_json(
                    msg=(
                        "block_volumes, launch_details, and secondary_vnics must "
                        "be set inside options when instance_type=instance_options"
                    )
                )

    def create_resource(self):
        """Create a configuration and return its SDK model.

        Returns:
            The created configuration model.
        """
        params = self.module.params
        source = params.get("source") or "none"
        common = dict(
            compartment_id=params.get("compartment_id"),
            display_name=params.get("name"),
            freeform_tags=params.get("freeform_tags"),
            defined_tags=params.get("defined_tags"),
            source=source.upper(),
        )
        if source == "instance":
            details = oci.core.models.CreateInstanceConfigurationFromInstanceDetails(
                instance_id=params.get("instance_id"), **common
            )
        else:
            details = oci.core.models.CreateInstanceConfigurationDetails(
                instance_details=build_instance_configuration_details(
                    params.get("instance_details")
                ),
                **common
            )
        return self.call_with_retry(
            self.client.create_instance_configuration,
            create_instance_configuration=details,
        ).data

    def build_update_details(self, update_model_fields):
        """Build the SDK update model from mutable fields.

        Args:
            update_model_fields: Fields selected by the shared update planner.

        Returns:
            The OCI update details model.
        """
        return oci.core.models.UpdateInstanceConfigurationDetails(**update_model_fields)

    def delete_resource(self, resource):
        """Delete the configuration and wait until OCI removes it.

        Args:
            resource: The configuration model to delete.

        Returns:
            The result from the shared delete waiter.
        """
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_instance_configuration,
            instance_configuration_id=resource.id,
        )

    def compare_update_field_values(self, current_value, desired_value, compare=None):
        """Compare templates as normalized nested subsets, including list items.

        The base comparison does not type nested template data or compare list
        entries as nested subsets.

        Args:
            current_value: The SDK template value.
            desired_value: The user supplied template value.
            compare: The selected shared comparison strategy.

        Returns:
            True when values differ.
        """
        if compare == "subset_dict":
            current_value = serialize_oci_model(current_value)
            desired_value = serialize_oci_model(build_instance_configuration_details(desired_value))
            return values_differ_as_subset(current_value, desired_value, compare_list_items=True)
        return super().compare_update_field_values(current_value, desired_value, compare)


def main():
    """Run the instance configuration resource module."""
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        instance_configuration_id=dict(type="str"),
        source=dict(type="str", choices=["none", "instance"], default="none"),
        instance_id=dict(type="str"),
        instance_details=dict(
            type="dict",
            options={
                **deepcopy(COMPUTE_CONFIGURATION_ENTRY_ARGS),
                "instance_type": dict(
                    type="str", choices=["compute", "instance_options"], default="compute"
                ),
                "options": dict(
                    type="list", elements="dict", options=deepcopy(COMPUTE_CONFIGURATION_ENTRY_ARGS)
                ),
            },
        ),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[("instance_id", "instance_details")],
    )
    OciInstanceConfigurationModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
