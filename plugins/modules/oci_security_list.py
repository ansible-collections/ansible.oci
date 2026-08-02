# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_security_list
short_description: Manage a Security List resource in Oracle Cloud Infrastructure
description:
  - Create, update, and delete OCI security lists.
  - Uses the shared OCI helper layer for authentication, waiting, retry
    behavior, and result shaping.
  - Create requests must omit C(security_list_id). After create, capture the
    returned security list ID and use it for later C(state=present) and
    C(state=absent) tasks.
  - C(ingress_security_rules) and C(egress_security_rules) are each replaced
    in full on update. The module does not merge individual rules into the
    existing rule sets.
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
      - The desired lifecycle state of the security list.
    type: str
    choices: [present, absent]
    default: present
  security_list_id:
    description:
      - The OCID of the security list.
      - When provided, the module manages this exact security list.
      - Required to distinguish between multiple security lists that share
        the same scoped C(name).
    type: str
  name:
    description:
      - Human-readable name for the security list.
      - Required when creating a security list.
      - When C(security_list_id) is omitted, the module uses
        C(compartment_id + vcn_id + name) to find an existing security list.
      - If exactly one security list matches, C(state=present) manages it as
        the update target and C(state=absent) deletes it.
      - If more than one security list matches, the task fails and the caller
        must supply C(security_list_id).
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the security list.
      - Required when creating a security list.
      - Also scopes name-based security list lookups when
        C(security_list_id) is omitted.
    type: str
  vcn_id:
    description:
      - The OCID of the VCN containing the security list.
      - Required when creating a security list.
      - Also scopes name-based security list lookups when
        C(security_list_id) is omitted.
    type: str
  ingress_security_rules:
    description:
      - The full set of ingress rules for the security list.
      - Replaces the entire ingress rule set on update. Omit this to leave
        existing ingress rules untouched.
    type: list
    elements: dict
    suboptions:
      source:
        description:
          - A source CIDR block, OCI service C(cidr_block) label, or network
            security group OCID, depending on C(source_type).
        type: str
        required: true
      source_type:
        description:
          - The type of C(source).
        type: str
        choices: [CIDR_BLOCK, SERVICE_CIDR_BLOCK, NETWORK_SECURITY_GROUP]
        default: CIDR_BLOCK
      protocol:
        description:
          - The transport protocol, as a decimal IANA protocol number string
            (for example C("6") for TCP, C("17") for UDP, C("1") for ICMP),
            or C(all) for all protocols.
        type: str
        required: true
      is_stateless:
        description:
          - Whether the rule is stateless.
        type: bool
        default: false
      description:
        description:
          - An optional human-readable description of the rule.
        type: str
      tcp_options:
        description:
          - Optional TCP source and destination port range restrictions.
        type: dict
        suboptions:
          source_port_min:
            description: Minimum source port in the range.
            type: int
          source_port_max:
            description: Maximum source port in the range.
            type: int
          destination_port_min:
            description: Minimum destination port in the range.
            type: int
          destination_port_max:
            description: Maximum destination port in the range.
            type: int
      udp_options:
        description:
          - Optional UDP source and destination port range restrictions.
        type: dict
        suboptions:
          source_port_min:
            description: Minimum source port in the range.
            type: int
          source_port_max:
            description: Maximum source port in the range.
            type: int
          destination_port_min:
            description: Minimum destination port in the range.
            type: int
          destination_port_max:
            description: Maximum destination port in the range.
            type: int
      icmp_options:
        description:
          - Optional ICMP type and code restrictions.
        type: dict
        suboptions:
          type:
            description: The ICMP type.
            type: int
            required: true
          code:
            description: The ICMP code.
            type: int
  egress_security_rules:
    description:
      - The full set of egress rules for the security list.
      - Replaces the entire egress rule set on update. Omit this to leave
        existing egress rules untouched.
    type: list
    elements: dict
    suboptions:
      destination:
        description:
          - A destination CIDR block, OCI service C(cidr_block) label, or
            network security group OCID, depending on C(destination_type).
        type: str
        required: true
      destination_type:
        description:
          - The type of C(destination).
        type: str
        choices: [CIDR_BLOCK, SERVICE_CIDR_BLOCK, NETWORK_SECURITY_GROUP]
        default: CIDR_BLOCK
      protocol:
        description:
          - The transport protocol, as a decimal IANA protocol number string
            (for example C("6") for TCP, C("17") for UDP, C("1") for ICMP),
            or C(all) for all protocols.
        type: str
        required: true
      is_stateless:
        description:
          - Whether the rule is stateless.
        type: bool
        default: false
      description:
        description:
          - An optional human-readable description of the rule.
        type: str
      tcp_options:
        description:
          - Optional TCP source and destination port range restrictions.
        type: dict
        suboptions:
          source_port_min:
            description: Minimum source port in the range.
            type: int
          source_port_max:
            description: Maximum source port in the range.
            type: int
          destination_port_min:
            description: Minimum destination port in the range.
            type: int
          destination_port_max:
            description: Maximum destination port in the range.
            type: int
      udp_options:
        description:
          - Optional UDP source and destination port range restrictions.
        type: dict
        suboptions:
          source_port_min:
            description: Minimum source port in the range.
            type: int
          source_port_max:
            description: Maximum source port in the range.
            type: int
          destination_port_min:
            description: Minimum destination port in the range.
            type: int
          destination_port_max:
            description: Maximum destination port in the range.
            type: int
      icmp_options:
        description:
          - Optional ICMP type and code restrictions.
        type: dict
        suboptions:
          type:
            description: The ICMP type.
            type: int
            required: true
          code:
            description: The ICMP code.
            type: int
"""

EXAMPLES = r"""
- name: Create a security list allowing inbound SSH and all outbound traffic
  oracle.oci.oci_security_list:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-security-list
    ingress_security_rules:
      - source: 0.0.0.0/0
        protocol: "6"
        tcp_options:
          destination_port_min: 22
          destination_port_max: 22
    egress_security_rules:
      - destination: 0.0.0.0/0
        protocol: all
  register: created_security_list

- name: Replace the ingress rules on an existing security list
  oracle.oci.oci_security_list:
    state: present
    security_list_id: "{{ created_security_list.resource.id }}"
    ingress_security_rules:
      - source: 10.0.0.0/16
        protocol: "6"
        tcp_options:
          destination_port_min: 443
          destination_port_max: 443

- name: Delete the created security list
  oracle.oci.oci_security_list:
    state: absent
    security_list_id: "{{ created_security_list.resource.id }}"

- name: Delete a uniquely named security list without providing security_list_id
  oracle.oci.oci_security_list:
    state: absent
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-security-list
"""

RETURN = r"""
resource:
  description: The security list resource.
  returned: when state != absent
  type: dict
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
WAIT_FOR_SECURITY_LIST_STATES = [LIFECYCLE_AVAILABLE]

INGRESS_SCALAR_FIELDS = ("source", "source_type", "protocol", "description")
EGRESS_SCALAR_FIELDS = ("destination", "destination_type", "protocol", "description")

PORT_OPTIONS_SUBOPTIONS = dict(
    source_port_min=dict(type="int"),
    source_port_max=dict(type="int"),
    destination_port_min=dict(type="int"),
    destination_port_max=dict(type="int"),
)
ICMP_OPTIONS_SUBOPTIONS = dict(
    type=dict(type="int", required=True),
    code=dict(type="int"),
)


def _port_range_from_user(opts, prefix):
    min_value = opts.get(f"{prefix}_min")
    max_value = opts.get(f"{prefix}_max")
    if min_value is None and max_value is None:
        return None
    return {"min": min_value, "max": max_value}


def _protocol_options_from_user(opts):
    if opts is None:
        return None
    source_range = _port_range_from_user(opts, "source_port")
    destination_range = _port_range_from_user(opts, "destination_port")
    if source_range is None and destination_range is None:
        return None
    return {"source_port_range": source_range, "destination_port_range": destination_range}


def _protocol_options_from_resource(opts):
    if not opts:
        return None
    source_range = opts.get("source_port_range")
    destination_range = opts.get("destination_port_range")
    if not source_range and not destination_range:
        return None
    return {
        "source_port_range": (
            {"min": source_range.get("min"), "max": source_range.get("max")}
            if source_range
            else None
        ),
        "destination_port_range": (
            {"min": destination_range.get("min"), "max": destination_range.get("max")}
            if destination_range
            else None
        ),
    }


def _icmp_options_from_user(opts):
    if opts is None:
        return None
    return {"type": opts.get("type"), "code": opts.get("code")}


def _icmp_options_from_resource(opts):
    if not opts:
        return None
    return {"type": opts.get("type"), "code": opts.get("code")}


def _normalize_rule_from_user(rule, scalar_fields):
    normalized = {field: rule.get(field) for field in scalar_fields}
    normalized["is_stateless"] = bool(rule.get("is_stateless") or False)
    normalized["tcp_options"] = _protocol_options_from_user(rule.get("tcp_options"))
    normalized["udp_options"] = _protocol_options_from_user(rule.get("udp_options"))
    normalized["icmp_options"] = _icmp_options_from_user(rule.get("icmp_options"))
    return normalized


def _normalize_rule_from_resource(rule, scalar_fields):
    normalized = {field: rule.get(field) for field in scalar_fields}
    normalized["is_stateless"] = bool(rule.get("is_stateless") or False)
    normalized["tcp_options"] = _protocol_options_from_resource(rule.get("tcp_options"))
    normalized["udp_options"] = _protocol_options_from_resource(rule.get("udp_options"))
    normalized["icmp_options"] = _icmp_options_from_resource(rule.get("icmp_options"))
    return normalized


def _rules_sort_key(normalized_rules):
    return sorted(json.dumps(rule, sort_keys=True) for rule in normalized_rules)


def _build_port_range(port_range):
    if port_range is None:
        return None
    return oci.core.models.PortRange(min=port_range.get("min"), max=port_range.get("max"))


def _build_protocol_options(model_cls, normalized_options):
    if normalized_options is None:
        return None
    return model_cls(
        source_port_range=_build_port_range(normalized_options.get("source_port_range")),
        destination_port_range=_build_port_range(
            normalized_options.get("destination_port_range")
        ),
    )


def build_ingress_rule_model(rule):
    normalized = _normalize_rule_from_user(rule, INGRESS_SCALAR_FIELDS)
    icmp_options = normalized["icmp_options"]
    return oci.core.models.IngressSecurityRule(
        source=normalized["source"],
        source_type=normalized["source_type"],
        protocol=normalized["protocol"],
        is_stateless=normalized["is_stateless"],
        description=normalized["description"],
        tcp_options=_build_protocol_options(
            oci.core.models.TcpOptions, normalized["tcp_options"]
        ),
        udp_options=_build_protocol_options(
            oci.core.models.UdpOptions, normalized["udp_options"]
        ),
        icmp_options=(
            oci.core.models.IcmpOptions(**icmp_options) if icmp_options else None
        ),
    )


def build_egress_rule_model(rule):
    normalized = _normalize_rule_from_user(rule, EGRESS_SCALAR_FIELDS)
    icmp_options = normalized["icmp_options"]
    return oci.core.models.EgressSecurityRule(
        destination=normalized["destination"],
        destination_type=normalized["destination_type"],
        protocol=normalized["protocol"],
        is_stateless=normalized["is_stateless"],
        description=normalized["description"],
        tcp_options=_build_protocol_options(
            oci.core.models.TcpOptions, normalized["tcp_options"]
        ),
        udp_options=_build_protocol_options(
            oci.core.models.UdpOptions, normalized["udp_options"]
        ),
        icmp_options=(
            oci.core.models.IcmpOptions(**icmp_options) if icmp_options else None
        ),
    )


def build_create_security_list_details(params):
    ingress_security_rules = params.get("ingress_security_rules")
    egress_security_rules = params.get("egress_security_rules")
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "vcn_id": params.get("vcn_id"),
            "display_name": params.get("name"),
            "ingress_security_rules": (
                [build_ingress_rule_model(rule) for rule in ingress_security_rules]
                if ingress_security_rules is not None
                else None
            ),
            "egress_security_rules": (
                [build_egress_rule_model(rule) for rule in egress_security_rules]
                if egress_security_rules is not None
                else None
            ),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.core.models.CreateSecurityListDetails(**details)


class OciSecurityListModule(OciResourceBase):
    """Concrete resource adapter for OCI security lists."""

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    resource_id_param = "security_list_id"
    list_resource_method = "list_security_lists"
    list_filter_params = ("vcn_id",)
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "security list"
    update_field_specs = [
        {
            "param_name": "name",
            "resource_field": "display_name",
            "update_field": "display_name",
            "is_mutable": True,
        },
        {
            "param_name": "ingress_security_rules",
            "resource_field": "ingress_security_rules",
            "is_mutable": True,
            "strategy": "plan_ingress_rules_strategy",
        },
        {
            "param_name": "egress_security_rules",
            "resource_field": "egress_security_rules",
            "is_mutable": True,
            "strategy": "plan_egress_rules_strategy",
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
            self.client.get_security_list,
            security_list_id=resource_id,
        )

    def plan_ingress_rules_strategy(self, resource, resource_dict, spec, desired_value):
        return self._plan_rules_strategy(
            resource_dict.get("ingress_security_rules"),
            desired_value,
            INGRESS_SCALAR_FIELDS,
        )

    def plan_egress_rules_strategy(self, resource, resource_dict, spec, desired_value):
        return self._plan_rules_strategy(
            resource_dict.get("egress_security_rules"),
            desired_value,
            EGRESS_SCALAR_FIELDS,
        )

    def _plan_rules_strategy(self, current_rules, desired_rules, scalar_fields):
        normalized_current = [
            _normalize_rule_from_resource(rule, scalar_fields)
            for rule in (current_rules or [])
        ]
        normalized_desired = [
            _normalize_rule_from_user(rule, scalar_fields)
            for rule in (desired_rules or [])
        ]
        if _rules_sort_key(normalized_current) == _rules_sort_key(normalized_desired):
            return []
        return [("replace", desired_rules or [])]

    def create_resource(self):
        create_security_list_details = build_create_security_list_details(
            self.module.params
        )
        response = self.call_with_retry(
            self.client.create_security_list,
            create_security_list_details=create_security_list_details,
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_SECURITY_LIST_STATES,
        )

    def build_update_details(self, update_model_fields):
        return oci.core.models.UpdateSecurityListDetails(**update_model_fields)

    def update_resource(self, resource):
        update_plan = self.get_update_plan(resource)
        update_model_fields = dict(update_plan["update_model_fields"])

        for strategy_operation in update_plan["strategy_operations"]:
            if strategy_operation["param_name"] == "ingress_security_rules":
                operations = strategy_operation["operations"]
                if operations:
                    _, desired_rules = operations[0]
                    update_model_fields["ingress_security_rules"] = [
                        build_ingress_rule_model(rule) for rule in desired_rules
                    ]
            elif strategy_operation["param_name"] == "egress_security_rules":
                operations = strategy_operation["operations"]
                if operations:
                    _, desired_rules = operations[0]
                    update_model_fields["egress_security_rules"] = [
                        build_egress_rule_model(rule) for rule in desired_rules
                    ]

        if not update_model_fields:
            return resource

        update_details = self.build_update_details(update_model_fields)
        response = self.call_with_retry(
            self.client.update_security_list,
            security_list_id=resource.id,
            update_security_list_details=update_details,
        )
        return self.get_mutation_result(
            response.data,
            resource.id,
            WAIT_FOR_SECURITY_LIST_STATES,
        )

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_security_list,
            security_list_id=resource.id,
        )


def main():
    rule_common_suboptions = dict(
        protocol=dict(type="str", required=True),
        is_stateless=dict(type="bool", default=False),
        description=dict(type="str"),
        tcp_options=dict(type="dict", options=dict(PORT_OPTIONS_SUBOPTIONS)),
        udp_options=dict(type="dict", options=dict(PORT_OPTIONS_SUBOPTIONS)),
        icmp_options=dict(type="dict", options=dict(ICMP_OPTIONS_SUBOPTIONS)),
    )

    ingress_options = dict(
        source=dict(type="str", required=True),
        source_type=dict(
            type="str",
            choices=["CIDR_BLOCK", "SERVICE_CIDR_BLOCK", "NETWORK_SECURITY_GROUP"],
            default="CIDR_BLOCK",
        ),
    )
    ingress_options.update(rule_common_suboptions)

    egress_options = dict(
        destination=dict(type="str", required=True),
        destination_type=dict(
            type="str",
            choices=["CIDR_BLOCK", "SERVICE_CIDR_BLOCK", "NETWORK_SECURITY_GROUP"],
            default="CIDR_BLOCK",
        ),
    )
    egress_options.update(rule_common_suboptions)

    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        security_list_id=dict(type="str"),
        vcn_id=dict(type="str"),
        ingress_security_rules=dict(
            type="list",
            elements="dict",
            options=ingress_options,
        ),
        egress_security_rules=dict(
            type="list",
            elements="dict",
            options=egress_options,
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciSecurityListModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
