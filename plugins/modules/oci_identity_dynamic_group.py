# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_identity_dynamic_group
short_description: Manage a dynamic group in an OCI IAM identity domain
description:
  - Creates, updates, and deletes dynamic groups through the OCI IAM Identity Domains System for Cross-domain Identity Management (SCIM) API.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_tags_options
options:
  state:
    description: Desired state of the dynamic group.
    type: str
    choices: [present, absent]
    default: present
  domain_id:
    description:
      - OCID of the identity domain.
      - Set exactly one of C(domain_id) or C(domain_url).
    type: str
  domain_url:
    description:
      - Service endpoint of the identity domain.
      - Set exactly one of C(domain_id) or C(domain_url).
    type: str
  dynamic_group_id:
    description: SCIM identifier of the dynamic group.
    type: str
  name:
    description:
      - Display name of the dynamic group.
      - Set a nonempty value to create a dynamic group.
      - Used for exact lookup when C(dynamic_group_id) is omitted.
    type: str
  description:
    description: Description of the dynamic group.
    type: str
  matching_rule:
    description:
      - Matching rule for the dynamic group.
      - Set a nonempty value to create a dynamic group.
    type: str
"""

EXAMPLES = r"""
- name: Create a dynamic group
  ansible.oci.oci_identity_dynamic_group:
    domain_id: ocid1.domain.oc1..example
    name: compute-instances
    matching_rule: "instance.compartment.id = 'ocid1.compartment.oc1..example'"

- name: Update a dynamic group
  ansible.oci.oci_identity_dynamic_group:
    domain_url: https://idcs-example.identity.oraclecloud.com
    dynamic_group_id: 0123456789abcdef
    description: Compute instances for the application
    matching_rule: "ALL {instance.compartment.id = 'ocid1.compartment.oc1..example'}"

- name: Delete a dynamic group
  ansible.oci.oci_identity_dynamic_group:
    domain_id: ocid1.domain.oc1..example
    dynamic_group_id: 0123456789abcdef
    state: absent
"""

RETURN = r"""
resource:
  description: The dynamic group in the identity domain.
  returned: when state is present, except check mode that predicts a change
  type: dict
  contains:
    id:
      description: SCIM identifier.
      type: str
    ocid:
      description: OCI identifier, when exposed by the identity domain.
      type: str
    domain_id:
      description: OCID of the identity domain containing the dynamic group.
      type: str
    name:
      description: Display name.
      type: str
    description:
      description: Description of the dynamic group.
      type: str
    matching_rule:
      description: Matching rule of the dynamic group.
      type: str
    freeform_tags:
      description: Freeform tags on the dynamic group.
      type: dict
    defined_tags:
      description: Defined tags on the dynamic group, including tags applied by OCI.
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
    build_model,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_identity_domains import (
    CORE_DYNAMIC_GROUP_SCHEMA,
    OCI_IDENTITY_DOMAIN_ARGS,
    OciIdentityDomainResourceBase,
    build_schemas,
    build_tags_extension,
    serialize_dynamic_group,
)

oci = import_oci_sdk()[0]


def build_dynamic_group(params):
    """Build the SDK model for an Identity Domains dynamic group.

    Args:
        params: Ansible module parameters.

    Returns:
        An Identity Domains DynamicResourceGroup model.
    """
    tags = build_tags_extension(
        params.get("freeform_tags"), params.get("defined_tags")
    )
    return build_model(
        {
            "schemas": build_schemas(CORE_DYNAMIC_GROUP_SCHEMA, tags is not None),
            "display_name": params.get("name"),
            "description": params.get("description"),
            "matching_rule": params.get("matching_rule"),
            "urn_ietf_params_scim_schemas_oracle_idcs_extension_oci_tags": tags,
        },
        oci.identity_domains.models.DynamicResourceGroup,
    )


class OciIdentityDynamicGroupModule(OciIdentityDomainResourceBase):
    """Manage one Identity Domains dynamic group."""

    resource_id_param = "dynamic_group_id"
    resource_id_kwarg = "dynamic_resource_group_id"
    list_resource_method = "list_dynamic_resource_groups"
    name_lookup_param = "name"
    common_list_filter_params = ()
    create_required_fields = ("name", "matching_rule")
    create_resource_name = "dynamic group"
    patch_method_name = "patch_dynamic_resource_group"
    scim_update_paths = (
        ("name", "displayName"),
        ("description", "description"),
        ("matching_rule", "matchingRule"),
    )
    scim_response_attributes = ("matchingRule",)

    def serialize_result_resource(self, resource):
        """Serialize a dynamic group for module output and comparisons.

        The inherited serializer does not normalize SCIM tags and metadata.

        Args:
            resource: Identity Domains dynamic group model.

        Returns:
            A dictionary of dynamic group fields.
        """
        return serialize_dynamic_group(resource)

    def validate_create_request(self):
        """Require nonempty name and matching rule values for creation.

        The inherited validator permits empty strings and spaces.

        Raises:
            SystemExit: When a required value is empty.
        """
        super(OciIdentityDynamicGroupModule, self).validate_create_request()
        for field in ("name", "matching_rule"):
            if not self.module.params[field].strip():
                self.module.fail_json(
                    msg=f"Creating a dynamic group requires a nonempty {field}"
                )

    def get_resource_response(self, resource_id):
        """Get a dynamic group by its SCIM identifier.

        Args:
            resource_id: SCIM identifier of the dynamic group.

        Returns:
            The SDK response for the get operation.
        """
        return self.call_with_retry(
            self.client.get_dynamic_resource_group,
            dynamic_resource_group_id=resource_id,
            **self.get_scim_response_kwargs(),
        )

    def create_resource(self):
        """Create a dynamic group and return its SDK model.

        Returns:
            The created dynamic group model.
        """
        return self.call_with_retry(
            self.client.create_dynamic_resource_group,
            dynamic_resource_group=build_dynamic_group(self.module.params),
            **self.get_scim_response_kwargs(),
        ).data

    def delete_resource(self, resource):
        """Delete a dynamic group by its SCIM identifier.

        Args:
            resource: Dynamic group model to delete.
        """
        self.call_with_retry(
            self.client.delete_dynamic_resource_group,
            dynamic_resource_group_id=resource.id,
        )


def main():
    """Run the dynamic group resource module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_TAG_ARGS,
        **OCI_IDENTITY_DOMAIN_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        dynamic_group_id=dict(type="str"),
        name=dict(type="str"),
        description=dict(type="str"),
        matching_rule=dict(type="str"),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["domain_id", "domain_url"]],
        mutually_exclusive=[["domain_id", "domain_url"]],
    )
    OciIdentityDynamicGroupModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
