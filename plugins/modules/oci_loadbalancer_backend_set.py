# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_loadbalancer_backend_set
short_description: Manage a backend set on an OCI load balancer
description:
  - Create, update, or delete a backend set on an OCI load balancer.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_wait_options
options:
  load_balancer_id:
    description:
      - The OCID of the load balancer that contains the backend set.
    type: str
    required: true
  name:
    description:
      - The backend set name. It must contain only alphanumeric characters, dashes, or underscores and cannot contain spaces.
    type: str
    required: true
  policy:
    description:
      - The load balancing policy. C(round_robin) distributes requests in sequence,
        C(least_connections) selects the backend with the fewest active connections,
        and C(ip_hash) sends clients with the same IP address to the same backend.
      - Required when creating a backend set.
    type: str
    choices: [round_robin, least_connections, ip_hash]
  backends:
    description:
      - The backend server membership and any supplied per-backend settings.
      - On update, the supplied membership is reconciled as a whole; an empty list removes all members.
    type: list
    elements: dict
    suboptions:
      ip_address:
        description:
          - The IP address of the backend server.
          - To reproduce the Console's Compute Instances selection, supply the compute instance's private IP address.
          - Obtain the private IP address from the instance's VNIC before calling this module.
            The module accepts the IP address directly and does not resolve an instance OCID.
        type: str
        required: true
      port:
        description: The communication port of the backend server.
        type: int
        required: true
      weight:
        description: The backend server's load balancing weight.
        type: int
      backup:
        description:
          - Whether this backend receives traffic only when other backends are unhealthy.
          - Backends marked as backup cannot be used with the IP Hash policy.
        type: bool
      drain:
        description: Whether this backend should receive no new incoming traffic.
        type: bool
      offline:
        description: Whether the load balancer should treat this backend as offline.
        type: bool
  health_checker:
    description:
      - Health check settings. Required when creating a backend set.
      - If this dictionary is omitted during an update, the current health check settings stay unchanged.
      - If this dictionary is supplied, omitted fields use defaults. This can reset custom settings.
      - Values from C(module_defaults) take priority over these defaults.
      - Specify C(health_checker.retries) in later tasks to retain a custom retry count.
      - Without C(module_defaults), omitting C(retries) from this dictionary resets its value to 3.
      - Updates preserve health check settings without module input options,
        including C(is_force_plain_text) (Force plaintext health checks).
    type: dict
    suboptions:
      protocol:
        description: The health check protocol, C(http) or C(tcp).
        type: str
        default: http
        choices: [http, tcp]
      url_path:
        description: The path to check when using HTTP.
        type: str
        default: /
      port:
        description: The port used by the health check. The default is 80.
        type: int
        default: 80
      return_code:
        description: The response status expected from a healthy HTTP backend.
        type: int
        default: 200
      retries:
        description: The number of retries before a backend is considered unhealthy.
        type: int
        default: 3
      timeout_in_millis:
        description: The health check response timeout in milliseconds.
        type: int
        default: 3000
      interval_in_millis:
        description: The interval between health checks in milliseconds.
        type: int
        default: 10000
      response_body_regex:
        description: A regular expression used to inspect an HTTP response body.
        type: str
        default: ''
  ssl_configuration:
    description:
      - SSL configuration for backend connections.
    type: dict
    suboptions:
      verify_depth:
        description: Maximum peer certificate chain verification depth.
        type: int
      verify_peer_certificate:
        description: Whether to verify peer certificates.
        type: bool
      trusted_certificate_authority_ids:
        description: OCIDs of trusted certificate authorities or bundles.
        type: list
        elements: str
      certificate_ids:
        description: OCIDs of certificates; OCI currently accepts one certificate ID.
        type: list
        elements: str
      certificate_name:
        description: Certificate bundle name.
        type: str
      protocols:
        description:
          - SSL/TLS protocols for backend connections.
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
  session_persistence_configuration:
    description:
      - Application cookie persistence settings.
      - Supplying this option replaces the load balancer cookie configuration.
      - If both persistence options are omitted, the current configuration is preserved.
      - Mutually exclusive with C(lb_cookie_session_persistence_configuration).
    type: dict
    suboptions:
      cookie_name:
        description: Cookie name used to identify a persistent session; use C(*) to match any cookie.
        type: str
        required: true
      disable_fallback:
        description: Whether clients are prevented from moving to another backend when their backend is unavailable.
        type: bool
  lb_cookie_session_persistence_configuration:
    description:
      - Load balancer cookie persistence settings.
      - Supplying this option replaces the application cookie configuration.
      - If both persistence options are omitted, the current configuration is preserved.
      - Mutually exclusive with C(session_persistence_configuration).
    type: dict
    suboptions:
      cookie_name:
        description: Name of the cookie inserted by the load balancer.
        type: str
      disable_fallback:
        description: Whether clients are prevented from moving to another backend when their backend is unavailable.
        type: bool
      domain:
        description: Domain attribute for the cookie.
        type: str
      path:
        description: Path attribute for the cookie.
        type: str
      max_age_in_seconds:
        description: Cookie lifetime in seconds; must be at least one second.
        type: int
      is_secure:
        description: Whether to add the Secure cookie attribute.
        type: bool
      is_http_only:
        description: Whether to add the HttpOnly cookie attribute.
        type: bool
  wait:
    description:
      - Whether to wait for the OCI work request to complete before returning.
      - When false, the returned resource is an immediate snapshot. It may contain
        only its name if OCI has not exposed the child yet.
    type: bool
    default: true
  state:
    description:
      - The desired state of the backend set.
    type: str
    choices: [present, absent]
    default: present
"""

EXAMPLES = r"""
- name: Create a backend set
  ansible.oci.oci_loadbalancer_backend_set:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    name: app_pool
    policy: round_robin
    backends:
      - ip_address: 10.0.0.7
        port: 8080
        weight: 3
    health_checker: {}

- name: Set a custom health check retry count
  ansible.oci.oci_loadbalancer_backend_set:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    name: app_pool
    health_checker:
      retries: 7

- name: Reset health check values to defaults
  ansible.oci.oci_loadbalancer_backend_set:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    name: app_pool
    health_checker: {}

- name: Update a backend set health check
  ansible.oci.oci_loadbalancer_backend_set:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    name: app_pool
    health_checker:
      url_path: /ready

- name: Delete a backend set
  ansible.oci.oci_loadbalancer_backend_set:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    name: app_pool
    state: absent
"""

RETURN = r"""
resource:
  description: The backend set acted upon. Not returned when C(state=absent).
  returned: when state is present
  type: dict
  contains:
    name:
      description: The backend set name.
      type: str
      sample: app_pool
    policy:
      description: The load balancing policy.
      type: str
      sample: ROUND_ROBIN
    backends:
      description: Backend servers configured for the set.
      type: list
      elements: dict
    health_checker:
      description: Health check settings for the set.
      type: dict
    ssl_configuration:
      description: SSL configuration for backend connections.
      type: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    OCI_WAIT_ARGS,
    import_oci_sdk,
    serialize_oci_model,
    values_differ_as_subset,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_loadbalancer import (
    OciLoadBalancerSubresourceBase,
    build_load_balancer_model,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_loadbalancer_common import (
    merge_load_balancer_fields,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    UpdateFieldSpec,
)

oci = import_oci_sdk()[0]


class OciLoadBalancerBackendSetModule(OciLoadBalancerSubresourceBase):
    """Lifecycle adapter for OCI load balancer backend sets."""

    create_model_name = "CreateBackendSetDetails"
    create_method_name = "create_backend_set_and_wait_for_state"
    create_details_name = "create_backend_set_details"
    update_model_name = "UpdateBackendSetDetails"
    update_method_name = "update_backend_set_and_wait_for_state"
    update_details_name = "update_backend_set_details"
    delete_method_name = "delete_backend_set_and_wait_for_state"
    create_resource_name = "load balancer backend set"
    create_required_fields = ("name", "policy", "health_checker")

    update_field_specs = (
        UpdateFieldSpec(
            param_name="policy", is_mutable=True, strategy="plan_enum_update"
        ),
        UpdateFieldSpec(
            param_name="health_checker", is_mutable=True, compare="subset_dict"
        ),
        UpdateFieldSpec(
            param_name="ssl_configuration", is_mutable=True, compare="subset_dict"
        ),
        UpdateFieldSpec(
            param_name="session_persistence_configuration",
            is_mutable=True,
            compare="subset_dict",
        ),
        UpdateFieldSpec(
            param_name="lb_cookie_session_persistence_configuration",
            is_mutable=True,
            compare="subset_dict",
        ),
    )

    def get_resource_response(self, resource_id):
        """Fetch the named backend set.

        Args:
            resource_id: Backend set name.

        Returns:
            The SDK response.
        """
        return self.call_with_retry(
            self.client.get_backend_set,
            load_balancer_id=self.module.params.get("load_balancer_id"),
            backend_set_name=resource_id,
        )

    def mutation_kwargs(self, operation):
        """Build scoped arguments for a resource mutation.

        Args:
            operation: Create, update, or delete operation.

        Returns:
            The SDK keyword arguments.
        """
        kwargs = super(OciLoadBalancerBackendSetModule, self).mutation_kwargs(
            operation
        )
        if operation in ("update", "delete"):
            kwargs["backend_set_name"] = self.resource_name
        return kwargs

    def build_update_plan(self, resource):
        """Plan field and backend membership changes.

        Args:
            resource: Current backend set SDK model.

        Returns:
            The update plan.
        """
        update_plan = super(OciLoadBalancerBackendSetModule, self).build_update_plan(
            resource
        )
        desired_backends = self.module.params.get("backends")
        if desired_backends is not None and self.backends_differ(
            resource, desired_backends
        ):
            update_plan["update_needed"] = True
            update_plan["update_model_fields"]["backends"] = desired_backends
        return update_plan

    @staticmethod
    def _backend_key(backend):
        """Identify a backend by its address and port.

        Args:
            backend: Serialized backend fields.

        Returns:
            The IP address and port tuple.
        """
        return backend.get("ip_address"), backend.get("port")

    def backends_differ(self, resource, desired_backends):
        """Compare membership and supplied fields, ignoring backend order.

        Args:
            resource: Current backend set SDK model.
            desired_backends: Requested backend configurations.

        Returns:
            True when an update is needed.
        """
        current_backends = serialize_oci_model(resource).get("backends") or []
        desired_backends = desired_backends or []
        current_keys = [self._backend_key(backend) for backend in current_backends]
        desired_keys = [self._backend_key(backend) for backend in desired_backends]
        if sorted(current_keys) != sorted(desired_keys):
            return True

        current_by_key = {
            self._backend_key(backend): backend for backend in current_backends
        }
        for desired_backend in desired_backends:
            current_backend = current_by_key[self._backend_key(desired_backend)]
            if values_differ_as_subset(current_backend, desired_backend):
                return True
        return False

    def build_update_details(self, update_model_fields, resource=None):
        """Build update details while preserving fields and clearing persistence.

        Backend set updates need full nested values, and OCI requires an explicit
        sentinel to clear the opposite persistence configuration.

        Args:
            update_model_fields: Fields selected for update.
            resource: Current backend set SDK model, if available.

        Returns:
            An UpdateBackendSetDetails model.
        """
        fields = dict(update_model_fields)
        if resource is not None:
            fields = merge_load_balancer_fields(resource, fields)
            if "backends" in update_model_fields:
                current = serialize_oci_model(resource).get("backends") or []
                current_by_key = {
                    self._backend_key(backend): backend for backend in current
                }
                fields["backends"] = [
                    merge_load_balancer_fields(
                        current_by_key.get(self._backend_key(desired_backend), {}),
                        desired_backend,
                    )
                    for desired_backend in update_model_fields["backends"]
                ]
        ssl_configuration = fields.get("ssl_configuration")
        if isinstance(ssl_configuration, dict):
            fields["ssl_configuration"] = dict(ssl_configuration)
            ssl_configuration = fields["ssl_configuration"]
            ssl_configuration.pop("server_order_preference", None)

        details = build_load_balancer_model(self.update_model_name, fields)
        persistence_fields = {
            "session_persistence_configuration",
            "lb_cookie_session_persistence_configuration",
        }
        supplied_persistence_fields = persistence_fields.intersection(
            update_model_fields
        )
        if len(supplied_persistence_fields) == 1:
            supplied_field = supplied_persistence_fields.pop()
            opposite_field = next(
                iter(persistence_fields - {supplied_field})
            )
            setattr(details, opposite_field, oci.util.NONE_SENTINEL)
        return details


def main():
    """Initialize and run the backend set module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_WAIT_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        load_balancer_id=dict(type="str", required=True),
        name=dict(type="str", required=True),
        policy=dict(
            type="str", choices=["round_robin", "least_connections", "ip_hash"]
        ),
        backends=dict(
            type="list",
            elements="dict",
            options=dict(
                ip_address=dict(type="str", required=True),
                port=dict(type="int", required=True),
                weight=dict(type="int"),
                backup=dict(type="bool"),
                drain=dict(type="bool"),
                offline=dict(type="bool"),
            ),
        ),
        health_checker=dict(
            type="dict",
            options=dict(
                protocol=dict(
                    type="str", default="http", choices=["http", "tcp"]
                ),
                url_path=dict(type="str", default="/"),
                port=dict(type="int", default=80),
                return_code=dict(type="int", default=200),
                retries=dict(type="int", default=3),
                timeout_in_millis=dict(type="int", default=3000),
                interval_in_millis=dict(type="int", default=10000),
                response_body_regex=dict(type="str", default=""),
            ),
        ),
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
            ),
        ),
        session_persistence_configuration=dict(
            type="dict",
            options=dict(
                cookie_name=dict(type="str", required=True),
                disable_fallback=dict(type="bool"),
            ),
        ),
        lb_cookie_session_persistence_configuration=dict(
            type="dict",
            options=dict(
                cookie_name=dict(type="str"),
                disable_fallback=dict(type="bool"),
                domain=dict(type="str"),
                path=dict(type="str"),
                max_age_in_seconds=dict(type="int"),
                is_secure=dict(type="bool"),
                is_http_only=dict(type="bool"),
            ),
        ),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        mutually_exclusive=[
            [
                "session_persistence_configuration",
                "lb_cookie_session_persistence_configuration",
            ]
        ],
        supports_check_mode=True,
    )
    OciLoadBalancerBackendSetModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
