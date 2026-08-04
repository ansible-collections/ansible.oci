# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_dhcp_options
short_description: Manage a DHCP Options resource in Oracle Cloud Infrastructure
description:
  - Create, update, and delete OCI VCN DHCP options.
  - Uses the shared OCI helper layer for authentication, waiting, retry
    behavior, and result shaping.
  - Create requests must omit C(dhcp_options_id). After create, capture the
    returned DHCP options ID and use it for later C(state=present) and
    C(state=absent) tasks.
  - The OCI API always replaces the full C(options) list on update. This
    module mirrors that behavior; a partial C(options) list on update replaces
    every existing DHCP option, it does not merge with the current set.
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
      - The desired lifecycle state of the DHCP options.
    type: str
    choices: [present, absent]
    default: present
  dhcp_options_id:
    description:
      - The OCID of the DHCP options.
      - When provided, the module manages this exact DHCP options set.
      - Required to distinguish between multiple DHCP options sets that share
        the same scoped C(name).
    type: str
  name:
    description:
      - Human-readable name for the DHCP options.
      - Required when creating DHCP options.
      - When C(dhcp_options_id) is omitted, the module uses
        C(compartment_id + vcn_id + name) to find an existing DHCP options
        set.
      - If exactly one DHCP options set matches, C(state=present) manages it
        as the update target and C(state=absent) deletes it.
      - If more than one DHCP options set matches, the task fails and the
        caller must supply C(dhcp_options_id).
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the DHCP options.
      - Required when creating DHCP options.
      - Also scopes name-based DHCP options lookups when C(dhcp_options_id)
        is omitted.
    type: str
  vcn_id:
    description:
      - The OCID of the VCN containing the DHCP options.
      - Required when creating DHCP options.
      - The module does not support moving existing DHCP options to another
        VCN.
      - Also scopes name-based DHCP options lookups when C(dhcp_options_id)
        is omitted.
    type: str
  options:
    description:
      - The list of DHCP options to apply.
      - OCI replaces the entire list on update, so provide every option that
        should exist after the change, not only the ones being added.
      - Order does not affect idempotency; only the content of the list is
        compared.
      - The returned C(resource.options) uses this same C(option_type)/
        C(server_type) vocabulary, translated from OCI's native enum casing,
        so a value read from one task can be fed back into another
        unchanged.
    type: list
    elements: dict
    suboptions:
      option_type:
        description:
          - The type of DHCP option.
        type: str
        required: true
        choices: [domain_name_server, search_domain]
      server_type:
        description:
          - The source of the DNS servers for the subnets in the VCN.
          - Used when C(option_type=domain_name_server).
        type: str
        choices: [vcn_local, vcn_local_plus_internet, custom_dns_server]
      custom_dns_servers:
        description:
          - Up to three custom DNS server IP addresses.
          - Used when C(option_type=domain_name_server) and
            C(server_type=custom_dns_server).
        type: list
        elements: str
      search_domain_names:
        description:
          - A single search domain name according to RFC 952 and RFC 1123.
          - Used when C(option_type=search_domain).
        type: list
        elements: str
  domain_name_type:
    description:
      - The domain name type used for the VCN.
      - The returned C(resource.domain_name_type) uses this same vocabulary,
        translated from OCI's native enum casing, so a value read from one
        task can be fed back into another unchanged.
    type: str
    choices: [subnet_domain, vcn_domain, custom_domain]
"""

EXAMPLES = r"""
- name: Create DHCP options with a DNS and a search domain option
  oracle.oci.oci_dhcp_options:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-dhcp-options
    options:
      - option_type: domain_name_server
        server_type: vcn_local_plus_internet
      - option_type: search_domain
        search_domain_names:
          - example.oraclevcn.com
  register: created_dhcp_options

- name: Reconcile a uniquely named DHCP options set by name
  oracle.oci.oci_dhcp_options:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-dhcp-options
    domain_name_type: vcn_domain
    options:
      - option_type: domain_name_server
        server_type: custom_dns_server
        custom_dns_servers:
          - 10.0.0.10
      - option_type: search_domain
        search_domain_names:
          - example.oraclevcn.com

- name: Delete the created DHCP options
  oracle.oci.oci_dhcp_options:
    state: absent
    dhcp_options_id: "{{ created_dhcp_options.resource.id }}"

- name: Delete a uniquely named DHCP options set without providing dhcp_options_id
  oracle.oci.oci_dhcp_options:
    state: absent
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-dhcp-options
"""

RETURN = r"""
resource:
  description: The DHCP options resource.
  returned: when state != absent
  type: dict
  contains:
    id:
      description: The OCID of the DHCP options.
      type: str
      returned: always
      sample: ocid1.dhcpoptions.oc1..example
    name:
      description: The display name of the DHCP options.
      type: str
      returned: always
      sample: example-dhcp-options
    compartment_id:
      description: The OCID of the compartment containing the DHCP options.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    vcn_id:
      description: The OCID of the VCN containing the DHCP options.
      type: str
      returned: always
      sample: ocid1.vcn.oc1..example
    lifecycle_state:
      description: The current lifecycle state of the DHCP options.
      type: str
      returned: always
      sample: AVAILABLE
    options:
      description: >-
        The DHCP options, using the same C(option_type)/C(server_type)
        snake_case vocabulary accepted as input.
      type: list
      elements: dict
      returned: always
      sample:
        - option_type: domain_name_server
          server_type: vcn_local_plus_internet
        - option_type: search_domain
          search_domain_names:
            - example.oraclevcn.com
    domain_name_type:
      description: The domain name type used for the VCN.
      type: str
      returned: always
      sample: SUBNET_DOMAIN
    freeform_tags:
      description: Free-form tags applied to the DHCP options.
      type: dict
      returned: always
      sample: {"environment": "production"}
    defined_tags:
      description: Defined tags applied to the DHCP options.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
    time_created:
      description: The date and time the DHCP options were created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
  sample:
    id: ocid1.dhcpoptions.oc1..example
    name: example-dhcp-options
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    lifecycle_state: AVAILABLE
    options:
      - option_type: domain_name_server
        server_type: vcn_local_plus_internet
      - option_type: search_domain
        search_domain_names:
          - example.oraclevcn.com
    domain_name_type: SUBNET_DOMAIN
    freeform_tags: {"environment": "production"}
    defined_tags: {"Operations": {"CostCenter": "42"}}
    time_created: "2026-01-01T00:00:00.000Z"
"""

import json

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.oracle.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_AVAILABLE,
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
    "vcn_id",
    "name",
]
WAIT_FOR_DHCP_OPTIONS_STATES = [LIFECYCLE_AVAILABLE]

# Ansible-facing option_type/server_type values are snake_case, matching this
# collection's convention for choices. OCI's own API uses PascalCase-ish
# enum strings for these same fields (DhcpDnsOption.type/server_type,
# DhcpSearchDomainOption.type), so every value crossing the module/SDK
# boundary is translated explicitly instead of exposing OCI's native casing
# to callers.
OPTION_TYPE_DNS = "domain_name_server"
OPTION_TYPE_SEARCH_DOMAIN = "search_domain"

OPTION_TYPE_TO_OCI = {
    OPTION_TYPE_DNS: "DomainNameServer",
    OPTION_TYPE_SEARCH_DOMAIN: "SearchDomain",
}
OCI_OPTION_TYPE_TO_ANSIBLE = {
    oci_value: ansible_value for ansible_value, oci_value in OPTION_TYPE_TO_OCI.items()
}

SERVER_TYPE_TO_OCI = {
    "vcn_local": "VcnLocal",
    "vcn_local_plus_internet": "VcnLocalPlusInternet",
    "custom_dns_server": "CustomDnsServer",
}
OCI_SERVER_TYPE_TO_ANSIBLE = {
    oci_value: ansible_value for ansible_value, oci_value in SERVER_TYPE_TO_OCI.items()
}

DOMAIN_NAME_TYPE_TO_OCI = {
    "subnet_domain": "SUBNET_DOMAIN",
    "vcn_domain": "VCN_DOMAIN",
    "custom_domain": "CUSTOM_DOMAIN",
}
OCI_DOMAIN_NAME_TYPE_TO_ANSIBLE = {
    oci_value: ansible_value for ansible_value, oci_value in DOMAIN_NAME_TYPE_TO_OCI.items()
}


def _normalize_option(option):
    """Normalize one ansible-facing option dict for order-insensitive comparison."""
    normalized = {"option_type": option.get("option_type")}
    if option.get("option_type") == OPTION_TYPE_DNS:
        normalized["server_type"] = option.get("server_type")
        normalized["custom_dns_servers"] = sorted(option.get("custom_dns_servers") or [])
    else:
        normalized["search_domain_names"] = sorted(option.get("search_domain_names") or [])
    return normalized


def _normalize_current_option(option):
    """Normalize one serialized OCI DhcpOption dict (keyed by ``type``).

    Raises ``ValueError`` for a ``type`` this module does not recognize,
    instead of silently guessing a subtype, so an OCI API addition surfaces
    as a clear failure rather than a misclassified comparison.
    """
    oci_type = option.get("type")
    if oci_type not in OCI_OPTION_TYPE_TO_ANSIBLE:
        raise ValueError(
            f"Unsupported DHCP option type returned by OCI: {oci_type!r}"
        )
    option_type = OCI_OPTION_TYPE_TO_ANSIBLE[oci_type]
    if option_type == OPTION_TYPE_DNS:
        return {
            "option_type": OPTION_TYPE_DNS,
            "server_type": OCI_SERVER_TYPE_TO_ANSIBLE.get(
                option.get("server_type"), option.get("server_type")
            ),
            "custom_dns_servers": sorted(option.get("custom_dns_servers") or []),
        }
    return {
        "option_type": OPTION_TYPE_SEARCH_DOMAIN,
        "search_domain_names": sorted(option.get("search_domain_names") or []),
    }


def _normalized_options(options):
    return [_normalize_option(option) for option in (options or [])]


def _normalized_current_options(options):
    return [_normalize_current_option(option) for option in (options or [])]


def _options_sort_key(normalized_options):
    return sorted(json.dumps(option, sort_keys=True) for option in normalized_options)


def normalize_result_option(option):
    """Translate one serialized DhcpOption dict to the ansible-facing shape.

    OCI's raw API response uses a ``type`` key with PascalCase-ish enum
    values (``DomainNameServer``/``SearchDomain``/``VcnLocal``/etc). This
    renames ``type`` to ``option_type`` and translates both ``option_type``
    and ``server_type`` to the same snake_case vocabulary accepted as module
    input, so a returned resource reads the same way it was written -
    round-tripping the value straight back into the module works unchanged.
    """
    if not isinstance(option, dict):
        return option

    normalized = dict(option)
    oci_type = normalized.pop("type", None)
    normalized["option_type"] = OCI_OPTION_TYPE_TO_ANSIBLE.get(oci_type, oci_type)
    if "server_type" in normalized:
        normalized["server_type"] = OCI_SERVER_TYPE_TO_ANSIBLE.get(
            normalized["server_type"], normalized["server_type"]
        )
    return normalized


def normalize_result_options(options):
    return [normalize_result_option(option) for option in (options or [])]


def build_option_models(options):
    """Build the OCI SDK DhcpOption model list from the ansible options value."""
    models = []
    for option in options or []:
        if option.get("option_type") == OPTION_TYPE_DNS:
            server_type = option.get("server_type")
            models.append(
                oci.core.models.DhcpDnsOption(
                    server_type=SERVER_TYPE_TO_OCI.get(server_type, server_type),
                    custom_dns_servers=option.get("custom_dns_servers"),
                )
            )
        else:
            models.append(
                oci.core.models.DhcpSearchDomainOption(
                    search_domain_names=option.get("search_domain_names"),
                )
            )
    return models


def build_create_dhcp_options_details(params):
    domain_name_type = params.get("domain_name_type")
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "vcn_id": params.get("vcn_id"),
            "display_name": params.get("name"),
            "domain_name_type": DOMAIN_NAME_TYPE_TO_OCI.get(
                domain_name_type, domain_name_type
            ),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    options = params.get("options")
    if options:
        details["options"] = build_option_models(options)
    return oci.core.models.CreateDhcpDetails(**details)


class OciDhcpOptionsModule(OciResourceBase):
    """Concrete resource adapter for OCI VCN DHCP options."""

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    resource_id_param = "dhcp_options_id"
    list_resource_method = "list_dhcp_options"
    list_filter_params = ["vcn_id"]
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "DHCP options"
    update_wait_states = WAIT_FOR_DHCP_OPTIONS_STATES
    update_field_specs = [
        {
            "param_name": "name",
            "resource_field": "display_name",
            "update_field": "display_name",
            "is_mutable": True,
        },
        {
            "param_name": "domain_name_type",
            "resource_field": "domain_name_type",
            "is_mutable": True,
            "strategy": "plan_domain_name_type_strategy",
        },
        {
            "param_name": "options",
            "resource_field": "options",
            "is_mutable": True,
            "strategy": "plan_options_strategy",
        },
        {
            "param_name": "vcn_id",
            "resource_field": "vcn_id",
            "is_mutable": False,
        },
        {
            "param_name": "compartment_id",
            "resource_field": "compartment_id",
            "is_mutable": False,
        },
    ]

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_dhcp_options,
            dhcp_id=resource_id,
        )

    def create_resource(self):
        response = self.call_with_retry(
            self.client.create_dhcp_options,
            create_dhcp_details=build_create_dhcp_options_details(self.module.params),
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_DHCP_OPTIONS_STATES,
        )

    def plan_options_strategy(self, resource, resource_dict, spec, desired_value):
        try:
            current_options = _normalized_current_options(resource_dict.get("options"))
        except ValueError as exc:
            self.module.fail_json(
                msg=(
                    f"Cannot compare options for DHCP options {getattr(resource, 'id', None)}: "
                    f"{exc}"
                )
            )
        desired_options = _normalized_options(desired_value)
        if _options_sort_key(current_options) == _options_sort_key(desired_options):
            return []
        return [("replace", desired_value or [])]

    def plan_domain_name_type_strategy(self, resource, resource_dict, spec, desired_value):
        desired_oci_value = DOMAIN_NAME_TYPE_TO_OCI.get(desired_value, desired_value)
        if resource_dict.get("domain_name_type") == desired_oci_value:
            return []
        return [("replace", desired_oci_value)]

    def build_update_details(self, update_model_fields):
        return oci.core.models.UpdateDhcpDetails(**update_model_fields)

    def update_resource(self, resource):
        update_plan = self.get_update_plan(resource)
        update_model_fields = dict(update_plan["update_model_fields"])

        for strategy_operation in update_plan["strategy_operations"]:
            param_name = strategy_operation["param_name"]
            for operation in strategy_operation["operations"]:
                if operation[0] != "replace":
                    continue
                if param_name == "options":
                    update_model_fields["options"] = build_option_models(operation[1])
                elif param_name == "domain_name_type":
                    update_model_fields["domain_name_type"] = operation[1]

        if not update_model_fields:
            return resource

        update_details = self.build_update_details(update_model_fields)
        response = self.call_with_retry(
            self.client.update_dhcp_options,
            dhcp_id=resource.id,
            update_dhcp_details=update_details,
        )
        return self.get_mutation_result(
            response.data,
            resource.id,
            self.update_wait_states,
        )

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_dhcp_options,
            dhcp_id=resource.id,
        )

    def serialize_result_resource(self, resource):
        result = super().serialize_result_resource(resource)
        if isinstance(result, dict):
            if "options" in result:
                result["options"] = normalize_result_options(result["options"])
            if "domain_name_type" in result:
                result["domain_name_type"] = OCI_DOMAIN_NAME_TYPE_TO_ANSIBLE.get(
                    result["domain_name_type"], result["domain_name_type"]
                )
        return result


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        dhcp_options_id=dict(type="str"),
        vcn_id=dict(type="str"),
        options=dict(
            type="list",
            elements="dict",
            options=dict(
                option_type=dict(
                    type="str",
                    required=True,
                    choices=[OPTION_TYPE_DNS, OPTION_TYPE_SEARCH_DOMAIN],
                ),
                server_type=dict(
                    type="str",
                    choices=list(SERVER_TYPE_TO_OCI),
                ),
                custom_dns_servers=dict(type="list", elements="str"),
                search_domain_names=dict(type="list", elements="str"),
            ),
        ),
        domain_name_type=dict(
            type="str",
            choices=list(DOMAIN_NAME_TYPE_TO_OCI),
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciDhcpOptionsModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
