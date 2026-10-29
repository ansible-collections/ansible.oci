# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_dns_resolver_endpoint
short_description: Manage a DNS resolver endpoint in Oracle Cloud Infrastructure
description:
  - Create, update, and delete DNS resolver endpoints.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_wait_options
  - ansible.oci.oci_tags_options
options:
  state:
    description: The desired state of the endpoint.
    type: str
    choices: [present, absent]
    default: present
  resolver_id:
    description: The OCID of the DNS resolver that contains the endpoint.
    type: str
    required: true
  name:
    description:
      - The endpoint name within the resolver.
      - It must start with a letter or underscore and contain only letters, digits, and underscores.
      - This value identifies the endpoint for get, update, and delete calls.
    type: str
    required: true
  subnet_id:
    description: The OCID of the subnet for the endpoint VNIC. This field is create-only.
    type: str
  forwarding_address:
    description: The IPv4 address for forwarding DNS queries.
    type: str
  is_forwarding:
    description: Whether the endpoint forwards DNS queries.
    type: bool
  is_listening:
    description: Whether the endpoint listens for DNS queries.
    type: bool
  listening_address:
    description: The IPv4 address on which the endpoint listens.
    type: str
  nsg_ids:
    description: The network security group OCIDs for the endpoint VNIC.
    type: list
    elements: str
  security_attributes:
    description: Security attributes for the endpoint.
    type: dict
"""

EXAMPLES = r"""
- name: Create a resolver endpoint
  ansible.oci.oci_dns_resolver_endpoint:
    resolver_id: ocid1.dnsresolver.oc1..example
    name: example_endpoint
    subnet_id: ocid1.subnet.oc1..example
    is_listening: true
    nsg_ids:
      - ocid1.networksecuritygroup.oc1..example
"""

RETURN = r"""
resource:
  description: The resolver endpoint resource.
  returned: when state != absent
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    OCI_TAG_ARGS,
    OCI_WAIT_ARGS,
    filter_none_values,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

oci = import_oci_sdk()[0]

CREATE_REQUIRED_FIELDS = ("resolver_id", "name")


def build_create_details(params):
    """Build the SDK create model from supplied endpoint parameters.

    Args:
        params: The active Ansible module parameters.

    Returns:
        The OCI resolver VNIC endpoint create model.
    """
    fields = filter_none_values(
        {
            "name": params.get("name"),
            "forwarding_address": params.get("forwarding_address"),
            "is_forwarding": params.get("is_forwarding"),
            "is_listening": params.get("is_listening"),
            "listening_address": params.get("listening_address"),
            "subnet_id": params.get("subnet_id"),
            "nsg_ids": params.get("nsg_ids"),
            "security_attributes": params.get("security_attributes"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.dns.models.CreateResolverVnicEndpointDetails(**fields)


class OciDnsResolverEndpointModule(OciResourceBase):
    """Manage one endpoint in an OCI DNS resolver."""

    @property
    def client_class(self):
        """Return the OCI DNS service client class."""
        return oci.dns.DnsClient

    resource_id_param = None
    list_resource_method = None
    name_lookup_param = None
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "resolver endpoint"
    update_wait_states = ("ACTIVE",)
    update_field_specs = (
        UpdateFieldSpec(param_name="freeform_tags", is_mutable=True),
        UpdateFieldSpec(param_name="defined_tags", is_mutable=True),
        UpdateFieldSpec(param_name="nsg_ids", is_mutable=True, compare="sorted_list"),
        UpdateFieldSpec(param_name="security_attributes", is_mutable=True),
    )

    def resolve_target_resource(self):
        """Resolve the endpoint with its composite resolver ID and name.

        The inherited lookup uses one resource ID. Resolver endpoints require
        both the resolver ID and endpoint name, so this method must override it.

        Returns:
            The endpoint model, or None when OCI returns 404.
        """
        return self.get_resource_by_id(self.module.params.get("name"))

    def get_resource_response(self, resource_id):
        """Return the SDK response for the endpoint name used by this task.

        Args:
            resource_id: The endpoint name used by the resource base class.

        Returns:
            The OCI SDK response wrapper.
        """
        return self.call_with_retry(
            self.client.get_resolver_endpoint,
            resolver_id=self.module.params.get("resolver_id"),
            resolver_endpoint_name=resource_id,
        )

    def create_resource(self):
        """Create the endpoint and return its SDK model.

        Returns:
            The created endpoint model.
        """
        response = self.call_with_retry(
            self.client.create_resolver_endpoint,
            resolver_id=self.module.params.get("resolver_id"),
            create_resolver_endpoint_details=build_create_details(self.module.params),
        )
        return self.get_mutation_result(
            response.data,
            self.module.params.get("name"),
            self.update_wait_states,
        )

    def build_update_details(self, update_model_fields):
        """Build the SDK update model from fields that need changes.

        Args:
            update_model_fields: The desired SDK model fields.

        Returns:
            The OCI resolver VNIC endpoint update model.
        """
        return oci.dns.models.UpdateResolverVnicEndpointDetails(**update_model_fields)

    def update_resource(self, resource):
        """Update mutable endpoint fields by resolver ID and endpoint name.

        The inherited update call accepts one resource ID. The endpoint API
        requires resolver ID and endpoint name, so this method must override it.

        Args:
            resource: The current endpoint model.

        Returns:
            The updated endpoint model.
        """
        fields = self.get_update_plan(resource)["update_model_fields"]
        if not fields:
            return resource
        response = self.call_with_retry(
            self.client.update_resolver_endpoint,
            resolver_id=self.module.params.get("resolver_id"),
            resolver_endpoint_name=self.module.params.get("name"),
            update_resolver_endpoint_details=self.build_update_details(fields),
        )
        return self.get_mutation_result(
            response.data,
            self.module.params.get("name"),
            self.update_wait_states,
        )

    def delete_resource(self, resource):
        """Delete the endpoint by resolver ID and endpoint name.

        The inherited delete call accepts one resource ID. The endpoint API
        requires resolver ID and endpoint name, so this method must override it.

        Args:
            resource: The endpoint model to delete.

        Returns:
            The deletion response data.
        """
        response = self.call_delete_fn(
            resource,
            self.client.delete_resolver_endpoint,
            resolver_id=self.module.params.get("resolver_id"),
            resolver_endpoint_name=self.module.params.get("name"),
        )
        if not self.module.params.get("wait", True):
            return response.data
        return self.wait_for_resource_id(
            self.module.params.get("name"),
            tuple(self.dead_states),
        )


def main():
    """Run the resolver endpoint resource module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_TAG_ARGS,
        **OCI_WAIT_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        resolver_id=dict(type="str", required=True),
        name=dict(type="str", required=True),
        subnet_id=dict(type="str"),
        forwarding_address=dict(type="str"),
        is_forwarding=dict(type="bool"),
        is_listening=dict(type="bool"),
        listening_address=dict(type="str"),
        nsg_ids=dict(type="list", elements="str"),
        security_attributes=dict(type="dict"),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    OciDnsResolverEndpointModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
