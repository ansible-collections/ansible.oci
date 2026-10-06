# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_loadbalancer
short_description: Manage an OCI load balancer
description: >-
  Create, update, and delete OCI load balancers.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_name_lookup_options
  - ansible.oci.oci_tags_options
options:
  wait:
    description:
      - Whether to wait for a lifecycle operation to finish.
      - When false, create and update return an immediate resource snapshot, or an ID-only result if OCI has not exposed the resource yet.
      - A metadata or reserved-IP update followed by a shape resize still waits for the first work request to finish before starting the resize.
    type: bool
    default: true
  wait_timeout:
    description:
      - Maximum number of seconds to wait for each lifecycle operation.
    type: int
    default: 1200
  wait_interval:
    description:
      - Maximum number of seconds between status checks.
    type: int
    default: 30
  state:
    description:
      - The desired state of the load balancer.
    type: str
    choices: [present, absent]
    default: present
  load_balancer_id:
    description:
      - The OCID of the load balancer to manage.
      - Use C(id) as an alias.
    type: str
    aliases: [id]
  name:
    description:
      - The load balancer display name.
      - Required when creating a load balancer.
      - When C(load_balancer_id) is omitted, name lookup is scoped by C(compartment_id).
      - Use C(display_name) as an alias.
    type: str
    aliases: [display_name]
  compartment_id:
    description:
      - The OCID of the compartment containing the load balancer.
      - Required when creating a load balancer and when looking up by name.
    type: str
  subnet_ids:
    description:
      - The OCIDs of the subnets for the load balancer.
      - Required when creating a load balancer and immutable afterwards.
    type: list
    elements: str
  is_private:
    description:
      - Whether the load balancer has a private IP address.
      - This is create-time only. Omitting the value lets OCI select the default.
    type: bool
  shape_name:
    description:
      - The load balancer shape name. OCI determines supported values for the region.
      - Required when creating a load balancer. Shape changes are supported.
      - OCI deprecated fixed shapes in May 2023; use C(flexible) for new load balancers.
      - Switching to C(flexible) requires C(shape_details).
    type: str
  shape_details:
    description:
      - Bandwidth bounds for a C(flexible) shape.
      - Required when creating or switching to C(flexible).
      - Supplying only this option resizes the current shape.
    type: dict
    suboptions:
      minimum_bandwidth_in_mbps:
        description:
          - Minimum bandwidth in Mbps. Values must be from 10 to 8000 and no greater than the maximum.
        type: int
        required: true
      maximum_bandwidth_in_mbps:
        description:
          - Maximum bandwidth in Mbps. Values must be from 10 to 8000 and no less than the minimum.
        type: int
        required: true
  reserved_ips:
    description:
      - Reserved public IP addresses to attach to the load balancer.
      - On update, supplied IDs are added while existing unmentioned addresses are preserved.
      - Adding new IDs on update requires C(ip_mode=ipv6) when the current mode is C(ipv4).
      - OCI validates reserved IP type and prefix compatibility.
      - An empty list does not detach existing addresses.
    type: list
    elements: dict
    suboptions:
      id:
        description:
          - The OCID of a reserved public IP address.
        type: str
        required: true
  ip_mode:
    description:
      - The IP mode for the load balancer. C(ipv6) enables dual-stack operation.
      - C(ipv6) requires a subnet enabled for IPv6 in the target region. OCI validates
        whether its prefix is compatible with the selected public or private setting.
    type: str
    choices: [ipv4, ipv6]
"""

EXAMPLES = r"""
- name: Create a flexible load balancer
  ansible.oci.oci_loadbalancer:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: example-lb
    subnet_ids:
      - ocid1.subnet.oc1..example
    shape_name: flexible
    shape_details:
      minimum_bandwidth_in_mbps: 100
      maximum_bandwidth_in_mbps: 800
    ip_mode: ipv4
  register: created_lb

- name: Rename and resize a load balancer
  ansible.oci.oci_loadbalancer:
    load_balancer_id: "{{ created_lb.resource.id }}"
    name: renamed-lb
    shape_details:
      minimum_bandwidth_in_mbps: 200
      maximum_bandwidth_in_mbps: 1200

- name: Create a public load balancer with a reserved IP and tags
  ansible.oci.oci_loadbalancer:
    compartment_id: ocid1.compartment.oc1..example
    name: public-lb
    subnet_ids:
      - ocid1.subnet.oc1..public
    shape_name: flexible
    shape_details:
      minimum_bandwidth_in_mbps: 100
      maximum_bandwidth_in_mbps: 800
    is_private: false
    ip_mode: ipv4
    reserved_ips:
      - id: ocid1.publicip.oc1..example
    freeform_tags:
      environment: production

- name: Create a private dual-stack load balancer
  ansible.oci.oci_loadbalancer:
    compartment_id: ocid1.compartment.oc1..example
    name: private-dual-stack-lb
    subnet_ids:
      - ocid1.subnet.oc1..dualstack
    shape_name: flexible
    shape_details:
      minimum_bandwidth_in_mbps: 100
      maximum_bandwidth_in_mbps: 800
    is_private: true
    ip_mode: ipv6
    defined_tags:
      Operations:
        CostCenter: "42"

- name: Delete a load balancer by its OCID
  ansible.oci.oci_loadbalancer:
    state: absent
    load_balancer_id: "{{ created_lb.resource.id }}"
"""

RETURN = r"""
resource:
  description:
    - The load balancer resource, with the OCI display name returned as C(name).
    - With C(wait=false), the resource may reflect an operation still in progress or contain only C(id) if it is not yet available.
    - Changes predicted in check mode do not return a resource.
  returned: when state is present and no change is predicted in check mode
  type: dict
  contains:
    id:
      description: The OCID of the load balancer.
      type: str
      returned: when available
    name:
      description: The display name of the load balancer, returned as name.
      type: str
      returned: when available
    compartment_id:
      description: The OCID of the containing compartment.
      type: str
      returned: when available
    lifecycle_state:
      description: The current lifecycle state of the load balancer.
      type: str
      returned: when available
    shape_name:
      description: The OCI shape name, such as flexible.
      type: str
      returned: when available
    shape_details:
      description: The bandwidth configuration of a flexible load balancer.
      type: dict
      returned: when available
      contains:
        minimum_bandwidth_in_mbps:
          description: The minimum bandwidth in Mbps.
          type: int
          returned: when available
        maximum_bandwidth_in_mbps:
          description: The maximum bandwidth in Mbps.
          type: int
          returned: when available
    ip_mode:
      description: The IP mode returned by OCI as IPV4 or IPV6.
      type: str
      returned: when available
    is_private:
      description: Whether the load balancer has a private IP address.
      type: bool
      returned: when available
    ip_addresses:
      description: The IP addresses assigned to the load balancer.
      type: list
      returned: when available
      elements: dict
      contains:
        ip_address:
          description: The allocated IP address.
          type: str
          returned: when available
        is_public:
          description: Whether the IP address is public.
          type: bool
          returned: when available
        reserved_ip:
          description: The reserved public IP reference, or null when no reserved IP is attached.
          type: dict
          returned: when available
          contains:
            id:
              description: The OCID of the reserved public IP.
              type: str
              returned: when a reserved IP is attached
    subnet_ids:
      description: The OCIDs of the subnets used by the load balancer.
      type: list
      returned: when available
      elements: str
    network_security_group_ids:
      description: The OCIDs of the associated network security groups.
      type: list
      returned: when available
      elements: str
    is_delete_protection_enabled:
      description: Whether deletion protection is enabled. May be null when unset.
      type: bool
      returned: when available
    is_request_id_enabled:
      description: Whether request IDs are enabled. May be null when unset.
      type: bool
      returned: when available
    request_id_header:
      description: The request ID header name. May be null when unset.
      type: str
      returned: when available
    backend_sets:
      description: Backend set configurations keyed by name.
      type: dict
      returned: when available
    listeners:
      description: Listener configurations keyed by name.
      type: dict
      returned: when available
    certificates:
      description: Certificate configurations keyed by name.
      type: dict
      returned: when available
    hostnames:
      description: Hostname configurations keyed by name.
      type: dict
      returned: when available
    path_route_sets:
      description: Path route set configurations keyed by name.
      type: dict
      returned: when available
    routing_policies:
      description: Routing policy configurations keyed by name.
      type: dict
      returned: when available
    rule_sets:
      description: Rule set configurations keyed by name.
      type: dict
      returned: when available
    ssl_cipher_suites:
      description: SSL cipher suite configurations keyed by name.
      type: dict
      returned: when available
    freeform_tags:
      description: Free-form tags applied to the load balancer.
      type: dict
      returned: when available
    defined_tags:
      description: Defined tags applied to the load balancer.
      type: dict
      returned: when available
    system_tags:
      description: System tags returned by OCI.
      type: dict
      returned: when available
    security_attributes:
      description: Security attributes returned by OCI.
      type: dict
      returned: when available
    time_created:
      description: The date and time the load balancer was created.
      type: str
      returned: when available
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_COMMON_ARGS,
    filter_none_values,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

oci = import_oci_sdk()[0]

CREATE_REQUIRED_FIELDS = (
    "compartment_id",
    "name",
    "shape_name",
    "subnet_ids",
)
FLEXIBLE_SHAPE_NAME = "flexible"
IP_MODE_TO_OCI = {
    "ipv4": "IPV4",
    "ipv6": "IPV6",
}
FLEXIBLE_SHAPE_BOUNDS_ERROR = (
    "Flexible load balancer bandwidth must satisfy "
    "10 <= minimum_bandwidth_in_mbps <= maximum_bandwidth_in_mbps <= 8000."
)


def _is_flexible_shape(shape_name):
    """Return whether the shape name identifies the Flexible shape.

    Args:
        shape_name: Shape name to check.

    Returns:
        True when the name is Flexible, ignoring case.
    """
    return (
        isinstance(shape_name, str)
        and shape_name.casefold() == FLEXIBLE_SHAPE_NAME.casefold()
    )


def _same_shape_name(left, right):
    """Compare shape names without regard to case.

    Args:
        left: First shape name.
        right: Second shape name.

    Returns:
        True when both names are equal, ignoring case.
    """
    if left is None or right is None:
        return left == right
    return left.casefold() == right.casefold()


def _shape_details_dict(value):
    """Convert shape details to a dictionary with unset values removed.

    Args:
        value: Shape details mapping or SDK model.

    Returns:
        The normalized details dictionary, or None when value is None.
    """
    return filter_none_values(dict(value)) if value is not None else None


def _validate_shape_details(module, shape_name, shape_details, required=False):
    """Validate shape-details usage and Flexible bandwidth bounds.

    Args:
        module: Ansible module used to report invalid input.
        shape_name: Requested load-balancer shape name.
        shape_details: Requested Flexible bandwidth bounds.
        required: Whether Flexible shape details are required.
    """
    if _is_flexible_shape(shape_name) and shape_details is None:
        if required:
            module.fail_json(
                msg="shape_details is required when shape_name is Flexible."
            )
        return
    if shape_details is None:
        return
    if not _is_flexible_shape(shape_name):
        module.fail_json(
            msg="shape_details can only be used with shape_name Flexible."
        )

    details = _shape_details_dict(shape_details)
    minimum = details.get("minimum_bandwidth_in_mbps") if details else None
    maximum = details.get("maximum_bandwidth_in_mbps") if details else None
    if (
        minimum is None
        or maximum is None
        or minimum < 10
        or maximum > 8000
        or minimum > maximum
    ):
        module.fail_json(msg=FLEXIBLE_SHAPE_BOUNDS_ERROR)


def build_create_load_balancer_details(params):
    """Build the OCI create model, translating IP mode and shape names.

    Args:
        params: Ansible module parameters for the new load balancer.

    Returns:
        An OCI CreateLoadBalancerDetails model.
    """
    shape_details = params.get("shape_details")
    shape_name = params.get("shape_name")
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "display_name": params.get("name"),
            "subnet_ids": params.get("subnet_ids"),
            "shape_name": (
                FLEXIBLE_SHAPE_NAME if _is_flexible_shape(shape_name) else shape_name
            ),
            "shape_details": (
                oci.load_balancer.models.ShapeDetails(
                    **_shape_details_dict(shape_details)
                )
                if shape_details is not None
                else None
            ),
            "is_private": params.get("is_private"),
            "ip_mode": IP_MODE_TO_OCI.get(
                params.get("ip_mode"), params.get("ip_mode")
            ),
            "reserved_ips": (
                [
                    oci.load_balancer.models.ReservedIP(**reserved_ip)
                    for reserved_ip in params.get("reserved_ips") or []
                ]
                if params.get("reserved_ips") is not None
                else None
            ),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.load_balancer.models.CreateLoadBalancerDetails(**details)


class OciLoadBalancerModule(OciResourceBase):
    """Concrete resource adapter for OCI load balancers."""

    @property
    def client_class(self):
        """Return the load-balancer service client required by this adapter."""
        return oci.load_balancer.LoadBalancerClient

    resource_id_param = "load_balancer_id"
    list_resource_method = "list_load_balancers"
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "load balancer"
    update_field_specs = (
        UpdateFieldSpec(
            param_name="name",
            resource_field="display_name",
            is_mutable=True,
        ),
        UpdateFieldSpec(
            param_name="compartment_id",
            is_mutable=False,
            immutable_reason="OCI does not move load balancers through update",
        ),
        UpdateFieldSpec(
            param_name="subnet_ids",
            is_mutable=False,
            compare="sorted_list",
        ),
        UpdateFieldSpec(
            param_name="is_private",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="ip_mode",
            is_mutable=True,
            strategy="plan_ip_mode_update",
        ),
        UpdateFieldSpec(
            param_name="reserved_ips",
            is_mutable=True,
            strategy="plan_reserved_ip_update",
        ),
    )

    def get_resource_response(self, resource_id):
        """Fetch a load balancer for base lookups and wait polling.

        This override supplies the concrete SDK getter required by the base
        resource helper.

        Args:
            resource_id: OCI load-balancer identifier.

        Returns:
            The SDK response from get_load_balancer.
        """
        return self.call_with_retry(
            self.client.get_load_balancer,
            load_balancer_id=resource_id,
        )

    def validate_create_request(self):
        """Apply load-balancer subnet and Flexible-shape create validation.

        This override adds a nonempty subnet check and Flexible bandwidth
        bounds validation to the shared required-field checks.
        """
        super(OciLoadBalancerModule, self).validate_create_request()
        if not self.module.params.get("subnet_ids"):
            self.module.fail_json(
                msg="Creating a load balancer requires a non-empty subnet_ids list."
            )
        _validate_shape_details(
            self.module,
            self.module.params.get("shape_name"),
            self.module.params.get("shape_details"),
            required=True,
        )

    def plan_reserved_ip_update(
        self, resource, resource_dict, spec, desired_reserved_ips
    ):
        """Plan reserved-IP additions supported during an IPv4-to-IPv6 change.

        Args:
            resource: Current load-balancer SDK model.
            resource_dict: Serialized current resource fields.
            spec: Update field specification for reserved IPs.
            desired_reserved_ips: Requested reserved-IP entries.

        Returns:
            A list of reserved-IP update operations.
        """
        desired_ids = {
            reserved_ip.get("id")
            for reserved_ip in desired_reserved_ips or []
            if reserved_ip and reserved_ip.get("id")
        }
        if not desired_ids:
            return []

        current_ids = {
            (ip.get("reserved_ip") or {}).get("id")
            for ip in resource_dict.get("ip_addresses") or []
            if isinstance(ip, dict) and isinstance(ip.get("reserved_ip"), dict)
        }
        current_ids.discard(None)
        if desired_ids.issubset(current_ids):
            return []

        requested_ip_mode = self.module.params.get("ip_mode")
        requested_ip_mode = IP_MODE_TO_OCI.get(
            requested_ip_mode, requested_ip_mode
        )
        current_ip_mode = resource_dict.get("ip_mode")
        if (
            not isinstance(requested_ip_mode, str)
            or requested_ip_mode != IP_MODE_TO_OCI["ipv6"]
            or not isinstance(current_ip_mode, str)
            or current_ip_mode != IP_MODE_TO_OCI["ipv4"]
        ):
            self.module.fail_json(
                msg=(
                    "OCI supports adding reserved IPs on update only while "
                    "changing ip_mode from IPV4 to IPV6."
                )
            )

        return [
            {
                "reserved_ips": [
                    {"id": reserved_id}
                    for reserved_id in sorted(current_ids | desired_ids)
                ]
            }
        ]

    def plan_ip_mode_update(self, resource, resource_dict, spec, desired_ip_mode):
        """Plan an IP-mode update using the explicit Ansible-to-OCI mapping.

        Args:
            resource: Current load-balancer SDK model.
            resource_dict: Serialized current resource fields.
            spec: Update field specification for IP mode.
            desired_ip_mode: Requested Ansible IP-mode value.

        Returns:
            An empty list when unchanged, or one mapped update operation.
        """
        desired_oci_value = IP_MODE_TO_OCI.get(
            desired_ip_mode, desired_ip_mode
        )
        if resource_dict.get("ip_mode") == desired_oci_value:
            return []
        return [{"ip_mode": desired_oci_value}]

    def build_update_plan(self, resource):
        """Extend shared planning with IP mode, reserved IPs, and shape changes.

        This override folds translated IP-mode and reserved-IP operations into
        metadata updates and plans the separate shape endpoint operation.

        Args:
            resource: Current load-balancer SDK model.

        Returns:
            The complete load-balancer update plan.
        """
        update_plan = super(OciLoadBalancerModule, self).build_update_plan(resource)
        for strategy_plan in update_plan["strategy_operations"]:
            for operation in strategy_plan["operations"]:
                update_plan["update_model_fields"].update(operation)

        shape_update = self.plan_shape_update(resource)
        update_plan["shape_update"] = shape_update
        if shape_update is not None:
            update_plan["update_needed"] = True
        return update_plan

    def plan_shape_update(self, resource):
        """Build a shape update model when shape settings differ.

        Args:
            resource: Current load-balancer SDK model.

        Returns:
            An UpdateLoadBalancerShapeDetails model, or None when unchanged.
        """
        desired_shape_name = self.module.params.get("shape_name")
        desired_shape_details = self.module.params.get("shape_details")
        if desired_shape_name is None and desired_shape_details is None:
            return None

        resource_dict = self.serialize_result_resource(resource) or {}
        current_shape_name = resource_dict.get("shape_name")
        current_shape_details = _shape_details_dict(resource_dict.get("shape_details"))
        target_shape_name = desired_shape_name or current_shape_name
        if desired_shape_details is not None:
            target_shape_details = _shape_details_dict(desired_shape_details)
        elif _is_flexible_shape(target_shape_name):
            target_shape_details = current_shape_details
        else:
            target_shape_details = None

        if (
            _is_flexible_shape(target_shape_name)
            and desired_shape_name is not None
            and not _is_flexible_shape(current_shape_name)
            and desired_shape_details is None
        ):
            self.module.fail_json(
                msg="shape_details is required when switching shape_name to Flexible."
            )
        _validate_shape_details(
            self.module,
            target_shape_name,
            target_shape_details,
            required=False,
        )

        shape_details_match = (
            not _is_flexible_shape(target_shape_name)
            or target_shape_details == current_shape_details
        )
        if (
            _same_shape_name(target_shape_name, current_shape_name)
            and shape_details_match
        ):
            return None

        update_fields = {
            "shape_name": (
                FLEXIBLE_SHAPE_NAME
                if _is_flexible_shape(target_shape_name)
                else target_shape_name
            )
        }
        if target_shape_details is not None:
            update_fields["shape_details"] = oci.load_balancer.models.ShapeDetails(
                **target_shape_details
            )
        return oci.load_balancer.models.UpdateLoadBalancerShapeDetails(
            **filter_none_values(update_fields)
        )

    def make_work_request_fetcher(self):
        """Build the SDK waiter's fetch hook and fail on failed work.

        Returns:
            A callback that fetches and validates the current work request.
        """

        def fetch_work_request(response=None):
            """Fetch the current work request and reject failed requests.

            Args:
                response: Previous SDK waiter response, if available.

            Returns:
                The refreshed SDK work-request response.

            Raises:
                RuntimeError: If the waiter has no work-request ID or the
                    request has failed.
            """
            current_request = getattr(response, "data", None)
            requested_id = getattr(current_request, "id", None)
            if not requested_id:
                raise RuntimeError("The OCI waiter did not provide a work request ID")

            def fail_if_failed(work_request):
                """Raise when a work request reports the FAILED state.

                Args:
                    work_request: Work-request model to inspect.

                Raises:
                    RuntimeError: If the work request failed.
                """
                if getattr(work_request, "lifecycle_state", None) != "FAILED":
                    return
                error_details = getattr(work_request, "error_details", None) or []
                messages = []
                for detail in error_details:
                    message = getattr(detail, "message", None)
                    code = getattr(detail, "error_code", None)
                    messages.append(": ".join(part for part in (code, message) if part))
                reason = "; ".join(messages) or "no error details were returned"
                raise RuntimeError(f"Work request {requested_id} failed: {reason}")

            # Check the initial waiter response as well as every refreshed request.
            fail_if_failed(current_request)
            latest_response = self.client.get_work_request(requested_id)
            fail_if_failed(latest_response.data)
            return latest_response

        return fetch_work_request

    def _composite_call(self, operation, method_name, wait_states, **kwargs):
        """Invoke an OCI composite operation with the requested wait states.

        Args:
            operation: Human-readable operation name for error messages.
            method_name: Composite client method to invoke.
            wait_states: Work-request states that complete the operation.
            **kwargs: Arguments passed to the composite method.

        Returns:
            The composite operation SDK response.
        """
        composite = oci.load_balancer.LoadBalancerClientCompositeOperations(
            self.client
        )
        waiter_kwargs = {}
        if wait_states:
            waiter_kwargs = {
                "max_wait_seconds": self.module.params.get("wait_timeout", 1200),
                "max_interval_seconds": self.module.params.get("wait_interval", 30),
                "fetch_func": self.make_work_request_fetcher(),
            }

        previous_retry_strategy = getattr(self.client, "retry_strategy", None)
        self.client.retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY
        try:
            return getattr(composite, method_name)(
                wait_for_states=wait_states,
                waiter_kwargs=waiter_kwargs,
                **kwargs,
            )
        except oci.exceptions.CompositeOperationError as exc:
            partial_results = getattr(exc, "partial_results", None) or []
            work_request_id = None
            if partial_results:
                work_request_id = (getattr(partial_results[-1], "headers", None) or {}).get(
                    "opc-work-request-id"
                )
            cause = getattr(exc, "cause", None) or exc
            self.module.fail_json(
                msg=(
                    f"Failed to {operation} load balancer; work request "
                    f"{work_request_id or 'ID unavailable'}: {cause}"
                )
            )
        except oci.exceptions.ServiceError as exc:
            self.module.fail_json(
                msg=f"Failed to {operation} load balancer: {exc}"
            )
        finally:
            self.client.retry_strategy = previous_retry_strategy

    def _get_immediate_resource(self, resource_id, operation):
        """Fetch the resource after an operation that does not wait.

        Args:
            resource_id: OCI load-balancer identifier.
            operation: Operation name for error reporting.

        Returns:
            The fetched resource, or an ID-only result if it is unavailable.
        """
        try:
            resource = self.get_resource_by_id(resource_id)
        except oci.exceptions.ServiceError as exc:
            self.module.fail_json(
                msg=f"Failed to read the load balancer after {operation}: {exc}"
            )
        return resource if resource is not None else {"id": resource_id}

    def create_resource(self):
        """Create a load balancer and resolve its result through OCI work requests.

        This override resolves asynchronous creation and obtains the resource
        ID when wait=False.

        Returns:
            The created load-balancer model or an ID-only result.
        """
        waiting = self.module.params.get("wait", True)
        response = self._composite_call(
            "create",
            "create_load_balancer_and_wait_for_state",
            ["SUCCEEDED"] if waiting else [],
            create_load_balancer_details=build_create_load_balancer_details(
                self.module.params
            ),
        )
        if waiting:
            resource = response.data
            if getattr(resource, "id", None):
                return resource
            self.module.fail_json(
                msg="The OCI create operation did not return a completed load balancer resource."
            )

        work_request_id = (response.headers or {}).get("opc-work-request-id")
        if not work_request_id:
            self.module.fail_json(
                msg="The OCI create response did not include a work request ID."
            )
        try:
            work_request = self.call_with_retry(
                self.client.get_work_request,
                work_request_id,
            ).data
        except oci.exceptions.ServiceError as exc:
            self.module.fail_json(
                msg=(
                    f"Failed to resolve the load balancer for work request "
                    f"{work_request_id}: {exc}"
                )
            )
        load_balancer_id = getattr(work_request, "load_balancer_id", None)
        if not load_balancer_id:
            self.module.fail_json(
                msg=(
                    f"Work request {work_request_id} did not include a load balancer ID."
                )
            )
        return self._get_immediate_resource(load_balancer_id, "create")

    def build_update_details(self, update_model_fields):
        """Build update details after translating IP mode and ReservedIP fields.

        The base requires each adapter to construct its service-specific SDK
        payload.

        Args:
            update_model_fields: Fields selected by the update planner.

        Returns:
            An OCI UpdateLoadBalancerDetails model.
        """
        fields = dict(update_model_fields)
        if "ip_mode" in fields:
            fields["ip_mode"] = IP_MODE_TO_OCI.get(
                fields["ip_mode"], fields["ip_mode"]
            )
        if "reserved_ips" in fields:
            fields["reserved_ips"] = [
                oci.load_balancer.models.ReservedIP(**reserved_ip)
                for reserved_ip in fields["reserved_ips"]
            ]
        return oci.load_balancer.models.UpdateLoadBalancerDetails(**fields)

    def _get_shape_update_result(self, resource_id, response, waiting):
        """Resolve the resource after a shape update operation.

        Args:
            resource_id: OCI load-balancer identifier.
            response: Shape update SDK response.
            waiting: Whether the response contains a completed work request.

        Returns:
            The updated resource or an ID-only result when not waiting.
        """
        if not waiting:
            return self._get_immediate_resource(resource_id, "update")

        work_request = response.data
        if getattr(work_request, "lifecycle_state", None) != "SUCCEEDED":
            self.module.fail_json(
                msg="The OCI shape update did not return a succeeded work request."
            )
        try:
            resource = self.get_resource_by_id(resource_id)
        except oci.exceptions.ServiceError as exc:
            self.module.fail_json(
                msg=f"Failed to read the load balancer after resizing: {exc}"
            )
        if resource is None:
            self.module.fail_json(
                msg=(
                    f"Work request {getattr(work_request, 'id', 'unknown')} "
                    "finished resizing the load balancer, but the load balancer "
                    "could not be retrieved."
                )
            )
        return resource

    def update_resource(self, resource):
        """Apply metadata and shape updates through their separate OCI APIs.

        This override sequences both endpoints and waits on work requests,
        because the resource reaching ACTIVE alone does not prove completion.

        Args:
            resource: Current load-balancer SDK model.

        Returns:
            The latest load-balancer model or ID-only result.
        """
        update_plan = self.get_update_plan(resource)
        update_fields = update_plan["update_model_fields"]
        shape_update = update_plan.get("shape_update")
        waiting = self.module.params.get("wait", True)
        current_resource = resource
        if update_fields:
            response = self._composite_call(
                "update",
                "update_load_balancer_and_wait_for_state",
                ["SUCCEEDED"] if waiting or shape_update is not None else [],
                load_balancer_id=resource.id,
                update_load_balancer_details=self.build_update_details(update_fields),
            )
            if waiting or shape_update is not None:
                current_resource = response.data
                if getattr(current_resource, "id", None) is None:
                    self.module.fail_json(
                        msg=(
                            "The OCI metadata update did not return a completed "
                            "load balancer resource."
                        )
                    )

        if shape_update is not None:
            response = self._composite_call(
                "update shape",
                "update_load_balancer_shape_and_wait_for_state",
                ["SUCCEEDED"] if waiting else [],
                load_balancer_id=resource.id,
                update_load_balancer_shape_details=shape_update,
            )
            current_resource = self._get_shape_update_result(
                resource.id, response, waiting
            )
        elif update_fields and not waiting:
            current_resource = self._get_immediate_resource(resource.id, "update")

        return current_resource

    def delete_resource(self, resource):
        """Delete the load balancer through the shared delete helper.

        This override binds the raw SDK delete call and delegates waiting and
        error handling to the base helper.

        Args:
            resource: Load-balancer SDK model to delete.

        Returns:
            The result from the base delete helper.
        """
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_load_balancer,
            load_balancer_id=resource.id,
        )


def main():
    """Build the module argument spec and run the load-balancer resource module."""
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        load_balancer_id=dict(type="str", aliases=["id"]),
        name=dict(type="str", aliases=["display_name"]),
        compartment_id=dict(type="str"),
        subnet_ids=dict(type="list", elements="str"),
        is_private=dict(type="bool"),
        shape_name=dict(type="str"),
        shape_details=dict(
            type="dict",
            options=dict(
                minimum_bandwidth_in_mbps=dict(type="int", required=True),
                maximum_bandwidth_in_mbps=dict(type="int", required=True),
            ),
        ),
        reserved_ips=dict(
            type="list",
            elements="dict",
            options=dict(id=dict(type="str", required=True)),
        ),
        ip_mode=dict(type="str", choices=["ipv4", "ipv6"]),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )
    OciLoadBalancerModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
