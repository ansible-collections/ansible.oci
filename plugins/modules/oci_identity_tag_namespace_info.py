# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_identity_tag_namespace_info
short_description: Retrieve OCI tag namespace information
description:
  - Retrieve one tag namespace or list tag namespaces in a compartment.
  - This module does not change OCI resources.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  tag_namespace_id:
    description:
      - The OCID of a tag namespace to retrieve.
      - When set, this option takes priority over list filters.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment whose tag namespaces are listed.
      - Required when C(tag_namespace_id) is not set.
    type: str
  include_subcompartments:
    description:
      - Include namespaces from child compartments in the list.
    type: bool
    default: false
  lifecycle_state:
    description:
      - Filter namespaces by lifecycle state.
    type: str
    choices: [active, inactive, deleting, deleted]
  name:
    description:
      - Filter namespaces by name. The match is case-insensitive.
    type: str
"""

EXAMPLES = r"""
- name: List active tag namespaces
  ansible.oci.oci_identity_tag_namespace_info:
    compartment_id: ocid1.tenancy.oc1..example
    lifecycle_state: active

- name: List namespaces in child compartments
  ansible.oci.oci_identity_tag_namespace_info:
    compartment_id: ocid1.tenancy.oc1..example
    include_subcompartments: true

- name: Get one namespace
  ansible.oci.oci_identity_tag_namespace_info:
    tag_namespace_id: ocid1.tagnamespace.oc1..example
"""

RETURN = r"""
tag_namespaces:
  description: Tag namespaces that matched the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the namespace.
      type: str
      returned: always
      sample: ocid1.tagnamespace.oc1..example
    compartment_id:
      description: The OCID of the namespace compartment.
      type: str
      returned: always
      sample: ocid1.tenancy.oc1..example
    name:
      description: The namespace name.
      type: str
      returned: always
      sample: Operations
    description:
      description: The namespace description.
      type: str
      returned: always
      sample: Tags for operations resources
    is_retired:
      description: Whether the namespace is retired.
      type: bool
      returned: always
      sample: false
    lifecycle_state:
      description: The current lifecycle state of the namespace.
      type: str
      returned: always
      sample: ACTIVE
    time_created:
      description: The creation time in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
    freeform_tags:
      description: Free-form tags applied to the namespace.
      type: dict
      returned: always
      sample: {owner: platform}
    defined_tags:
      description: Defined tags applied to the namespace.
      type: dict
      returned: always
      sample: {Operations: {CostCenter: "42"}}
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
    normalize_enum_values,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

oci = import_oci_sdk()[0]


class OciIdentityTagNamespaceInfoModule(OciInfoBase):
    """Retrieve tag namespaces through the OCI identity client."""

    @property
    def client_class(self):
        """Return the OCI identity client class.

        Returns:
            The OCI identity client class.
        """
        return oci.identity.IdentityClient

    results_key = "tag_namespaces"
    resource_id_param = "tag_namespace_id"
    resource_get_method = "get_tag_namespace"
    list_resource_method = "list_tag_namespaces"
    list_filter_params = ("compartment_id", "include_subcompartments", "lifecycle_state")
    name_response_field = "name"

    def collect_list_filters(self, *param_groups):
        """Normalize lifecycle state because the base does not map enum values.

        Args:
            param_groups: Parameter groups supported by the list operation.

        Returns:
            Non-empty filters with lifecycle state in OCI casing.
        """
        filters = super(OciIdentityTagNamespaceInfoModule, self).collect_list_filters(
            *param_groups
        )
        return normalize_enum_values(filters, frozenset({"lifecycle_state"}))

    def filter_resources_by_display_name(self, resources, name_value):
        """Filter names case-insensitively because the base filter uses exact case.

        Args:
            resources: Namespace models returned by OCI.
            name_value: The requested namespace name.

        Returns:
            Namespace models whose names match without case sensitivity.
        """
        if name_value is None:
            return resources
        requested = name_value.casefold()
        return [
            resource
            for resource in resources
            if str(getattr(resource, self.name_response_field, "")).casefold()
            == requested
        ]


def main():
    """Create the Ansible module and run the namespace info query."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        tag_namespace_id=dict(type="str"),
        compartment_id=dict(type="str"),
        include_subcompartments=dict(type="bool", default=False),
        lifecycle_state=dict(
            type="str",
            choices=["active", "inactive", "deleting", "deleted"],
        ),
        name=dict(type="str"),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["tag_namespace_id", "compartment_id"]],
    )
    OciIdentityTagNamespaceInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
