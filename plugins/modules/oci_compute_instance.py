# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_compute_instance
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
  - This module launches instances from an image only. Launching from a boot
    volume, and updating C(create_vnic_details) or C(launch_options) fields
    after create, are not supported.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - oracle.oci.oci_auth_options
  - oracle.oci.oci_name_lookup_options
  - oracle.oci.oci_wait_options
  - oracle.oci.oci_tags_options
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
    type: str
  shape:
    description:
      - The shape of the instance, for example C(VM.Standard.E4.Flex).
      - Required when creating an instance.
      - Supports updates. OCI requires the instance to be stopped before
        changing its shape.
      - OCI stages shape changes made while the instance is stopped and only
        applies them the next time the instance starts. C(resource) reflects
        the previous value until then; rerunning this module with C(wait=true)
        after C(power_state=RUNNING) confirms the change applied.
    type: str
  shape_config:
    description:
      - Flexible shape configuration for shapes that support it.
      - Supports updates. OCI requires the instance to be stopped before
        changing shape configuration.
      - OCI stages shape_config changes made while the instance is stopped and
        only applies them the next time the instance starts. C(resource)
        reflects the previous values until then; rerunning this module with
        C(wait=true) after C(power_state=RUNNING) confirms the resize applied.
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
      - Required when creating an instance.
      - The module does not update this field after create.
    type: str
  boot_volume_size_in_gbs:
    description:
      - The size of the boot volume in GBs.
      - The module does not update this field after create.
    type: int
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
  launch_options:
    description:
      - Advanced launch options such as C(boot_volume_type) and
        C(network_type).
      - The module does not update this field after create.
    type: dict
  fault_domain:
    description:
      - The fault domain to launch the instance in.
      - The module does not update this field after create.
    type: str
  power_state:
    description:
      - The desired power state of the instance.
      - When set, the module issues an OCI power action to reach this state
        whenever it differs from the instance's current C(lifecycle_state).
      - Applied on create (after the instance reaches C(RUNNING)) and on every
        C(state=present) run.
    type: str
    choices: [RUNNING, STOPPED]
"""

EXAMPLES = r"""
- name: Launch an instance
  oracle.oci.oci_compute_instance:
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

- name: Reconcile a uniquely named instance by name
  oracle.oci.oci_compute_instance:
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

- name: Stop the instance
  oracle.oci.oci_compute_instance:
    instance_id: "{{ created_instance.resource.id }}"
    power_state: STOPPED

- name: Resize the stopped instance's flexible shape
  oracle.oci.oci_compute_instance:
    instance_id: "{{ created_instance.resource.id }}"
    shape_config:
      ocpus: 4
      memory_in_gbs: 64

- name: Start the instance again
  oracle.oci.oci_compute_instance:
    instance_id: "{{ created_instance.resource.id }}"
    power_state: RUNNING

- name: Terminate the instance
  oracle.oci.oci_compute_instance:
    state: absent
    instance_id: "{{ created_instance.resource.id }}"

- name: Terminate a uniquely named instance without providing instance_id
  oracle.oci.oci_compute_instance:
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
      description: The OCID of the image used to launch the instance.
      type: str
      returned: always
      sample: ocid1.image.oc1..example
    lifecycle_state:
      description: The current lifecycle state of the instance.
      type: str
      returned: always
      sample: RUNNING
    metadata:
      description: Custom metadata key/value pairs on the instance.
      type: dict
      returned: always
      sample: {"ssh_authorized_keys": "ssh-rsa AAAA..."}
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
    time_created:
      description: The date and time the instance was created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
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

from ansible_collections.oracle.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_RUNNING,
    LIFECYCLE_STOPPED,
    OCI_COMMON_ARGS,
    filter_none_values,
    import_oci_sdk,
)
from ansible_collections.oracle.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]

CREATE_REQUIRED_FIELDS = [
    "compartment_id",
    "availability_domain",
    "shape",
    "image_id",
    "subnet_id",
    "name",
]
WAIT_FOR_LAUNCH_STATES = [LIFECYCLE_RUNNING]
WAIT_FOR_SETTLED_STATES = [LIFECYCLE_RUNNING, LIFECYCLE_STOPPED]
POWER_STATE_ACTIONS = {
    LIFECYCLE_RUNNING: "START",
    LIFECYCLE_STOPPED: "STOP",
}


def build_create_vnic_details(params):
    details = filter_none_values(
        {
            "subnet_id": params.get("subnet_id"),
            "assign_public_ip": params.get("assign_public_ip"),
            "hostname_label": params.get("hostname_label"),
            "nsg_ids": params.get("nsg_ids"),
        }
    )
    if not details:
        return None
    return oci.core.models.CreateVnicDetails(**details)


def build_source_details(params):
    image_id = params.get("image_id")
    if not image_id:
        return None
    details = filter_none_values(
        {
            "image_id": image_id,
            "boot_volume_size_in_gbs": params.get("boot_volume_size_in_gbs"),
        }
    )
    return oci.core.models.InstanceSourceViaImageDetails(**details)


def build_shape_config(params, model_class):
    shape_config = params.get("shape_config")
    if not shape_config:
        return None
    return model_class(**shape_config)


def build_launch_options(params):
    launch_options = params.get("launch_options")
    if not launch_options:
        return None
    return oci.core.models.LaunchOptions(**launch_options)


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
            "launch_options": build_launch_options(params),
            "fault_domain": params.get("fault_domain"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.core.models.LaunchInstanceDetails(**details)


class OciComputeInstanceModule(OciResourceBase):
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
    update_field_specs = [
        {
            "param_name": "name",
            "resource_field": "display_name",
            "update_field": "display_name",
            "is_mutable": True,
        },
        {
            "param_name": "shape",
            "resource_field": "shape",
            "update_field": "shape",
            "is_mutable": True,
        },
        {
            "param_name": "shape_config",
            "resource_field": "shape_config",
            "update_field": "shape_config",
            "is_mutable": True,
            "compare": "shape_config_subset",
        },
        {
            "param_name": "metadata",
            "resource_field": "metadata",
            "update_field": "metadata",
            "is_mutable": True,
        },
        {
            "param_name": "power_state",
            "is_mutable": True,
            "strategy": "plan_power_state_strategy",
        },
        {
            "param_name": "availability_domain",
            "resource_field": "availability_domain",
            "is_mutable": False,
        },
        {
            "param_name": "compartment_id",
            "resource_field": "compartment_id",
            "is_mutable": False,
        },
        {
            "param_name": "image_id",
            "resource_field": "image_id",
            "is_mutable": False,
        },
        {
            "param_name": "fault_domain",
            "resource_field": "fault_domain",
            "is_mutable": False,
        },
        {
            "param_name": "launch_options",
            "resource_field": "launch_options",
            "is_mutable": False,
            "immutable_reason": "updating launch_options after create is not supported by this module",
        },
    ]

    def compare_update_field_values(self, current_value, desired_value, compare=None):
        """Extend the shared comparator with a shape_config-specific mode.

        OCI echoes back a fully populated ``shape_config`` (including fields
        this module never sets, such as ``networking_bandwidth_in_gbps``), so
        a plain equality check would always report drift. This compares only
        the keys the caller actually supplied.
        """
        if compare == "shape_config_subset":
            current_value = current_value or {}
            return any(
                current_value.get(key) != value
                for key, value in (desired_value or {}).items()
            )
        return super().compare_update_field_values(
            current_value, desired_value, compare=compare
        )

    def plan_power_state_strategy(self, resource, resource_dict, spec, desired_value):
        current_state = resource_dict.get("lifecycle_state")
        if desired_value == current_state:
            return []
        action = POWER_STATE_ACTIONS.get(desired_value)
        if action is None:
            raise ValueError(f"Unsupported power_state: {desired_value}")
        return [action]

    def _apply_power_action(self, instance_id, action):
        self.call_with_retry(
            self.client.instance_action,
            instance_id=instance_id,
            action=action,
        )
        target_state = LIFECYCLE_RUNNING if action == "START" else LIFECYCLE_STOPPED
        return self.wait_for_resource_id(instance_id, [target_state])

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_instance,
            instance_id=resource_id,
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
        desired_power_state = self.module.params.get("power_state")
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
        )
        return self.get_mutation_result(
            response.data,
            resource.id,
            WAIT_FOR_SETTLED_STATES,
        )

    def build_update_details(self, update_model_fields):
        update_model_fields = dict(update_model_fields)
        if "shape_config" in update_model_fields:
            update_model_fields["shape_config"] = build_shape_config(
                {"shape_config": update_model_fields["shape_config"]},
                oci.core.models.UpdateInstanceShapeConfigDetails,
            )
        return oci.core.models.UpdateInstanceDetails(**update_model_fields)

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.terminate_instance,
            instance_id=resource.id,
        )


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        instance_id=dict(type="str"),
        availability_domain=dict(type="str"),
        shape=dict(type="str"),
        shape_config=dict(
            type="dict",
            options=dict(
                ocpus=dict(type="float"),
                memory_in_gbs=dict(type="float"),
            ),
        ),
        image_id=dict(type="str"),
        boot_volume_size_in_gbs=dict(type="int"),
        subnet_id=dict(type="str"),
        assign_public_ip=dict(type="bool"),
        hostname_label=dict(type="str"),
        nsg_ids=dict(type="list", elements="str"),
        metadata=dict(type="dict"),
        launch_options=dict(type="dict"),
        fault_domain=dict(type="str"),
        power_state=dict(type="str", choices=["RUNNING", "STOPPED"]),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciComputeInstanceModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
