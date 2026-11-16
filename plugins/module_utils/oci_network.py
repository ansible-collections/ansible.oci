"""Shared VNIC arguments and IPv6 model construction."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import filter_none_values

VNIC_ARGS = dict(
    assign_ipv6_ip=dict(type="bool"),
    assign_public_ip=dict(type="bool"),
    assign_private_dns_record=dict(type="bool"),
    defined_tags=dict(type="dict"),
    display_name=dict(type="str"),
    freeform_tags=dict(type="dict"),
    security_attributes=dict(type="dict"),
    hostname_label=dict(type="str"),
    ipv6_address_ipv6_subnet_cidr_pair_details=dict(
        type="list",
        elements="dict",
        options=dict(
            ipv6_id=dict(type="str"),
            ipv6_subnet_cidr=dict(type="str"),
            ipv6_address=dict(type="str"),
        ),
    ),
    subnet_cidr=dict(type="str"),
    nsg_ids=dict(type="list", elements="str"),
    private_ip=dict(type="str"),
    private_ip_id=dict(type="str"),
    skip_source_dest_check=dict(type="bool"),
    subnet_id=dict(type="str"),
    vlan_id=dict(type="str"),
)


def build_ipv6_address_pairs(pairs, model_class):
    """Build IPv6 SDK models without changing the supplied dictionaries."""
    if pairs is None:
        return None
    return [model_class(**filter_none_values(pair)) for pair in pairs]
