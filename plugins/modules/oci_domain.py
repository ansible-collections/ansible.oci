# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_domain
short_description: Manage OCI identity domains
description:
  - Create, update, and delete OCI identity domains.
  - Identity domains are compartment-scoped resources. Use the compartment
    OCID as C(compartment_id).
  - Domain creation, update, and deletion are asynchronous operations.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_name_lookup_options
  - ansible.oci.oci_wait_options
  - ansible.oci.oci_tags_options
options:
  state:
    description:
      - The desired lifecycle state of the identity domain.
    type: str
    choices: [present, absent]
    default: present
  domain_id:
    description:
      - The OCID of the identity domain to manage.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the identity domain.
      - Required when creating a domain and when looking up a domain by C(name).
    type: str
  name:
    description:
      - The mutable display name of the identity domain.
      - Required when creating a domain.
    type: str
  description:
    description:
      - The identity domain description. It may be empty.
      - Required when creating a domain.
    type: str
  home_region:
    description:
      - The OCI region where the identity domain is homed.
      - This is the domain property and is separate from the OCI client
        authentication region.
      - Required when creating a domain and immutable afterwards.
    type: str
  license_type:
    description:
      - The license type for the identity domain.
      - Required when creating a domain and immutable through this module.
    type: str
  is_hidden_on_login:
    description:
      - Whether the domain is hidden on the sign-in screen.
    type: bool
  admin_first_name:
    description:
      - The initial administrator's first name.
      - Used only when creating a domain.
    type: str
  admin_last_name:
    description:
      - The initial administrator's last name.
      - Used only when creating a domain.
    type: str
  admin_user_name:
    description:
      - The initial administrator's user name.
      - Used only when creating a domain.
    type: str
  admin_email:
    description:
      - The initial administrator's email address.
      - Used only when creating a domain.
    type: str
  is_notification_bypassed:
    description:
      - Whether creation of the initial administrator bypasses notifications.
      - Used only when creating a domain.
    type: bool
  is_primary_email_required:
    description:
      - Whether users in the identity domain require a primary email address.
      - This controls user creation policy; it does not require an
        C(admin_email) when no administrator details are provided.
      - Used only when creating a domain.
    type: bool
"""

EXAMPLES = r"""
- name: Create an identity domain
  ansible.oci.oci_domain:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: project-development
    description: Development identity domain
    home_region: us-ashburn-1
    license_type: free
  register: identity_domain

- name: Update an identity domain
  ansible.oci.oci_domain:
    state: present
    domain_id: "{{ identity_domain.resource.id }}"
    name: project-development-updated
    description: Updated development identity domain

- name: Delete an identity domain
  ansible.oci.oci_domain:
    state: absent
    domain_id: "{{ identity_domain.resource.id }}"
"""

RETURN = r"""
resource:
  description: The identity domain resource.
  returned: when state != absent
  type: dict
  contains:
    id:
      description: The OCID of the identity domain.
      type: str
      returned: always
      sample: ocid1.domain.oc1..example
    compartment_id:
      description: The OCID of the compartment containing the identity domain.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    name:
      description: The display name of the identity domain.
      type: str
      returned: always
      sample: example-domain
    description:
      description: The description of the identity domain.
      type: str
      returned: always
      sample: Example identity domain
    url:
      description: The URL of the identity domain.
      type: str
      returned: always
      sample: https://idcs.example.identity.oraclecloud.com:443
    home_region_url:
      description: The identity domain URL in its home region.
      type: str
      returned: always
      sample: https://idcs.example.us-sanjose-idcs-1.identity.us-sanjose-1.oci.oraclecloud.com:443
    home_region:
      description: The OCI region where the identity domain is homed.
      type: str
      returned: always
      sample: us-sanjose-1
    replica_regions:
      description: The regions where the identity domain is replicated.
      type: list
      elements: dict
      returned: always
      contains:
        region:
          description: The replicated region name.
          type: str
          returned: always
          sample: us-phoenix-1
        url:
          description: The identity domain URL for the replicated region.
          type: str
          returned: always
          sample: https://idcs.example.us-phoenix-idcs-1.identity.us-phoenix-1.oci.oraclecloud.com:443
        regional_url:
          description: The regional URL for the replicated identity domain.
          type: str
          returned: always
          sample: https://idcs.example.identity.oraclecloud.com:443
        state:
          description: The lifecycle state of the replicated region.
          type: str
          returned: always
          sample: ACTIVE
    type:
      description: The type of the identity domain.
      type: str
      returned: always
      sample: SECONDARY
    license_type:
      description: The license type of the identity domain.
      type: str
      returned: always
      sample: free
    is_hidden_on_login:
      description: Whether the identity domain is hidden on the sign-in screen.
      type: bool
      returned: always
      sample: false
    lifecycle_state:
      description: The current lifecycle state of the identity domain.
      type: str
      returned: always
      sample: ACTIVE
    lifecycle_details:
      description: Details about the current identity domain lifecycle state.
      type: str
      returned: always
      sample: null
    freeform_tags:
      description: Free-form tags applied to the identity domain.
      type: dict
      returned: always
      sample: {environment: production}
    defined_tags:
      description: Defined tags applied to the identity domain.
      type: dict
      returned: always
      sample: {Operations: {CostCenter: "42"}}
    time_created:
      description: The date and time the identity domain was created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
  sample:
    id: ocid1.domain.oc1..example
    compartment_id: ocid1.compartment.oc1..example
    name: example-domain
    description: Example identity domain
    home_region: us-sanjose-1
    license_type: free
    is_hidden_on_login: false
    lifecycle_state: ACTIVE
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_ACTIVE,
    OCI_COMMON_ARGS,
    filter_none_values,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]

CREATE_REQUIRED_FIELDS = (
    "compartment_id",
    "name",
    "description",
    "home_region",
    "license_type",
)


def build_create_domain_details(params):
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "display_name": params.get("name"),
            "description": params.get("description"),
            "home_region": params.get("home_region"),
            "license_type": params.get("license_type"),
            "is_hidden_on_login": params.get("is_hidden_on_login"),
            "admin_first_name": params.get("admin_first_name"),
            "admin_last_name": params.get("admin_last_name"),
            "admin_user_name": params.get("admin_user_name"),
            "admin_email": params.get("admin_email"),
            "is_notification_bypassed": params.get("is_notification_bypassed"),
            "is_primary_email_required": params.get("is_primary_email_required"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.identity.models.CreateDomainDetails(**details)


class OciDomainModule(OciResourceBase):
    """Concrete resource adapter for OCI identity domains."""

    @property
    def client_class(self):
        return oci.identity.IdentityClient

    resource_id_param = "domain_id"
    list_resource_method = "list_domains"
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "identity domain"
    update_field_specs = (
        UpdateFieldSpec(
            param_name="compartment_id",
            is_mutable=False,
            immutable_reason="OCI does not move domains through update_domain",
        ),
        UpdateFieldSpec(
            param_name="name",
            resource_field="display_name",
            is_mutable=True,
        ),
        UpdateFieldSpec(param_name="description", is_mutable=True),
        UpdateFieldSpec(param_name="is_hidden_on_login", is_mutable=True),
        UpdateFieldSpec(
            param_name="home_region",
            is_mutable=False,
            immutable_reason="OCI sets the domain home region at creation",
        ),
        UpdateFieldSpec(
            param_name="license_type",
            is_mutable=False,
            immutable_reason="changing license types is not supported by this module",
        ),
        UpdateFieldSpec(
            param_name="admin_first_name",
            is_mutable=False,
            immutable_reason="administrator details are create-time only",
        ),
        UpdateFieldSpec(
            param_name="admin_last_name",
            is_mutable=False,
            immutable_reason="administrator details are create-time only",
        ),
        UpdateFieldSpec(
            param_name="admin_user_name",
            is_mutable=False,
            immutable_reason="administrator details are create-time only",
        ),
        UpdateFieldSpec(
            param_name="admin_email",
            is_mutable=False,
            immutable_reason="administrator details are create-time only",
        ),
        UpdateFieldSpec(
            param_name="is_notification_bypassed",
            is_mutable=False,
            immutable_reason="notification settings are create-time only",
        ),
        UpdateFieldSpec(
            param_name="is_primary_email_required",
            is_mutable=False,
            immutable_reason="primary email settings are create-time only",
        ),
    )

    def get_resource_response(self, resource_id):
        return self.call_with_retry(self.client.get_domain, domain_id=resource_id)

    def _get_work_request(self, response, wait=True):
        work_request_id = response.headers["opc-work-request-id"]
        if wait:
            return self.wait_for_work_request(
                self.client,
                work_request_id,
                get_work_request_fn=self.client.get_iam_work_request,
            )
        return self.call_with_retry(self.client.get_iam_work_request, work_request_id)

    def create_resource(self):
        response = self.call_with_retry(
            self.client.create_domain,
            create_domain_details=build_create_domain_details(self.module.params),
        )
        work_request = self._get_work_request(
            response,
            wait=self.module.params.get("wait", True),
        )
        domain_id = work_request.resources[0].identifier
        return self.wait_for_resource_id(domain_id, (LIFECYCLE_ACTIVE,))

    def build_update_details(self, update_model_fields):
        return oci.identity.models.UpdateDomainDetails(**update_model_fields)

    def update_resource(self, resource):
        update_plan = self.get_update_plan(resource)
        response = self.call_with_retry(
            self.client.update_domain,
            domain_id=resource.id,
            update_domain_details=self.build_update_details(
                update_plan["update_model_fields"]
            ),
        )
        self._get_work_request(response, wait=self.module.params.get("wait", True))
        return self.wait_for_resource_id(resource.id, (LIFECYCLE_ACTIVE,))

    def delete_resource(self, resource):
        if resource.lifecycle_state == LIFECYCLE_ACTIVE:
            response = self.call_with_retry(
                self.client.deactivate_domain,
                domain_id=resource.id,
            )
            # OCI requires deactivation to finish before deletion can start.
            self._get_work_request(response)

        response = self.call_with_retry(
            self.client.delete_domain,
            domain_id=resource.id,
        )
        if self.module.params.get("wait", True):
            self._get_work_request(response)


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        domain_id=dict(type="str"),
        compartment_id=dict(type="str"),
        name=dict(type="str"),
        description=dict(type="str"),
        home_region=dict(type="str"),
        license_type=dict(type="str"),
        is_hidden_on_login=dict(type="bool"),
        admin_first_name=dict(type="str"),
        admin_last_name=dict(type="str"),
        admin_user_name=dict(type="str"),
        admin_email=dict(type="str"),
        is_notification_bypassed=dict(type="bool"),
        is_primary_email_required=dict(type="bool"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciDomainModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
