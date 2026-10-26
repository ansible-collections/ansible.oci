# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: oci_network_ipsec_connection
short_description: Manage an OCI IPSec connection and its tunnels
description:
- Create, update, and delete an OCI IPSec connection.
- Use C(tunnel_configuration) only when you create a connection.
- Use C(tunnels) to update existing tunnels by their OCID.
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
    description: The desired state of the IPSec connection.
    type: str
    choices:
    - present
    - absent
    default: present
  ipsc_id:
    description:
    - The OCID of the IPSec connection.
    - Use this option for updates and deletion after creation.
    type: str
  compartment_id:
    description:
    - The OCID of the compartment that contains the connection.
    - Required for creation and name lookup.
    - This value is immutable after creation.
    type: str
  name:
    description:
    - The display name of the connection.
    - Required for creation.
    - When ipsc_id is omitted, compartment_id and name identify an existing connection.
    type: str
  cpe_id:
    description:
    - The OCID of the CPE for this connection.
    - Required for creation and immutable after creation.
    type: str
  drg_id:
    description:
    - The OCID of the DRG for this connection.
    - Required for creation and immutable after creation.
    type: str
  cpe_local_identifier:
    description: The local identifier for the CPE. This value is mutable.
    type: str
  cpe_local_identifier_type:
    description: The type of the CPE local identifier.
    type: str
    choices:
    - ip_address
    - hostname
  static_routes:
    description:
    - Static routes to the CPE.
    - Required for creation. An empty list is valid when both tunnels use BGP.
    - The complete route list is replaced on update.
    type: list
    elements: str
  tunnel_configuration:
    description:
    - Tunnel settings for connection creation.
    - The API supports at most two tunnel objects.
    - The module does not compare this option after creation.
    type: list
    elements: dict
    suboptions:
      name:
        description: A user-friendly tunnel name.
        type: str
      routing:
        description: The tunnel routing type.
        type: str
        choices:
        - bgp
        - static
        - policy
      ike_version:
        description: The Internet Key Exchange version.
        type: str
        choices:
        - v1
        - v2
      shared_secret:
        description: The pre-shared key for the tunnel.
        type: str
      bgp_session_config:
        description: BGP session settings for the tunnel.
        type: dict
        suboptions:
          oracle_interface_ip:
            description: The Oracle tunnel interface IPv4 address.
            type: str
          customer_interface_ip:
            description: The customer tunnel interface IPv4 address.
            type: str
          oracle_interface_ipv6:
            description: The Oracle tunnel interface IPv6 address.
            type: str
          customer_interface_ipv6:
            description: The customer tunnel interface IPv6 address.
            type: str
          customer_bgp_asn:
            description: The customer BGP autonomous system number.
            type: str
      oracle_initiation:
        description: Whether Oracle can initiate the tunnel.
        type: str
        choices:
        - initiator_or_responder
        - responder_only
      nat_translation_enabled:
        description: Whether NAT traversal is enabled.
        type: str
        choices:
        - enabled
        - disabled
        - auto
      phase_one_config:
        description: IKE phase one settings.
        type: dict
        suboptions:
          is_custom_phase_one_config:
            description: Whether custom phase one settings are used.
            type: bool
          authentication_algorithm:
            description: The phase one authentication algorithm.
            type: str
            choices:
            - sha2_384
            - sha2_256
            - sha1_96
          encryption_algorithm:
            description: The phase one encryption algorithm.
            type: str
            choices:
            - aes_256_cbc
            - aes_192_cbc
            - aes_128_cbc
          diffie_helman_group:
            description: The phase one Diffie-Hellman group.
            type: str
            choices:
            - group2
            - group5
            - group14
            - group19
            - group20
            - group24
          lifetime_in_seconds:
            description: The phase one key lifetime in seconds.
            type: int
      phase_two_config:
        description: IPSec phase two settings.
        type: dict
        suboptions:
          is_custom_phase_two_config:
            description: Whether custom phase two settings are used.
            type: bool
          authentication_algorithm:
            description:
            - The phase two authentication algorithm for CBC encryption.
            - Ignored with GCM encryption because GCM includes authentication.
            type: str
            choices:
            - hmac_sha2_256_128
            - hmac_sha1_128
          encryption_algorithm:
            description: The phase two encryption algorithm.
            type: str
            choices:
            - aes_256_gcm
            - aes_192_gcm
            - aes_128_gcm
            - aes_256_cbc
            - aes_192_cbc
            - aes_128_cbc
          lifetime_in_seconds:
            description: The phase two key lifetime in seconds.
            type: int
          is_pfs_enabled:
            description: Whether perfect forward secrecy is enabled.
            type: bool
          pfs_dh_group:
            description: The phase two Diffie-Hellman group.
            type: str
            choices:
            - group2
            - group5
            - group14
            - group19
            - group20
            - group24
      dpd_config:
        description: Dead peer detection settings.
        type: dict
        suboptions:
          dpd_mode:
            description: The dead peer detection mode.
            type: str
            choices:
            - initiate_and_respond
            - respond_only
          dpd_timeout_in_sec:
            description: The dead peer detection timeout in seconds.
            type: int
      encryption_domain_config:
        description: Traffic selectors for the tunnel.
        type: dict
        suboptions:
          oracle_traffic_selector:
            description: Oracle traffic CIDRs.
            type: list
            elements: str
          cpe_traffic_selector:
            description: CPE traffic CIDRs.
            type: list
            elements: str
  tunnels:
    description:
    - Updates to existing tunnels identified by tunnel_id.
    - Requires an existing connection. Omitted tunnels are unchanged.
    - An empty list makes no tunnel changes.
    - The module waits before dependent tunnel or secret updates, even when O(wait=false).
    - Settings are updated before shared secrets. Completed changes remain applied if a later operation fails.
    type: list
    elements: dict
    suboptions:
      tunnel_id:
        description: The OCID of an existing tunnel.
        type: str
        required: true
      name:
        description: A user-friendly tunnel name.
        type: str
      routing:
        description: The tunnel routing type.
        type: str
        choices:
        - bgp
        - static
        - policy
      ike_version:
        description: The Internet Key Exchange version.
        type: str
        choices:
        - v1
        - v2
      shared_secret:
        description:
        - The new pre-shared key for this tunnel.
        - When omitted, the module does not read or update the shared secret.
        - Updating the secret can interrupt tunnel traffic during reprovisioning.
        type: str
      bgp_session_config:
        description: BGP session settings for the tunnel.
        type: dict
        suboptions:
          oracle_interface_ip:
            description: The Oracle tunnel interface IPv4 address.
            type: str
          customer_interface_ip:
            description: The customer tunnel interface IPv4 address.
            type: str
          oracle_interface_ipv6:
            description: The Oracle tunnel interface IPv6 address.
            type: str
          customer_interface_ipv6:
            description: The customer tunnel interface IPv6 address.
            type: str
          customer_bgp_asn:
            description: The customer BGP autonomous system number.
            type: str
      oracle_initiation:
        description: Whether Oracle can initiate the tunnel.
        type: str
        choices:
        - initiator_or_responder
        - responder_only
      nat_translation_enabled:
        description: Whether NAT traversal is enabled.
        type: str
        choices:
        - enabled
        - disabled
        - auto
      phase_one_config:
        description: IKE phase one settings.
        type: dict
        suboptions:
          is_custom_phase_one_config:
            description: Whether custom phase one settings are used.
            type: bool
          authentication_algorithm:
            description: The phase one authentication algorithm.
            type: str
            choices:
            - sha2_384
            - sha2_256
            - sha1_96
          encryption_algorithm:
            description: The phase one encryption algorithm.
            type: str
            choices:
            - aes_256_cbc
            - aes_192_cbc
            - aes_128_cbc
          diffie_helman_group:
            description: The phase one Diffie-Hellman group.
            type: str
            choices:
            - group2
            - group5
            - group14
            - group19
            - group20
            - group24
          lifetime_in_seconds:
            description: The phase one key lifetime in seconds.
            type: int
      phase_two_config:
        description: IPSec phase two settings.
        type: dict
        suboptions:
          is_custom_phase_two_config:
            description: Whether custom phase two settings are used.
            type: bool
          authentication_algorithm:
            description:
            - The phase two authentication algorithm for CBC encryption.
            - Ignored with GCM encryption because GCM includes authentication.
            type: str
            choices:
            - hmac_sha2_256_128
            - hmac_sha1_128
          encryption_algorithm:
            description: The phase two encryption algorithm.
            type: str
            choices:
            - aes_256_gcm
            - aes_192_gcm
            - aes_128_gcm
            - aes_256_cbc
            - aes_192_cbc
            - aes_128_cbc
          lifetime_in_seconds:
            description: The phase two key lifetime in seconds.
            type: int
          is_pfs_enabled:
            description: Whether perfect forward secrecy is enabled.
            type: bool
          pfs_dh_group:
            description: The phase two Diffie-Hellman group.
            type: str
            choices:
            - group2
            - group5
            - group14
            - group19
            - group20
            - group24
      dpd_config:
        description: Dead peer detection settings.
        type: dict
        suboptions:
          dpd_mode:
            description: The dead peer detection mode.
            type: str
            choices:
            - initiate_and_respond
            - respond_only
          dpd_timeout_in_sec:
            description: The dead peer detection timeout in seconds.
            type: int
      encryption_domain_config:
        description: Traffic selectors for the tunnel.
        type: dict
        suboptions:
          oracle_traffic_selector:
            description: Oracle traffic CIDRs.
            type: list
            elements: str
          cpe_traffic_selector:
            description: CPE traffic CIDRs.
            type: list
            elements: str
"""

EXAMPLES = r"""
- name: Create the CPE
  ansible.oci.oci_network_cpe:
    compartment_id: ocid1.compartment.oc1..example
    name: site-cpe
    ip_address: 203.0.113.2
  register: cpe

- name: Create an IPSec connection with two tunnel configurations
  ansible.oci.oci_network_ipsec_connection:
    compartment_id: ocid1.compartment.oc1..example
    name: site-vpn
    cpe_id: "{{ cpe.resource.id }}"
    drg_id: ocid1.drg.oc1..example
    static_routes: [10.10.0.0/16]
    tunnel_configuration:
      - name: primary
        routing: bgp
        ike_version: v2
        shared_secret: "{{ vault_primary_secret }}"
        bgp_session_config:
          oracle_interface_ip: 169.254.10.1/30
          customer_interface_ip: 169.254.10.2/30
          customer_bgp_asn: "64512"
      - name: backup
        routing: static
        ike_version: v2
  register: vpn

- name: Read tunnel IDs
  ansible.oci.oci_network_ipsec_connection_info:
    ipsc_id: "{{ vpn.resource.id }}"
    include_tunnels: true
  register: vpn_info

- name: Update an existing tunnel and its secret
  ansible.oci.oci_network_ipsec_connection:
    ipsc_id: "{{ vpn.resource.id }}"
    tunnels:
      - tunnel_id: "{{ vpn_info.ipsec_connections[0].tunnels[0].id }}"
        routing: bgp
        phase_two_config:
          is_pfs_enabled: true
        shared_secret: "{{ vault_updated_secret }}"

- name: Read tunnel details and shared secrets
  ansible.oci.oci_network_ipsec_connection_info:
    ipsc_id: "{{ vpn.resource.id }}"
    include_shared_secret: true
  register: vpn_with_secrets
  no_log: true

- name: Delete the IPSec connection and its tunnels
  ansible.oci.oci_network_ipsec_connection:
    state: absent
    ipsc_id: "{{ vpn.resource.id }}"
"""

RETURN = r"""
resource:
  description: The IPSec connection.
  returned: when state=present, except when check mode predicts a change
  type: dict
  contains:
    id:
      description: The OCID of the IPSec connection.
      type: str
    name:
      description: The display name of the connection.
      type: str
    compartment_id:
      description: The connection compartment OCID.
      type: str
    cpe_id:
      description: The CPE OCID.
      type: str
    drg_id:
      description: The DRG OCID.
      type: str
    cpe_local_identifier:
      description: The CPE local identifier.
      type: str
    cpe_local_identifier_type:
      description: The CPE local identifier type.
      type: str
    static_routes:
      description: Static routes for the connection.
      type: list
      elements: str
    lifecycle_state:
      description: The connection lifecycle state.
      type: str
    transport_type:
      description: The connection transport type.
      type: str
    time_created:
      description: The connection creation time.
      type: str
    freeform_tags:
      description: Free-form tags.
      type: dict
    defined_tags:
      description: Defined tags.
      type: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_COMMON_ARGS,
    build_model,
    normalize_enum_values,
    rename_aliased_fields,
    serialize_oci_model,
    values_differ_as_subset,
    import_oci_sdk,
    strip_none_values,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
    _fetch_during_wait,
)

oci = import_oci_sdk()[0]

CREATE_REQUIRED_FIELDS = ("compartment_id", "name", "cpe_id", "drg_id", "static_routes")
AVAILABLE = ("AVAILABLE",)


ENUM_KEYS = frozenset(
    {
        "routing",
        "ike_version",
        "oracle_initiation",
        "nat_translation_enabled",
        "cpe_local_identifier_type",
        "authentication_algorithm",
        "encryption_algorithm",
        "diffie_helman_group",
        "pfs_dh_group",
        "dpd_mode",
    }
)

DH_GROUPS = ["group2", "group5", "group14", "group19", "group20", "group24"]
TUNNEL_OPTIONS = {
    "name": dict(type="str"),
    "routing": dict(type="str", choices=["bgp", "static", "policy"]),
    "ike_version": dict(type="str", choices=["v1", "v2"]),
    "shared_secret": dict(type="str", no_log=True),
    "bgp_session_config": dict(
        type="dict",
        options={
            "oracle_interface_ip": dict(type="str"),
            "customer_interface_ip": dict(type="str"),
            "oracle_interface_ipv6": dict(type="str"),
            "customer_interface_ipv6": dict(type="str"),
            "customer_bgp_asn": dict(type="str"),
        },
    ),
    "oracle_initiation": dict(
        type="str",
        choices=["initiator_or_responder", "responder_only"],
    ),
    "nat_translation_enabled": dict(
        type="str",
        choices=["enabled", "disabled", "auto"],
    ),
    "phase_one_config": dict(
        type="dict",
        options={
            "is_custom_phase_one_config": dict(type="bool"),
            "authentication_algorithm": dict(
                type="str",
                choices=["sha2_384", "sha2_256", "sha1_96"],
            ),
            "encryption_algorithm": dict(
                type="str",
                choices=["aes_256_cbc", "aes_192_cbc", "aes_128_cbc"],
            ),
            "diffie_helman_group": dict(type="str", choices=DH_GROUPS),
            "lifetime_in_seconds": dict(type="int"),
        },
    ),
    "phase_two_config": dict(
        type="dict",
        options={
            "is_custom_phase_two_config": dict(type="bool"),
            "authentication_algorithm": dict(
                type="str",
                choices=["hmac_sha2_256_128", "hmac_sha1_128"],
            ),
            "encryption_algorithm": dict(
                type="str",
                choices=[
                    "aes_256_gcm",
                    "aes_192_gcm",
                    "aes_128_gcm",
                    "aes_256_cbc",
                    "aes_192_cbc",
                    "aes_128_cbc",
                ],
            ),
            "lifetime_in_seconds": dict(type="int"),
            "is_pfs_enabled": dict(type="bool"),
            "pfs_dh_group": dict(type="str", choices=DH_GROUPS),
        },
    ),
    "dpd_config": dict(
        type="dict",
        options={
            "dpd_mode": dict(
                type="str", choices=["initiate_and_respond", "respond_only"]
            ),
            "dpd_timeout_in_sec": dict(type="int"),
        },
    ),
    "encryption_domain_config": dict(
        type="dict",
        options={
            "oracle_traffic_selector": dict(type="list", elements="str"),
            "cpe_traffic_selector": dict(type="list", elements="str"),
        },
    ),
}


PHASE_CONFIG_FIELDS = {
    "phase_one_details": (
        "phase_one_config",
        {
            "is_custom_phase_one_config": "is_custom_phase_one_config",
            "custom_authentication_algorithm": "authentication_algorithm",
            "custom_encryption_algorithm": "encryption_algorithm",
            "lifetime": "lifetime_in_seconds",
            "custom_dh_group": "diffie_helman_group",
        },
    ),
    "phase_two_details": (
        "phase_two_config",
        {
            "is_custom_phase_two_config": "is_custom_phase_two_config",
            "custom_authentication_algorithm": "authentication_algorithm",
            "custom_encryption_algorithm": "encryption_algorithm",
            "lifetime": "lifetime_in_seconds",
            "dh_group": "pfs_dh_group",
            "is_pfs_enabled": "is_pfs_enabled",
        },
    ),
}


def _phase_two_config(fields, current=None):
    """Remove separate authentication when phase two uses GCM encryption.

    Args:
        fields: Requested phase two fields with normalized enums.
        current: Current phase two fields for partial updates.

    Returns:
        Requested fields with authentication removed when GCM applies.
    """
    fields = dict(fields or {})
    algorithm = fields.get("encryption_algorithm") or (current or {}).get(
        "encryption_algorithm", ""
    )
    if algorithm.endswith("_GCM"):
        fields.pop("authentication_algorithm", None)
    return fields


def build_tunnel_details(fields, model_class):
    """Build nested tunnel models from the SDK field types.

    Args:
        fields: Supplied tunnel fields.
        model_class: SDK tunnel class for creation or update requests.

    Returns:
        The SDK tunnel request model.
    """
    fields = normalize_enum_values(strip_none_values(fields), ENUM_KEYS)
    fields = rename_aliased_fields(fields, {"name": "display_name"})
    if "phase_two_config" in fields:
        fields["phase_two_config"] = _phase_two_config(fields["phase_two_config"])

    field_types = model_class().swagger_types
    for field, value in fields.items():
        if isinstance(value, dict):
            nested_class = getattr(oci.core.models, field_types[field])
            fields[field] = build_model(value, nested_class)
    return build_model(fields, model_class)


def normalize_tunnel(value):
    """Map tunnel response fields to comparable request fields.

    Args:
        value: SDK tunnel model or mapping of desired fields.

    Returns:
        Configured fields with normalized enums and selector order.
    """
    value = rename_aliased_fields(
        strip_none_values(serialize_oci_model(value)),
        {
            "bgp_session_info": "bgp_session_config",
            "oracle_can_initiate": "oracle_initiation",
        },
    )
    dpd = {
        key: value[key]
        for key in ("dpd_mode", "dpd_timeout_in_sec")
        if key in value
    }
    if dpd:
        value["dpd_config"] = dpd

    for response_field, (request_field, aliases) in PHASE_CONFIG_FIELDS.items():
        details = value.pop(response_field, None)
        if details is not None:
            configured = {key: details.get(key) for key in aliases}
            value[request_field] = rename_aliased_fields(configured, aliases)

    value = normalize_enum_values(strip_none_values(value), ENUM_KEYS)
    if "encryption_domain_config" in value:
        value["encryption_domain_config"] = {
            key: sorted(selectors)
            for key, selectors in value["encryption_domain_config"].items()
        }
    return value


def tunnel_field_changes(current, desired):
    """Find changes to supplied tunnel fields.

    Args:
        current: Current SDK tunnel.
        desired: Supplied update fields without the secret or tunnel ID.

    Returns:
        Changed fields in the SDK request shape.
    """
    actual = normalize_tunnel(current)
    desired = normalize_tunnel(desired)
    if "phase_two_config" in desired:
        desired["phase_two_config"] = _phase_two_config(
            desired["phase_two_config"], actual.get("phase_two_config")
        )

    # OCI returns null after an IPv4 BGP interface is cleared.
    current_bgp = actual.setdefault("bgp_session_config", {})
    current_bgp.setdefault("oracle_interface_ip", "")
    current_bgp.setdefault("customer_interface_ip", "")
    return {
        key: value
        for key, value in desired.items()
        if values_differ_as_subset(actual.get(key), value)
    }


def _tunnel_options(item):
    """Extract tunnel settings without identifiers or secrets.

    Args:
        item: One tunnel update entry.

    Returns:
        Supplied SDK update fields.
    """
    fields = strip_none_values(dict(item))
    fields.pop("tunnel_id", None)
    name = fields.pop("name", None)
    if name is not None:
        fields["display_name"] = name
    fields.pop("shared_secret", None)
    return fields


class OciNetworkIpsecConnectionModule(OciResourceBase):
    """Manage IPSec connections and their existing tunnels."""

    @property
    def client_class(self):
        """Return the SDK client class.

        Returns:
            The OCI virtual network client class.
        """
        return oci.core.VirtualNetworkClient

    resource_id_param = "ipsc_id"
    list_resource_method = "list_ip_sec_connections"
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "IPSec connection"
    update_method_name = "update_ip_sec_connection"
    update_details_name = "update_ip_sec_connection_details"
    update_wait_states = AVAILABLE
    update_field_specs = (
        UpdateFieldSpec(
            param_name="name", resource_field="display_name", is_mutable=True
        ),
        UpdateFieldSpec(
            param_name="static_routes", is_mutable=True, compare="sorted_list"
        ),
        UpdateFieldSpec(param_name="cpe_local_identifier", is_mutable=True),
        UpdateFieldSpec(
            param_name="cpe_local_identifier_type",
            is_mutable=True,
            compare="enum",
        ),
        UpdateFieldSpec(param_name="compartment_id", is_mutable=False),
        UpdateFieldSpec(param_name="cpe_id", is_mutable=False),
        UpdateFieldSpec(param_name="drg_id", is_mutable=False),
    )

    def get_resource_response(self, resource_id):
        """Fetch one connection through the shared retry helper.

        Args:
            resource_id: Connection OCID.

        Returns:
            The SDK response.
        """
        return self.call_with_retry(
            self.client.get_ip_sec_connection, ipsc_id=resource_id
        )

    def compare_update_field_values(self, current_value, desired_value, compare=None):
        """Extend shared comparison for lowercase enum inputs.

        Args:
            current_value: Current SDK field value.
            desired_value: Supplied module field value.
            compare: Comparison strategy.

        Returns:
            True when the values differ.
        """
        if compare == "enum":
            desired_value = desired_value.upper()
            compare = None
        return super().compare_update_field_values(
            current_value, desired_value, compare
        )

    def validate_create_request(self):
        """Extend create validation to reject updates to nonexistent tunnels."""
        super().validate_create_request()
        if self.module.params.get("tunnels"):
            self.module.fail_json(
                msg="tunnels requires an existing connection. Use tunnel_configuration during creation."
            )
        if len(self.module.params.get("tunnel_configuration") or []) > 2:
            self.module.fail_json(
                msg="tunnel_configuration accepts at most two tunnels."
            )

    def create_resource(self):
        """Create a connection with its initial tunnel settings.

        Returns:
            The immediate or completed connection model.
        """
        fields = {
            key: self.module.params.get(key)
            for key in (
                "compartment_id",
                "cpe_id",
                "drg_id",
                "static_routes",
                "cpe_local_identifier",
                "cpe_local_identifier_type",
                "freeform_tags",
                "defined_tags",
                "tunnel_configuration",
            )
        }
        fields["display_name"] = self.module.params.get("name")
        if fields["tunnel_configuration"] is not None:
            fields["tunnel_configuration"] = [
                build_tunnel_details(tunnel, oci.core.models.CreateIPSecConnectionTunnelDetails)
                for tunnel in fields["tunnel_configuration"]
            ]
        response = self.call_with_retry(
            self.client.create_ip_sec_connection,
            create_ip_sec_connection_details=build_model(
                fields,
                oci.core.models.CreateIPSecConnectionDetails,
                enum_keys=ENUM_KEYS,
            ),
        )
        return self.get_mutation_result(response.data, response.data.id, AVAILABLE)

    def build_update_details(self, update_model_fields):
        """Build the connection update model used by the shared update flow.

        Args:
            update_model_fields: Fields selected by the shared update planner.

        Returns:
            The typed SDK update model.
        """
        return build_model(
            update_model_fields,
            oci.core.models.UpdateIPSecConnectionDetails,
            enum_keys=ENUM_KEYS,
        )

    def get_mutation_result(self, response_data, resource_id, target_states):
        """Extend shared waiting to complete parent changes before tunnel changes.

        Args:
            response_data: Data returned by the successful mutation.
            resource_id: Connection OCID.
            target_states: Expected connection lifecycle states.

        Returns:
            The immediate or completed connection model.
        """
        self._mutation_completed = True
        try:
            if (
                not self.module.params.get("wait", True)
                and getattr(self, "_cached_tunnel_plan", None)
                and tuple(target_states) == AVAILABLE
            ):
                return self._wait_for_response(
                    lambda: self.get_resource_response(resource_id),
                ).data
            return super().get_mutation_result(
                response_data, resource_id, target_states
            )
        except Exception as exc:
            self.module.fail_json(
                changed=True,
                msg="The OCI change completed, but waiting failed: %s" % exc,
            )

    def resolve_target_resource(self):
        """Extend lookup to validate every tunnel before any connection mutation.

        Returns:
            The current connection, or None when it is absent.
        """
        resource = super().resolve_target_resource()
        if (
            resource is not None
            and self.module.params.get("state", "present") == "present"
        ):
            self._validate_tunnels(resource.id)
        return resource

    def _validate_tunnels(self, ipsc_id):
        """Check tunnel identifiers and connection ownership.

        Args:
            ipsc_id: Connection OCID.
        """
        ids = [item["tunnel_id"] for item in self.module.params.get("tunnels") or []]
        if len(ids) != len(set(ids)):
            self.module.fail_json(
                msg="tunnels must not contain duplicate tunnel_id values."
            )
        if not ids:
            return
        current = self.list_all_resources(
            self.client.list_ip_sec_connection_tunnels,
            ipsc_id=ipsc_id,
        )
        known = {item.id for item in current}
        missing = [tunnel_id for tunnel_id in ids if tunnel_id not in known]
        if missing:
            self.module.fail_json(
                msg="Tunnel IDs do not belong to the IPSec connection: %s"
                % ", ".join(missing),
            )

    def _tunnel_plan(self, ipsc_id):
        """Build the tunnel change plan once before mutations.

        Args:
            ipsc_id: Connection OCID.

        Returns:
            Settings and secret changes for the requested tunnels.
        """
        if getattr(self, "_cached_tunnel_plan", None) is not None:
            return self._cached_tunnel_plan
        plan = []
        for item in self.module.params.get("tunnels") or []:
            current = self.call_with_retry(
                self.client.get_ip_sec_connection_tunnel,
                ipsc_id=ipsc_id,
                tunnel_id=item["tunnel_id"],
            ).data
            fields = tunnel_field_changes(current, _tunnel_options(item))
            secret_change = False
            if item.get("shared_secret") is not None:
                current_secret = self.call_with_retry(
                    self.client.get_ip_sec_connection_tunnel_shared_secret,
                    ipsc_id=ipsc_id,
                    tunnel_id=item["tunnel_id"],
                ).data
                secret_change = current_secret.shared_secret != item["shared_secret"]
            if fields or secret_change:
                plan.append({"item": item, "fields": fields, "secret": secret_change})
        self._cached_tunnel_plan = plan
        return plan

    def extra_change_needed(self, resource):
        """Use the shared extra-change hook for tunnel updates.

        Args:
            resource: Current connection.

        Returns:
            True when a tunnel setting or secret differs.
        """
        return bool(self._tunnel_plan(resource.id))

    def _apply_tunnel_settings(self, ipsc_id, entry):
        """Update tunnel settings and wait before dependent secret updates.

        Args:
            ipsc_id: Connection OCID.
            entry: Planned changes for one tunnel.
        """
        if not entry["fields"]:
            return

        tunnel_id = entry["item"]["tunnel_id"]
        details = build_tunnel_details(
            entry["fields"], oci.core.models.UpdateIPSecConnectionTunnelDetails
        )
        self.call_with_retry(
            self.client.update_ip_sec_connection_tunnel,
            ipsc_id=ipsc_id,
            tunnel_id=tunnel_id,
            update_ip_sec_connection_tunnel_details=details,
        )
        self._mutation_completed = True
        if self.module.params.get("wait", True) or entry["secret"]:
            self._wait_for_tunnel(ipsc_id, tunnel_id)

    def _apply_tunnel_secret(self, ipsc_id, entry):
        """Update a changed tunnel secret and apply the requested final wait.

        Args:
            ipsc_id: Connection OCID.
            entry: Planned changes for one tunnel.
        """
        if not entry["secret"]:
            return

        item = entry["item"]
        details = build_model(
            {"shared_secret": item["shared_secret"]},
            oci.core.models.UpdateIPSecConnectionTunnelSharedSecretDetails,
        )
        self.call_with_retry(
            self.client.update_ip_sec_connection_tunnel_shared_secret,
            ipsc_id=ipsc_id,
            tunnel_id=item["tunnel_id"],
            update_ip_sec_connection_tunnel_shared_secret_details=details,
        )
        self._mutation_completed = True
        if self.module.params.get("wait", True):
            self._wait_for_tunnel(ipsc_id, item["tunnel_id"])

    def apply_extra_change(self, resource):
        """Apply tunnel changes through the shared lifecycle hook.

        Args:
            resource: Connection after any parent update.

        Returns:
            The connection model without secret data.
        """
        try:
            for entry in self._tunnel_plan(resource.id):
                self._apply_tunnel_settings(resource.id, entry)
                self._apply_tunnel_secret(resource.id, entry)
        except Exception as exc:
            self.module.fail_json(
                changed=getattr(self, "_mutation_completed", False),
                msg="IPSec tunnel update failed. Completed changes remain applied: %s"
                % exc,
            )
        self._cached_tunnel_plan = []
        return resource

    def _wait_for_response(self, fetch):
        """Wait for a connection or tunnel through the SDK waiter.

        Args:
            fetch: Function that returns a fresh SDK response.

        Returns:
            The response with lifecycle state AVAILABLE.
        """
        return oci.wait_until(
            self.client,
            fetch(),
            max_interval_seconds=self.module.params.get("wait_interval", 30),
            max_wait_seconds=self.module.params.get("wait_timeout", 1200),
            evaluate_response=lambda response: response.data.lifecycle_state
            in AVAILABLE,
            fetch_func=lambda response=None: _fetch_during_wait(fetch, response),
        )

    def _wait_for_tunnel(self, ipsc_id, tunnel_id):
        """Wait for tunnel availability using both correct resource identifiers.

        Args:
            ipsc_id: Connection OCID.
            tunnel_id: Tunnel OCID.

        Returns:
            The completed SDK response.
        """
        return self._wait_for_response(
            lambda: self.call_with_retry(
                self.client.get_ip_sec_connection_tunnel,
                ipsc_id=ipsc_id,
                tunnel_id=tunnel_id,
            )
        )

    def delete_resource(self, resource):
        """Delete the connection and its tunnels through the shared helper.

        Args:
            resource: Connection to delete.

        Returns:
            The immediate or completed deletion result.
        """
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_ip_sec_connection,
            ipsc_id=resource.id,
        )


def main():
    """Initialize and run the IPSec connection module."""
    spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        ipsc_id=dict(type="str"),
        name=dict(type="str"),
        cpe_id=dict(type="str"),
        drg_id=dict(type="str"),
        static_routes=dict(type="list", elements="str"),
        cpe_local_identifier=dict(type="str"),
        cpe_local_identifier_type=dict(type="str", choices=["ip_address", "hostname"]),
        tunnel_configuration=dict(type="list", elements="dict", options=TUNNEL_OPTIONS),
        tunnels=dict(
            type="list",
            elements="dict",
            options=dict(TUNNEL_OPTIONS, tunnel_id=dict(type="str", required=True)),
        ),
    )
    module = AnsibleModule(argument_spec=spec, supports_check_mode=True)
    OciNetworkIpsecConnectionModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
