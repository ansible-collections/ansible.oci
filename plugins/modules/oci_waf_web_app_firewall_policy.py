# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Manage OCI Web Application Firewall policies."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
---
module: oci_waf_web_app_firewall_policy
short_description: Manage an OCI Web Application Firewall policy
description:
  - Create, update, and delete regional OCI Web Application Firewall policies.
version_added: 1.2.0
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_name_lookup_options
  - ansible.oci.oci_wait_options
  - ansible.oci.oci_tags_options
options:
  state:
    description: The desired state of the WAF policy.
    type: str
    choices:
      - present
      - absent
    default: present

  web_app_firewall_policy_id:
    description: The OCID of the policy to manage.
    type: str

  actions:
    description: Named actions referenced by policy rules. A supplied list replaces the existing actions.
    type: list
    elements: dict
    suboptions:
      type:
        description: The type of this action, rule, or response body.
        type: str
        choices:
          - allow
          - check
          - return_http_response
        required: true

      name:
        description: The case-sensitive name of the action or rule.
        type: str
        required: true

      code:
        description: The HTTP response code. Required and supported only when the action type is C(return_http_response).
        type: int

      headers:
        description: HTTP headers returned by this action. Supported only when the action type is C(return_http_response).
        type: list
        elements: dict
        suboptions:
          name:
            description: The case-sensitive name of the action or rule.
            type: str
            required: true

          value:
            description: The case-sensitive HTTP header value.
            type: str
            required: true

      body:
        description: The static HTTP response body. Supported only when the action type is C(return_http_response).
        type: dict
        suboptions:
          type:
            description: The type of this action, rule, or response body.
            type: str
            choices:
              - static_text
            required: true

          text:
            description: The response text. Letter case is preserved.
            type: str
            required: true

  request_access_control:
    description: Access rules for incoming requests. Unspecified object fields retain their existing values.
    type: dict
    suboptions:
      default_action_name:
        description: The action used when no access rule matches. Reference an allow or HTTP response
          action.
        type: str
        required: true

      rules:
        description: Ordered rules for this policy section. A supplied list replaces existing rules. An
          empty list removes all rules.
        type: list
        elements: dict
        suboptions:
          name:
            description: The case-sensitive name of the action or rule.
            type: str
            required: true

          condition_language:
            description: The language used for the rule condition.
            type: str
            choices:
              - jmespath

          condition:
            description: The rule condition. Letter case is preserved. OCI validates the expression.
            type: str

          action_name:
            description: The name of an action defined in this policy.
            type: str
            required: true

  request_rate_limiting:
    description: Limits for incoming requests. Unspecified object fields retain their existing values.
    type: dict
    suboptions:
      rules:
        description: Ordered rules for this policy section. A supplied list replaces existing rules. An
          empty list removes all rules.
        type: list
        elements: dict
        suboptions:
          name:
            description: The case-sensitive name of the action or rule.
            type: str
            required: true

          condition_language:
            description: The language used for the rule condition.
            type: str
            choices:
              - jmespath

          condition:
            description: The rule condition. Letter case is preserved. OCI validates the expression.
            type: str

          action_name:
            description: The name of an action defined in this policy.
            type: str
            required: true

          configurations:
            description: Rate limits applied when this rule matches.
            type: list
            elements: dict
            required: true
            suboptions:
              period_in_seconds:
                description: The period used to count requests, in seconds.
                type: int
                required: true

              requests_limit:
                description: The maximum number of requests in the period.
                type: int
                required: true

              action_duration_in_seconds:
                description: The duration of the action after the request limit is exceeded, in seconds.
                type: int

  request_protection:
    description: Protection rules for incoming requests. Unspecified object fields retain their existing
      values.
    type: dict
    suboptions:
      rules:
        description: Ordered rules for this policy section. A supplied list replaces existing rules. An
          empty list removes all rules.
        type: list
        elements: dict
        suboptions:
          name:
            description: The case-sensitive name of the action or rule.
            type: str
            required: true

          condition_language:
            description: The language used for the rule condition.
            type: str
            choices:
              - jmespath

          condition:
            description: The rule condition. Letter case is preserved. OCI validates the expression.
            type: str

          action_name:
            description: The name of an action defined in this policy.
            type: str
            required: true

          protection_capabilities:
            description: Protection capabilities evaluated by this rule.
            type: list
            elements: dict
            required: true
            suboptions:
              key:
                description: The OCI identifier of the protection capability.
                type: str
                required: true

              version:
                description: The version of the protection capability.
                type: int
                required: true

              exclusions:
                description: Request fields excluded from this protection capability.
                type: dict
                suboptions:
                  request_cookies:
                    description: Cookie names excluded from evaluation.
                    type: list
                    elements: str

                  args:
                    description: Argument names excluded from evaluation.
                    type: list
                    elements: str

              action_name:
                description: The name of an action defined in this policy.
                type: str

              collaborative_action_threshold:
                description: The score that activates the collaborative protection action.
                type: int

              collaborative_weights:
                description: Weights for individual collaborative protection capabilities.
                type: list
                elements: dict
                suboptions:
                  key:
                    description: The OCI identifier of the protection capability.
                    type: str
                    required: true

                  weight:
                    description: The weight assigned to the capability.
                    type: int
                    required: true

          protection_capability_settings:
            description: Settings for protection capabilities evaluated by this rule.
            type: dict
            suboptions:
              max_number_of_arguments:
                description: The maximum number of request arguments.
                type: int

              max_single_argument_length:
                description: The maximum length of one request argument.
                type: int

              max_total_argument_length:
                description: The maximum combined length of request arguments.
                type: int

              max_http_request_headers:
                description: The maximum number of HTTP request headers.
                type: int

              max_http_request_header_length:
                description: The maximum combined length of HTTP request headers.
                type: int

              allowed_http_methods:
                description: HTTP methods allowed by protection capabilities. Letter case is preserved.
                type: list
                elements: str

          is_body_inspection_enabled:
            description: Whether protection rules inspect the request body.
            type: bool

      body_inspection_size_limit_in_bytes:
        description: The maximum size of the inspected request body, in bytes.
        type: int

      body_inspection_size_limit_exceeded_action_name:
        description: The action used when the body inspection size limit is exceeded.
        type: str

  response_access_control:
    description: Access rules for outgoing responses. Unspecified object fields retain their existing
      values.
    type: dict
    suboptions:
      rules:
        description: Ordered rules for this policy section. A supplied list replaces existing rules. An
          empty list removes all rules.
        type: list
        elements: dict
        suboptions:
          name:
            description: The case-sensitive name of the action or rule.
            type: str
            required: true

          condition_language:
            description: The language used for the rule condition.
            type: str
            choices:
              - jmespath

          condition:
            description: The rule condition. Letter case is preserved. OCI validates the expression.
            type: str

          action_name:
            description: The name of an action defined in this policy.
            type: str
            required: true

  response_protection:
    description: Protection rules for outgoing responses. Unspecified object fields retain their existing
      values.
    type: dict
    suboptions:
      rules:
        description: Ordered rules for this policy section. A supplied list replaces existing rules. An
          empty list removes all rules.
        type: list
        elements: dict
        suboptions:
          name:
            description: The case-sensitive name of the action or rule.
            type: str
            required: true

          condition_language:
            description: The language used for the rule condition.
            type: str
            choices:
              - jmespath

          condition:
            description: The rule condition. Letter case is preserved. OCI validates the expression.
            type: str

          action_name:
            description: The name of an action defined in this policy.
            type: str
            required: true

          protection_capabilities:
            description: Protection capabilities evaluated by this rule.
            type: list
            elements: dict
            required: true
            suboptions:
              key:
                description: The OCI identifier of the protection capability.
                type: str
                required: true

              version:
                description: The version of the protection capability.
                type: int
                required: true

              exclusions:
                description: Request fields excluded from this protection capability.
                type: dict
                suboptions:
                  request_cookies:
                    description: Cookie names excluded from evaluation.
                    type: list
                    elements: str

                  args:
                    description: Argument names excluded from evaluation.
                    type: list
                    elements: str

              action_name:
                description: The name of an action defined in this policy.
                type: str

              collaborative_action_threshold:
                description: The score that activates the collaborative protection action.
                type: int

              collaborative_weights:
                description: Weights for individual collaborative protection capabilities.
                type: list
                elements: dict
                suboptions:
                  key:
                    description: The OCI identifier of the protection capability.
                    type: str
                    required: true

                  weight:
                    description: The weight assigned to the capability.
                    type: int
                    required: true

          protection_capability_settings:
            description: Settings for protection capabilities evaluated by this rule.
            type: dict
            suboptions:
              max_number_of_arguments:
                description: The maximum number of request arguments.
                type: int

              max_single_argument_length:
                description: The maximum length of one request argument.
                type: int

              max_total_argument_length:
                description: The maximum combined length of request arguments.
                type: int

              max_http_request_headers:
                description: The maximum number of HTTP request headers.
                type: int

              max_http_request_header_length:
                description: The maximum combined length of HTTP request headers.
                type: int

              allowed_http_methods:
                description: HTTP methods allowed by protection capabilities. Letter case is preserved.
                type: list
                elements: str

  system_tags:
    description: Oracle system tags applied to the policy.
    type: dict

  name:
    description:
      - The policy display name.
      - Required for creation. Without a policy ID, name lookup uses the supplied compartment.
    type: str

  compartment_id:
    description:
      - The OCID of the compartment containing the policy.
      - Required for creation and name lookup. This module cannot change the compartment.
    type: str
notes:
  - The policy section determines each rule type. Do not specify C(type) in rules.
  - When C(wait=false), the module returns the immediate OCI response snapshot without polling.
"""

EXAMPLES = r"""
- name: Create a WAF policy with a default action
  ansible.oci.oci_waf_web_app_firewall_policy:
    compartment_id: ocid1.compartment.oc1..example
    name: example-policy
    actions:
      - name: allow-request
        type: allow
    request_access_control:
      default_action_name: allow-request

- name: Rename a WAF policy
  ansible.oci.oci_waf_web_app_firewall_policy:
    web_app_firewall_policy_id: ocid1.webappfirewallpolicy.oc1..example
    name: updated-policy

- name: Delete a WAF policy
  ansible.oci.oci_waf_web_app_firewall_policy:
    web_app_firewall_policy_id: ocid1.webappfirewallpolicy.oc1..example
    state: absent
"""

RETURN = r"""
resource:
  description:
    - The full policy returned by OCI.
    - Fields can contain null when OCI does not set a value.
  returned: when state is present and no change is predicted in check mode
  type: dict
  sample:
    id: ocid1.webappfirewallpolicy.oc1..example
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
      returned: when available
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
      returned: when available
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
      returned: when available
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
      returned: when available
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
      returned: when available
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
      returned: when available
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
    OCI_COMMON_ARGS,
    filter_none_values,
    import_oci_sdk,
    serialize_oci_model,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_waf import (
    build_policy_fields,
    waf_subset_differs,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]

CREATE_REQUIRED_FIELDS = ("compartment_id", "name")
WAF_READY_STATES = ("ACTIVE",)
WAF_RULE_FIELDS = (
    "actions",
    "request_access_control",
    "request_rate_limiting",
    "request_protection",
    "response_access_control",
    "response_protection",
)


def build_create_web_app_firewall_policy_details(params):
    """Build typed OCI create details from module parameters.

    Args:
        params: Module parameter dictionary.

    Returns:
        An OCI CreateWebAppFirewallPolicyDetails model.
    """
    values = build_policy_fields(oci.waf.models, params)
    values["compartment_id"] = params.get("compartment_id")
    return oci.waf.models.CreateWebAppFirewallPolicyDetails(
        **filter_none_values(values)
    )


class OciWafWebAppFirewallPolicyModule(OciResourceBase):
    """Resource adapter for OCI Web Application Firewall policies."""

    @property
    def client_class(self):
        """Return the WAF service client class.

        Returns:
            The OCI WafClient class.
        """
        return oci.waf.WafClient

    resource_id_param = "web_app_firewall_policy_id"
    list_resource_method = "list_web_app_firewall_policies"
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "Web Application Firewall policy"
    update_method_name = "update_web_app_firewall_policy"
    update_details_name = "update_web_app_firewall_policy_details"
    update_wait_states = WAF_READY_STATES
    list_filter_params = ()
    update_field_specs = (
        UpdateFieldSpec("name", is_mutable=True, resource_field="display_name"),
        UpdateFieldSpec("compartment_id", is_mutable=False),
        UpdateFieldSpec("actions", is_mutable=True, compare="waf_actions"),
        *tuple(
            UpdateFieldSpec(field, is_mutable=True, compare="waf")
            for field in WAF_RULE_FIELDS[1:]
        ),
        UpdateFieldSpec("system_tags", is_mutable=True),
    )

    def get_resource_response(self, resource_id):
        """Fetch a policy by OCID.

        Args:
            resource_id: Policy OCID.

        Returns:
            OCI response containing the policy.
        """
        return self.call_with_retry(
            self.client.get_web_app_firewall_policy,
            web_app_firewall_policy_id=resource_id,
        )

    def hydrate_named_resource(self, resource):
        """Fetch the full policy because list summaries omit policy settings.

        Args:
            resource: Policy summary returned by list.

        Returns:
            Full policy model.
        """
        return self.get_resource_by_id(resource.id)

    def compare_update_field_values(self, current_value, desired_value, compare=None):
        """Compare nested WAF fields with ordered rules and server defaults.

        Args:
            current_value: Current serialized SDK value.
            desired_value: Desired module value.
            compare: Shared comparison strategy name.

        Returns:
            True when the desired value differs.
        """
        if compare == "waf_actions":
            return waf_subset_differs(current_value, desired_value, "actions")
        if compare == "waf":
            return waf_subset_differs(current_value, desired_value)
        return super(
            OciWafWebAppFirewallPolicyModule, self
        ).compare_update_field_values(current_value, desired_value, compare)

    def create_resource(self):
        """Create a policy and wait for its work request when requested.

        Returns:
            The created policy model.
        """
        response = self.call_with_retry(
            self.client.create_web_app_firewall_policy,
            create_web_app_firewall_policy_details=build_create_web_app_firewall_policy_details(
                self.module.params
            ),
        )
        return self._mutation_result(response)

    def build_update_details(self, update_model_fields):
        """Build typed OCI update details from planned fields.

        Args:
            update_model_fields: Typed fields selected by the update planner.

        Returns:
            The OCI UpdateWebAppFirewallPolicyDetails model.
        """
        return oci.waf.models.UpdateWebAppFirewallPolicyDetails(**update_model_fields)

    def update_resource(self, resource):
        """Apply the update plan and wait for its asynchronous operation.

        The inherited update method cannot wait for the returned work request.

        Args:
            resource: The current OCI resource model.

        Returns:
            The updated resource or its immediate snapshot.
        """
        plan = self.get_update_plan(resource)
        if not plan["update_model_fields"]:
            return resource
        values = dict(plan["update_model_fields"])
        current = serialize_oci_model(resource)
        for field in WAF_RULE_FIELDS:
            if field in values:
                values[field] = _merge_policy_value(current.get(field), values[field])
        response = self.call_with_retry(
            self.client.update_web_app_firewall_policy,
            web_app_firewall_policy_id=resource.id,
            update_web_app_firewall_policy_details=self.build_update_details(
                build_policy_fields(oci.waf.models, dict_to_models_params(values))
            ),
        )
        if not self.module.params.get("wait", True):
            return response.data or resource
        return self._mutation_result(response, resource.id)

    def _mutation_result(self, response, resource_id=None):
        """Wait for a policy operation because OCI updates return no resource.

        Args:
            response: The response from the create or update operation.
            resource_id: The existing policy ID, when updating.

        Returns:
            The immediate resource or the policy after the configured wait.
        """
        resource_id = resource_id or getattr(response.data, "id", None)
        if not self.module.params.get("wait", True):
            return response.data or {"id": resource_id}
        work_request_id = response.headers.get("opc-work-request-id")
        if work_request_id:
            self.wait_for_work_request(self.client, work_request_id)
            return self.get_resource_response(resource_id).data
        return self.get_mutation_result(response.data, resource_id, WAF_READY_STATES)

    def delete_resource(self, resource):
        """Delete the policy and wait for its work request when available.

        Args:
            resource: The policy model to delete.

        Returns:
            The deletion response data or the result from the resource waiter.
        """
        response = self.call_delete_fn(
            resource,
            self.client.delete_web_app_firewall_policy,
            web_app_firewall_policy_id=resource.id,
        )
        if not self.module.params.get("wait", True):
            return response.data
        work_request_id = response.headers.get("opc-work-request-id")
        if work_request_id:
            self.wait_for_work_request(self.client, work_request_id)
            return response.data
        return self.get_mutation_result(
            response.data, resource.id, tuple(self.dead_states)
        )


def _merge_policy_value(current, desired):
    """Merge supplied object fields while replacing supplied lists.

    Args:
        current: The current object or field value.
        desired: The supplied object or field value.

    Returns:
        The merged object or the desired list or scalar value.
    """
    if isinstance(current, dict) and isinstance(desired, dict):
        merged = dict(current)
        for key, value in desired.items():
            if value is not None:
                merged[key] = _merge_policy_value(current.get(key), value)
        return merged
    return desired


def dict_to_models_params(values):
    """Map planned update fields to the names used by the model builder.

    Args:
        values: The fields selected by the update planner.

    Returns:
        A dictionary with the collection name field.
    """
    params = dict(values)
    params["name"] = params.pop("display_name", None)
    return params


def validate_action_options(module):
    """Reject response fields for actions that do not return an HTTP response."""
    for index, action in enumerate(module.params.get("actions") or []):
        if action["type"] == "return_http_response":
            continue
        incompatible = [
            field
            for field in ("code", "headers", "body")
            if action.get(field) is not None
        ]
        if incompatible:
            module.fail_json(
                msg="actions[%s] with type=%s does not support: %s. "
                "These fields require type=return_http_response."
                % (index, action["type"], ", ".join(incompatible))
            )


def main():
    """Build the argument specification and execute the module."""
    action_options = dict(
        type=dict(
            type="str",
            choices=["allow", "check", "return_http_response"],
            required=True,
        ),
        name=dict(type="str", required=True),
        code=dict(type="int"),
        headers=dict(
            type="list",
            elements="dict",
            options=dict(
                name=dict(type="str", required=True),
                value=dict(type="str", required=True),
            ),
        ),
        body=dict(
            type="dict",
            options=dict(
                type=dict(type="str", choices=["static_text"], required=True),
                text=dict(type="str", required=True),
            ),
        ),
    )
    rule_options = dict(
        name=dict(type="str", required=True),
        condition_language=dict(type="str", choices=["jmespath"]),
        condition=dict(type="str"),
        action_name=dict(type="str", required=True),
    )
    access_rule_options = dict(rule_options)
    rate_rule_options = dict(
        rule_options,
        configurations=dict(
            type="list",
            elements="dict",
            required=True,
            options=dict(
                period_in_seconds=dict(type="int", required=True),
                requests_limit=dict(type="int", required=True),
                action_duration_in_seconds=dict(type="int"),
            ),
        ),
    )
    protection_rule_options = dict(
        rule_options,
        protection_capabilities=dict(
            type="list",
            elements="dict",
            required=True,
            options=dict(
                key=dict(type="str", no_log=False, required=True),
                version=dict(type="int", required=True),
                exclusions=dict(
                    type="dict",
                    options=dict(
                        request_cookies=dict(type="list", elements="str"),
                        args=dict(type="list", elements="str"),
                    ),
                ),
                action_name=dict(type="str"),
                collaborative_action_threshold=dict(type="int"),
                collaborative_weights=dict(
                    type="list",
                    elements="dict",
                    options=dict(
                        key=dict(type="str", no_log=False, required=True),
                        weight=dict(type="int", required=True),
                    ),
                ),
            ),
        ),
        protection_capability_settings=dict(
            type="dict",
            options=dict(
                max_number_of_arguments=dict(type="int"),
                max_single_argument_length=dict(type="int"),
                max_total_argument_length=dict(type="int"),
                max_http_request_headers=dict(type="int"),
                max_http_request_header_length=dict(type="int"),
                allowed_http_methods=dict(type="list", elements="str"),
            ),
        ),
    )
    access_section = dict(
        type="dict",
        options=dict(
            default_action_name=dict(type="str", required=True),
            rules=dict(type="list", elements="dict", options=access_rule_options),
        ),
    )
    rate_section = dict(
        type="dict",
        options=dict(
            rules=dict(type="list", elements="dict", options=rate_rule_options)
        ),
    )
    request_protection_section = dict(
        type="dict",
        options=dict(
            rules=dict(
                type="list",
                elements="dict",
                options=dict(
                    protection_rule_options,
                    is_body_inspection_enabled=dict(type="bool"),
                ),
            ),
            body_inspection_size_limit_in_bytes=dict(type="int"),
            body_inspection_size_limit_exceeded_action_name=dict(type="str"),
        ),
    )
    response_protection_section = dict(
        type="dict",
        options=dict(
            rules=dict(type="list", elements="dict", options=protection_rule_options)
        ),
    )
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        web_app_firewall_policy_id=dict(type="str"),
        actions=dict(
            type="list",
            elements="dict",
            options=action_options,
            required_if=[("type", "return_http_response", ["code"])],
        ),
        request_access_control=access_section,
        request_rate_limiting=rate_section,
        request_protection=request_protection_section,
        response_access_control=dict(
            type="dict",
            options=dict(
                rules=dict(type="list", elements="dict", options=access_rule_options)
            ),
        ),
        response_protection=response_protection_section,
        system_tags=dict(type="dict"),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    validate_action_options(module)
    OciWafWebAppFirewallPolicyModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
