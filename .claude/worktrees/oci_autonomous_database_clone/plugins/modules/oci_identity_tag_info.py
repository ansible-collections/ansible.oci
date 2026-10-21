# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_identity_tag_info
short_description: Get tag definitions from an OCI tag namespace
description:
  - Gets one tag by name or lists tags in an OCI tag namespace.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  tag_namespace_id:
    description: OCID of the tag namespace.
    type: str
    required: true
  name:
    description:
      - Case-insensitive name of one tag to get. Supply a nonempty name.
      - The supplied spelling is preserved.
    type: str
  lifecycle_state:
    description: Filter tags by lifecycle state when listing.
    type: str
    choices: [active, inactive, deleting, deleted]
"""

EXAMPLES = r"""
- name: List active tags in a namespace
  ansible.oci.oci_identity_tag_info:
    tag_namespace_id: ocid1.tagnamespace.oc1..example
    lifecycle_state: active

- name: Get one tag by name
  ansible.oci.oci_identity_tag_info:
    tag_namespace_id: ocid1.tagnamespace.oc1..example
    name: Environment
"""

RETURN = r"""
tags:
  description: Tag definitions that match the query.
  returned: always
  type: list
  elements: dict
  contains:
    name:
      description: Tag name with the spelling returned by OCI.
      type: str
    id:
      description: OCID of the tag definition.
      type: str
    tag_namespace_id:
      description: OCID of the tag namespace.
      returned: when name is supplied
      type: str
    lifecycle_state:
      description: Current tag lifecycle state.
      type: str
    is_retired:
      description: Whether the tag is retired.
      type: bool
    is_cost_tracking:
      description: Whether the tag is a cost-tracking tag.
      type: bool
    validator:
      description: Validator returned by get_tag. List summaries omit this field.
      type: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
    normalize_enum_values,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

oci = import_oci_sdk()[0]


class OciIdentityTagInfoModule(OciInfoBase):
    """Get one tag or list tag summaries in a namespace."""

    @property
    def client_class(self):
        """Return the OCI Identity client class.

        Returns:
            The SDK class used by the inherited client constructor.
        """
        return oci.identity.IdentityClient

    results_key = "tags"
    list_filter_params = ("tag_namespace_id", "lifecycle_state")

    def fetch_resources(self):
        """Get one named tag or list tags with an optional state filter.

        The inherited getter supplies one identifier. This API also requires the namespace.

        Returns:
            Full tag models for get, or tag summaries for list.

        Raises:
            SystemExit: If the supplied name is empty.
        """
        params = self.module.params
        namespace_id = params["tag_namespace_id"]
        name = params.get("name")
        if name is not None:
            if not name:
                self.module.fail_json(msg="name must be nonempty")
            return self.get_resource_by_id(
                name,
                self.client.get_tag,
                tag_namespace_id=namespace_id,
                tag_name=name,
            )
        kwargs = self.collect_list_filters(self.list_filter_params)
        kwargs = normalize_enum_values(kwargs, {"lifecycle_state"})
        return self.list_all_resources(
            self.client.list_tags,
            **kwargs,
        )


def main():
    """Configure and run the tag info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        tag_namespace_id=dict(type="str", required=True),
        name=dict(type="str"),
        lifecycle_state=dict(
            type="str", choices=["active", "inactive", "deleting", "deleted"]
        ),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    OciIdentityTagInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
