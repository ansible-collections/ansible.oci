# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_network_security_group_rule
short_description: Manage a rule in an OCI Network Security Group
description:
  - Create, update, and delete a single rule in an OCI Network Security Group.
  - Use M(ansible.oci.oci_network_security_group) to create the Network Security
    Group that owns the rule.
  - Rules are matched by their Oracle-assigned identifier for updates and
    deletion. New rules are matched by their supplied properties so repeated
    create requests are idempotent.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  state:
    description:
      - The desired state of the Network Security Group rule.
    type: str
    choices: [present, absent]
    default: present
  network_security_group_id:
    description:
      - The OCID of the Network Security Group that owns the rule.
    type: str
    required: true
  security_rule_id:
    description:
      - The Oracle-assigned identifier of an existing rule.
      - Required for updates and deletion. Omit it when creating a rule.
    type: str
  direction:
    description:
      - Whether the rule applies to inbound or outbound traffic.
      - Required when creating a rule.
    type: str
    choices: [ingress, egress]
  protocol:
    description:
      - The transport protocol. Use C(all) or an IPv4 protocol number, such
        as C(1), C(6), C(17), or C(58).
      - Required when creating a rule.
      - refer to the IANA protocol numbers at https://www.iana.org/assignments/protocol-numbers
    type: str
  source:
    description:
      - The source CIDR, service CIDR, or Network Security Group OCID.
      - Required when creating an ingress rule.
    type: str
  source_type:
    description:
      - The type of value supplied in O(source).
      - Defaults to C(cidr_block) when creating an ingress rule.
    type: str
    choices: [cidr_block, service_cidr_block, network_security_group]
  destination:
    description:
      - The destination CIDR, service CIDR, or Network Security Group OCID.
      - Required when creating an egress rule.
    type: str
  destination_type:
    description:
      - The type of value supplied in O(destination).
      - Defaults to C(cidr_block) when creating an egress rule.
    type: str
    choices: [cidr_block, service_cidr_block, network_security_group]
  description:
    description:
      - An optional description for the rule.
    type: str
  is_stateless:
    description:
      - Whether the rule is stateless.
      - Defaults to C(false) when creating a rule.
    type: bool
  tcp_options:
    description:
      - TCP source and destination port constraints.
    type: dict
    suboptions:
      source_port_min:
        description: The minimum source port.
        type: int
      source_port_max:
        description: The maximum source port.
        type: int
      destination_port_min:
        description: The minimum destination port.
        type: int
      destination_port_max:
        description: The maximum destination port.
        type: int
  udp_options:
    description:
      - UDP source and destination port constraints.
    type: dict
    suboptions:
      source_port_min:
        description: The minimum source port.
        type: int
      source_port_max:
        description: The maximum source port.
        type: int
      destination_port_min:
        description: The minimum destination port.
        type: int
      destination_port_max:
        description: The maximum destination port.
        type: int
  icmp_options:
    description:
      - ICMP type and optional code constraints.
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
- name: Add an ingress SSH rule
  ansible.oci.oci_network_security_group_rule:
    network_security_group_id: ocid1.networksecuritygroup.oc1..example
    direction: ingress
    source: 10.0.0.0/16
    protocol: "6"
    tcp_options:
      destination_port_min: 22
      destination_port_max: 22
  register: ingress_rule

- name: Update the rule description
  ansible.oci.oci_network_security_group_rule:
    network_security_group_id: ocid1.networksecuritygroup.oc1..example
    security_rule_id: "04ABEC"
    description: Allow SSH from the application network

- name: Allow ingress traffic from another Network Security Group
  ansible.oci.oci_network_security_group_rule:
    network_security_group_id: ocid1.networksecuritygroup.oc1..example
    direction: ingress
    protocol: all
    source: ocid1.networksecuritygroup.oc1..peer
    source_type: network_security_group

- name: Delete the rule
  ansible.oci.oci_network_security_group_rule:
    state: absent
    network_security_group_id: ocid1.networksecuritygroup.oc1..example
    security_rule_id: "04ABEC"
"""

RETURN = r"""
resource:
  description: The Network Security Group rule.
  returned: when state is present
  type: dict
  contains:
    id:
      description: The Oracle-assigned rule identifier.
      type: str
      returned: always
    direction:
      description: The direction of the rule.
      type: str
      returned: always
    protocol:
      description: The IP protocol used by the rule.
      type: str
      returned: always
    source:
      description: The source used by an ingress rule.
      type: str
      returned: when direction is ingress
    source_type:
      description: The source value type.
      type: str
      returned: when direction is ingress
    destination:
      description: The destination used by an egress rule.
      type: str
      returned: when direction is egress
    destination_type:
      description: The destination value type.
      type: str
      returned: when direction is egress
    description:
      description: The rule description.
      type: str
      returned: always
    is_stateless:
      description: Whether the rule is stateless.
      type: bool
      returned: always
    is_valid:
      description: Whether referenced resources make the rule valid.
      type: bool
      returned: always
    time_created:
      description: The date and time when the rule was created.
      type: str
      returned: always
    tcp_options:
      description: TCP options configured on the rule.
      type: dict
      returned: when configured
    udp_options:
      description: UDP options configured on the rule.
      type: dict
      returned: when configured
    icmp_options:
      description: ICMP options configured on the rule.
      type: dict
      returned: when configured
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    filter_none_values,
    import_oci_sdk,
    serialize_oci_model,
    values_differ_as_subset,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]

DIRECTION_TO_OCI = {
    "ingress": "INGRESS",
    "egress": "EGRESS",
}
RULE_VALUE_TYPE_TO_OCI = {
    "cidr_block": "CIDR_BLOCK",
    "service_cidr_block": "SERVICE_CIDR_BLOCK",
    "network_security_group": "NETWORK_SECURITY_GROUP",
}
RULE_CHOICE_TO_OCI = {
    "direction": DIRECTION_TO_OCI,
    "source_type": RULE_VALUE_TYPE_TO_OCI,
    "destination_type": RULE_VALUE_TYPE_TO_OCI,
}
RULE_FIELDS = (
    "description",
    "destination",
    "destination_type",
    "direction",
    "is_stateless",
    "protocol",
    "source",
    "source_type",
)
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


def _port_range_from_user(options, prefix):
    min_value = options.get(f"{prefix}_min")
    max_value = options.get(f"{prefix}_max")
    if min_value is None and max_value is None:
        return None
    return {"min": min_value, "max": max_value}


def _protocol_options_from_user(options):
    if options is None:
        return None
    source_range = _port_range_from_user(options, "source_port")
    destination_range = _port_range_from_user(options, "destination_port")
    if source_range is None and destination_range is None:
        return None
    return {
        "source_port_range": source_range,
        "destination_port_range": destination_range,
    }


def _icmp_options_from_user(options):
    if options is None:
        return None
    return filter_none_values({"type": options.get("type"), "code": options.get("code")})


def normalize_rule_params(params, apply_create_defaults=False):
    normalized = filter_none_values(
        {field: params.get(field) for field in RULE_FIELDS}
    )
    for field_name, value_map in RULE_CHOICE_TO_OCI.items():
        value = normalized.get(field_name)
        if value is not None:
            normalized[field_name] = value_map.get(value, value)
    normalized["tcp_options"] = _protocol_options_from_user(
        params.get("tcp_options")
    )
    normalized["udp_options"] = _protocol_options_from_user(
        params.get("udp_options")
    )
    normalized["icmp_options"] = _icmp_options_from_user(
        params.get("icmp_options")
    )
    normalized = filter_none_values(normalized)

    if apply_create_defaults:
        normalized.setdefault("is_stateless", False)
        if normalized.get("direction") == "INGRESS":
            normalized.setdefault("source_type", "CIDR_BLOCK")
        elif normalized.get("direction") == "EGRESS":
            normalized.setdefault("destination_type", "CIDR_BLOCK")
    return normalized


def normalize_rule_resource(resource):
    resource_dict = serialize_oci_model(resource)
    normalized = filter_none_values(
        {field: resource_dict.get(field) for field in RULE_FIELDS}
    )
    for options_field in ("tcp_options", "udp_options", "icmp_options"):
        options = resource_dict.get(options_field)
        if options is not None:
            normalized[options_field] = options
    return normalized


def _build_port_range(port_range):
    if port_range is None:
        return None
    return oci.core.models.PortRange(**port_range)


def _build_protocol_options(model_class, options):
    if options is None:
        return None
    return model_class(
        source_port_range=_build_port_range(options.get("source_port_range")),
        destination_port_range=_build_port_range(
            options.get("destination_port_range")
        ),
    )


def build_security_rule_model(model_class, normalized, security_rule_id=None):
    model_fields = dict(normalized)
    tcp_options = model_fields.pop("tcp_options", None)
    udp_options = model_fields.pop("udp_options", None)
    icmp_options = model_fields.pop("icmp_options", None)
    if security_rule_id is not None:
        model_fields["id"] = security_rule_id
    if tcp_options is not None:
        model_fields["tcp_options"] = _build_protocol_options(
            oci.core.models.TcpOptions,
            tcp_options,
        )
    if udp_options is not None:
        model_fields["udp_options"] = _build_protocol_options(
            oci.core.models.UdpOptions,
            udp_options,
        )
    if icmp_options is not None:
        model_fields["icmp_options"] = oci.core.models.IcmpOptions(**icmp_options)
    return model_class(**model_fields)


class OciNetworkSecurityGroupRuleModule(OciResourceBase):
    """Manage one rule through OCI's bulk NSG rule endpoints."""

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    resource_id_param = "security_rule_id"
    name_lookup_param = None
    common_update_field_specs = ()
    create_required_fields = ("direction", "protocol")
    create_resource_name = "Network Security Group rule"
    update_field_specs = (
        UpdateFieldSpec(param_name="description", is_mutable=True),
        UpdateFieldSpec(param_name="is_stateless", is_mutable=True),
        UpdateFieldSpec(param_name="protocol", is_mutable=True),
        UpdateFieldSpec(param_name="source", is_mutable=True),
        UpdateFieldSpec(param_name="destination", is_mutable=True),
        UpdateFieldSpec(
            param_name="direction",
            is_mutable=True,
            strategy="plan_choice_field_strategy",
        ),
        UpdateFieldSpec(
            param_name="source_type",
            is_mutable=True,
            strategy="plan_choice_field_strategy",
        ),
        UpdateFieldSpec(
            param_name="destination_type",
            is_mutable=True,
            strategy="plan_choice_field_strategy",
        ),
        UpdateFieldSpec(
            param_name="tcp_options",
            is_mutable=True,
            strategy="plan_rule_options_strategy",
        ),
        UpdateFieldSpec(
            param_name="udp_options",
            is_mutable=True,
            strategy="plan_rule_options_strategy",
        ),
        UpdateFieldSpec(
            param_name="icmp_options",
            is_mutable=True,
            strategy="plan_rule_options_strategy",
        ),
    )

    def list_security_rules(self):
        return self.list_all_resources(
            self.client.list_network_security_group_security_rules,
            network_security_group_id=self.module.params[
                "network_security_group_id"
            ],
        )

    def find_rule_by_id(self, security_rules, security_rule_id):
        return next(
            (
                rule
                for rule in security_rules
                if getattr(rule, "id", None) == security_rule_id
            ),
            None,
        )

    def find_matching_rule(self, security_rules, desired_rule):
        for security_rule in security_rules:
            if not values_differ_as_subset(
                serialize_oci_model(security_rule),
                desired_rule,
            ):
                return security_rule
        return None

    def get_resource_response(self, resource_id):
        resource = self.find_rule_by_id(self.list_security_rules(), resource_id)
        return oci.response.Response(200, {}, resource, None)

    def resolve_target_resource(self):
        if self.resource_id:
            return self.get_resource_by_id(self.resource_id)

        self.validate_create_request()
        desired_rule = normalize_rule_params(
            self.module.params,
            apply_create_defaults=True,
        )
        return self.find_matching_rule(
            self.list_security_rules(),
            desired_rule,
        )

    def validate_create_request(self):
        self._require_create_fields()
        params = self.module.params
        missing = []
        if params.get("direction") == "ingress" and params.get("source") is None:
            missing.append("source")
        if (
            params.get("direction") == "egress"
            and params.get("destination") is None
        ):
            missing.append("destination")
        if missing:
            self.module.fail_json(
                msg=(
                    "Creating a Network Security Group rule requires the "
                    f"following parameters: {', '.join(missing)}"
                )
            )

    def validate_effective_rule(self, current_rule, desired_fields):
        effective_rule = dict(serialize_oci_model(current_rule))
        effective_rule.update(desired_fields)
        direction = effective_rule.get("direction")
        if direction == "INGRESS" and not effective_rule.get("source"):
            self.module.fail_json(
                msg="An ingress Network Security Group rule requires source"
            )
        if direction == "EGRESS" and not effective_rule.get("destination"):
            self.module.fail_json(
                msg="An egress Network Security Group rule requires destination"
            )

    def rule_from_mutation_response(self, response, operation):
        security_rules = getattr(response.data, "security_rules", None) or []
        if not security_rules:
            self.module.fail_json(
                msg=f"OCI returned no rule after the {operation} operation"
            )
        return security_rules[0]

    def create_resource(self):
        desired_rule = normalize_rule_params(
            self.module.params,
            apply_create_defaults=True,
        )
        add_details = oci.core.models.AddNetworkSecurityGroupSecurityRulesDetails(
            security_rules=[
                build_security_rule_model(
                    oci.core.models.AddSecurityRuleDetails,
                    desired_rule,
                )
            ]
        )
        response = self.call_with_retry(
            self.client.add_network_security_group_security_rules,
            network_security_group_id=self.module.params[
                "network_security_group_id"
            ],
            add_network_security_group_security_rules_details=add_details,
        )
        return self.rule_from_mutation_response(response, "add")

    def plan_choice_field_strategy(
        self,
        resource,
        resource_dict,
        spec,
        desired_value,
    ):
        desired_oci_value = RULE_CHOICE_TO_OCI[spec.param_name].get(
            desired_value,
            desired_value,
        )
        if resource_dict.get(spec.param_name) == desired_oci_value:
            return []
        return [("replace", desired_oci_value)]

    def plan_rule_options_strategy(
        self,
        resource,
        resource_dict,
        spec,
        desired_value,
    ):
        if spec.param_name == "icmp_options":
            desired_options = _icmp_options_from_user(desired_value)
        else:
            desired_options = _protocol_options_from_user(desired_value)
        if not values_differ_as_subset(
            resource_dict.get(spec.param_name),
            desired_options,
        ):
            return []
        return [("replace", desired_options)]

    def get_planned_update_fields(self, update_plan):
        update_fields = dict(update_plan["update_model_fields"])
        for strategy_operation in update_plan["strategy_operations"]:
            operations = strategy_operation["operations"]
            if operations and operations[0][0] == "replace":
                update_fields[strategy_operation["param_name"]] = operations[0][1]
        return update_fields

    def needs_update(self, resource):
        update_plan = self.get_update_plan(resource)
        if not update_plan["update_needed"]:
            return False
        self.validate_effective_rule(
            resource,
            self.get_planned_update_fields(update_plan),
        )
        return True

    def update_resource(self, resource):
        update_fields = normalize_rule_resource(resource)
        update_fields.update(
            self.get_planned_update_fields(self.get_update_plan(resource))
        )
        if update_fields.get("direction") == "INGRESS":
            update_fields.pop("destination", None)
            update_fields.pop("destination_type", None)
        elif update_fields.get("direction") == "EGRESS":
            update_fields.pop("source", None)
            update_fields.pop("source_type", None)
        update_details = (
            oci.core.models.UpdateNetworkSecurityGroupSecurityRulesDetails(
                security_rules=[
                    build_security_rule_model(
                        oci.core.models.UpdateSecurityRuleDetails,
                        update_fields,
                        security_rule_id=resource.id,
                    )
                ]
            )
        )
        response = self.call_with_retry(
            self.client.update_network_security_group_security_rules,
            network_security_group_id=self.module.params[
                "network_security_group_id"
            ],
            update_network_security_group_security_rules_details=update_details,
        )
        return self.rule_from_mutation_response(response, "update")

    def delete_resource(self, resource):
        remove_details = (
            oci.core.models.RemoveNetworkSecurityGroupSecurityRulesDetails(
                security_rule_ids=[resource.id]
            )
        )
        self.call_with_retry(
            self.client.remove_network_security_group_security_rules,
            network_security_group_id=self.module.params[
                "network_security_group_id"
            ],
            remove_network_security_group_security_rules_details=remove_details,
        )

    def serialize_result_resource(self, resource):
        result = super().serialize_result_resource(resource)
        if not isinstance(result, dict):
            return result
        for field_name, value_map in RULE_CHOICE_TO_OCI.items():
            oci_to_ansible = {
                oci_value: ansible_value
                for ansible_value, oci_value in value_map.items()
            }
            value = result.get(field_name)
            if value is not None:
                result[field_name] = oci_to_ansible.get(value, value)
        return result


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        network_security_group_id=dict(type="str", required=True),
        security_rule_id=dict(type="str"),
        direction=dict(type="str", choices=list(DIRECTION_TO_OCI)),
        protocol=dict(type="str"),
        source=dict(type="str"),
        source_type=dict(type="str", choices=list(RULE_VALUE_TYPE_TO_OCI)),
        destination=dict(type="str"),
        destination_type=dict(type="str", choices=list(RULE_VALUE_TYPE_TO_OCI)),
        description=dict(type="str"),
        is_stateless=dict(type="bool"),
        tcp_options=dict(type="dict", options=dict(PORT_OPTIONS_SUBOPTIONS)),
        udp_options=dict(type="dict", options=dict(PORT_OPTIONS_SUBOPTIONS)),
        icmp_options=dict(type="dict", options=dict(ICMP_OPTIONS_SUBOPTIONS)),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[("state", "absent", ["security_rule_id"])],
    )

    OciNetworkSecurityGroupRuleModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
