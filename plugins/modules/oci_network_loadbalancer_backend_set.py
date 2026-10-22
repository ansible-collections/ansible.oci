# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: oci_network_loadbalancer_backend_set
short_description: Manage an OCI Network Load Balancer backend set
description:
- Create, update, or delete an OCI Network Load Balancer backend set.
version_added: 1.2.0
author:
- Ron Gershburg (@ronger4)
extends_documentation_fragment:
- ansible.oci.oci_auth_options
- ansible.oci.oci_wait_options
options:
  network_load_balancer_id:
    description: The OCID of the network load balancer.
    type: str
    required: true
  name:
    description: The backend set name.
    type: str
    required: true
  policy:
    description: Packet fields used to select a backend. Required when creating a backend set.
    type: str
    choices:
    - two_tuple
    - three_tuple
    - five_tuple
  ip_version:
    description:
    - IP version used by this backend set.
    - Each listener and its backend set must use the same IP version.
    - For a parent with both IP versions, create separate IPv4 and IPv6 listeners and backend sets.
    - See U(https://docs.oracle.com/en-us/iaas/Content/NetworkLoadBalancer/NetworkLoadBalancers/create-network-load-balancer.htm).
    type: str
    choices:
    - ipv4
    - ipv6
  is_preserve_source:
    description:
    - Whether backends receive the original source IP address.
    - This option cannot be disabled when the parent preserves source and destination addresses.
    type: bool
  is_fail_open:
    description: Whether to continue sending traffic when all backends are unhealthy.
    type: bool
  is_instant_failover_enabled:
    description: Whether to move existing connections when their backend becomes unhealthy.
    type: bool
  is_instant_failover_tcp_reset_enabled:
    description: Whether to send TCP resets when instant failover moves traffic to another backend.
    type: bool
  are_operationally_active_backends_preferred:
    description: Whether the active backend keeps receiving traffic after the previous backend recovers.
    type: bool
  health_checker:
    description:
    - Health check settings for this backend set.
    - Supply protocol when creating a backend set.
    - Omitted fields stay unchanged during updates.
    type: dict
    suboptions:
      protocol:
        description:
        - Health check protocol.
        - Currently supported protocols are C(http), C(https), C(tcp), C(udp), and C(dns).
        - See Oracle's documentation for the latest supported protocols at
          U(https://docs.oracle.com/en-us/iaas/Content/NetworkLoadBalancer/HealthCheckPolicies/health-check-policy-management.htm).
        type: str
      port:
        description: Port used by the health check.
        type: int
      retries:
        description: Number of retries before a backend changes health state.
        type: int
      timeout_in_millis:
        description: Maximum response time in milliseconds for each health check.
        type: int
      interval_in_millis:
        description: Time in milliseconds between health checks.
        type: int
      url_path:
        description: URL path requested by HTTP health checks.
        type: str
      response_body_regex:
        description: Regular expression used to check the response body.
        type: str
      return_code:
        description: HTTP response code for a healthy backend.
        type: int
      request_data:
        description: Base64-encoded data to send in TCP or UDP health checks.
        type: str
      response_data:
        description: Base64-encoded data expected in TCP or UDP health check responses.
        type: str
      dns:
        description: DNS query fields for DNS health checks.
        type: dict
        suboptions:
          transport_protocol:
            type: str
            choices:
            - udp
            - tcp
            description: Transport protocol for DNS queries.
          domain_name:
            type: str
            description: Domain name to query.
          query_class:
            type: str
            choices:
            - in
            - ch
            description:
            - Class of DNS records to query.
            - C(in) is the Internet class, used for ordinary DNS records.
            - C(ch) is the Chaos class. Use this class when the DNS server supports it.
            - See U(https://www.iana.org/assignments/dns-parameters/dns-parameters.xhtml#dns-parameters-2)
              and U(https://docs.oracle.com/iaas/api/#/en/networkloadbalancer/20200501/datatypes/DnsHealthCheckerDetails).
          query_type:
            type: str
            choices:
            - a
            - txt
            - aaaa
            description: Type of DNS records to query.
          rcodes:
            type: list
            elements: str
            choices:
            - noerror
            - servfail
            - nxdomain
            - refused
            description: DNS response codes that indicate a healthy backend.
  backends:
    description:
    - Complete desired membership for this backend set.
    - Omit this option to preserve membership. Supply an empty list to remove all backends.
    - Each entry requires a unique name. Existing entries keep omitted fields.
    type: list
    elements: dict
    suboptions:
      name:
        description: Unique backend name.
        type: str
        required: true
      ip_address:
        description: Backend IP address. Supply this or target_id for a new backend.
        type: str
      target_id:
        description: OCID of the backend target. Supply this or ip_address for a new backend.
        type: str
      port:
        description: Backend port. Required for a new backend.
        type: int
      weight:
        description: Backend load balancing weight.
        type: int
      is_backup:
        description: Whether this backend is a backup.
        type: bool
      is_drain:
        description: Whether this backend is draining.
        type: bool
      is_offline:
        description: Whether this backend is offline.
        type: bool
  wait:
    description: Whether to wait for the work request to complete.
    type: bool
    default: true
  state:
    description: The desired resource state.
    type: str
    choices:
    - present
    - absent
    default: present
"""

EXAMPLES = r"""
- name: Create a Network Load Balancer backend set
  ansible.oci.oci_network_loadbalancer_backend_set:
    network_load_balancer_id: ocid1.networkloadbalancer.oc1..example
    name: application
    policy: five_tuple
    health_checker:
      protocol: tcp
      port: 8080
    backends:
      - name: app-a
        ip_address: 10.0.0.10
        port: 8080
        weight: 2

- name: Update backend weight without changing other settings
  ansible.oci.oci_network_loadbalancer_backend_set:
    network_load_balancer_id: ocid1.networkloadbalancer.oc1..example
    name: application
    backends:
      - name: app-a
        weight: 5

- name: Create backend sets on an existing NLB with both IP versions
  ansible.oci.oci_network_loadbalancer_backend_set:
    network_load_balancer_id: ocid1.networkloadbalancer.oc1..example
    name: "application-{{ item.version }}"
    ip_version: "{{ item.version }}"
    policy: five_tuple
    health_checker:
      protocol: tcp
      port: 8080
    backends:
      - name: app-a
        ip_address: "{{ item.address }}"
        port: 8080
  loop:
    - version: ipv4
      address: 10.0.0.10
    - version: ipv6
      address: "2001:db8::10"
"""

RETURN = r"""
resource:
  description: The backend set after the operation.
  returned: when state is present
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    OCI_WAIT_ARGS,
    merge_mappings,
    serialize_oci_model,
    values_differ_as_subset,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    UpdateFieldSpec,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_network_loadbalancer import (
    OciNetworkLoadBalancerSubresourceBase,
    NETWORK_LOAD_BALANCER_BACKEND_ARGUMENT_SPEC,
    NETWORK_LOAD_BALANCER_HEALTH_CHECKER_ARGUMENT_SPEC,
    validate_network_load_balancer_backend,
)


class OciNetworkLoadBalancerBackendSetModule(OciNetworkLoadBalancerSubresourceBase):
    """Manage one backend set."""

    create_model_name = "CreateBackendSetDetails"
    create_method_name = "create_backend_set"
    create_details_name = "create_backend_set_details"
    update_model_name = "UpdateBackendSetDetails"
    update_method_name = "update_backend_set"
    update_details_name = "update_backend_set_details"
    delete_method_name = "delete_backend_set"
    create_resource_name = "backend set"

    def get_resource_response(self, resource_id):
        """Read one child resource from OCI.

        Args:
            resource_id: The child resource name.

        Returns:
            The SDK response wrapper.
        """
        return self.call_with_retry(
            self.client.get_backend_set,
            network_load_balancer_id=self.module.params["network_load_balancer_id"],
            backend_set_name=resource_id,
        )

    def mutation_kwargs(self, operation):
        """Build the SDK arguments for a child mutation.

        Args:
            operation: The lifecycle operation name.

        Returns:
            Parent ID and child identity arguments.
        """
        values = super(OciNetworkLoadBalancerBackendSetModule, self).mutation_kwargs(
            operation
        )
        if operation != "create":
            values["backend_set_name"] = self.resource_name
        return values

    create_required_fields = ("policy", "health_checker")

    def validate_create_request(self):
        """Validate backend membership before creating a backend set."""
        super(OciNetworkLoadBalancerBackendSetModule, self).validate_create_request()
        backends = self._index_requested_backends(self.module.params.get("backends") or [])
        for backend in backends.values():
            validate_network_load_balancer_backend(self.module, backend)
        checker = self.module.params["health_checker"]
        if checker.get("protocol") is None:
            self.module.fail_json(
                msg="health_checker.protocol is required when creating a backend set."
            )

    def _index_requested_backends(self, backends):
        """Index requested backends by name and reject duplicate names.

        Args:
            backends: Requested backend dictionaries.

        Returns:
            Backend dictionaries indexed by name.
        """
        by_name = {}
        for backend in backends:
            name = backend["name"]
            if name in by_name:
                self.module.fail_json(msg="Each backend name must be unique in backends.")
            by_name[name] = backend
        return by_name

    @staticmethod
    def _backend_membership_changed(current_by_name, desired_by_name):
        """Compare backend names and supplied fields.

        Args:
            current_by_name: Current backends indexed by name.
            desired_by_name: Requested backends indexed by name.

        Returns:
            True when membership or a supplied field differs.
        """
        return set(current_by_name) != set(desired_by_name) or any(
            values_differ_as_subset(current_by_name[name], backend)
            for name, backend in desired_by_name.items()
        )

    def _merge_backend_membership(self, current_by_name, desired_by_name):
        """Validate new backends and preserve omitted fields on existing backends.

        Args:
            current_by_name: Current backends indexed by name.
            desired_by_name: Requested backends indexed by name.

        Returns:
            Merged backend dictionaries in the requested order.
        """
        merged = []
        for name, backend in desired_by_name.items():
            if name not in current_by_name:
                validate_network_load_balancer_backend(self.module, backend)
            merged.append(merge_mappings(current_by_name.get(name, {}), backend))
        return merged

    update_field_specs = (
        UpdateFieldSpec(param_name="policy", is_mutable=True, compare="enum"),
        UpdateFieldSpec(param_name="ip_version", is_mutable=True, compare="enum"),
        UpdateFieldSpec(param_name="is_preserve_source", is_mutable=True),
        UpdateFieldSpec(param_name="is_fail_open", is_mutable=True),
        UpdateFieldSpec(param_name="is_instant_failover_enabled", is_mutable=True),
        UpdateFieldSpec(
            param_name="is_instant_failover_tcp_reset_enabled", is_mutable=True
        ),
        UpdateFieldSpec(
            param_name="are_operationally_active_backends_preferred",
            is_mutable=True,
        ),
        UpdateFieldSpec(
            param_name="health_checker",
            is_mutable=True,
            compare="nlb_health_checker",
        ),
    )

    def build_update_plan(self, resource):
        """Build an update plan with backend membership keyed by name.

        Args:
            resource: The current backend set model.

        Returns:
            An update plan with omitted backend fields preserved.
        """
        plan = super(OciNetworkLoadBalancerBackendSetModule, self).build_update_plan(
            resource
        )
        desired = self.module.params.get("backends")
        if desired is None:
            return plan
        desired_by_name = self._index_requested_backends(desired)
        current_items = serialize_oci_model(resource.backends or [])
        current_by_name = {item["name"]: item for item in current_items}
        if self._backend_membership_changed(current_by_name, desired_by_name):
            merged = self._merge_backend_membership(current_by_name, desired_by_name)
            plan["update_needed"] = True
            plan["update_model_fields"]["backends"] = merged
        return plan


def main():
    """Initialize and run the backend set module."""
    spec = dict(OCI_AUTH_ARGS)
    spec.update(dict(OCI_WAIT_ARGS))
    spec.update(
        dict(
            network_load_balancer_id=dict(type="str", required=True),
            name=dict(type="str", required=True),
        )
    )
    backend_fields = dict(NETWORK_LOAD_BALANCER_BACKEND_ARGUMENT_SPEC)
    backend_fields["name"] = dict(type="str", required=True)
    spec.update(
        dict(
            policy=dict(type="str", choices=["two_tuple", "three_tuple", "five_tuple"]),
            ip_version=dict(type="str", choices=["ipv4", "ipv6"]),
            is_preserve_source=dict(type="bool"),
            is_fail_open=dict(type="bool"),
            is_instant_failover_enabled=dict(type="bool"),
            is_instant_failover_tcp_reset_enabled=dict(type="bool"),
            are_operationally_active_backends_preferred=dict(type="bool"),
            health_checker=dict(
                type="dict", options=NETWORK_LOAD_BALANCER_HEALTH_CHECKER_ARGUMENT_SPEC
            ),
            backends=dict(type="list", elements="dict", options=backend_fields),
        )
    )
    spec.update(
        dict(state=dict(type="str", choices=["present", "absent"], default="present"))
    )
    module = AnsibleModule(argument_spec=spec, supports_check_mode=True)
    OciNetworkLoadBalancerBackendSetModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
