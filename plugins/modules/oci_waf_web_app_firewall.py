# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_waf_web_app_firewall
short_description: Manage an OCI Web Application Firewall
description:
  - Create, update, and delete an OCI Web Application Firewall attached to a load balancer.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_name_lookup_options
  - ansible.oci.oci_wait_options
  - ansible.oci.oci_tags_options
options:
  state:
    description: Desired state of the Web Application Firewall.
    type: str
    choices: [present, absent]
    default: present

  web_app_firewall_id:
    description: OCID of the Web Application Firewall to manage.
    type: str

  name:
    description:
      - Display name of the Web Application Firewall.
      - Required when creating a firewall.
      - Name lookup uses C(name) and C(compartment_id).
    type: str

  compartment_id:
    description:
      - OCID of the compartment containing the Web Application Firewall.
      - Required when creating a firewall and when using name lookup.
    type: str

  load_balancer_id:
    description:
      - OCID of the load balancer attached to the firewall.
      - Required when creating a firewall and immutable after creation.
    type: str

  web_app_firewall_policy_id:
    description:
      - OCID of the Web Application Firewall policy.
      - Required when creating a firewall.
    type: str

  system_tags:
    description: Oracle system tags for the firewall.
    type: dict
notes:
  - This module supports only load balancer backends. The backend type is always C(LOAD_BALANCER).
"""

EXAMPLES = r"""
- name: Create a Web Application Firewall
  ansible.oci.oci_waf_web_app_firewall:
    compartment_id: ocid1.compartment.oc1..example
    name: example-waf
    load_balancer_id: ocid1.loadbalancer.oc1..example
    web_app_firewall_policy_id: ocid1.webappfirewallpolicy.oc1..example

- name: Delete a Web Application Firewall
  ansible.oci.oci_waf_web_app_firewall:
    state: absent
    web_app_firewall_id: ocid1.webappfirewall.oc1..example
"""

RETURN = r"""
resource:
  description:
    - The full firewall returned by OCI.
    - The sample shows a firewall attached to a load balancer.
    - Fields can contain null when OCI does not set a value.
  returned: when state is present and no change is predicted in check mode
  type: dict
  sample:
    id: ocid1.webappfirewall.oc1..example
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
      description: The backend type. The value can be LOAD_BALANCER.
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
    OCI_COMMON_ARGS,
    filter_none_values,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

oci = import_oci_sdk()[0]

CREATE_REQUIRED_FIELDS = (
    "compartment_id",
    "name",
    "load_balancer_id",
    "web_app_firewall_policy_id",
)
WAIT_FOR_WAF_STATES = ("ACTIVE",)


def build_create_web_app_firewall_details(params):
    """Build the OCI load-balancer WebAppFirewall create model.

    Args:
        params: Ansible module parameters.

    Returns:
        An OCI CreateWebAppFirewallLoadBalancerDetails model.
    """
    fields = filter_none_values(
        {
            "display_name": params.get("name"),
            "compartment_id": params.get("compartment_id"),
            "backend_type": "LOAD_BALANCER",
            "load_balancer_id": params.get("load_balancer_id"),
            "web_app_firewall_policy_id": params.get("web_app_firewall_policy_id"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
            "system_tags": params.get("system_tags"),
        }
    )
    return oci.waf.models.CreateWebAppFirewallLoadBalancerDetails(**fields)


class OciWafWebAppFirewallModule(OciResourceBase):
    """Concrete resource adapter for OCI Web Application Firewalls."""

    @property
    def client_class(self):
        """Return the OCI WAF client class.

        Returns:
            The WafClient class.
        """
        return oci.waf.WafClient

    resource_id_param = "web_app_firewall_id"
    list_resource_method = "list_web_app_firewalls"
    list_filter_params = ()
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "Web Application Firewall"
    update_method_name = "update_web_app_firewall"
    update_details_name = "update_web_app_firewall_details"
    update_wait_states = WAIT_FOR_WAF_STATES
    update_field_specs = (
        UpdateFieldSpec(
            param_name="name", resource_field="display_name", is_mutable=True
        ),
        UpdateFieldSpec(param_name="load_balancer_id", is_mutable=False),
        UpdateFieldSpec(param_name="web_app_firewall_policy_id", is_mutable=True),
        UpdateFieldSpec(param_name="compartment_id", is_mutable=False),
        UpdateFieldSpec(param_name="system_tags", is_mutable=True),
    )

    def get_resource_response(self, resource_id):
        """Fetch a Web Application Firewall by OCID.

        Args:
            resource_id: Web Application Firewall OCID.

        Returns:
            The OCI response from get_web_app_firewall.
        """
        return self.call_with_retry(
            self.client.get_web_app_firewall,
            web_app_firewall_id=resource_id,
        )

    def create_resource(self):
        """Create a Web Application Firewall and apply the shared wait flow.

        Returns:
            The created or immediately returned Web Application Firewall model.
        """
        response = self.call_with_retry(
            self.client.create_web_app_firewall,
            create_web_app_firewall_details=build_create_web_app_firewall_details(
                self.module.params
            ),
        )
        if not self.module.params.get("wait", True):
            return response.data
        work_request_id = getattr(response, "headers", {}).get("opc-work-request-id")
        if work_request_id:
            self.wait_for_work_request(self.client, work_request_id)
            resource_id = getattr(response.data, "id", None)
            return (
                self.get_resource_response(resource_id).data
                if resource_id
                else response.data
            )
        return self.get_mutation_result(
            response.data, getattr(response.data, "id", None), WAIT_FOR_WAF_STATES
        )

    def build_update_details(self, update_model_fields):
        """Build the OCI WebAppFirewall update model.

        Args:
            update_model_fields: Fields selected by the shared update planner.

        Returns:
            An OCI UpdateWebAppFirewallDetails model.
        """
        return oci.waf.models.UpdateWebAppFirewallDetails(**update_model_fields)

    def update_resource(self, resource):
        """Apply the update plan and wait for its asynchronous operation.

        The inherited update method cannot wait for the returned work request.

        Args:
            resource: The current OCI resource model.

        Returns:
            The updated resource or its immediate snapshot.
        """
        update_plan = self.get_update_plan(resource)
        if not update_plan["update_model_fields"]:
            return resource
        response = self.call_with_retry(
            self.client.update_web_app_firewall,
            web_app_firewall_id=resource.id,
            update_web_app_firewall_details=self.build_update_details(
                update_plan["update_model_fields"]
            ),
        )
        if not self.module.params.get("wait", True):
            return response.data or resource
        work_request_id = getattr(response, "headers", {}).get("opc-work-request-id")
        if work_request_id:
            self.wait_for_work_request(self.client, work_request_id)
            return self.get_resource_response(resource.id).data
        return self.get_mutation_result(response.data, resource.id, WAIT_FOR_WAF_STATES)

    def delete_resource(self, resource):
        """Delete a Web Application Firewall and apply the shared wait flow.

        Args:
            resource: Web Application Firewall model to delete.

        Returns:
            The deletion response data or waited result.
        """
        response = self.call_delete_fn(
            resource,
            self.client.delete_web_app_firewall,
            web_app_firewall_id=resource.id,
        )
        if self.module.params.get("wait", True):
            work_request_id = getattr(response, "headers", {}).get(
                "opc-work-request-id"
            )
            if work_request_id:
                self.wait_for_work_request(self.client, work_request_id)
            else:
                self.get_mutation_result(
                    response.data, resource.id, tuple(self.dead_states)
                )
        return response.data


def main():
    """Build the argument specification and execute the module."""
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        web_app_firewall_id=dict(type="str"),
        load_balancer_id=dict(type="str"),
        web_app_firewall_policy_id=dict(type="str"),
        system_tags=dict(type="dict"),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    OciWafWebAppFirewallModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
