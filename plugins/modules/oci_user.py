# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_user
short_description: Manage a user in an OCI IAM identity domain
description:
  - Creates, updates, and deletes users through the OCI IAM Identity Domains SCIM API.
  - Supply either C(domain_id) or C(domain_url) to select the identity domain.
  - When C(user_id) is omitted, C(user_name) is used for exact lookup.
version_added: "1.1.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_tags_options
options:
  state:
    description: Desired state of the user.
    type: str
    choices: [present, absent]
    default: present
  domain_id:
    description: OCID of the identity domain. Mutually exclusive with C(domain_url).
    type: str
  domain_url:
    description: Service endpoint of the identity domain. Mutually exclusive with C(domain_id).
    type: str
  user_id:
    description: SCIM identifier of the user.
    type: str
  user_name:
    description: Unique login name. Required for creation.
    type: str
  name:
    description: Display name of the user.
    type: str
  given_name:
    description: Given name of the user.
    type: str
  family_name:
    description: Family name of the user. Required for creation.
    type: str
  email:
    description:
      - Work email address. An empty value is invalid.
      - Required for creation when the identity domain requires a primary email address.
    type: str
  description:
    description: Description of the user.
    type: str
  active:
    description: Whether the user can sign in.
    type: bool
"""

EXAMPLES = r"""
- name: Create a user in an identity domain
  ansible.oci.oci_user:
    domain_id: ocid1.domain.oc1..example
    user_name: application@example.com
    name: Application User
    given_name: Application
    family_name: User
    email: application@example.com
    active: true

- name: Disable a user using the domain endpoint directly
  ansible.oci.oci_user:
    domain_url: https://idcs-example.identity.oraclecloud.com
    user_id: 0123456789abcdef
    active: false
"""

RETURN = r"""
resource:
  description: The identity-domain user.
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
      description: OCID of the identity domain containing the user.
      type: str
    user_name:
      description: Login name.
      type: str
    name:
      description: Display name of the user.
      type: str
    given_name:
      description: Given name of the user, if present.
      type: str
    family_name:
      description: Family name of the user, if present.
      type: str
    email:
      description: Work email address, if present.
      type: str
    description:
      description: Description of the user, if present.
      type: str
    active:
      description: Whether the user can sign in.
      type: bool
    freeform_tags:
      description: Freeform tags on the user.
      type: dict
    defined_tags:
      description: Defined tags on the user, including tags applied automatically by OCI.
      type: dict
    time_created:
      description: User creation time from SCIM metadata, if present.
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
    CORE_USER_SCHEMA,
    OCI_IDENTITY_DOMAIN_ARGS,
    OCI_TAGS_SCHEMA,
    OciIdentityDomainsMixin,
    build_operation,
    build_patch_op,
    build_schemas,
    build_tags_extension,
    escape_scim_filter_value,
    normalize_defined_tags,
    normalize_freeform_tags,
    work_email,
    serialize_user,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import OciResourceBase

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]


def build_user(params):
    name = None
    if params.get("given_name") is not None or params.get("family_name") is not None:
        name = oci.identity_domains.models.UserName(
            given_name=params.get("given_name"),
            family_name=params.get("family_name"),
        )
    emails = None
    if params.get("email") is not None:
        emails = [
            oci.identity_domains.models.UserEmails(
                value=params["email"], type="work", primary=True
            )
        ]
    tags = build_tags_extension(
        params.get("freeform_tags"), params.get("defined_tags")
    )
    return oci.identity_domains.models.User(
        schemas=build_schemas(CORE_USER_SCHEMA, tags is not None),
        user_name=params.get("user_name"),
        display_name=params.get("name"),
        name=name,
        emails=emails,
        description=params.get("description"),
        active=params.get("active"),
        urn_ietf_params_scim_schemas_oracle_idcs_extension_oci_tags=tags,
    )


class OciUserModule(OciIdentityDomainsMixin, OciResourceBase):
    resource_id_param = "user_id"
    list_resource_method = "list_users"
    name_lookup_param = "user_name"
    name_response_field = "user_name"
    common_list_filter_params = ()
    create_required_fields = ("user_name", "family_name")
    create_resource_name = "user"
    common_update_field_specs = ()
    update_field_specs = ()

    def serialize_result_resource(self, resource):
        return serialize_user(resource)

    def validate_create_request(self):
        super(OciUserModule, self).validate_create_request()
        for field in self.create_required_fields:
            if not self.module.params[field].strip():
                self.module.fail_json(
                    msg=f"Creating a user requires a nonempty {field}"
                )
        self.validate_email()

    def validate_email(self):
        email = self.module.params.get("email")
        if email is not None and not email.strip():
            self.module.fail_json(msg="email must be a nonempty work address")

    def find_resources_by_name(self):
        if not self.has_name_lookup_request:
            return []
        value = escape_scim_filter_value(self.name_lookup_value)
        return self.list_all_resources(
            self.client.list_users, filter=f'userName eq "{value}"'
        )

    def get_resource_response(self, resource_id):
        return self.call_with_retry(self.client.get_user, user_id=resource_id)

    def create_resource(self):
        return self.call_with_retry(
            self.client.create_user, user=build_user(self.module.params)
        ).data

    def build_update_plan(self, resource):
        params = self.module.params
        name = getattr(resource, "name", None)
        tags = getattr(
            resource,
            "urn_ietf_params_scim_schemas_oracle_idcs_extension_oci_tags",
            None,
        )
        current = {
            "user_name": getattr(resource, "user_name", None),
            "name": getattr(resource, "display_name", None),
            "given_name": getattr(name, "given_name", None),
            "family_name": getattr(name, "family_name", None),
            "email": work_email(resource),
            "description": getattr(resource, "description", None),
            "active": getattr(resource, "active", None),
            "freeform_tags": normalize_freeform_tags(tags),
            "defined_tags": normalize_defined_tags(tags),
        }
        paths = {
            "user_name": "userName",
            "name": "displayName",
            "given_name": "name.givenName",
            "family_name": "name.familyName",
            "description": "description",
            "active": "active",
        }
        operations = []
        for param_name, path in paths.items():
            desired = params.get(param_name)
            if desired is not None and desired != current[param_name]:
                operations.append(build_operation("REPLACE", path, desired))
        self.validate_email()
        if params.get("email") is not None and params["email"] != current["email"]:
            emails = getattr(resource, "emails", None) or []
            if current["email"] is not None:
                operations.append(
                    build_operation(
                        "REPLACE", 'emails[type eq "work"].value', params["email"]
                    )
                )
            else:
                work = oci.identity_domains.models.UserEmails(
                    value=params["email"],
                    type="work",
                    primary=not any(
                        getattr(email, "primary", False) for email in emails
                    ),
                )
                operations.append(build_operation("ADD", "emails", [work]))
        tag_values = {
            "freeform_tags": ("freeformTags", oci.identity_domains.models.FreeformTags),
            "defined_tags": ("definedTags", oci.identity_domains.models.DefinedTags),
        }
        for param_name, (path, model) in tag_values.items():
            desired = params.get(param_name)
            if desired is None or desired == current[param_name]:
                continue
            if param_name == "freeform_tags":
                value = [model(key=key, value=val) for key, val in sorted(desired.items())]
            else:
                value = [
                    model(namespace=namespace, key=key, value=val)
                    for namespace, values in sorted(desired.items())
                    for key, val in sorted(values.items())
                ]
            operations.append(
                build_operation("REPLACE", f"{OCI_TAGS_SCHEMA}:{path}", value)
            )
        return {"update_needed": bool(operations), "operations": operations}

    def update_resource(self, resource):
        operations = self.get_update_plan(resource)["operations"]
        return self.call_with_retry(
            self.client.patch_user,
            user_id=resource.id,
            patch_op=build_patch_op(operations),
        ).data

    def delete_resource(self, resource):
        self.call_with_retry(self.client.delete_user, user_id=resource.id)


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_TAG_ARGS,
        **OCI_IDENTITY_DOMAIN_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        user_id=dict(type="str"),
        user_name=dict(type="str"),
        name=dict(type="str"),
        given_name=dict(type="str"),
        family_name=dict(type="str"),
        email=dict(type="str"),
        description=dict(type="str"),
        active=dict(type="bool"),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["domain_id", "domain_url"]],
        mutually_exclusive=[["domain_id", "domain_url"]],
    )
    OciUserModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
