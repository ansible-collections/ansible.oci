# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_loadbalancer_listener
short_description: Manage a Load Balancer listener in Oracle Cloud Infrastructure
description:
  - Create, update, or delete a listener on an OCI Load Balancer.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_wait_options
options:
  wait:
    description:
      - Whether to wait for the OCI work request to complete before returning.
      - When false, the module reads the listener once after the operation. If OCI has not exposed the listener yet, C(resource) contains only its C(name).
    type: bool
    default: true
  state:
    description:
      - The desired listener state.
    type: str
    choices: [present, absent]
    default: present
  load_balancer_id:
    description:
      - OCID of the Load Balancer that contains the listener.
    type: str
    required: true
  name:
    description:
      - Unique listener name. OCI does not allow this name to be changed.
    type: str
    required: true
  default_backend_set_name:
    description:
      - Name of the listener's backend set.
      - Required when creating a listener. If supplied for an existing listener, it is reconciled.
    type: str
  port:
    description:
      - Port on which the listener accepts connections.
      - Required when creating a listener. If supplied for an existing listener, it is reconciled.
    type: int
  protocol:
    description:
      - Protocol accepted by the listener, one of C(http), C(http2), C(grpc), or C(tcp).
      - Use C(http) with C(ssl_configuration) to enable HTTPS, as in the OCI Console.
      - C(http2) and C(grpc) require C(ssl_configuration).
      - Required when creating a listener. If supplied for an existing listener, it is reconciled.
    type: str
    choices: [http, http2, grpc, tcp]
  hostname_names:
    description:
      - Names of the hostnames associated with the listener.
    type: list
    elements: str
  path_route_set_name:
    description:
      - Name of the path route set for this listener. OCI deprecates path route sets in favor of routing policies.
    type: str
  routing_policy_name:
    description:
      - Name of the routing policy applied to this listener.
    type: str
  ssl_configuration:
    description:
      - SSL settings for the listener. Supplied fields are merged with current settings during updates.
    type: dict
    suboptions:
      verify_depth:
        description: Maximum peer certificate chain verification depth.
        type: int
      verify_peer_certificate:
        description: Whether to verify peer certificates.
        type: bool
      trusted_certificate_authority_ids:
        description: OCIDs of trusted certificate authorities or CA bundles.
        type: list
        elements: str
      certificate_ids:
        description: Certificate OCIDs. OCI currently accepts one certificate OCID.
        type: list
        elements: str
      certificate_name:
        description: Friendly name of the certificate bundle. OCI does not allow the name to be changed.
        type: str
      protocols:
        description:
          - SSL/TLS protocols for listener connections.
          - Use OCI spelling, for example C(TLSv1.2). The module passes values unchanged to OCI.
          - OCI validates supported versions.
            See U(https://docs.oracle.com/en-us/iaas/tools/python/latest/api/load_balancer/models/oci.load_balancer.models.SSLConfigurationDetails.html).
          - On creation, OCI defaults to C(TLSv1.2) when omitted.
          - During updates, omitted protocols stay unchanged.
        type: list
        elements: str
      cipher_suite_name:
        description: Cipher suite used for HTTPS or SSL connections.
        type: str
      server_order_preference:
        description: Whether server ciphers take precedence over client ciphers.
        type: str
        choices: [enabled, disabled]
  connection_configuration:
    description:
      - Connection settings for the listener. Supplied fields are merged with current settings during updates.
    type: dict
    suboptions:
      idle_timeout:
        description: Maximum idle time, in seconds, between client and backend traffic.
        type: int
        required: true
      backend_tcp_proxy_protocol_version:
        description: Backend TCP Proxy Protocol version.
        type: int
  rule_set_names:
    description:
      - Names of rule sets applied to the listener.
    type: list
    elements: str
"""

EXAMPLES = r"""
- name: Create a TCP listener
  ansible.oci.oci_loadbalancer_listener:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    name: tcp-listener
    default_backend_set_name: app-backends
    port: 8080
    protocol: tcp

- name: Change a listener port
  ansible.oci.oci_loadbalancer_listener:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    name: tcp-listener
    port: 8081

- name: Delete a listener
  ansible.oci.oci_loadbalancer_listener:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    name: tcp-listener
    state: absent
"""

RETURN = r"""
resource:
  description:
    - The listener after a create or update.
    - When C(wait=false), this is an immediate snapshot and can contain only C(name) until OCI exposes the listener.
  returned: when state=present and the listener is found or a mutation completes
  type: dict
  contains:
    name:
      description: Listener name.
      type: str
      returned: always
    default_backend_set_name:
      description: Associated backend set name.
      type: str
      returned: when available from OCI
    port:
      description: Listener port.
      type: int
      returned: when available from OCI
    protocol:
      description: Listener protocol.
      type: str
      returned: when available from OCI
    hostname_names:
      description: Associated hostnames.
      type: list
      elements: str
      returned: when configured and available from OCI
    path_route_set_name:
      description: Associated path route set name.
      type: str
      returned: when configured and available from OCI
    routing_policy_name:
      description: Associated routing policy name.
      type: str
      returned: when configured and available from OCI
    ssl_configuration:
      description: Listener SSL settings.
      type: dict
      returned: when configured and available from OCI
    connection_configuration:
      description: Listener connection settings.
      type: dict
      returned: when configured and available from OCI
    rule_set_names:
      description: Names of applied rule sets.
      type: list
      elements: str
      returned: when configured and available from OCI
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    OCI_WAIT_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_loadbalancer import (
    OciLoadBalancerSubresourceBase,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    UpdateFieldSpec,
)
oci = import_oci_sdk()[0]


class OciLoadBalancerListenerModule(OciLoadBalancerSubresourceBase):
    """Manage one listener under a scoped Load Balancer."""

    create_model_name = "CreateListenerDetails"
    create_method_name = "create_listener_and_wait_for_state"
    create_details_name = "create_listener_details"
    update_model_name = "UpdateListenerDetails"
    update_method_name = "update_listener_and_wait_for_state"
    update_details_name = "update_listener_details"
    delete_method_name = "delete_listener_and_wait_for_state"
    create_resource_name = "listener"
    create_required_fields = (
        "default_backend_set_name",
        "port",
        "protocol",
    )

    update_field_specs = (
        UpdateFieldSpec(param_name="default_backend_set_name", is_mutable=True),
        UpdateFieldSpec(param_name="port", is_mutable=True),
        UpdateFieldSpec(
            param_name="protocol", is_mutable=True, strategy="plan_enum_update"
        ),
        UpdateFieldSpec(
            param_name="hostname_names",
            is_mutable=True,
            compare="sorted_list",
        ),
        UpdateFieldSpec(param_name="path_route_set_name", is_mutable=True),
        UpdateFieldSpec(param_name="routing_policy_name", is_mutable=True),
        UpdateFieldSpec(
            param_name="ssl_configuration",
            is_mutable=True,
            compare="subset_dict",
        ),
        UpdateFieldSpec(
            param_name="connection_configuration",
            is_mutable=True,
            compare="subset_dict",
        ),
        UpdateFieldSpec(
            param_name="rule_set_names",
            is_mutable=True,
            compare="sorted_list",
        ),
    )

    def get_resource_response(self, resource_id):
        """Fetch the named listener.

        Args:
            resource_id: Listener name.

        Returns:
            The SDK response; data is None for a missing listener.
        """
        response = self.call_with_retry(
            self.client.get_load_balancer,
            load_balancer_id=self.module.params["load_balancer_id"],
        )
        listeners = getattr(response.data, "listeners", None) or {}
        return oci.response.Response(200, {}, listeners.get(resource_id), None)

    def mutation_kwargs(self, operation):
        """Build scoped arguments for a resource mutation.

        Args:
            operation: Create, update, or delete operation.

        Returns:
            The SDK keyword arguments.
        """
        kwargs = super(OciLoadBalancerListenerModule, self).mutation_kwargs(operation)
        if operation in ("update", "delete"):
            kwargs["listener_name"] = self.resource_name
        return kwargs


def main():
    """Initialize and run the listener module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_WAIT_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        load_balancer_id=dict(type="str", required=True),
        name=dict(type="str", required=True),
        default_backend_set_name=dict(type="str"),
        port=dict(type="int"),
        protocol=dict(type="str", choices=["http", "http2", "grpc", "tcp"]),
        hostname_names=dict(type="list", elements="str"),
        path_route_set_name=dict(type="str"),
        routing_policy_name=dict(type="str"),
        ssl_configuration=dict(
            type="dict",
            options=dict(
                verify_depth=dict(type="int"),
                verify_peer_certificate=dict(type="bool"),
                trusted_certificate_authority_ids=dict(type="list", elements="str"),
                certificate_ids=dict(type="list", elements="str"),
                certificate_name=dict(type="str"),
                protocols=dict(
                    type="list",
                    elements="str",
                ),
                cipher_suite_name=dict(type="str"),
                server_order_preference=dict(
                    type="str",
                    choices=["enabled", "disabled"],
                ),
            ),
        ),
        connection_configuration=dict(
            type="dict",
            options=dict(
                idle_timeout=dict(type="int", required=True),
                backend_tcp_proxy_protocol_version=dict(type="int"),
            ),
        ),
        rule_set_names=dict(type="list", elements="str"),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    OciLoadBalancerListenerModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
