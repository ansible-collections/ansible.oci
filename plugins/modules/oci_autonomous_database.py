# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_autonomous_database
short_description: Manage an Autonomous Database in Oracle Cloud Infrastructure
description:
  - Create, update, start, stop, and delete serverless OCI Autonomous Databases.
  - Uses the shared OCI helper layer for authentication, waiting, retry
    behavior, and result shaping.
  - Create requests must omit C(autonomous_database_id). After create, capture
    the returned ID and use it for later tasks.
version_added: "1.1.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_name_lookup_options
  - ansible.oci.oci_wait_options
  - ansible.oci.oci_tags_options
notes:
  - This module manages Autonomous Databases on shared (serverless)
    infrastructure only. Creating from a clone or backup, dedicated
    infrastructure, and Data Guard configurations are not supported.
options:
  state:
    description:
      - The desired state of the Autonomous Database.
      - C(present) creates the database if it is missing and reconciles
        supported mutable options; it does not change the running state.
      - C(running) and C(stopped) additionally ensure the database is started
        or stopped, creating and reconciling it first when necessary.
      - C(absent) terminates the database.
    type: str
    choices: [present, absent, running, stopped]
    default: present
  autonomous_database_id:
    description:
      - The OCID of the Autonomous Database.
      - When provided, the module manages this exact database.
      - Required to distinguish between multiple databases that share the same
        scoped C(name).
    type: str
  name:
    description:
      - The user-friendly display name of the Autonomous Database.
      - Required when creating a database.
      - When C(autonomous_database_id) is omitted, the module uses
        C(compartment_id + name) to find an existing database.
      - If exactly one database matches, the request manages it; if more than
        one matches, the task fails and the caller must supply
        C(autonomous_database_id).
      - The display name is not required to be unique and can be changed after
        create.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the Autonomous Database.
      - Required when creating a database.
      - The module does not move an existing database to another compartment.
      - Also scopes name-based lookups when C(autonomous_database_id) is omitted.
    type: str
  db_name:
    description:
      - The database name.
      - Required when creating a database.
      - The module does not rename an existing database.
    type: str
  admin_password:
    description:
      - The password for the default C(ADMIN) user.
      - Required when creating a database.
      - The OCI API never returns this value, so the module sets it only at
        create time and does not reconcile or rotate it on later runs.
    type: str
  db_workload:
    description:
      - The Autonomous Database workload type.
      - Set only at create time; the module does not change it afterwards.
    type: str
    choices: [oltp, dw, ajd, apex]
  compute_model:
    description:
      - The compute model of the Autonomous Database.
      - Set only at create time; the module does not change it afterwards.
    type: str
    choices: [ecpu, ocpu]
  compute_count:
    description:
      - The compute amount (ECPUs) available to the database.
      - Use with the C(ECPU) compute model.
    type: float
  cpu_core_count:
    description:
      - The number of OCPU cores available to the database.
      - Use with the C(OCPU) compute model.
    type: int
  data_storage_size_in_tbs:
    description:
      - The size, in terabytes, of the data volume.
    type: int
  data_storage_size_in_gbs:
    description:
      - The size, in gigabytes, of the data volume.
    type: int
  is_auto_scaling_enabled:
    description:
      - Whether compute auto scaling is enabled for the database.
    type: bool
  is_auto_scaling_for_storage_enabled:
    description:
      - Whether storage auto scaling is enabled for the database.
    type: bool
  is_free_tier:
    description:
      - Whether the database is provisioned as an Always Free resource.
    type: bool
  is_mtls_connection_required:
    description:
      - Whether mutual TLS (mTLS) is required for connections to the database.
    type: bool
  license_model:
    description:
      - The Oracle license model that applies to the database.
    type: str
    choices: [license_included, bring_your_own_license]
  db_version:
    description:
      - The Oracle Database version for the Autonomous Database.
    type: str
  subnet_id:
    description:
      - The OCID of the subnet the database is attached to for a private
        endpoint.
      - Set only at create time; the module does not change it afterwards.
    type: str
  nsg_ids:
    description:
      - The OCIDs of the network security groups the private endpoint belongs
        to.
    type: list
    elements: str
  private_endpoint_label:
    description:
      - The hostname prefix for the private endpoint.
      - Set only at create time; the module does not change it afterwards.
    type: str
  whitelisted_ips:
    description:
      - The client IP access control list (ACL).
      - Addresses and CIDR blocks that are allowed to connect to the database.
    type: list
    elements: str
"""

EXAMPLES = r"""
- name: Create a serverless Autonomous Database
  ansible.oci.oci_autonomous_database:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: example-adb
    db_name: exampleadb
    admin_password: "{{ adb_admin_password }}"
    db_workload: oltp
    compute_model: ecpu
    compute_count: 2
    data_storage_size_in_tbs: 1
    is_auto_scaling_enabled: true
  register: created_adb

- name: Scale the Autonomous Database up
  ansible.oci.oci_autonomous_database:
    state: present
    autonomous_database_id: "{{ created_adb.resource.id }}"
    compute_count: 4

- name: Ensure the Autonomous Database is stopped
  ansible.oci.oci_autonomous_database:
    state: stopped
    autonomous_database_id: "{{ created_adb.resource.id }}"

- name: Ensure the Autonomous Database is running
  ansible.oci.oci_autonomous_database:
    state: running
    autonomous_database_id: "{{ created_adb.resource.id }}"

- name: Terminate the Autonomous Database
  ansible.oci.oci_autonomous_database:
    state: absent
    autonomous_database_id: "{{ created_adb.resource.id }}"
"""

RETURN = r"""
resource:
  description: The Autonomous Database resource.
  returned: when state != absent
  type: dict
  contains:
    id:
      description: The OCID of the Autonomous Database.
      type: str
      returned: always
      sample: ocid1.autonomousdatabase.oc1..example
    name:
      description: The display name of the Autonomous Database.
      type: str
      returned: always
      sample: example-adb
    db_name:
      description: The database name.
      type: str
      returned: always
      sample: exampleadb
    compartment_id:
      description: The OCID of the compartment containing the database.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    lifecycle_state:
      description: The current lifecycle state of the database.
      type: str
      returned: always
      sample: AVAILABLE
    db_workload:
      description: The workload type of the database.
      type: str
      returned: always
      sample: OLTP
    compute_model:
      description: The compute model of the database.
      type: str
      returned: always
      sample: ECPU
    compute_count:
      description: The compute amount (ECPUs) available to the database.
      type: float
      returned: always
      sample: 2.0
    cpu_core_count:
      description: The number of OCPU cores available to the database.
      type: int
      returned: always
      sample: null
    data_storage_size_in_tbs:
      description: The size, in terabytes, of the data volume.
      type: int
      returned: always
      sample: 1
    is_auto_scaling_enabled:
      description: Whether compute auto scaling is enabled.
      type: bool
      returned: always
      sample: true
    is_free_tier:
      description: Whether the database is an Always Free resource.
      type: bool
      returned: always
      sample: false
    is_mtls_connection_required:
      description: Whether mutual TLS is required for connections.
      type: bool
      returned: always
      sample: true
    license_model:
      description: The Oracle license model that applies to the database.
      type: str
      returned: always
      sample: LICENSE_INCLUDED
    db_version:
      description: The Oracle Database version.
      type: str
      returned: always
      sample: "19c"
    subnet_id:
      description: The OCID of the subnet for a private endpoint.
      type: str
      returned: always
      sample: null
    nsg_ids:
      description: The network security groups the private endpoint belongs to.
      type: list
      elements: str
      returned: always
      sample: []
    private_endpoint_ip:
      description: The private endpoint IP address of the database.
      type: str
      returned: always
      sample: null
    whitelisted_ips:
      description: The client IP access control list.
      type: list
      elements: str
      returned: always
      sample: []
    connection_strings:
      description: The connection strings used to connect to the database.
      type: dict
      returned: always
      sample: {}
    freeform_tags:
      description: Free-form tags applied to the database.
      type: dict
      returned: always
      sample: {"environment": "production"}
    defined_tags:
      description: Defined tags applied to the database.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
    time_created:
      description: The date and time the database was created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
  sample:
    id: ocid1.autonomousdatabase.oc1..example
    name: example-adb
    db_name: exampleadb
    compartment_id: ocid1.compartment.oc1..example
    lifecycle_state: AVAILABLE
    db_workload: OLTP
    compute_model: ECPU
    compute_count: 2.0
    data_storage_size_in_tbs: 1
    is_auto_scaling_enabled: true
    license_model: LICENSE_INCLUDED
    time_created: "2026-01-01T00:00:00.000Z"
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_AVAILABLE,
    LIFECYCLE_STOPPED,
    OCI_COMMON_ARGS,
    build_model,
    import_oci_sdk,
    normalize_enum_values,
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
    "name",
    "db_name",
    "admin_password",
]
COMPUTE_FIELDS = ("compute_count", "cpu_core_count")
STORAGE_FIELDS = ("data_storage_size_in_tbs", "data_storage_size_in_gbs")

# Fields copied onto CreateAutonomousDatabaseDetails. All map 1:1 from module
# params except ``display_name``, which the module exposes as ``name``.
CREATE_DETAIL_KEYS = (
    "compartment_id",
    "db_name",
    "display_name",
    "admin_password",
    "db_workload",
    "compute_model",
    "compute_count",
    "cpu_core_count",
    "data_storage_size_in_tbs",
    "data_storage_size_in_gbs",
    "is_auto_scaling_enabled",
    "is_auto_scaling_for_storage_enabled",
    "is_free_tier",
    "is_mtls_connection_required",
    "license_model",
    "db_version",
    "subnet_id",
    "nsg_ids",
    "private_endpoint_label",
    "whitelisted_ips",
    "freeform_tags",
    "defined_tags",
)

# Module inputs use lowercase snake_case choices (Ansible convention), while
# OCI's wire format and returned resources use upper-case constants (for example
# "oltp" -> "OLTP", "license_included" -> "LICENSE_INCLUDED"). ``main`` normalizes
# module params through normalize_enum_values once, so the create builder and the
# update drift checks all see the same upper-case vocabulary as the serialized OCI
# resource.
ENUM_KEYS = frozenset({"db_workload", "compute_model", "license_model"})
WAIT_FOR_ADB_AVAILABLE = [LIFECYCLE_AVAILABLE]
WAIT_FOR_ADB_STOPPED = [LIFECYCLE_STOPPED]
# A field update does not itself change the database's power state, so after
# updating a database that was already STOPPED, OCI applies the change and
# leaves it STOPPED rather than transitioning it to AVAILABLE. Waiting on
# either settled state (instead of only AVAILABLE) lets the update complete
# normally for a stopped database too; see oci_instance.py's
# WAIT_FOR_SETTLED_STATES for the same pattern.
WAIT_FOR_ADB_SETTLED = [LIFECYCLE_AVAILABLE, LIFECYCLE_STOPPED]


def build_create_autonomous_database_details(params):
    """Build the serverless Autonomous Database create-details model.

    Args:
        params: The active Ansible module parameters.

    Returns:
        A populated ``CreateAutonomousDatabaseDetails`` model, which implies the
        serverless (``source=NONE``) create path.
    """
    # The SDK model's display field is ``display_name``; the module exposes it as
    # ``name``, so seed that key before selecting fields for the model.
    source = dict(params, display_name=params.get("name"))
    return build_model(
        source,
        oci.database.models.CreateAutonomousDatabaseDetails,
        CREATE_DETAIL_KEYS,
    )


class OciAutonomousDatabaseModule(OciResourceBase):
    """Concrete resource adapter for serverless OCI Autonomous Databases."""

    @property
    def client_class(self):
        return oci.database.DatabaseClient

    resource_id_param = "autonomous_database_id"
    list_resource_method = "list_autonomous_databases"
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "autonomous database"
    update_method_name = "update_autonomous_database"
    update_details_name = "update_autonomous_database_details"
    update_wait_states = WAIT_FOR_ADB_SETTLED
    update_field_specs = (
        UpdateFieldSpec(
            param_name="name",
            is_mutable=True,
            resource_field="display_name",
            update_field="display_name",
        ),
        UpdateFieldSpec(param_name="compute_count", is_mutable=True),
        UpdateFieldSpec(param_name="cpu_core_count", is_mutable=True),
        UpdateFieldSpec(param_name="data_storage_size_in_tbs", is_mutable=True),
        UpdateFieldSpec(param_name="data_storage_size_in_gbs", is_mutable=True),
        UpdateFieldSpec(param_name="is_auto_scaling_enabled", is_mutable=True),
        UpdateFieldSpec(
            param_name="is_auto_scaling_for_storage_enabled", is_mutable=True
        ),
        UpdateFieldSpec(param_name="is_free_tier", is_mutable=True),
        UpdateFieldSpec(param_name="is_mtls_connection_required", is_mutable=True),
        UpdateFieldSpec(param_name="license_model", is_mutable=True),
        UpdateFieldSpec(param_name="db_version", is_mutable=True),
        UpdateFieldSpec(
            param_name="whitelisted_ips",
            is_mutable=True,
            compare="sorted_list",
        ),
        UpdateFieldSpec(
            param_name="nsg_ids",
            is_mutable=True,
            compare="sorted_list",
        ),
        UpdateFieldSpec(
            param_name="db_name",
            is_mutable=False,
            immutable_reason="OCI does not support renaming the database",
        ),
        UpdateFieldSpec(param_name="compartment_id", is_mutable=False),
        UpdateFieldSpec(param_name="db_workload", is_mutable=False),
        UpdateFieldSpec(param_name="compute_model", is_mutable=False),
        UpdateFieldSpec(param_name="subnet_id", is_mutable=False),
        UpdateFieldSpec(param_name="private_endpoint_label", is_mutable=False),
    )

    def validate_create_request(self):
        """Validate a serverless create request before calling the OCI API.

        Extends the shared required-field check with the serverless sizing
        requirement that at least one compute field and one storage field are
        supplied, because the OCI API rejects a serverless create without them.

        Raises:
            AnsibleFailJson: Via ``fail_json`` when a required field or a
                compute/storage selection is missing.
        """
        super(OciAutonomousDatabaseModule, self).validate_create_request()
        if not any(self.module.params.get(field) is not None for field in COMPUTE_FIELDS):
            self.module.fail_json(
                msg=(
                    "Creating an autonomous database requires one of the "
                    f"following parameters: {', '.join(COMPUTE_FIELDS)}"
                )
            )
        if not any(self.module.params.get(field) is not None for field in STORAGE_FIELDS):
            self.module.fail_json(
                msg=(
                    "Creating an autonomous database requires one of the "
                    f"following parameters: {', '.join(STORAGE_FIELDS)}"
                )
            )

    def get_resource_response(self, resource_id):
        """Return the raw OCI get-response wrapper for one database.

        Args:
            resource_id: The OCID of the Autonomous Database.

        Returns:
            The OCI SDK response whose ``data`` is the ``AutonomousDatabase``.
        """
        return self.call_with_retry(
            self.client.get_autonomous_database,
            autonomous_database_id=resource_id,
        )

    def create_resource(self):
        """Create the serverless Autonomous Database and return the model.

        Returns:
            The created ``AutonomousDatabase`` model, waited to ``AVAILABLE``
            when waiting is enabled.
        """
        create_details = build_create_autonomous_database_details(self.module.params)
        response = self.call_with_retry(
            self.client.create_autonomous_database,
            create_autonomous_database_details=create_details,
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_ADB_AVAILABLE,
        )

    def build_update_details(self, update_model_fields):
        """Build the OCI update-details model from planned field changes.

        Args:
            update_model_fields: The fields the shared planner marked as changed.

        Returns:
            A populated ``UpdateAutonomousDatabaseDetails`` model.
        """
        return oci.database.models.UpdateAutonomousDatabaseDetails(**update_model_fields)

    def delete_resource(self, resource):
        """Terminate the Autonomous Database and wait for a terminal state.

        Args:
            resource: The current ``AutonomousDatabase`` model to terminate.

        Returns:
            The terminated resource model, or the raw response when waiting is
            disabled.
        """
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_autonomous_database,
            autonomous_database_id=resource.id,
        )

    def desired_power_state(self):
        """Return the lifecycle state the requested C(state) implies.

        Returns:
            ``AVAILABLE`` for C(running), ``STOPPED`` for C(stopped), or ``None``
            for C(present), which leaves the running state unmanaged.
        """
        state = self.module.params.get("state", "present")
        if state == "running":
            return LIFECYCLE_AVAILABLE
        if state == "stopped":
            return LIFECYCLE_STOPPED
        return None

    def power_change_needed(self, resource):
        """Return ``True`` when a start/stop transition is required.

        Args:
            resource: The current ``AutonomousDatabase`` model.

        Returns:
            ``True`` only when the requested C(state) maps to a power state and
            the database currently sits in the opposite settled state, so a
            database that is mid-transition or in another state is left alone.
        """
        desired = self.desired_power_state()
        if desired is None:
            return False
        current = getattr(resource, "lifecycle_state", None)
        if desired == LIFECYCLE_AVAILABLE:
            return current == LIFECYCLE_STOPPED
        return current == LIFECYCLE_AVAILABLE

    def apply_power_state(self, resource):
        """Start or stop the database to match the requested C(state).

        Args:
            resource: The current ``AutonomousDatabase`` model to transition.

        Returns:
            The refreshed resource model after the transition, waited to the
            target state when waiting is enabled.
        """
        if self.desired_power_state() == LIFECYCLE_AVAILABLE:
            response = self.call_with_retry(
                self.client.start_autonomous_database,
                autonomous_database_id=resource.id,
            )
            target_states = WAIT_FOR_ADB_AVAILABLE
        else:
            response = self.call_with_retry(
                self.client.stop_autonomous_database,
                autonomous_database_id=resource.id,
            )
            target_states = WAIT_FOR_ADB_STOPPED
        return self.get_mutation_result(response.data, resource.id, target_states)

    def execute_resource_module(self):
        """Run the present/absent/running/stopped lifecycle for the module.

        Overrides the base present/absent flow because the inherited
        implementation cannot express the C(running) and C(stopped) power
        states this resource supports. Resource resolution, create, update, and
        delete still reuse the inherited hooks; only the extra power-state
        reconciliation is added here.
        """
        state = self.module.params.get("state", "present")

        if state == "absent":
            self._execute_absent()
            return

        # state in (present, running, stopped)
        resource = self.resolve_target_resource()
        if resource is None:
            self._execute_create()
            return

        self._execute_update(resource)

    def _execute_absent(self):
        self.validate_delete_request()
        resource = self.resolve_target_resource()
        if resource is None:
            self.module.exit_json(changed=False)
        if self.check_mode:
            self.module.exit_json(changed=True)
        self.delete_resource(resource)
        self.module.exit_json(changed=True)

    def _execute_create(self):
        if self.resource_id:
            self.fail_missing_update_target()
        self.validate_create_request()
        if self.check_mode:
            self.module.exit_json(changed=True)
        resource = self.create_resource()
        # With wait=False, create_resource() returns the raw create response
        # without confirming the database reached AVAILABLE, so it is
        # typically still PROVISIONING here. power_change_needed() would
        # then see neither settled state and skip the transition even when
        # one was requested. Only chase the power state when waiting is
        # enabled, matching oci_instance.py's launch-then-stop handling; a
        # wait=False run that requests running/stopped at create time
        # settles into the OCI default (AVAILABLE) and needs a follow-up
        # run to reach the requested power state.
        if self.module.params.get("wait", True) and self.power_change_needed(
            resource
        ):
            resource = self.apply_power_state(resource)
        self.module.exit_json(
            changed=True,
            resource=self.serialize_result_resource(resource),
        )

    def _execute_update(self, resource):
        update_needed = self.needs_update(resource)
        power_needed = self.power_change_needed(resource)
        if self.check_mode:
            self.module.exit_json(changed=update_needed or power_needed)

        changed = False
        if update_needed:
            resource = self.update_resource(resource)
            changed = True
        if self.power_change_needed(resource):
            resource = self.apply_power_state(resource)
            changed = True

        self.module.exit_json(
            changed=changed,
            resource=self.serialize_result_resource(resource),
        )


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(
            type="str",
            choices=["present", "absent", "running", "stopped"],
            default="present",
        ),
        autonomous_database_id=dict(type="str"),
        db_name=dict(type="str"),
        admin_password=dict(type="str", no_log=True),
        db_workload=dict(type="str", choices=["oltp", "dw", "ajd", "apex"]),
        compute_model=dict(type="str", choices=["ecpu", "ocpu"]),
        compute_count=dict(type="float"),
        cpu_core_count=dict(type="int"),
        data_storage_size_in_tbs=dict(type="int"),
        data_storage_size_in_gbs=dict(type="int"),
        is_auto_scaling_enabled=dict(type="bool"),
        is_auto_scaling_for_storage_enabled=dict(type="bool"),
        is_free_tier=dict(type="bool"),
        is_mtls_connection_required=dict(type="bool"),
        license_model=dict(
            type="str",
            choices=["license_included", "bring_your_own_license"],
        ),
        db_version=dict(type="str"),
        subnet_id=dict(type="str"),
        nsg_ids=dict(type="list", elements="str"),
        private_endpoint_label=dict(type="str"),
        whitelisted_ips=dict(type="list", elements="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )
    # Convert the lowercase snake_case enum choices to the upper-case constants
    # OCI expects, in one pass, so the create builder and drift comparisons
    # downstream all work against the SDK vocabulary. See ENUM_KEYS.
    module.params = normalize_enum_values(module.params, ENUM_KEYS)

    OciAutonomousDatabaseModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
