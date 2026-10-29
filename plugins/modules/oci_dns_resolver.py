# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_dns_resolver
short_description: Update a DNS resolver in Oracle Cloud Infrastructure
description:
  - Update a DNS resolver by its OCID.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_wait_options
  - ansible.oci.oci_tags_options
options:
  resolver_id:
    description:
      - The OCID of the resolver to update.
    type: str
    required: true
  name:
    description:
      - The display name for the resolver.
    type: str
  attached_views:
    description:
      - The views to attach to the resolver.
      - This replaces the current attached view list.
    type: list
    elements: dict
    suboptions:
      view_id:
        description:
          - The OCID of the view to attach.
        type: str
        required: true
  forward_rules:
    description:
      - Forward rules to apply to the resolver.
      - This replaces the current resolver rules list.
      - Each rule must include C(destination_addresses) and C(source_endpoint_name).
      - The module sets the action to C(FORWARD).
    type: list
    elements: dict
    suboptions:
      destination_addresses:
        description:
          - The destination IP addresses for forwarding.
        type: list
        elements: str
        required: true
      source_endpoint_name:
        description:
          - The source endpoint name for the rule.
        type: str
        required: true
      client_address_conditions:
        description:
          - Client address conditions for the rule.
        type: list
        elements: str
      qname_cover_conditions:
        description:
          - DNS query name conditions for the rule.
        type: list
        elements: str
"""

EXAMPLES = r"""
- name: Update resolver settings
  ansible.oci.oci_dns_resolver:
    resolver_id: ocid1.dnsresolver.oc1..example
    name: production-resolver
    freeform_tags:
      environment: production
    attached_views:
      - view_id: ocid1.dnsview.oc1..example
    forward_rules:
      - destination_addresses:
          - 10.0.0.10
        source_endpoint_name: forward_endpoint
        qname_cover_conditions:
          - example.com
"""

RETURN = r"""
resource:
  description: The updated resolver.
  returned: always
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    OCI_TAG_ARGS,
    OCI_WAIT_ARGS,
    filter_none_values,
    import_oci_sdk,
    serialize_oci_model,
    values_differ_as_subset,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import LIFECYCLE_ACTIVE
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

oci = import_oci_sdk()[0]


def _canonical(value):
    """Return a stable form for comparing SDK models and input dictionaries.

    Args:
        value: An SDK model, mapping, sequence, or scalar value.

    Returns:
        A recursively normalized value.
    """
    if isinstance(value, dict):
        return {key: _canonical(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if hasattr(value, "swagger_types"):
        return _canonical(serialize_oci_model(value))
    return value


def build_resolver_update_details(params):
    """Build SDK update details from the supplied resolver fields.

    Args:
        params: Ansible module parameters.

    Returns:
        An OCI UpdateResolverDetails model.
    """
    fields = filter_none_values(
        {
            "display_name": params.get("name"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
            "attached_views": params.get("attached_views"),
            "rules": params.get("forward_rules"),
        }
    )
    if "attached_views" in fields:
        fields["attached_views"] = [
            oci.dns.models.AttachedViewDetails(**view)
            for view in fields["attached_views"]
        ]
    if "rules" in fields:
        fields["rules"] = [
            oci.dns.models.ResolverForwardRuleDetails(action="FORWARD", **rule)
            for rule in fields["rules"]
        ]
    return oci.dns.models.UpdateResolverDetails(**fields)


WAIT_FOR_RESOLVER_STATES = (LIFECYCLE_ACTIVE,)


class OciDnsResolverModule(OciResourceBase):
    """Update a DNS resolver by ID."""

    resource_id_param = "resolver_id"
    update_wait_states = WAIT_FOR_RESOLVER_STATES

    @property
    def update_field_specs(self):
        """Return the fields that the resolver update operation supports."""
        return (
            UpdateFieldSpec("name", resource_field="display_name", is_mutable=True),
            UpdateFieldSpec("attached_views", is_mutable=True),
            UpdateFieldSpec("forward_rules", is_mutable=True, resource_field="rules", update_field="rules"),
        )

    @property
    def client_class(self):
        return oci.dns.DnsClient

    def execute(self):
        """Fetch the resolver, predict or apply updates, and return its model.

        Returns:
            None. The method exits through Ansible's module result API.
        """
        resolver_id = self.module.params["resolver_id"]
        response = self.call_with_retry(self.client.get_resolver, resolver_id=resolver_id)
        current = response.data
        fields = {
            "display_name": self.module.params.get("name"),
            "freeform_tags": self.module.params.get("freeform_tags"),
            "defined_tags": self.module.params.get("defined_tags"),
            "attached_views": self.module.params.get("attached_views"),
            "rules": self.module.params.get("forward_rules"),
        }
        changed = False
        for field, desired in fields.items():
            if desired is None:
                continue
            current_value = _canonical(getattr(current, field, None))
            desired_value = desired
            if field == "rules":
                desired_value = [dict(rule, action="FORWARD") for rule in desired]
            if values_differ_as_subset(current_value, _canonical(desired_value)):
                changed = True
                break
        if changed and not self.module.check_mode:
            details = build_resolver_update_details(self.module.params)
            response = self.call_with_retry(
                self.client.update_resolver,
                resolver_id=resolver_id,
                update_resolver_details=details,
            )
            current = self.get_mutation_result(
                response.data,
                resolver_id,
                WAIT_FOR_RESOLVER_STATES,
            )
        self.module.exit_json(changed=changed, resource=self.serialize_result_resource(current))

    def create_resource(self):
        """Reject resource creation because OCI creates resolvers with VCNs."""
        raise NotImplementedError("DNS resolvers cannot be created by this module")

    def delete_resource(self, resource):
        """Reject deletion because this module only updates DNS resolvers."""
        raise NotImplementedError("DNS resolvers cannot be deleted by this module")

    def get_resource_response(self, resource_id):
        """Return the OCI response for the resolver wait helper.

        Args:
            resource_id: The resolver OCID.

        Returns:
            The OCI response wrapper for the resolver.
        """
        return self.call_with_retry(self.client.get_resolver, resolver_id=resource_id)


def main():
    """Run the resolver update module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_WAIT_ARGS,
        **OCI_TAG_ARGS,
        resolver_id=dict(type="str", required=True),
        name=dict(type="str"),
        attached_views=dict(type="list", elements="dict", options=dict(view_id=dict(type="str", required=True))),
        forward_rules=dict(
            type="list",
            elements="dict",
            options=dict(
                destination_addresses=dict(type="list", elements="str", required=True),
                source_endpoint_name=dict(type="str", required=True),
                client_address_conditions=dict(type="list", elements="str"),
                qname_cover_conditions=dict(type="list", elements="str"),
            ),
        ),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    OciDnsResolverModule(module).execute()


if __name__ == "__main__":
    main()
