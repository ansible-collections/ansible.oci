# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_instance
short_description: Manage a Compute instance resource in Oracle Cloud Infrastructure
description:
  - Launch, update, and terminate OCI Compute instances.
  - Uses the shared OCI helper layer for authentication, waiting, retry
    behavior, and result shaping.
  - Create requests must omit C(instance_id). After create, capture the
    returned instance ID and use it for later C(state=present) and
    C(state=absent) tasks.
  - C(power_state) drives OCI power actions (start/stop) independently of
    C(state). It is evaluated after create and on every C(state=present) run.
  - This module does not support attaching extra volumes at launch
    (C(launch_volume_attachments)), placement-constraint-based capacity
    topologies, or C(licensing_configs). It also does not update
    C(create_vnic_details) fields (for example C(subnet_id) or
    C(assign_public_ip)) after create.
version_added: "1.0.0"
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
      - The desired lifecycle state of the instance.
    type: str
    choices: [present, absent]
    default: present
  instance_id:
    description:
      - The OCID of the instance.
      - When provided, the module manages this exact instance.
      - Required to distinguish between multiple instances that share the
        same scoped C(name).
    type: str
  name:
    description:
      - Human-readable name for the instance.
      - Required when creating an instance.
      - When C(instance_id) is omitted, the module uses
        C(compartment_id + name) to find an existing instance.
      - If exactly one instance matches, C(state=present) manages it as the
        update target and C(state=absent) terminates it.
      - If more than one instance matches, the task fails and the caller must
        supply C(instance_id).
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the instance.
      - Required when creating an instance.
      - The module does not move an existing instance to another compartment.
      - Also scopes name-based instance lookups when C(instance_id) is
        omitted.
    type: str
  availability_domain:
    description:
      - The availability domain to launch the instance in.
      - Required when creating an instance.
      - The module does not update this field after create.
      - Availability domain names are tenancy-specific; use
        M(ansible.oci.oci_availability_domain_info) to discover the valid
        names for your tenancy and region instead of hardcoding them.
    type: str
  fault_domain:
    description:
      - The fault domain to launch the instance in.
      - The module does not update this field after create.
    type: str
  shape:
    description:
      - The shape of the instance, for example C(VM.Standard.E4.Flex).
      - Required when creating an instance.
      - Use M(ansible.oci.oci_shape_info) to discover compatible shape names and
        their capabilities before launching an instance.
      - Supports updates. OCI requires the instance to be stopped before
        changing its shape.
      - OCI stages shape changes made while the instance is stopped and only
        applies them the next time the instance starts. C(resource) reflects
        the previous value until then; rerunning this module with C(wait=true)
        after C(power_state=running) confirms the change applied.
    type: str
  shape_config:
    description:
      - Flexible shape configuration for shapes that support it.
      - Supports updates. OCI requires the instance to be stopped before
        changing shape configuration.
      - OCI stages shape_config changes made while the instance is stopped and
        only applies them the next time the instance starts. C(resource)
        reflects the previous values until then; rerunning this module with
        C(wait=true) after C(power_state=running) confirms the resize applied.
    type: dict
    suboptions:
      ocpus:
        description:
          - The total number of OCPUs available to the instance.
        type: float
      memory_in_gbs:
        description:
          - The total amount of memory available to the instance, in
            gigabytes.
        type: float
  image_id:
    description:
      - The OCID of the image used to launch the instance.
      - Use M(ansible.oci.oci_image_info) to discover platform and custom image
        OCIDs before launching an instance.
      - Exactly one of C(image_id) or C(boot_volume_id) is required when
        creating an instance.
      - The module does not update this field after create.
    type: str
  boot_volume_id:
    description:
      - The OCID of an existing boot volume to launch the instance from.
      - Exactly one of C(image_id) or C(boot_volume_id) is required when
        creating an instance.
      - The module does not update this field after create.
    type: str
  boot_volume_size_in_gbs:
    description:
      - The size of the boot volume in GBs.
      - Only used when creating from C(image_id).
      - The module does not update this field after create.
    type: int
  boot_volume_vpus_per_gb:
    description:
      - The number of volume performance units per GB used to baseline boot
        volume I/O performance, for example C(10) for balanced or C(20) for
        higher performance.
      - Only used when creating from C(image_id).
      - The module does not update this field after create.
    type: int
  kms_key_id:
    description:
      - The OCID of the Vault service key used to encrypt the boot volume.
      - Only used when creating from C(image_id).
      - The module does not update this field after create.
    type: str
  preserve_boot_volume_on_delete:
    description:
      - Whether to preserve the boot volume when terminating the instance with
        C(state=absent).
      - If omitted or set to C(false), OCI deletes the boot volume.
      - Only used when deleting an instance.
    type: bool
  subnet_id:
    description:
      - The OCID of the subnet for the instance's primary VNIC.
      - Required when creating an instance.
      - The module does not support moving an existing instance to another
        subnet.
    type: str
  assign_public_ip:
    description:
      - Whether to assign a public IP address to the primary VNIC.
      - The module does not update this field after create.
    type: bool
  vnic_name:
    description:
      - The display name for the instance's primary VNIC.
      - The module does not update this field after create.
    type: str
  private_ip:
    description:
      - A manually assigned private IPv4 address for the instance's primary
        VNIC.
      - Mutually exclusive with C(private_ip_id).
      - The module does not update this field after create.
    type: str
  private_ip_id:
    description:
      - The OCID of an existing reserved private IPv4 address to assign to the
        instance's primary VNIC.
      - Mutually exclusive with C(private_ip).
      - The module does not update this field after create.
    type: str
  hostname_label:
    description:
      - The hostname label for the primary VNIC.
      - The module does not update this field after create.
    type: str
  nsg_ids:
    description:
      - The OCIDs of the network security groups the primary VNIC belongs to.
      - The module does not update this field after create.
    type: list
    elements: str
  metadata:
    description:
      - Custom metadata key/value pairs, for example C(ssh_authorized_keys)
        and C(user_data) for cloud-init.
      - C(user_data) must already be base64-encoded, matching the OCI API
        contract.
      - Supports updates.
    type: dict
  extended_metadata:
    description:
      - Additional metadata key/value pairs that support nested JSON objects,
        for backward compatibility with older tooling that expects them
        separate from C(metadata).
      - Supports updates.
    type: dict
  security_attributes:
    description:
      - Zero Trust Packet Routing security attributes to apply to the
        instance, keyed by security attribute namespace.
      - Supports updates.
    type: dict
  launch_options:
    description:
      - Advanced boot and network emulation options. OCI infers safe defaults
        for most shapes and images; only set these to override that
        inference.
      - Supports updates, but OCI generally requires the instance to be
        stopped for the new values to take effect.
    type: dict
    suboptions:
      boot_volume_type:
        description:
          - The emulation type for the boot volume.
          - C(paravirtualized) is the common case for virtual machine shapes.
        type: str
        choices: [ide, iscsi, paravirtualized, scsi, vfio]
      firmware:
        description:
          - The firmware used to boot the instance.
        type: str
        choices: [bios, uefi_64]
      network_type:
        description:
          - The emulation type for the primary VNIC.
        type: str
        choices: [acceleratedpv, e1000, paravirtualized, vfio]
      remote_data_volume_type:
        description:
          - The emulation type for attached block volumes other than the boot
            volume.
        type: str
        choices: [ide, iscsi, paravirtualized, scsi, vfio]
      is_pv_encryption_in_transit_enabled:
        description:
          - Whether to enable in-transit encryption for the data volume's
            paravirtualized attachment.
        type: bool
      is_consistent_volume_naming_enabled:
        description:
          - Whether to enable consistent, OCI-assigned device naming for
            attached volumes.
        type: bool
  instance_options:
    description:
      - Optional mutable instance options.
      - Supports updates.
    type: dict
    suboptions:
      are_legacy_imds_endpoints_disabled:
        description:
          - Whether to disable the legacy (v1) instance metadata service
            endpoints, allowing only the more secure v2 endpoints.
        type: bool
  availability_config:
    description:
      - Options controlling what happens to the instance when the underlying
        infrastructure it runs on undergoes maintenance.
      - Supports updates.
    type: dict
    suboptions:
      is_live_migration_preferred:
        description:
          - Whether to prefer live migration over a reboot migration when
            infrastructure maintenance requires moving the instance.
        type: bool
      recovery_action:
        description:
          - What to do with the instance when infrastructure maintenance
            requires rebooting it.
        type: str
        choices: [restore_instance, stop_instance]
  preemptible_instance_config:
    description:
      - Marks the instance as preemptible, letting OCI reclaim its capacity
        when needed in exchange for lower cost.
      - Only used when creating an instance. The module does not update this
        field after create, and does not detect drift on it.
    type: dict
    suboptions:
      preserve_boot_volume:
        description:
          - Whether to preserve the boot volume when OCI reclaims a
            preemptible instance.
        type: bool
  agent_config:
    description:
      - Configuration for the Oracle Cloud Agent software running on the
        instance.
      - Supports updates.
    type: dict
    suboptions:
      all_plugins_disabled:
        description:
          - When C(true), every Oracle Cloud Agent plugin is stopped,
            overriding C(management_disabled), C(monitoring_disabled), and
            C(plugins_config). This includes the management plugins (OS
            Management Service Agent, Compute Instance Run Command), the
            monitoring plugins (Compute Instance Monitoring, Custom Logs
            Monitoring), and every other plugin (for example Bastion, Block
            Volume Management, Vulnerability Scanning, OS Management Hub
            Agent, Management Agent).
          - When C(false), enablement is decided by C(management_disabled),
            C(monitoring_disabled), and C(plugins_config) instead. Plugins
            listed in C(plugins_config) can still report C(ENABLED) on the
            resource while this is C(true); they are configured but not
            running.
          - Returned by OCI as C(are_all_plugins_disabled).
        type: bool
      management_disabled:
        description:
          - When C(true), the management plugins (OS Management Service
            Agent, Compute Instance Run Command) are stopped regardless of
            C(plugins_config).
          - When C(false), those two plugins follow their C(plugins_config)
            entries (or their platform default when unset).
          - Returned by OCI as C(is_management_disabled).
        type: bool
      monitoring_disabled:
        description:
          - When C(true), the monitoring plugins (Compute Instance
            Monitoring, Custom Logs Monitoring) are stopped regardless of
            C(plugins_config).
          - When C(false), those two plugins follow their C(plugins_config)
            entries (or their platform default when unset).
          - Returned by OCI as C(is_monitoring_disabled).
        type: bool
      plugins_config:
        description:
          - Per-plugin desired state, for example the Bastion or OS
            Management Hub Agent plugin. Available plugin names depend on
            the instance's image; use the names returned by
            M(ansible.oci.oci_instance_info) rather than hardcoding a list.
          - C(all_plugins_disabled), and C(management_disabled) or
            C(monitoring_disabled) for the plugins they cover, override the
            per-plugin C(desired_state) set here.
          - This list is compared as a whole against the resource, not
            matched element by element per plugin name. If this task lists
            only a subset of the plugins OCI returns (for example only
            Bastion, while OCI also returns Compute Instance Monitoring and
            others), the comparison always detects drift and the module
            reports C(changed) on every run, even though the unlisted
            plugins are left alone. To make this idempotent, supply the
            full C(plugins_config) list the instance already has (for
            example built from a prior M(ansible.oci.oci_instance_info)
            read), not just the plugins you intend to change.
        type: list
        elements: dict
        suboptions:
          name:
            description:
              - The plugin name, for example C(OS Management Hub Agent).
            type: str
          desired_state:
            description:
              - Whether the plugin should be enabled or disabled.
            type: str
            choices: [enabled, disabled]
  platform_config:
    description:
      - Platform-specific configuration, including confidential-computing
        options such as Secure Boot and firmware measurement.
      - Which suboptions are accepted depends on C(type); virtual machine
        shapes only support the confidential-computing booleans, while bare
        metal shapes also support the NUMA and core-count options.
      - Supports updates, though OCI may not support updating C(type) itself
        or bare-metal-only suboptions after create.
    type: dict
    suboptions:
      type:
        description:
          - The platform configuration family, matching the instance's shape.
            Not every shape supports C(platform_config); use
            M(ansible.oci.oci_shape_info) to look up the value for your shape
            (returned as C(shapes[].platform_config_options.type)) before
            setting this, since supported types can change as OCI adds shapes.
        type: str
      is_secure_boot_enabled:
        description:
          - Whether Secure Boot is enabled.
        type: bool
      is_trusted_platform_module_enabled:
        description:
          - Whether the Trusted Platform Module (TPM) is enabled.
        type: bool
      is_measured_boot_enabled:
        description:
          - Whether Measured Boot is enabled.
        type: bool
      is_memory_encryption_enabled:
        description:
          - Whether total memory encryption is enabled.
        type: bool
      is_symmetric_multi_threading_enabled:
        description:
          - Whether symmetric multithreading is enabled.
        type: bool
      numa_nodes_per_socket:
        description:
          - The NUMA nodes per socket. Only used for bare metal C(type)
            values.
        type: str
        choices: [nps0, nps1, nps2, nps4, nps6]
      is_access_control_service_enabled:
        description:
          - Whether the Access Control Service is enabled. Only used for bare
            metal C(type) values.
        type: bool
      are_virtual_instructions_enabled:
        description:
          - Whether virtualization instructions are available for nested
            virtualization. Only used for bare metal C(type) values.
        type: bool
      is_input_output_memory_management_unit_enabled:
        description:
          - Whether an I/O Memory Management Unit is enabled. Only used for
            bare metal C(type) values.
        type: bool
      percentage_of_cores_enabled:
        description:
          - The percentage of cores enabled, for fractional bare metal
            billing. Only used for bare metal C(type) values.
        type: int
  capacity_reservation_id:
    description:
      - The OCID of the compute capacity reservation this instance launches
        into.
      - Supports updates.
    type: str
  dedicated_vm_host_id:
    description:
      - The OCID of the dedicated virtual machine host this instance launches
        onto.
      - Supports updates.
    type: str
  cluster_placement_group_id:
    description:
      - The OCID of the cluster placement group for this instance.
      - The module does not update this field after create.
    type: str
  compute_cluster_id:
    description:
      - The OCID of the compute cluster this instance launches into, for
        remote direct memory access (RDMA) network placement.
      - The module does not update this field after create.
    type: str
  instance_configuration_id:
    description:
      - The OCID of the instance configuration used as a template for this
        launch.
      - The module does not update this field after create.
    type: str
  ipxe_script:
    description:
      - A custom iPXE script to control the instance's boot process.
      - The module does not update this field after create.
    type: str
  is_pv_encryption_in_transit_enabled:
    description:
      - Whether in-transit encryption is enabled for the boot volume's
        paravirtualized attachment.
      - The module does not update this field after create, and does not
        detect drift on it.
    type: bool
  is_ai_enterprise_enabled:
    description:
      - Whether NVIDIA AI Enterprise (NVAIE) is enabled for this instance.
      - Only relevant for supported NVIDIA GPU shapes. OCI ignores this on
        shapes that don't support NVIDIA AI Enterprise.
      - Supports updates.
    type: bool
  power_state:
    description:
      - The desired power state of the instance.
      - When set, the module issues an OCI power action to reach this state
        whenever it differs from the instance's current C(lifecycle_state).
      - Applied on create (after the instance reaches C(running)) and on
        every C(state=present) run.
    type: str
    choices: [running, stopped]
"""

EXAMPLES = r"""
- name: Launch an instance
  ansible.oci.oci_instance:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    name: example-instance
    shape: VM.Standard.E4.Flex
    shape_config:
      ocpus: 1
      memory_in_gbs: 16
    image_id: ocid1.image.oc1..example
    subnet_id: ocid1.subnet.oc1..example
    assign_public_ip: true
    metadata:
      ssh_authorized_keys: "ssh-rsa AAAA..."
  register: created_instance

- name: Launch an instance with a named primary VNIC and manual private IP
  ansible.oci.oci_instance:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    name: example-instance-with-static-private-ip
    shape: VM.Standard.E4.Flex
    image_id: ocid1.image.oc1..example
    subnet_id: ocid1.subnet.oc1..example
    vnic_name: example-primary-vnic
    private_ip: 10.0.0.10

- name: Look up the platform_config type supported by a shape before using it
  ansible.oci.oci_shape_info:
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    shape: VM.Standard.E4.Flex
  register: shape_lookup

- name: Launch an instance from an existing boot volume with confidential computing and agent options
  ansible.oci.oci_instance:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    name: example-instance-from-boot-volume
    shape: VM.Standard.E4.Flex
    shape_config:
      ocpus: 2
      memory_in_gbs: 32
    boot_volume_id: ocid1.bootvolume.oc1..example
    subnet_id: ocid1.subnet.oc1..example
    platform_config:
      # "amd_vm" here matches VM.Standard.E4.Flex; do not hardcode this for
      # other shapes, instead use the type discovered above:
      # "{{ shape_lookup.shapes[0].platform_config_options.type | lower }}"
      type: amd_vm
      is_secure_boot_enabled: true
      is_trusted_platform_module_enabled: true
      is_measured_boot_enabled: true
    availability_config:
      recovery_action: restore_instance
    instance_options:
      are_legacy_imds_endpoints_disabled: true
    agent_config:
      all_plugins_disabled: false
      plugins_config:
        - name: "Bastion"
          desired_state: enabled

- name: Reconcile a uniquely named instance by name
  ansible.oci.oci_instance:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    name: example-instance
    shape: VM.Standard.E4.Flex
    image_id: ocid1.image.oc1..example
    subnet_id: ocid1.subnet.oc1..example
    shape_config:
      ocpus: 2
      memory_in_gbs: 32

- name: Intentionally create a second instance with the same display name
  ansible.oci.oci_instance:
    state: present
    allow_duplicate_name: true
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    name: example-instance
    shape: VM.Standard.E4.Flex
    shape_config:
      ocpus: 1
      memory_in_gbs: 16
    image_id: ocid1.image.oc1..example
    subnet_id: ocid1.subnet.oc1..example

- name: Stop the instance
  ansible.oci.oci_instance:
    instance_id: "{{ created_instance.resource.id }}"
    power_state: stopped

- name: Resize the stopped instance's flexible shape
  ansible.oci.oci_instance:
    instance_id: "{{ created_instance.resource.id }}"
    shape_config:
      ocpus: 4
      memory_in_gbs: 64

- name: Start the instance again
  ansible.oci.oci_instance:
    instance_id: "{{ created_instance.resource.id }}"
    power_state: running

- name: Terminate the instance
  ansible.oci.oci_instance:
    state: absent
    instance_id: "{{ created_instance.resource.id }}"

- name: Terminate the instance but preserve its boot volume
  ansible.oci.oci_instance:
    state: absent
    instance_id: "{{ created_instance.resource.id }}"
    preserve_boot_volume_on_delete: true

- name: Terminate a uniquely named instance without providing instance_id
  ansible.oci.oci_instance:
    state: absent
    compartment_id: ocid1.compartment.oc1..example
    name: example-instance
"""

RETURN = r"""
resource:
  description: The instance resource.
  returned: when state != absent
  type: dict
  contains:
    id:
      description: The OCID of the instance.
      type: str
      returned: always
      sample: ocid1.instance.oc1..example
    name:
      description: The display name of the instance.
      type: str
      returned: always
      sample: example-instance
    compartment_id:
      description: The OCID of the compartment containing the instance.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    availability_domain:
      description: The availability domain the instance runs in.
      type: str
      returned: always
      sample: Uocm:PHX-AD-1
    fault_domain:
      description: The fault domain the instance runs in.
      type: str
      returned: always
      sample: FAULT-DOMAIN-1
    region:
      description: The region the instance runs in.
      type: str
      returned: always
      sample: us-phoenix-1
    shape:
      description: The shape of the instance.
      type: str
      returned: always
      sample: VM.Standard.E4.Flex
    shape_config:
      description: The flexible shape configuration of the instance, if any.
      type: dict
      returned: always
      sample: {"ocpus": 1.0, "memory_in_gbs": 16.0}
    image_id:
      description: The OCID of the image used to launch the instance, if any.
      type: str
      returned: always
      sample: ocid1.image.oc1..example
    source_details:
      description: The boot source details for the instance.
      type: dict
      returned: always
      sample: {"source_type": "image", "image_id": "ocid1.image.oc1..example"}
    lifecycle_state:
      description: The current lifecycle state of the instance.
      type: str
      returned: always
      sample: RUNNING
    launch_mode:
      description: How the instance's create_vnic_details, source_details, and other launch options were resolved.
      type: str
      returned: always
      sample: PARAVIRTUALIZED
    launch_options:
      description: The boot and network emulation options applied to the instance.
      type: dict
      returned: always
      sample: {"boot_volume_type": "PARAVIRTUALIZED", "firmware": "UEFI_64", "network_type": "PARAVIRTUALIZED"}
    instance_options:
      description: Mutable instance options applied to the instance.
      type: dict
      returned: always
      contains:
        are_legacy_imds_endpoints_disabled:
          description: Whether legacy (v1) instance metadata service endpoints are disabled.
          type: bool
          returned: always
          sample: true
      sample: {"are_legacy_imds_endpoints_disabled": true}
    availability_config:
      description: Maintenance-related availability options applied to the instance.
      type: dict
      returned: always
      contains:
        is_live_migration_preferred:
          description: Whether live migration is preferred over a reboot migration.
          type: bool
          returned: always
          sample: true
        recovery_action:
          description: What OCI does with the instance during infrastructure maintenance.
          type: str
          returned: always
          sample: RESTORE_INSTANCE
      sample: {"is_live_migration_preferred": true, "recovery_action": "RESTORE_INSTANCE"}
    preemptible_instance_config:
      description: Preemptible-instance configuration, if the instance is preemptible.
      type: dict
      returned: always
      sample: null
    agent_config:
      description: Oracle Cloud Agent configuration applied to the instance.
      type: dict
      returned: always
      contains:
        are_all_plugins_disabled:
          description: Whether every Oracle Cloud Agent plugin is disabled.
          type: bool
          returned: always
          sample: false
        is_management_disabled:
          description: Whether Oracle Cloud Agent's management functionality is disabled.
          type: bool
          returned: always
          sample: false
        is_monitoring_disabled:
          description: Whether Oracle Cloud Agent's monitoring functionality is disabled.
          type: bool
          returned: always
          sample: false
        plugins_config:
          description: Per-plugin enablement.
          type: list
          returned: always
          sample: [{"name": "Bastion", "desired_state": "ENABLED"}]
      sample: {"are_all_plugins_disabled": false, "plugins_config": [{"name": "Bastion", "desired_state": "ENABLED"}]}
    platform_config:
      description: Platform-specific configuration for the instance's shape family. The available keys vary by C(type).
      type: dict
      returned: always
      sample: {"type": "AMD_VM", "is_secure_boot_enabled": true, "is_trusted_platform_module_enabled": true}
    capacity_reservation_id:
      description: The OCID of the compute capacity reservation the instance launched into, if any.
      type: str
      returned: always
      sample: null
    dedicated_vm_host_id:
      description: The OCID of the dedicated virtual machine host the instance runs on, if any.
      type: str
      returned: always
      sample: null
    cluster_placement_group_id:
      description: The OCID of the instance's cluster placement group, if any.
      type: str
      returned: always
      sample: null
    instance_configuration_id:
      description: The OCID of the instance configuration used to launch the instance, if any.
      type: str
      returned: always
      sample: null
    is_ai_enterprise_enabled:
      description: Whether NVIDIA AI Enterprise (NVAIE) is enabled for the instance.
      type: bool
      returned: always
      sample: false
    metadata:
      description: Custom metadata key/value pairs on the instance.
      type: dict
      returned: always
      sample: {"ssh_authorized_keys": "ssh-rsa AAAA..."}
    extended_metadata:
      description: Additional metadata key/value pairs that support nested JSON objects.
      type: dict
      returned: always
      sample: {}
    security_attributes:
      description: Zero Trust Packet Routing security attributes applied to the instance.
      type: dict
      returned: always
      sample: {}
    freeform_tags:
      description: Free-form tags applied to the instance.
      type: dict
      returned: always
      sample: {"environment": "production"}
    defined_tags:
      description: Defined tags applied to the instance.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
    system_tags:
      description: System tags applied to the instance by OCI services.
      type: dict
      returned: always
      sample: {}
    time_created:
      description: The date and time the instance was created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
    time_maintenance_reboot_due:
      description: The date and time the instance is due for a maintenance reboot, if any, in RFC3339 format.
      type: str
      returned: always
      sample: null
  sample:
    id: ocid1.instance.oc1..example
    name: example-instance
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    shape: VM.Standard.E4.Flex
    shape_config: {"ocpus": 1.0, "memory_in_gbs": 16.0}
    image_id: ocid1.image.oc1..example
    lifecycle_state: RUNNING
    metadata: {"ssh_authorized_keys": "ssh-rsa AAAA..."}
    freeform_tags: {"environment": "production"}
    defined_tags: {"Operations": {"CostCenter": "42"}}
    time_created: "2026-01-01T00:00:00.000Z"
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_RUNNING,
    LIFECYCLE_STOPPED,
    OCI_COMMON_ARGS,
    filter_none_values,
    import_oci_sdk,
    normalize_enum_values,
    rename_aliased_fields,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]

CREATE_REQUIRED_FIELDS = [
    "compartment_id",
    "availability_domain",
    "shape",
    "subnet_id",
    "name",
]
WAIT_FOR_LAUNCH_STATES = [LIFECYCLE_RUNNING]
WAIT_FOR_SETTLED_STATES = [LIFECYCLE_RUNNING, LIFECYCLE_STOPPED]
# OCI can reject instance mutations with 409 Conflict for up to roughly a
# minute while the instance is still settling from a preceding mutation.
# Lifecycle waiters only see RUNNING/STOPPED, so that 409 is a transient
# "try again later" condition, not a real conflict. Ride it out here
# alongside the default 429/500/503 handling.
INSTANCE_MUTATION_MAX_RETRIES = 10
INSTANCE_MUTATION_RETRY_ON = (409, 429, 500, 503)
POWER_STATE_ACTIONS = {
    LIFECYCLE_RUNNING: "START",
    LIFECYCLE_STOPPED: "STOP",
}

# Module inputs use lowercase snake_case choices (Ansible convention), while
# OCI's wire format and returned resources use upper-case constants (for
# example RECOVERY_ACTION_STOP_INSTANCE -> "STOP_INSTANCE"). Every enum-like
# suboption this module exposes converts cleanly with a plain str.upper(), so
# a single normalization helper keyed on field name covers all of them,
# instead of one-off conversions scattered across each builder function. This
# set is also assigned to OciInstanceModule.enum_keys so the shared
# "subset_dict" comparator (see oci_resource.py) normalizes the same way.
ENUM_KEYS = {
    "power_state",
    "recovery_action",
    "desired_state",
    "type",
    "boot_volume_type",
    "firmware",
    "network_type",
    "remote_data_volume_type",
    "numa_nodes_per_socket",
}

# For mapping input to SDK model fields.
AGENT_CONFIG_PARAM_TO_OCI = {
    "all_plugins_disabled": "are_all_plugins_disabled",
    "management_disabled": "is_management_disabled",
    "monitoring_disabled": "is_monitoring_disabled",
}


def build_create_vnic_details(params):
    details = filter_none_values(
        {
            "subnet_id": params.get("subnet_id"),
            "assign_public_ip": params.get("assign_public_ip"),
            "display_name": params.get("vnic_name"),
            "private_ip": params.get("private_ip"),
            "private_ip_id": params.get("private_ip_id"),
            "hostname_label": params.get("hostname_label"),
            "nsg_ids": params.get("nsg_ids"),
        }
    )
    if not details:
        return None
    return oci.core.models.CreateVnicDetails(**details)


def build_source_details(params):
    image_id = params.get("image_id")
    boot_volume_id = params.get("boot_volume_id")
    if image_id:
        details = filter_none_values(
            {
                "image_id": image_id,
                "boot_volume_size_in_gbs": params.get("boot_volume_size_in_gbs"),
                "boot_volume_vpus_per_gb": params.get("boot_volume_vpus_per_gb"),
                "kms_key_id": params.get("kms_key_id"),
            }
        )
        return oci.core.models.InstanceSourceViaImageDetails(**details)
    if boot_volume_id:
        return oci.core.models.InstanceSourceViaBootVolumeDetails(
            boot_volume_id=boot_volume_id
        )
    return None


def build_shape_config(params, model_class):
    shape_config = params.get("shape_config")
    if not shape_config:
        return None
    return model_class(**filter_none_values(dict(shape_config)))


def build_launch_options(params):
    launch_options = params.get("launch_options")
    if not launch_options:
        return None
    details = filter_none_values(normalize_enum_values(dict(launch_options), ENUM_KEYS))
    return oci.core.models.LaunchOptions(**details)


def build_instance_options(params):
    instance_options = params.get("instance_options")
    if not instance_options:
        return None
    return oci.core.models.InstanceOptions(**filter_none_values(dict(instance_options)))


def build_availability_config(params, model_class):
    availability_config = params.get("availability_config")
    if not availability_config:
        return None
    details = filter_none_values(normalize_enum_values(dict(availability_config), ENUM_KEYS))
    return model_class(**details)


def build_preemptible_instance_config(params):
    preemptible_instance_config = params.get("preemptible_instance_config")
    if not preemptible_instance_config:
        return None
    preemption_action = oci.core.models.TerminatePreemptionAction(
        **filter_none_values(
            {"preserve_boot_volume": preemptible_instance_config.get("preserve_boot_volume")}
        )
    )
    return oci.core.models.PreemptibleInstanceConfigDetails(
        preemption_action=preemption_action
    )


def build_agent_config(params, model_class):
    agent_config = params.get("agent_config")
    if not agent_config:
        return None
    agent_config = rename_aliased_fields(agent_config, AGENT_CONFIG_PARAM_TO_OCI)
    plugins_config = agent_config.get("plugins_config")
    plugins = None
    if plugins_config:
        plugins = [
            oci.core.models.InstanceAgentPluginConfigDetails(
                **filter_none_values(normalize_enum_values(dict(plugin_config), ENUM_KEYS))
            )
            for plugin_config in plugins_config
        ]
    details = filter_none_values(
        {
            "are_all_plugins_disabled": agent_config.get("are_all_plugins_disabled"),
            "is_management_disabled": agent_config.get("is_management_disabled"),
            "is_monitoring_disabled": agent_config.get("is_monitoring_disabled"),
            "plugins_config": plugins,
        }
    )
    return model_class(**details)


# OCI uses distinct model classes per operation for several nested configs
# (for example LaunchInstanceAvailabilityConfigDetails vs
# UpdateInstanceAvailabilityConfigDetails vs the response-only
# InstanceAvailabilityConfig), even though the field sets are identical.
# platform_config is additionally polymorphic on "type", and bare-metal
# platform_config types have no update-context class at all (OCI does not
# support updating their platform_config after launch).
def build_platform_config(params, class_suffix):
    platform_config = params.get("platform_config")
    if not platform_config:
        return None
    normalized = normalize_enum_values(dict(platform_config), ENUM_KEYS)
    platform_type = normalized.pop("type", None)
    # OCI's SDK codegen names each polymorphic subtype's class after its
    # "type" discriminator converted to PascalCase, e.g. "AMD_MILAN_BM" ->
    # "AmdMilanBm". Deriving it avoids hand-maintaining a type->class map
    # that would otherwise need a manual update every time OCI adds a new
    # shape family.
    class_prefix = "".join(word.capitalize() for word in (platform_type or "").split("_"))
    model_class = getattr(oci.core.models, f"{class_prefix}{class_suffix}", None)
    if model_class is None:
        is_known_type = any(
            name.startswith(class_prefix) for name in dir(oci.core.models)
        )
        if not is_known_type:
            raise ValueError(f"Unsupported platform_config type: {platform_config.get('type')}")
        raise ValueError(
            f"platform_config type {platform_config.get('type')} does not support this operation"
        )
    details = filter_none_values(normalized)
    details["type"] = platform_type
    return model_class(**details)


def build_create_instance_details(params):
    details = filter_none_values(
        {
            "availability_domain": params.get("availability_domain"),
            "compartment_id": params.get("compartment_id"),
            "display_name": params.get("name"),
            "shape": params.get("shape"),
            "shape_config": build_shape_config(
                params, oci.core.models.LaunchInstanceShapeConfigDetails
            ),
            "source_details": build_source_details(params),
            "create_vnic_details": build_create_vnic_details(params),
            "metadata": params.get("metadata"),
            "extended_metadata": params.get("extended_metadata"),
            "security_attributes": params.get("security_attributes"),
            "launch_options": build_launch_options(params),
            "instance_options": build_instance_options(params),
            "availability_config": build_availability_config(
                params, oci.core.models.LaunchInstanceAvailabilityConfigDetails
            ),
            "preemptible_instance_config": build_preemptible_instance_config(params),
            "agent_config": build_agent_config(
                params, oci.core.models.LaunchInstanceAgentConfigDetails
            ),
            "platform_config": build_platform_config(params, "LaunchInstancePlatformConfig"),
            "fault_domain": params.get("fault_domain"),
            "capacity_reservation_id": params.get("capacity_reservation_id"),
            "dedicated_vm_host_id": params.get("dedicated_vm_host_id"),
            "cluster_placement_group_id": params.get("cluster_placement_group_id"),
            "compute_cluster_id": params.get("compute_cluster_id"),
            "instance_configuration_id": params.get("instance_configuration_id"),
            "ipxe_script": params.get("ipxe_script"),
            "is_pv_encryption_in_transit_enabled": params.get(
                "is_pv_encryption_in_transit_enabled"
            ),
            "is_ai_enterprise_enabled": params.get("is_ai_enterprise_enabled"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.core.models.LaunchInstanceDetails(**details)


# Builders reused for the update path. Each takes a single-key params-shaped
# dict (matching the create-path builder signatures above) so update payloads
# go through the exact same construction and enum-normalization logic as
# create payloads.
NESTED_UPDATE_BUILDERS = {
    "shape_config": lambda value: build_shape_config(
        {"shape_config": value}, oci.core.models.UpdateInstanceShapeConfigDetails
    ),
    "launch_options": lambda value: build_launch_options({"launch_options": value}),
    "instance_options": lambda value: build_instance_options({"instance_options": value}),
    "availability_config": lambda value: build_availability_config(
        {"availability_config": value},
        oci.core.models.UpdateInstanceAvailabilityConfigDetails,
    ),
    "agent_config": lambda value: build_agent_config(
        {"agent_config": value}, oci.core.models.UpdateInstanceAgentConfigDetails
    ),
    "platform_config": lambda value: build_platform_config(
        {"platform_config": value}, "UpdateInstancePlatformConfig"
    ),
}


class OciInstanceModule(OciResourceBase):
    """Concrete resource adapter for OCI Compute instances."""

    @property
    def client_class(self):
        return oci.core.ComputeClient

    resource_id_param = "instance_id"
    list_resource_method = "list_instances"
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "instance"
    update_method_name = "update_instance"
    update_details_name = "update_instance_details"
    update_wait_states = WAIT_FOR_SETTLED_STATES
    enum_keys = ENUM_KEYS
    update_field_specs = (
        UpdateFieldSpec(
            param_name="name",
            resource_field="display_name",
            is_mutable=True,
        ),
        UpdateFieldSpec(
            param_name="shape",
            is_mutable=True,
        ),
        UpdateFieldSpec(
            param_name="shape_config",
            is_mutable=True,
            compare="subset_dict",
        ),
        UpdateFieldSpec(
            param_name="metadata",
            is_mutable=True,
        ),
        UpdateFieldSpec(
            param_name="extended_metadata",
            is_mutable=True,
        ),
        UpdateFieldSpec(
            param_name="security_attributes",
            is_mutable=True,
        ),
        UpdateFieldSpec(
            param_name="capacity_reservation_id",
            is_mutable=True,
        ),
        UpdateFieldSpec(
            param_name="dedicated_vm_host_id",
            is_mutable=True,
        ),
        UpdateFieldSpec(
            param_name="is_ai_enterprise_enabled",
            is_mutable=True,
        ),
        UpdateFieldSpec(
            param_name="launch_options",
            is_mutable=True,
            compare="subset_dict",
        ),
        UpdateFieldSpec(
            param_name="instance_options",
            is_mutable=True,
            compare="subset_dict",
        ),
        UpdateFieldSpec(
            param_name="availability_config",
            is_mutable=True,
            compare="subset_dict",
        ),
        UpdateFieldSpec(
            param_name="agent_config",
            is_mutable=True,
            compare="subset_dict",
            desired_key_map=AGENT_CONFIG_PARAM_TO_OCI,
        ),
        UpdateFieldSpec(
            param_name="platform_config",
            is_mutable=True,
            compare="subset_dict",
        ),
        UpdateFieldSpec(
            param_name="power_state",
            is_mutable=True,
            strategy="plan_power_state_strategy",
        ),
        UpdateFieldSpec(
            param_name="availability_domain",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="compartment_id",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="image_id",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="fault_domain",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="cluster_placement_group_id",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="compute_cluster_id",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="instance_configuration_id",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="ipxe_script",
            is_mutable=False,
        ),
    )

    def plan_power_state_strategy(self, resource, resource_dict, spec, desired_value):
        current_state = resource_dict.get("lifecycle_state")
        desired_state = normalize_enum_values({"power_state": desired_value}, ENUM_KEYS)[
            "power_state"
        ]
        if desired_state == current_state:
            return []
        action = POWER_STATE_ACTIONS.get(desired_state)
        if action is None:
            raise ValueError(f"Unsupported power_state: {desired_value}")
        return [action]

    def _apply_power_action(self, instance_id, action):
        self.call_with_retry(
            self.client.instance_action,
            instance_id=instance_id,
            action=action,
            max_retries=INSTANCE_MUTATION_MAX_RETRIES,
            retry_on=INSTANCE_MUTATION_RETRY_ON,
        )
        target_state = LIFECYCLE_RUNNING if action == "START" else LIFECYCLE_STOPPED
        return self.wait_for_resource_id(instance_id, [target_state])

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_instance,
            instance_id=resource_id,
        )

    def validate_create_request(self):
        super().validate_create_request()
        if not self.module.params.get("image_id") and not self.module.params.get(
            "boot_volume_id"
        ):
            self.module.fail_json(
                msg="Creating an instance requires either image_id or boot_volume_id"
            )

    def create_resource(self):
        response = self.call_with_retry(
            self.client.launch_instance,
            launch_instance_details=build_create_instance_details(self.module.params),
        )
        resource = self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_LAUNCH_STATES,
        )
        desired_power_state = normalize_enum_values(
            {"power_state": self.module.params.get("power_state")}, ENUM_KEYS
        )["power_state"]
        if (
            resource is not None
            and desired_power_state == LIFECYCLE_STOPPED
            and self.module.params.get("wait", True)
        ):
            resource = self._apply_power_action(resource.id, "STOP")
        return resource

    def update_resource(self, resource):
        update_plan = self.get_update_plan(resource)
        power_actions = []
        for strategy_operation in update_plan["strategy_operations"]:
            if strategy_operation["param_name"] == "power_state":
                power_actions = strategy_operation["operations"]
                break

        current_resource = resource
        if power_actions:
            for action in power_actions:
                current_resource = self._apply_power_action(resource.id, action)
            update_plan = self.get_update_plan(current_resource)

        if not update_plan["update_model_fields"]:
            return current_resource if power_actions else resource

        update_details = self.build_update_details(update_plan["update_model_fields"])
        response = self.call_with_retry(
            self.client.update_instance,
            instance_id=resource.id,
            update_instance_details=update_details,
            max_retries=INSTANCE_MUTATION_MAX_RETRIES,
            retry_on=INSTANCE_MUTATION_RETRY_ON,
        )
        return self.get_mutation_result(
            response.data,
            resource.id,
            WAIT_FOR_SETTLED_STATES,
        )

    def build_update_details(self, update_model_fields):
        update_model_fields = dict(update_model_fields)
        for field_name, builder in NESTED_UPDATE_BUILDERS.items():
            if field_name in update_model_fields:
                update_model_fields[field_name] = builder(update_model_fields[field_name])
        return oci.core.models.UpdateInstanceDetails(**update_model_fields)

    def delete_resource(self, resource):
        delete_kwargs = filter_none_values(
            {
                "instance_id": resource.id,
                "preserve_boot_volume": self.module.params.get(
                    "preserve_boot_volume_on_delete"
                ),
            }
        )
        return self.delete_resource_and_wait(
            resource,
            self.client.terminate_instance,
            **delete_kwargs,
        )


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        instance_id=dict(type="str"),
        availability_domain=dict(type="str"),
        fault_domain=dict(type="str"),
        shape=dict(type="str"),
        shape_config=dict(
            type="dict",
            options=dict(
                ocpus=dict(type="float"),
                memory_in_gbs=dict(type="float"),
            ),
        ),
        image_id=dict(type="str"),
        boot_volume_id=dict(type="str"),
        boot_volume_size_in_gbs=dict(type="int"),
        boot_volume_vpus_per_gb=dict(type="int"),
        kms_key_id=dict(type="str"),
        preserve_boot_volume_on_delete=dict(type="bool"),
        subnet_id=dict(type="str"),
        assign_public_ip=dict(type="bool"),
        vnic_name=dict(type="str"),
        private_ip=dict(type="str"),
        private_ip_id=dict(type="str"),
        hostname_label=dict(type="str"),
        nsg_ids=dict(type="list", elements="str"),
        metadata=dict(type="dict"),
        extended_metadata=dict(type="dict"),
        security_attributes=dict(type="dict"),
        launch_options=dict(
            type="dict",
            options=dict(
                boot_volume_type=dict(
                    type="str", choices=["ide", "iscsi", "paravirtualized", "scsi", "vfio"]
                ),
                firmware=dict(type="str", choices=["bios", "uefi_64"]),
                network_type=dict(
                    type="str", choices=["acceleratedpv", "e1000", "paravirtualized", "vfio"]
                ),
                remote_data_volume_type=dict(
                    type="str", choices=["ide", "iscsi", "paravirtualized", "scsi", "vfio"]
                ),
                is_pv_encryption_in_transit_enabled=dict(type="bool"),
                is_consistent_volume_naming_enabled=dict(type="bool"),
            ),
        ),
        instance_options=dict(
            type="dict",
            options=dict(
                are_legacy_imds_endpoints_disabled=dict(type="bool"),
            ),
        ),
        availability_config=dict(
            type="dict",
            options=dict(
                is_live_migration_preferred=dict(type="bool"),
                recovery_action=dict(
                    type="str", choices=["restore_instance", "stop_instance"]
                ),
            ),
        ),
        preemptible_instance_config=dict(
            type="dict",
            options=dict(
                preserve_boot_volume=dict(type="bool"),
            ),
        ),
        agent_config=dict(
            type="dict",
            options=dict(
                all_plugins_disabled=dict(type="bool"),
                management_disabled=dict(type="bool"),
                monitoring_disabled=dict(type="bool"),
                plugins_config=dict(
                    type="list",
                    elements="dict",
                    options=dict(
                        name=dict(type="str"),
                        desired_state=dict(type="str", choices=["enabled", "disabled"]),
                    ),
                ),
            ),
        ),
        platform_config=dict(
            type="dict",
            options=dict(
                type=dict(type="str"),
                is_secure_boot_enabled=dict(type="bool"),
                is_trusted_platform_module_enabled=dict(type="bool"),
                is_measured_boot_enabled=dict(type="bool"),
                is_memory_encryption_enabled=dict(type="bool"),
                is_symmetric_multi_threading_enabled=dict(type="bool"),
                numa_nodes_per_socket=dict(
                    type="str", choices=["nps0", "nps1", "nps2", "nps4", "nps6"]
                ),
                is_access_control_service_enabled=dict(type="bool"),
                are_virtual_instructions_enabled=dict(type="bool"),
                is_input_output_memory_management_unit_enabled=dict(type="bool"),
                percentage_of_cores_enabled=dict(type="int"),
            ),
        ),
        capacity_reservation_id=dict(type="str"),
        dedicated_vm_host_id=dict(type="str"),
        cluster_placement_group_id=dict(type="str"),
        compute_cluster_id=dict(type="str"),
        instance_configuration_id=dict(type="str"),
        ipxe_script=dict(type="str"),
        is_pv_encryption_in_transit_enabled=dict(type="bool"),
        is_ai_enterprise_enabled=dict(type="bool"),
        power_state=dict(type="str", choices=["running", "stopped"]),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[
            ("image_id", "boot_volume_id"),
            ("private_ip", "private_ip_id"),
        ],
    )

    OciInstanceModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
