# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Retrieve OCI Web Application Firewall policies."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
---
module: oci_waf_web_app_firewall_policy_info
short_description: Retrieve OCI Web Application Firewall policies
description:
  - Retrieve one policy by OCID or list policies in a compartment.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_info_filter_options
options:
  compartment_id:
    type: str
    description: OCID of the compartment to query.

  web_app_firewall_policy_id:
    type: str
    description: OCID of one policy to retrieve.

  lifecycle_state:
    type: str
    choices: [creating, updating, active, deleting, deleted, failed]
    description: Lowercase lifecycle state filter.
"""

EXAMPLES = r"""
- name: List WAF policies
  ansible.oci.oci_waf_web_app_firewall_policy_info:
    compartment_id: ocid1.compartment.oc1..example
"""

RETURN = r"""
web_app_firewall_policies:
  description:
    - The policies that match the query.
    - A lookup by OCID returns the full policy shown in the sample.
    - A list query returns summary fields without actions or request and response settings.
    - Fields can contain null when OCI does not set a value.
  returned: always
  type: list
  elements: dict
  sample:
    - id: ocid1.webappfirewallpolicy.oc1..example
      name: example-policy
      compartment_id: ocid1.compartment.oc1..example
      time_created: '2026-01-01T12:00:00+00:00'
      time_updated: '2026-01-01T12:00:00+00:00'
      lifecycle_state: ACTIVE
      lifecycle_details: null
      actions:
        - type: ALLOW
          name: allow-request
        - type: CHECK
          name: block-request
        - type: RETURN_HTTP_RESPONSE
          name: response-error
          code: 403
          headers:
            - name: Content-Type
              value: application/json
          body:
            type: STATIC_TEXT
            text: '{"error":"request blocked"}'
        - type: RETURN_HTTP_RESPONSE
          name: response-error-dynamic
          code: 403
          headers:
            - name: Content-Type
              value: text/plain
          body:
            type: DYNAMIC
            template: Request blocked
      request_access_control:
        default_action_name: allow-request
        rules:
          - type: ACCESS_CONTROL
            name: block-bad-path
            condition_language: JMESPATH
            condition: 'true'
            action_name: block-request
      request_rate_limiting:
        rules:
          - type: REQUEST_RATE_LIMITING
            name: limit-api-requests
            condition_language: JMESPATH
            condition: 'true'
            action_name: block-request
            configurations:
              - period_in_seconds: 60
                requests_limit: 100
                action_duration_in_seconds: 300
      request_protection:
        rules:
          - type: PROTECTION
            name: inspect-requests
            condition_language: JMESPATH
            condition: 'true'
            action_name: block-request
            protection_capabilities:
              - key: '942100'
                version: 1
                exclusions:
                  request_cookies:
                    - session-id
                  args:
                    - tracking_id
                action_name: block-request
                collaborative_action_threshold: 5
                collaborative_weights:
                  - key: '942100'
                    weight: 1
            protection_capability_settings:
              max_number_of_arguments: 128
              max_single_argument_length: 4096
              max_total_argument_length: 8192
              max_http_request_headers: 64
              max_http_request_header_length: 4096
              allowed_http_methods:
                - GET
                - POST
            is_body_inspection_enabled: true
        body_inspection_size_limit_in_bytes: 8192
        body_inspection_size_limit_exceeded_action_name: block-request
      response_access_control:
        rules:
          - type: ACCESS_CONTROL
            name: return-blocked-response
            condition_language: JMESPATH
            condition: 'true'
            action_name: response-error
      response_protection:
        rules:
          - type: PROTECTION
            name: inspect-responses
            condition_language: JMESPATH
            condition: 'true'
            action_name: block-request
            protection_capabilities:
              - key: '942100'
                version: 1
                exclusions:
                  request_cookies:
                    - session-id
                  args:
                    - tracking_id
                action_name: block-request
                collaborative_action_threshold: 5
                collaborative_weights:
                  - key: '942100'
                    weight: 1
            protection_capability_settings:
              max_number_of_arguments: 128
              max_single_argument_length: 4096
              max_total_argument_length: 8192
              max_http_request_headers: 64
              max_http_request_header_length: 4096
              allowed_http_methods:
                - GET
                - POST
            is_body_inspection_enabled: false
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
      description: The policy OCID.
      type: str
      returned: when available
      sample: ocid1.webappfirewallpolicy.oc1..example
    name:
      description: The display name of the policy.
      type: str
      returned: when available
      sample: example-policy
    compartment_id:
      description: The OCID of the containing compartment.
      type: str
      returned: when available
      sample: ocid1.compartment.oc1..example
    time_created:
      description: The date and time when OCI created the policy.
      type: str
      returned: when available
      sample: '2026-01-01T12:00:00+00:00'
    time_updated:
      description: The date and time when OCI updated the policy.
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
    actions:
      description: Named actions used by policy rules. Action fields depend on the action type.
      type: list
      elements: dict
      returned: when retrieved by OCID
      contains:
        type:
          description: The action type, such as ALLOW, CHECK, or RETURN_HTTP_RESPONSE.
          type: str
          returned: when available
          sample: ALLOW
        name:
          description: The action name used by a rule.
          type: str
          returned: when available
          sample: allow-request
        code:
          description: The HTTP status code for a RETURN_HTTP_RESPONSE action.
          type: int
          returned: when the action type is RETURN_HTTP_RESPONSE
          sample: 403
        headers:
          description: The response headers for a RETURN_HTTP_RESPONSE action.
          type: list
          elements: dict
          returned: when the action type is RETURN_HTTP_RESPONSE
          contains:
            name:
              description: The header name.
              type: str
              returned: when available
              sample: Content-Type
            value:
              description: The header value.
              type: str
              returned: when available
              sample: application/json
        body:
          description: The response body for a RETURN_HTTP_RESPONSE action.
          type: dict
          returned: when the action type is RETURN_HTTP_RESPONSE
          contains:
            type:
              description: The body type, such as STATIC_TEXT or DYNAMIC.
              type: str
              returned: when available
              sample: STATIC_TEXT
            text:
              description: Static response text.
              type: str
              returned: when the response body type is STATIC_TEXT
              sample: '{"error":"request blocked"}'
            template:
              description: The response body template.
              type: str
              returned: when the response body type is DYNAMIC
              sample: Request blocked
    request_access_control:
      description: Access control settings for incoming requests.
      type: dict
      returned: when retrieved by OCID
      contains:
        default_action_name:
          description: The action name for a request that matches no rule.
          type: str
          returned: when available
          sample: allow-request
        rules:
          description: Rules that match incoming requests.
          type: list
          elements: dict
          returned: when available
          contains:
            type:
              description: The rule type. OCI returns ACCESS_CONTROL.
              type: str
              returned: when available
              sample: ACCESS_CONTROL
            name:
              description: The rule name.
              type: str
              returned: when available
              sample: block-bad-path
            condition_language:
              description: The language used by the rule condition.
              type: str
              returned: when available
              sample: JMESPATH
            condition:
              description: The rule condition.
              type: str
              returned: when available
              sample: 'true'
            action_name:
              description: The action name for a matching request.
              type: str
              returned: when available
              sample: block-request
    request_rate_limiting:
      description: Rate limiting settings for incoming requests.
      type: dict
      returned: when retrieved by OCID
      contains:
        rules:
          description: Rules that limit request rates.
          type: list
          elements: dict
          returned: when available
          contains:
            type:
              description: The rule type. OCI returns REQUEST_RATE_LIMITING.
              type: str
              returned: when available
              sample: REQUEST_RATE_LIMITING
            name:
              description: The rule name.
              type: str
              returned: when available
              sample: limit-api-requests
            condition_language:
              description: The language used by the rule condition.
              type: str
              returned: when available
              sample: JMESPATH
            condition:
              description: The rule condition.
              type: str
              returned: when available
              sample: 'true'
            action_name:
              description: The action name for requests that exceed the limit.
              type: str
              returned: when available
              sample: block-request
            configurations:
              description: Rate limit settings for the rule.
              type: list
              elements: dict
              returned: when available
              contains:
                period_in_seconds:
                  description: The time period for the request limit, in seconds.
                  type: int
                  returned: when available
                  sample: 60
                requests_limit:
                  description: The maximum number of requests in the period.
                  type: int
                  returned: when available
                  sample: 100
                action_duration_in_seconds:
                  description: The time to apply the action, in seconds.
                  type: int
                  returned: when available
                  sample: 300
    request_protection:
      description: Protection settings for incoming requests.
      type: dict
      returned: when retrieved by OCID
      contains:
        rules:
          description: Protection rules for incoming requests.
          type: list
          elements: dict
          returned: when available
          contains:
            type:
              description: The rule type. OCI returns PROTECTION.
              type: str
              returned: when available
              sample: PROTECTION
            name:
              description: The rule name.
              type: str
              returned: when available
              sample: inspect-requests
            condition_language:
              description: The language used by the rule condition.
              type: str
              returned: when available
              sample: JMESPATH
            condition:
              description: The rule condition.
              type: str
              returned: when available
              sample: 'true'
            action_name:
              description: The action name for a matching request.
              type: str
              returned: when available
              sample: block-request
            protection_capabilities:
              description: Protection capabilities enabled by this rule.
              type: list
              elements: dict
              returned: when available
              contains:
                key:
                  description: The capability key.
                  type: str
                  returned: when available
                  sample: '942100'
                version:
                  description: The capability version number.
                  type: int
                  returned: when available
                  sample: 1
                exclusions:
                  description: Request values excluded from capability inspection.
                  type: dict
                  returned: when available
                  contains:
                    request_cookies:
                      description: Cookie names excluded from inspection.
                      type: list
                      elements: str
                      returned: when available
                      sample:
                        - session-id
                    args:
                      description: Argument names excluded from inspection.
                      type: list
                      elements: str
                      returned: when available
                      sample:
                        - tracking_id
                action_name:
                  description: The action name for a detected threat.
                  type: str
                  returned: when available
                  sample: block-request
                collaborative_action_threshold:
                  description: The threshold for a collaborative capability action.
                  type: int
                  returned: when available
                  sample: 5
                collaborative_weights:
                  description: Weight overrides for collaborative capability checks.
                  type: list
                  elements: dict
                  returned: when available
                  contains:
                    key:
                      description: The capability key.
                      type: str
                      returned: when available
                      sample: '942100'
                    weight:
                      description: The capability weight.
                      type: int
                      returned: when available
                      sample: 1
            protection_capability_settings:
              description: Limits and allowed methods for protection capabilities.
              type: dict
              returned: when available
              contains:
                max_number_of_arguments:
                  description: The maximum number of request arguments.
                  type: int
                  returned: when available
                  sample: 128
                max_single_argument_length:
                  description: The maximum length of one request argument.
                  type: int
                  returned: when available
                  sample: 4096
                max_total_argument_length:
                  description: The maximum total length of request arguments.
                  type: int
                  returned: when available
                  sample: 8192
                max_http_request_headers:
                  description: The maximum number of request headers.
                  type: int
                  returned: when available
                  sample: 64
                max_http_request_header_length:
                  description: The maximum length of one request header.
                  type: int
                  returned: when available
                  sample: 4096
                allowed_http_methods:
                  description: HTTP methods allowed by the rule.
                  type: list
                  elements: str
                  returned: when available
                  sample:
                    - GET
                    - POST
            is_body_inspection_enabled:
              description: Whether the rule inspects the request body.
              type: bool
              returned: when available
              sample: true
        body_inspection_size_limit_in_bytes:
          description: The maximum request body size to inspect, in bytes.
          type: int
          returned: when available
          sample: 8192
        body_inspection_size_limit_exceeded_action_name:
          description: The action name when the body size limit is exceeded.
          type: str
          returned: when available
          sample: block-request
    response_access_control:
      description: Access control settings for outgoing responses. Its rules use the same fields as request
        access control rules.
      type: dict
      returned: when retrieved by OCID
      contains:
        rules:
          description: Rules that match outgoing responses.
          type: list
          elements: dict
          returned: when available
          contains:
            type:
              description: The rule type. OCI returns ACCESS_CONTROL.
              type: str
              returned: when available
              sample: ACCESS_CONTROL
            name:
              description: The rule name.
              type: str
              returned: when available
              sample: return-blocked-response
            condition_language:
              description: The language used by the rule condition.
              type: str
              returned: when available
              sample: JMESPATH
            condition:
              description: The rule condition.
              type: str
              returned: when available
              sample: 'true'
            action_name:
              description: The action name for a matching response.
              type: str
              returned: when available
              sample: response-error
    response_protection:
      description: Protection settings for outgoing responses. Its rules use the same fields as request
        protection rules.
      type: dict
      returned: when retrieved by OCID
      contains:
        rules:
          description: Protection rules for outgoing responses.
          type: list
          elements: dict
          returned: when available
          contains:
            type:
              description: The rule type. OCI returns PROTECTION.
              type: str
              returned: when available
              sample: PROTECTION
            name:
              description: The rule name.
              type: str
              returned: when available
              sample: inspect-responses
            condition_language:
              description: The language used by the rule condition.
              type: str
              returned: when available
              sample: JMESPATH
            condition:
              description: The rule condition.
              type: str
              returned: when available
              sample: 'true'
            action_name:
              description: The action name for a matching response.
              type: str
              returned: when available
              sample: block-request
            protection_capabilities:
              description: Protection capabilities enabled by this rule.
              type: list
              elements: dict
              returned: when available
              contains:
                key:
                  description: The capability key.
                  type: str
                  returned: when available
                  sample: '942100'
                version:
                  description: The capability version number.
                  type: int
                  returned: when available
                  sample: 1
                exclusions:
                  description: Request values excluded from capability inspection.
                  type: dict
                  returned: when available
                  contains:
                    request_cookies:
                      description: Cookie names excluded from inspection.
                      type: list
                      elements: str
                      returned: when available
                      sample:
                        - session-id
                    args:
                      description: Argument names excluded from inspection.
                      type: list
                      elements: str
                      returned: when available
                      sample:
                        - tracking_id
                action_name:
                  description: The action name for a detected threat.
                  type: str
                  returned: when available
                  sample: block-request
                collaborative_action_threshold:
                  description: The threshold for a collaborative capability action.
                  type: int
                  returned: when available
                  sample: 5
                collaborative_weights:
                  description: Weight overrides for collaborative capability checks.
                  type: list
                  elements: dict
                  returned: when available
                  contains:
                    key:
                      description: The capability key.
                      type: str
                      returned: when available
                      sample: '942100'
                    weight:
                      description: The capability weight.
                      type: int
                      returned: when available
                      sample: 1
            protection_capability_settings:
              description: Limits and allowed methods for protection capabilities.
              type: dict
              returned: when available
              contains:
                max_number_of_arguments:
                  description: The maximum number of request arguments.
                  type: int
                  returned: when available
                  sample: 128
                max_single_argument_length:
                  description: The maximum length of one request argument.
                  type: int
                  returned: when available
                  sample: 4096
                max_total_argument_length:
                  description: The maximum total length of request arguments.
                  type: int
                  returned: when available
                  sample: 8192
                max_http_request_headers:
                  description: The maximum number of request headers.
                  type: int
                  returned: when available
                  sample: 64
                max_http_request_header_length:
                  description: The maximum length of one request header.
                  type: int
                  returned: when available
                  sample: 4096
                allowed_http_methods:
                  description: HTTP methods allowed by the rule.
                  type: list
                  elements: str
                  returned: when available
                  sample:
                    - GET
                    - POST
            is_body_inspection_enabled:
              description: The request body inspection flag. Response protection rules cannot enable body inspection.
              type: bool
              returned: when available
              sample: false
    freeform_tags:
      description: Free-form tags for the policy.
      type: dict
      returned: when available
      sample:
        environment: test
    defined_tags:
      description: Defined tags for the policy.
      type: dict
      returned: when available
      sample:
        Operations:
          owner: example-user
    system_tags:
      description: Oracle system tags for the policy.
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

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]


class OciWafWebAppFirewallPolicyInfoModule(OciInfoBase):
    """Info adapter for OCI Web Application Firewall policies."""

    @property
    def client_class(self):
        """Return the WAF service client class.

        Returns:
            The OCI WafClient class.
        """
        return oci.waf.WafClient

    results_key = "web_app_firewall_policies"
    resource_id_param = "web_app_firewall_policy_id"
    resource_get_method = "get_web_app_firewall_policy"
    list_resource_method = "list_web_app_firewall_policies"
    list_filter_params = ("compartment_id", "lifecycle_state")

    def collect_list_filters(self, filter_params):
        """Collect list filters and convert lifecycle state to SDK casing.

        Args:
            filter_params: Supported OCI list filter parameter names.

        Returns:
            OCI list operation keyword arguments.
        """
        values = super(OciWafWebAppFirewallPolicyInfoModule, self).collect_list_filters(
            filter_params
        )
        if values.get("lifecycle_state"):
            values["lifecycle_state"] = [values["lifecycle_state"].upper()]
        return values


def main():
    """Build the argument specification and execute the module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        web_app_firewall_policy_id=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(
            type="str",
            choices=["creating", "updating", "active", "deleting", "deleted", "failed"],
        ),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "web_app_firewall_policy_id"]],
    )
    OciWafWebAppFirewallPolicyInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
