# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_group
short_description: Manage a group in an OCI IAM identity domain
description:
  - Creates, updates, and deletes groups through the OCI IAM Identity Domains SCIM API.
  - Supply either C(domain_id) or C(domain_url) to select the identity domain.
  - When C(group_id) is omitted, C(display_name) is used for exact lookup.
version_added: "1.1.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_tags_options
options:
  state:
    description: Desired state of the group.
    type: str
    choices: [present, absent]
    default: present
  domain_id:
    description: OCID of the identity domain. Mutually exclusive with C(domain_url).
    type: str
  domain_url:
    description: Service endpoint of the identity domain. Mutually exclusive with C(domain_id).
    type: str
  group_id:
    description: SCIM identifier of the group.
    type: str
  display_name:
    description: Display name of the group. A nonempty value is required for creation.
    type: str
"""

EXAMPLES = r"""
- name: Create a group
  ansible.oci.oci_group:
    domain_id: ocid1.domain.oc1..example
    display_name: application-admins

- name: Rename a group
  ansible.oci.oci_group:
    domain_url: https://idcs-example.identity.oraclecloud.com
    group_id: 0123456789abcdef
    display_name: application-operators

- name: Delete a group
  ansible.oci.oci_group:
    domain_id: ocid1.domain.oc1..example
    group_id: 0123456789abcdef
    state: absent
"""

RETURN = r"""
resource:
  description: The identity-domain group.
  returned: when state is present and check mode is off
  type: dict
  contains:
    id:
      description: SCIM identifier.
      type: str
    ocid:
      description: OCI identifier, when exposed by the identity domain.
      type: str
    domain_id:
      description: OCID of the identity domain containing the group.
      type: str
    display_name:
      description: Display name.
      type: str
    freeform_tags:
      description: Freeform tags on the group.
      type: dict
    defined_tags:
      description: Defined tags on the group, including tags applied automatically by OCI.
      type: dict
    time_created:
      description: Group creation time from SCIM metadata, if present.
      type: str
    time_modified:
      description: Last modification time from SCIM metadata, if present.
      type: str
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    OCI_TAG_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_identity_domains import (
    CORE_GROUP_SCHEMA,
    OCI_IDENTITY_DOMAIN_ARGS,
    OciIdentityDomainResourceBase,
    build_schemas,
    build_tags_extension,
    escape_scim_filter_value,
    serialize_group,
)

oci = import_oci_sdk()[0]


def build_group(params):
    tags = build_tags_extension(
        params.get("freeform_tags"), params.get("defined_tags")
    )
    return oci.identity_domains.models.Group(
        schemas=build_schemas(CORE_GROUP_SCHEMA, tags is not None),
        display_name=params.get("display_name"),
        urn_ietf_params_scim_schemas_oracle_idcs_extension_oci_tags=tags,
    )


class OciGroupModule(OciIdentityDomainResourceBase):
    resource_id_param = "group_id"
    list_resource_method = "list_groups"
    name_lookup_param = "display_name"
    common_list_filter_params = ()
    create_required_fields = ("display_name",)
    create_resource_name = "group"
    patch_method_name = "patch_group"
    scim_update_paths = (("display_name", "displayName"),)

    def serialize_result_resource(self, resource):
        return serialize_group(resource)

    def validate_create_request(self):
        super(OciGroupModule, self).validate_create_request()
        if not self.module.params["display_name"].strip():
            self.module.fail_json(
                msg="Creating a group requires a nonempty display_name"
            )

    def find_resources_by_name(self):
        if not self.has_name_lookup_request:
            return []
        value = escape_scim_filter_value(self.name_lookup_value)
        return self.list_all_resources(
            self.client.list_groups, filter=f'displayName eq "{value}"'
        )

    def get_resource_response(self, resource_id):
        return self.call_with_retry(self.client.get_group, group_id=resource_id)

    def create_resource(self):
        return self.call_with_retry(
            self.client.create_group, group=build_group(self.module.params)
        ).data

    def delete_resource(self, resource):
        self.call_with_retry(self.client.delete_group, group_id=resource.id)


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_TAG_ARGS,
        **OCI_IDENTITY_DOMAIN_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        group_id=dict(type="str"),
        display_name=dict(type="str"),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["domain_id", "domain_url"]],
        mutually_exclusive=[["domain_id", "domain_url"]],
    )
    OciGroupModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
