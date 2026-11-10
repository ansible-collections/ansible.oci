# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_health_check_info
short_description: Get OCI Health Checks monitor information
description:
  - Get one monitor or list monitor summaries in a compartment.
version_added: "1.3.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  monitor_type:
    description: The type of monitor to query.
    type: str
    choices: [http, ping]
    required: true
  monitor_id:
    description: The monitor OCID.
    type: str
  compartment_id:
    description: The OCID of the compartment to list.
    type: str
  name:
    description: Filter listed monitors by display name.
    type: str
  home_region:
    description: Filter listed monitors by home region.
    type: str
"""

EXAMPLES = r"""
- name: List HTTP monitors in a compartment
  ansible.oci.oci_health_check_info:
    monitor_type: http
    compartment_id: ocid1.compartment.oc1..example

- name: Get one ping monitor
  ansible.oci.oci_health_check_info:
    monitor_type: ping
    monitor_id: ocid1.pingmonitor.oc1..example
"""

RETURN = r"""
health_checks:
  description: The monitor resources that matched the request.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The monitor OCID.
      type: str
    name:
      description: The monitor display name.
      type: str
    compartment_id:
      description: The OCID of the monitor compartment.
      type: str
    targets:
      returned: When monitor_id is supplied and the field applies to the monitor type.
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
      returned: When monitor_id is supplied and the field applies to the monitor type.
      description: The time allowed for a probe to complete.
      type: int
      sample: 10
    port:
      returned: When monitor_id is supplied and the field applies to the monitor type.
      description: The target port for the monitor.
      type: int
      sample: 443
    method:
      returned: When monitor_id is supplied and the field applies to the monitor type.
      description: The HTTP request method.
      type: str
      sample: GET
    path:
      returned: When monitor_id is supplied and the field applies to the monitor type.
      description: The HTTP request path.
      type: str
      sample: /
    headers:
      returned: When monitor_id is supplied and the field applies to the monitor type.
      description: HTTP request headers.
      type: dict
    vantage_point_names:
      returned: When monitor_id is supplied and the field applies to the monitor type.
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
  sample:
    - id: ocid1.httpmonitor.oc1..example
      name: example-http-monitor
      compartment_id: ocid1.compartment.oc1..example
      interval_in_seconds: 30
      is_enabled: true
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_healthchecks import MONITOR_TYPES
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

oci = import_oci_sdk()[0]


class OciHealthCheckInfoModule(OciInfoBase):
    """Read one or more OCI HTTP or ping monitors."""

    @property
    def client_class(self):
        """Return the OCI Health Checks client class."""
        return oci.healthchecks.HealthChecksClient

    @property
    def dispatch(self):
        """Return SDK operation names for the requested monitor type."""
        return MONITOR_TYPES[self.module.params["monitor_type"]]

    @property
    def resource_get_method(self):
        """Return the monitor get operation name."""
        return self.dispatch["get"]

    @property
    def list_resource_method(self):
        """Return the monitor list operation name."""
        return self.dispatch["list"]

    results_key = "health_checks"
    resource_id_param = "monitor_id"
    resource_id_kwarg = "monitor_id"
    list_filter_params = ("compartment_id", "home_region")


def main():
    """Run the OCI Health Checks info module."""
    module = AnsibleModule(
        argument_spec=dict(
            OCI_AUTH_ARGS,
            monitor_type=dict(type="str", choices=list(MONITOR_TYPES), required=True),
            monitor_id=dict(type="str"),
            compartment_id=dict(type="str"),
            name=dict(type="str"),
            home_region=dict(type="str"),
        ),
        required_one_of=[["monitor_id", "compartment_id"]],
        supports_check_mode=True,
    )
    OciHealthCheckInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
