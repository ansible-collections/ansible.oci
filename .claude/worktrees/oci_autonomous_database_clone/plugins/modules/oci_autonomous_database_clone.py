# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_autonomous_database_clone
short_description: Manage a clone of an Autonomous Database in Oracle Cloud Infrastructure
description:
  - Create, rename, retag, and delete clones of serverless OCI Autonomous
    Databases.
  - Creates either a standard clone or a refreshable clone of a live source
    database.
version_added: "1.2.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_name_lookup_options
  - ansible.oci.oci_wait_options
  - ansible.oci.oci_tags_options
notes:
  - Only O(name), O(freeform_tags), and O(defined_tags) are reconciled on an
    existing clone. All other options apply only when the clone is created; use
    M(ansible.oci.oci_autonomous_database) to change them afterwards.
  - The module fails rather than manage a database that is not a clone, or
    that is a clone of a different source than O(source_id).
options:
  state:
    description:
      - The desired state of the clone.
      - V(present) creates the clone if it is missing and reconciles its name
        and tags.
      - V(absent) terminates the clone.
    type: str
    choices: [present, absent]
    default: present
  autonomous_database_id:
    description:
      - The OCID of the clone.
      - When provided, the module manages this exact clone.
      - Required to distinguish between multiple databases that share the same
        scoped O(name).
    type: str
  name:
    description:
      - The user-friendly display name of the clone.
      - Required when creating a clone.
      - When O(autonomous_database_id) is omitted, the module uses
        O(compartment_id) and O(name) to find an existing clone.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment to create the clone in.
      - Required when creating a clone.
      - Also scopes name-based lookups when O(autonomous_database_id) is
        omitted.
    type: str
  source_id:
    description:
      - The OCID of the source Autonomous Database to clone.
      - Required when creating a clone.
      - When provided for an existing clone, the module fails if the clone was
        created from a different source.
    type: str
  db_name:
    description:
      - The database name of the clone.
      - Required when creating a clone.
      - Must start with a letter, contain only letters and numbers, be at most
        30 characters, and be unique in the tenancy.
    type: str
  admin_password:
    description:
      - The password for the default C(ADMIN) user of the clone.
      - Required when creating a standard clone. Refreshable clones use the
        source database password.
    type: str
  clone_type:
    description:
      - The type of standard clone to create.
      - V(full) copies the database schema and data. V(metadata) copies only
        the schema.
      - Required when creating a standard clone. Optional for a refreshable
        clone.
    type: str
    choices: [full, metadata]
  refreshable:
    description:
      - Whether to create a refreshable clone, which can be refreshed with
        data from the source database.
    type: bool
    default: false
  refreshable_mode:
    description:
      - How a refreshable clone is refreshed.
      - Requires O(refreshable=true).
    type: str
    choices: [automatic, manual]
  auto_refresh_frequency_in_seconds:
    description:
      - How often an automatically refreshed clone is refreshed, between one
        hour and seven days.
      - Requires O(refreshable=true).
    type: int
  auto_refresh_point_lag_in_seconds:
    description:
      - How far, in seconds, the clone data lags the source database at each
        refresh, up to seven days. V(0) refreshes to the latest available
        point.
      - Requires O(refreshable=true).
    type: int
  time_of_auto_refresh_start:
    description:
      - The date and time, in RFC 3339 format, of the first automatic refresh.
      - Requires O(refreshable=true).
    type: str
  open_mode:
    description:
      - Whether a refreshable clone is opened read-only or read-write.
      - Requires O(refreshable=true).
    type: str
    choices: [read_only, read_write]
  compute_model:
    description:
      - The compute model of the clone.
    type: str
    choices: [ecpu, ocpu]
  compute_count:
    description:
      - The compute amount (ECPUs) available to the clone.
    type: float
  cpu_core_count:
    description:
      - The number of OCPU cores available to the clone.
    type: int
  data_storage_size_in_tbs:
    description:
      - The size, in terabytes, of the clone data volume.
      - Mutually exclusive with O(data_storage_size_in_gbs).
    type: int
  data_storage_size_in_gbs:
    description:
      - The size, in gigabytes, of the clone data volume.
      - Mutually exclusive with O(data_storage_size_in_tbs).
    type: int
  is_auto_scaling_enabled:
    description:
      - Whether compute auto scaling is enabled for the clone.
    type: bool
  is_auto_scaling_for_storage_enabled:
    description:
      - Whether storage auto scaling is enabled for the clone.
    type: bool
  license_model:
    description:
      - The Oracle license model that applies to the clone.
    type: str
    choices: [license_included, bring_your_own_license]
  subnet_id:
    description:
      - The OCID of the subnet for the clone private endpoint.
    type: str
  nsg_ids:
    description:
      - The OCIDs of the network security groups for the clone private
        endpoint.
    type: list
    elements: str
  private_endpoint_label:
    description:
      - The hostname prefix for the clone private endpoint.
    type: str
  whitelisted_ips:
    description:
      - The client IP addresses and CIDR blocks allowed to connect to the
        clone.
    type: list
    elements: str
"""

EXAMPLES = r"""
- name: Create a metadata-only clone of an Autonomous Database
  ansible.oci.oci_autonomous_database_clone:
    compartment_id: ocid1.compartment.oc1..example
    source_id: ocid1.autonomousdatabase.oc1..source
    name: example-adb-clone
    db_name: exampleclone
    admin_password: "{{ adb_admin_password }}"
    clone_type: metadata
    compute_model: ecpu
    compute_count: 2
    data_storage_size_in_tbs: 1
  register: adb_clone

- name: Create a manually refreshed, read-only clone
  ansible.oci.oci_autonomous_database_clone:
    compartment_id: ocid1.compartment.oc1..example
    source_id: ocid1.autonomousdatabase.oc1..source
    name: example-adb-refreshable
    db_name: examplerefresh
    refreshable: true
    refreshable_mode: manual
    open_mode: read_only
    compute_model: ecpu
    compute_count: 2

- name: Rename the clone and replace its tags
  ansible.oci.oci_autonomous_database_clone:
    autonomous_database_id: "{{ adb_clone.resource.id }}"
    name: example-adb-clone-renamed
    freeform_tags:
      environment: test

- name: Terminate the clone
  ansible.oci.oci_autonomous_database_clone:
    state: absent
    autonomous_database_id: "{{ adb_clone.resource.id }}"
"""

RETURN = r"""
resource:
  description: The cloned Autonomous Database.
  returned: when O(state=present)
  type: dict
  contains:
    id:
      description: The OCID of the clone.
      type: str
      returned: always
      sample: ocid1.autonomousdatabase.oc1..example
    name:
      description: The display name of the clone.
      type: str
      returned: always
      sample: example-adb-clone
    db_name:
      description: The database name of the clone.
      type: str
      returned: always
      sample: exampleclone
    compartment_id:
      description: The OCID of the compartment containing the clone.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    lifecycle_state:
      description: The current lifecycle state of the clone.
      type: str
      returned: always
      sample: AVAILABLE
    source_id:
      description: The OCID of the source database the clone was created from.
      type: str
      returned: always
      sample: ocid1.autonomousdatabase.oc1..source
    clone_type:
      description: The clone type.
      type: str
      returned: always
      sample: METADATA
    is_refreshable_clone:
      description: Whether the clone is a refreshable clone.
      type: bool
      returned: always
      sample: false
    refreshable_mode:
      description: How a refreshable clone is refreshed.
      type: str
      returned: always
      sample: null
    refreshable_status:
      description: Whether a refreshable clone is currently being refreshed.
      type: str
      returned: always
      sample: null
    open_mode:
      description: Whether the clone is open read-only or read-write.
      type: str
      returned: always
      sample: READ_WRITE
    time_of_last_refresh:
      description: The date and time a refreshable clone was last refreshed.
      type: str
      returned: always
      sample: null
    compute_model:
      description: The compute model of the clone.
      type: str
      returned: always
      sample: ECPU
    compute_count:
      description: The compute amount (ECPUs) available to the clone.
      type: float
      returned: always
      sample: 2.0
    data_storage_size_in_tbs:
      description: The size, in terabytes, of the clone data volume.
      type: int
      returned: always
      sample: 1
    freeform_tags:
      description: Free-form tags applied to the clone.
      type: dict
      returned: always
      sample: {"environment": "test"}
    defined_tags:
      description: Defined tags applied to the clone.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
    time_created:
      description: The date and time the clone was created, in RFC 3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
  sample:
    id: ocid1.autonomousdatabase.oc1..example
    name: example-adb-clone
    db_name: exampleclone
    compartment_id: ocid1.compartment.oc1..example
    lifecycle_state: AVAILABLE
    source_id: ocid1.autonomousdatabase.oc1..source
    clone_type: METADATA
    is_refreshable_clone: false
    open_mode: READ_WRITE
    compute_model: ECPU
    compute_count: 2.0
    data_storage_size_in_tbs: 1
    time_created: "2026-01-01T00:00:00.000Z"
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_AVAILABLE,
    LIFECYCLE_STOPPED,
    OCI_COMMON_ARGS,
    build_model,
    import_oci_sdk,
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
    "source_id",
    "db_name",
]
STANDARD_CLONE_REQUIRED_FIELDS = ("clone_type", "admin_password")
REFRESHABLE_ONLY_FIELDS = (
    "refreshable_mode",
    "auto_refresh_frequency_in_seconds",
    "auto_refresh_point_lag_in_seconds",
    "time_of_auto_refresh_start",
    "open_mode",
)

# Fields copied onto both clone create-details models. All map 1:1 from module
# params except ``display_name``, which the module exposes as ``name``.
COMMON_CREATE_DETAIL_KEYS = (
    "compartment_id",
    "source_id",
    "db_name",
    "display_name",
    "admin_password",
    "clone_type",
    "compute_model",
    "compute_count",
    "cpu_core_count",
    "data_storage_size_in_tbs",
    "data_storage_size_in_gbs",
    "is_auto_scaling_enabled",
    "is_auto_scaling_for_storage_enabled",
    "license_model",
    "subnet_id",
    "nsg_ids",
    "private_endpoint_label",
    "whitelisted_ips",
    "freeform_tags",
    "defined_tags",
)

# Module inputs use lowercase snake_case choices, while OCI expects upper-case
# constants. ``main`` upper-cases these top-level params once.
ENUM_KEYS = frozenset(
    {"clone_type", "compute_model", "license_model", "refreshable_mode", "open_mode"}
)
WAIT_FOR_CLONE_AVAILABLE = [LIFECYCLE_AVAILABLE]
# A rename or retag does not change the power state, so a stopped clone stays
# STOPPED after the update.
WAIT_FOR_CLONE_SETTLED = [LIFECYCLE_AVAILABLE, LIFECYCLE_STOPPED]


def build_create_clone_details(params):
    """Build the create-details model for a standard or refreshable clone.

    Args:
        params: The active Ansible module parameters.

    Returns:
        A ``CreateRefreshableAutonomousDatabaseCloneDetails`` model when
        ``refreshable`` is set, otherwise a
        ``CreateAutonomousDatabaseCloneDetails`` model.
    """
    source = dict(params, display_name=params.get("name"))
    if params.get("refreshable"):
        return build_model(
            source,
            oci.database.models.CreateRefreshableAutonomousDatabaseCloneDetails,
            COMMON_CREATE_DETAIL_KEYS + REFRESHABLE_ONLY_FIELDS,
        )
    return build_model(
        source,
        oci.database.models.CreateAutonomousDatabaseCloneDetails,
        COMMON_CREATE_DETAIL_KEYS,
    )


class OciAutonomousDatabaseCloneModule(OciResourceBase):
    """Concrete resource adapter for clones of serverless Autonomous Databases."""

    @property
    def client_class(self):
        return oci.database.DatabaseClient

    resource_id_param = "autonomous_database_id"
    list_resource_method = "list_autonomous_databases"
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "autonomous database clone"
    update_method_name = "update_autonomous_database"
    update_details_name = "update_autonomous_database_details"
    update_wait_states = WAIT_FOR_CLONE_SETTLED
    update_field_specs = (
        UpdateFieldSpec(
            param_name="name",
            is_mutable=True,
            resource_field="display_name",
            update_field="display_name",
        ),
    )

    def resolve_target_resource(self):
        """Return the target clone after confirming it is a clone of the source.

        The inherited lookup matches any Autonomous Database by ID or by
        compartment and name. It is extended so the module never adopts,
        updates, or terminates a database that is not a clone, or that was
        cloned from a different source than ``source_id``.

        Returns:
            The current ``AutonomousDatabase`` model, or ``None`` when no live
            database matches.

        Raises:
            AnsibleFailJson: Via ``fail_json`` when the matched database is not
                a clone or has a different source.
        """
        resource = super(OciAutonomousDatabaseCloneModule, self).resolve_target_resource()
        if resource is None:
            return None

        current_source_id = getattr(resource, "source_id", None)
        if current_source_id is None:
            self.module.fail_json(
                msg=(
                    f"Autonomous database {resource.id} is not a clone. Use "
                    "ansible.oci.oci_autonomous_database to manage it."
                )
            )
        source_id = self.module.params.get("source_id")
        if source_id is not None and current_source_id != source_id:
            self.module.fail_json(
                msg=(
                    f"Autonomous database {resource.id} is a clone of "
                    f"{current_source_id}, not {source_id}. Changing the source "
                    "of an existing clone is not supported."
                )
            )
        return resource

    def validate_create_request(self):
        """Validate a clone create request before calling the OCI API.

        Extends the shared required-field check with the fields each clone
        type needs: a standard clone requires ``clone_type`` and
        ``admin_password``, and refreshable-only options require
        ``refreshable``.

        Raises:
            AnsibleFailJson: Via ``fail_json`` when a required field is missing
                or a refreshable-only option is set for a standard clone.
        """
        super(OciAutonomousDatabaseCloneModule, self).validate_create_request()
        params = self.module.params
        if params.get("refreshable"):
            return

        missing = [field for field in STANDARD_CLONE_REQUIRED_FIELDS if params.get(field) is None]
        if missing:
            self.module.fail_json(
                msg=(
                    "Creating a standard autonomous database clone requires the "
                    f"following parameters: {', '.join(missing)}"
                )
            )
        refreshable_options = [field for field in REFRESHABLE_ONLY_FIELDS if params.get(field) is not None]
        if refreshable_options:
            self.module.fail_json(
                msg=(
                    "The following parameters require refreshable=true: "
                    f"{', '.join(refreshable_options)}"
                )
            )

    def get_resource_response(self, resource_id):
        """Return the raw OCI get-response wrapper for one clone.

        Args:
            resource_id: The OCID of the clone.

        Returns:
            The OCI SDK response whose ``data`` is the ``AutonomousDatabase``.
        """
        return self.call_with_retry(
            self.client.get_autonomous_database,
            autonomous_database_id=resource_id,
        )

    def create_resource(self):
        """Create the clone and return the resulting database model.

        Returns:
            The created ``AutonomousDatabase`` model, waited to ``AVAILABLE``
            when waiting is enabled.
        """
        response = self.call_with_retry(
            self.client.create_autonomous_database,
            create_autonomous_database_details=build_create_clone_details(
                self.module.params
            ),
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_CLONE_AVAILABLE,
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
        """Terminate the clone and wait for a terminal state.

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


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        autonomous_database_id=dict(type="str"),
        source_id=dict(type="str"),
        db_name=dict(type="str"),
        admin_password=dict(type="str", no_log=True),
        clone_type=dict(type="str", choices=["full", "metadata"]),
        refreshable=dict(type="bool", default=False),
        refreshable_mode=dict(type="str", choices=["automatic", "manual"]),
        auto_refresh_frequency_in_seconds=dict(type="int"),
        auto_refresh_point_lag_in_seconds=dict(type="int"),
        time_of_auto_refresh_start=dict(type="str"),
        open_mode=dict(type="str", choices=["read_only", "read_write"]),
        compute_model=dict(type="str", choices=["ecpu", "ocpu"]),
        compute_count=dict(type="float"),
        cpu_core_count=dict(type="int"),
        data_storage_size_in_tbs=dict(type="int"),
        data_storage_size_in_gbs=dict(type="int"),
        is_auto_scaling_enabled=dict(type="bool"),
        is_auto_scaling_for_storage_enabled=dict(type="bool"),
        license_model=dict(
            type="str",
            choices=["license_included", "bring_your_own_license"],
        ),
        subnet_id=dict(type="str"),
        nsg_ids=dict(type="list", elements="str"),
        private_endpoint_label=dict(type="str"),
        whitelisted_ips=dict(type="list", elements="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[["data_storage_size_in_tbs", "data_storage_size_in_gbs"]],
    )
    # Upper-case only the named top-level enum params so tag keys and values
    # that happen to match an enum name are never rewritten.
    for key in ENUM_KEYS:
        value = module.params.get(key)
        if isinstance(value, str):
            module.params[key] = value.upper()

    OciAutonomousDatabaseCloneModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
