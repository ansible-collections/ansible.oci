# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_waf_web_app_firewall_info
short_description: Retrieve OCI Web Application Firewall information
description: Retrieve one Web Application Firewall or list firewalls in a compartment.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_info_filter_options
options:
  web_app_firewall_id:
    description: OCID of one Web Application Firewall to retrieve.
    type: str

  compartment_id:
    description: OCID of the compartment to list Web Application Firewalls from.
    type: str

  name:
    description: Filter listed firewalls by display name.
    type: str

  lifecycle_state:
    description: Filter listed firewalls by lifecycle state.
    type: str
    choices: [creating, updating, active, deleting, deleted, failed]
"""

EXAMPLES = r"""
- name: List active Web Application Firewalls
  ansible.oci.oci_waf_web_app_firewall_info:
    compartment_id: ocid1.compartment.oc1..example
    lifecycle_state: active
"""

RETURN = r"""
web_app_firewalls:
  description:
    - The firewalls that match the query.
    - The sample shows a firewall attached to a load balancer.
    - Fields can contain null when OCI does not set a value.
  returned: always
  type: list
  elements: dict
  sample:
    - id: ocid1.webappfirewall.oc1..example
      name: example-waf
      compartment_id: ocid1.compartment.oc1..example
      backend_type: LOAD_BALANCER
      web_app_firewall_policy_id: ocid1.webappfirewallpolicy.oc1..example
      load_balancer_id: ocid1.loadbalancer.oc1..example
      time_created: '2026-01-01T12:00:00+00:00'
      time_updated: '2026-01-01T12:00:00+00:00'
      lifecycle_state: ACTIVE
      lifecycle_details: null
      freeform_tags:
        environment: test
      defined_tags:
        Operations:
          owner: example-user
      system_tags:
        orcl-cloud:
          free-tier-retained: 'true'
  contains:
    id:
      description: The Web Application Firewall OCID.
      type: str
      returned: when available
      sample: ocid1.webappfirewall.oc1..example
    name:
      description: The display name of the firewall.
      type: str
      returned: when available
      sample: example-waf
    compartment_id:
      description: The OCID of the containing compartment.
      type: str
      returned: when available
      sample: ocid1.compartment.oc1..example
    backend_type:
      description: The backend type. OCI returns LOAD_BALANCER for a load balancer firewall.
      type: str
      returned: when available
      sample: LOAD_BALANCER
    web_app_firewall_policy_id:
      description: The OCID of the applied policy.
      type: str
      returned: when available
      sample: ocid1.webappfirewallpolicy.oc1..example
    load_balancer_id:
      description: The OCID of the attached load balancer. This field is in load balancer firewall models.
      type: str
      returned: when available
      sample: ocid1.loadbalancer.oc1..example
    time_created:
      description: The date and time when OCI created the firewall.
      type: str
      returned: when available
      sample: '2026-01-01T12:00:00+00:00'
    time_updated:
      description: The date and time when OCI updated the firewall.
      type: str
      returned: when available
      sample: '2026-01-01T12:00:00+00:00'
    lifecycle_state:
      description: The lifecycle state. OCI returns an uppercase value.
      type: str
      returned: when available
      sample: ACTIVE
    lifecycle_details:
      description: Details about the current lifecycle state.
      type: str
      returned: when available
      sample: null
    freeform_tags:
      description: Free-form tags for the firewall.
      type: dict
      returned: when available
      sample:
        environment: test
    defined_tags:
      description: Defined tags for the firewall.
      type: dict
      returned: when available
      sample:
        Operations:
          owner: example-user
    system_tags:
      description: Oracle system tags for the firewall.
      type: dict
      returned: when available
      sample:
        orcl-cloud:
          free-tier-retained: 'true'
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

oci = import_oci_sdk()[0]


class OciWafWebAppFirewallInfoModule(OciInfoBase):
    """Concrete info adapter for OCI Web Application Firewalls."""

    @property
    def client_class(self):
        """Return the OCI WAF client class.

        Returns:
            The WafClient class.
        """
        return oci.waf.WafClient

    results_key = "web_app_firewalls"
    resource_id_param = "web_app_firewall_id"
    resource_get_method = "get_web_app_firewall"
    list_resource_method = "list_web_app_firewalls"
    list_filter_params = ("compartment_id", "lifecycle_state")

    def collect_list_filters(self, *param_groups):
        """Translate the user lifecycle state to OCI uppercase.

        Args:
            *param_groups: Parameter groups collected by the base helper.

        Returns:
            OCI list filters with lifecycle state converted to uppercase.
        """
        filters = super(OciWafWebAppFirewallInfoModule, self).collect_list_filters(
            *param_groups
        )
        if "lifecycle_state" in filters:
            filters["lifecycle_state"] = [filters["lifecycle_state"].upper()]
        return filters


def main():
    """Build the argument specification and execute the module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        web_app_firewall_id=dict(type="str"),
        compartment_id=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(
            type="str",
            choices=["creating", "updating", "active", "deleting", "deleted", "failed"],
        ),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["web_app_firewall_id", "compartment_id"]],
    )
    OciWafWebAppFirewallInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
