# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_health_check
short_description: Manage an OCI Health Checks monitor
description:
  - Create, update, or delete an HTTP or ping monitor.
version_added: "1.3.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_name_lookup_options
  - ansible.oci.oci_tags_options
options:
  state:
    description: The desired state of the monitor.
    type: str
    choices: [present, absent]
    default: present
  monitor_type:
    description: The type of monitor to manage.
    type: str
    choices: [http, ping]
    required: true
  monitor_id:
    description: The OCID of the monitor.
    type: str
  name:
    description:
      - The monitor name that OCI stores as C(display_name).
      - This option is required to create a monitor.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment.
      - Required for creation and name lookup.
      - This module cannot move an existing monitor to another compartment.
    type: str
  targets:
    description: Target host names or IP addresses. This option is required to create a monitor. List order is not significant.
    type: list
    elements: str
  vantage_point_names:
    description:
      - Names of vantage points that run probes.
      - OCI selects vantage points when this option is omitted during creation.
      - List order is not significant.
    type: list
    elements: str
  port:
    description:
      - The target port for the monitor.
      - When omitted during creation, OCI uses the default port for the protocol.
    type: int
  timeout_in_seconds:
    description: The probe timeout in seconds. The value cannot exceed the interval.
    type: int
    choices: [10, 20, 30, 60]
  protocol:
    description: The protocol. HTTP monitors accept C(http) or C(https). Ping monitors accept C(icmp) or C(tcp). This option is required to create a monitor.
    type: str
    choices: [http, https, icmp, tcp]
  method:
    description: The HTTP request method. This option applies only to HTTP monitors.
    type: str
    choices: [get, head]
  path:
    description: The request path for an HTTP monitor, including query parameters.
    type: str
  headers:
    description:
      - HTTP request headers for HTTP monitors.
      - OCI does not support the C(Authorization) header.
    type: dict
  interval_in_seconds:
    description: The time between probes in seconds. This option is required to create a monitor.
    type: int
    choices: [10, 30, 60]
  is_enabled:
    description: Whether the monitor is enabled.
    type: bool
"""

EXAMPLES = r"""
- name: Create an HTTP monitor
  ansible.oci.oci_health_check:
    monitor_type: http
    compartment_id: ocid1.compartment.oc1..example
    name: example-http-monitor
    targets: [www.example.com]
    protocol: https
    interval_in_seconds: 30
    timeout_in_seconds: 10
  register: created_monitor

- name: Update a ping monitor
  ansible.oci.oci_health_check:
    monitor_type: ping
    monitor_id: ocid1.pingmonitor.oc1..example
    targets: [www.example.com]
    protocol: icmp
    interval_in_seconds: 30

- name: Delete a monitor
  ansible.oci.oci_health_check:
    monitor_type: http
    state: absent
    monitor_id: ocid1.httpmonitor.oc1..example
"""

RETURN = r"""
resource:
  description: The monitor resource. The monitor name is returned as C(name).
  returned: When present and check mode does not predict a change.
  type: dict
  contains:
    id:
      description: The monitor OCID.
      type: str
      sample: ocid1.httpmonitor.oc1..example
    name:
      description: The monitor display name.
      type: str
      sample: example-http-monitor
    compartment_id:
      description: The OCID of the monitor compartment.
      type: str
      sample: ocid1.compartment.oc1..example
    targets:
      description: The probe targets.
      type: list
      elements: str
    protocol:
      description: The protocol used by the monitor.
      type: str
      sample: HTTPS
    interval_in_seconds:
      description: The interval between probes.
      type: int
      sample: 30
    timeout_in_seconds:
      description: The time allowed for a probe to complete.
      type: int
      sample: 10
    port:
      description: The target port for the monitor.
      type: int
      sample: 443
    method:
      description: The HTTP request method.
      type: str
      sample: GET
    path:
      description: The HTTP request path.
      type: str
      sample: /
    headers:
      description: HTTP request headers.
      type: dict
    vantage_point_names:
      description: The vantage points that run probes.
      type: list
      elements: str
    is_enabled:
      description: Whether the monitor is enabled.
      type: bool
      sample: true
    home_region:
      description: The home region of the monitor.
      type: str
    results_url:
      description: The URL for monitor probe results.
      type: str
    time_created:
      description: The time when OCI created the monitor.
      type: str
    freeform_tags:
      description: Free-form tags on the monitor.
      type: dict
    defined_tags:
      description: Defined tags on the monitor.
      type: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    OCI_NAME_LOOKUP_ARGS,
    OCI_TAG_ARGS,
    build_model,
    import_oci_sdk,
    normalize_choice_parameters,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_healthchecks import MONITOR_TYPES
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

oci = import_oci_sdk()[0]
PROTOCOL_VALUES = {"http": "HTTP", "https": "HTTPS", "icmp": "ICMP", "tcp": "TCP"}
CHOICE_VALUE_MAPS = {("protocol",): PROTOCOL_VALUES, ("method",): {"get": "GET", "head": "HEAD"}}
HTTP_FIELDS = ("method", "path", "headers")
MONITOR_FIELDS = (
    "targets", "vantage_point_names", "port", "timeout_in_seconds",
    "protocol", "display_name", "interval_in_seconds", "is_enabled",
    "freeform_tags", "defined_tags",
)


def build_monitor_details(params, monitor_type, creating=False):
    """Build the SDK request model for a monitor operation.

    Args:
        params: Module parameters.
        monitor_type: Either ``http`` or ``ping``.
        creating: Whether to include create-only compartment data.

    Returns:
        The matching OCI create or update model.
    """
    dispatch = MONITOR_TYPES[monitor_type]
    if creating:
        fields = list(MONITOR_FIELDS)
        if monitor_type == "http":
            fields.extend(HTTP_FIELDS)
        payload = {field: params.get(field) for field in fields}
        payload["display_name"] = params.get("name")
        payload["compartment_id"] = params.get("compartment_id")
        model_name = dispatch["create_model"]
    else:
        payload = dict(params)
        model_name = dispatch["update_model"]
    return build_model(payload, getattr(oci.healthchecks.models, model_name))


def validate_monitor_params(module, monitor_type, current=None):
    """Validate monitor type rules and effective timeout settings.

    Args:
        module: Active Ansible module.
        monitor_type: Either ``http`` or ``ping``.
        current: Existing monitor model for partial updates.

    Raises:
        Module failure when a parameter conflicts with the monitor type.
    """
    params = module.params
    if monitor_type == "ping":
        supplied = [field for field in HTTP_FIELDS if params.get(field) is not None]
        if supplied:
            module.fail_json(msg="HTTP-only options are not valid for ping monitors: %s" % ", ".join(supplied))
    protocol = params.get("protocol") or getattr(current, "protocol", None)
    allowed = {"http": ("http", "https"), "ping": ("icmp", "tcp")}[monitor_type]
    if protocol and protocol.lower() not in allowed:
        module.fail_json(msg="Protocol %s is not valid for %s monitors" % (protocol, monitor_type))
    interval = params.get("interval_in_seconds")
    timeout = params.get("timeout_in_seconds")
    interval = interval if interval is not None else getattr(current, "interval_in_seconds", None)
    timeout = timeout if timeout is not None else getattr(current, "timeout_in_seconds", None)
    if interval is not None and timeout is not None and timeout > interval:
        module.fail_json(msg="timeout_in_seconds must be less than or equal to interval_in_seconds")


CREATE_REQUIRED_FIELDS = ("compartment_id", "name", "targets", "protocol", "interval_in_seconds")


class OciHealthCheckModule(OciResourceBase):
    """Manage one OCI HTTP or ping monitor."""

    @property
    def client_class(self):
        """Return the OCI Health Checks client class."""
        return oci.healthchecks.HealthChecksClient

    @property
    def monitor_type(self):
        """Return the requested monitor type."""
        return self.module.params["monitor_type"]

    @property
    def dispatch(self):
        """Return SDK operation names for the requested monitor type."""
        return MONITOR_TYPES[self.monitor_type]

    @property
    def list_resource_method(self):
        """Return the monitor list operation name."""
        return self.dispatch["list"]

    resource_id_param = "monitor_id"
    name_lookup_param = "name"
    name_response_field = "display_name"
    list_filter_params = ()
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "monitor"
    update_wait_states = ()

    @property
    def update_field_specs(self):
        """Return mutable and immutable fields for the selected monitor type."""
        fields = [field for field in MONITOR_FIELDS if field not in ("display_name", "freeform_tags", "defined_tags")]
        if self.monitor_type == "http":
            fields.extend(HTTP_FIELDS)
        specs = [
            UpdateFieldSpec(
                param_name=field,
                resource_field=field,
                is_mutable=True,
                compare="sorted_list" if field in ("targets", "vantage_point_names") else None,
            )
            for field in fields
        ]
        specs.extend(
            (
                UpdateFieldSpec(param_name="name", resource_field="display_name", is_mutable=True),
                UpdateFieldSpec(param_name="compartment_id", is_mutable=False),
            )
        )
        return tuple(specs)

    def validate_create_request(self):
        """Validate required create fields and monitor-specific options."""
        super(OciHealthCheckModule, self).validate_create_request()
        validate_monitor_params(self.module, self.monitor_type)

    def get_resource_response(self, resource_id):
        """Get a monitor by ID through its type-specific operation.

        Args:
            resource_id: The monitor OCID.

        Returns:
            The OCI response wrapper.
        """
        return self.call_with_retry(
            getattr(self.client, self.dispatch["get"]),
            monitor_id=resource_id,
        )

    def hydrate_named_resource(self, resource):
        """Fetch full monitor fields because list operations return summaries.

        Args:
            resource: The summary matched by name.

        Returns:
            The full monitor model, or the summary when the get call returns no resource.
        """
        return self.get_resource_by_id(resource.id) or resource

    def needs_update(self, resource):
        """Validate effective values, then compare the requested fields.

        Args:
            resource: The current full monitor model.

        Returns:
            True when an update is needed.
        """
        validate_monitor_params(self.module, self.monitor_type, resource)
        return super(OciHealthCheckModule, self).needs_update(resource)

    def create_resource(self):
        """Create a monitor with its matching SDK model and API operation.

        Returns:
            The created monitor model.
        """
        details = build_monitor_details(self.module.params, self.monitor_type, creating=True)
        operation_name = self.dispatch["create"]
        operation = getattr(self.client, operation_name)
        return self.call_with_retry(
            operation,
            **{operation_name + "_details": details},
        ).data

    def update_resource(self, resource):
        """Update synchronously because Health Checks has no lifecycle waiter.

        Args:
            resource: The current monitor model.

        Returns:
            The updated monitor model.
        """
        plan = self.get_update_plan(resource)
        if not plan["update_model_fields"]:
            return resource
        fields = dict(plan["update_model_fields"])
        details = build_monitor_details(fields, self.monitor_type)
        operation_name = self.dispatch["update"]
        operation = getattr(self.client, operation_name)
        return self.call_with_retry(
            operation,
            monitor_id=resource.id,
            **{operation_name + "_details": details},
        ).data

    def delete_resource(self, resource):
        """Delete a monitor with its type-specific SDK operation.

        Args:
            resource: The monitor model to delete.
        """
        self.call_delete_fn(
            resource,
            getattr(self.client, self.dispatch["delete"]),
            monitor_id=resource.id,
        )


def main():
    """Run the OCI Health Checks monitor module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_NAME_LOOKUP_ARGS,
        **OCI_TAG_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        monitor_type=dict(type="str", choices=list(MONITOR_TYPES), required=True),
        monitor_id=dict(type="str"),
        targets=dict(type="list", elements="str"),
        vantage_point_names=dict(type="list", elements="str"),
        port=dict(type="int"),
        timeout_in_seconds=dict(type="int", choices=[10, 20, 30, 60]),
        protocol=dict(type="str", choices=list(PROTOCOL_VALUES)),
        method=dict(type="str", choices=["get", "head"]),
        path=dict(type="str"),
        headers=dict(type="dict"),
        interval_in_seconds=dict(type="int", choices=[10, 30, 60]),
        is_enabled=dict(type="bool"),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    normalize_choice_parameters(module, CHOICE_VALUE_MAPS)
    OciHealthCheckModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
