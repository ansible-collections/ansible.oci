# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_app_catalog_subscription
short_description: Manage an OCI Compute App Catalog subscription
description:
  - Create or delete an OCI Compute App Catalog subscription.
version_added: "1.3.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  state:
    description:
      - Use V(present) to accept the listing terms and create the subscription if it is absent.
      - Use V(absent) to delete the subscription.
    type: str
    choices: [present, absent]
    default: present
  compartment_id:
    description: The OCID of the compartment for the subscription.
    type: str
    required: true
  listing_id:
    description: The OCID of the App Catalog listing.
    type: str
    required: true
  listing_resource_version:
    description: The listing resource version to subscribe to.
    type: str
    required: true
  signature:
    description:
      - The agreement signature returned by the agreement operation.
      - Required only when C(state=present) creates a subscription.
    type: str
  time_retrieved:
    description:
      - The agreement retrieval time in RFC 3339 format.
      - Required only when C(state=present) creates a subscription.
    type: str
  oracle_terms_of_use_link:
    description:
      - The Oracle terms of use link returned by the agreement operation.
      - Required only when C(state=present) creates a subscription.
    type: str
  eula_link:
    description:
      - The end-user license agreement link returned by the agreement operation.
      - Used only when C(state=present) creates a subscription.
    type: str
"""

EXAMPLES = r"""
- name: Accept App Catalog terms and subscribe
  ansible.oci.oci_app_catalog_subscription:
    compartment_id: ocid1.compartment.oc1..example
    listing_id: ocid1.appcataloglisting.oc1..example
    listing_resource_version: "1.0"
    signature: agreement-signature
    time_retrieved: "2026-01-01T00:00:00+00:00"
    oracle_terms_of_use_link: https://www.oracle.com/legal/terms.html
    eula_link: https://example.com/eula.html

- name: Remove an App Catalog subscription
  ansible.oci.oci_app_catalog_subscription:
    state: absent
    compartment_id: ocid1.compartment.oc1..example
    listing_id: ocid1.appcataloglisting.oc1..example
    listing_resource_version: "1.0"
"""

RETURN = r"""
resource:
  description: The App Catalog subscription resource.
  returned: when state is present and a resource exists
  type: dict
  contains:
    publisher_name:
      description: The name of the listing publisher.
      type: str
      returned: always
    listing_id:
      description: The OCID of the listing.
      type: str
      returned: always
    listing_resource_version:
      description: The subscribed listing resource version.
      type: str
      returned: always
    listing_resource_id:
      description: The OCID of the subscribed listing resource.
      type: str
      returned: always
    name:
      description: The display name of the listing.
      type: str
      returned: always
    summary:
      description: The short listing summary.
      type: str
      returned: always
    compartment_id:
      description: The OCID of the subscription compartment.
      type: str
      returned: always
    time_created:
      description: The creation time in RFC 3339 format.
      type: str
      returned: always
  sample:
    publisher_name: Example Publisher
    listing_id: ocid1.appcataloglisting.oc1..example
    listing_resource_version: "1.0"
    listing_resource_id: ocid1.image.oc1..example
    name: Example image
    summary: Example image listing
    compartment_id: ocid1.compartment.oc1..example
    time_created: "2026-01-01T00:00:00+00:00"
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    build_model,
    filter_resources_by_response_field,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import OciResourceBase

oci = import_oci_sdk()[0]


class OciAppCatalogSubscriptionModule(OciResourceBase):
    """Manage one App Catalog subscription selected by listing and version."""

    @property
    def client_class(self):
        """Return the client class for Compute App Catalog operations.

        Returns:
            The OCI Compute client class.
        """
        return oci.core.ComputeClient

    create_required_fields = (
        "signature",
        "time_retrieved",
        "oracle_terms_of_use_link",
    )
    create_resource_name = "App Catalog subscription"
    update_field_specs = ()

    def resolve_target_resource(self):
        """Find a subscription by compartment, listing, and resource version.

        The inherited resolver uses an OCID or a display name. OCI identifies
        a subscription by the compartment, listing, and resource version.

        Returns:
            The matching subscription model, or ``None`` when absent.
        """
        resources = self.list_all_resources(
            self.client.list_app_catalog_subscriptions,
            compartment_id=self.module.params["compartment_id"],
            listing_id=self.module.params["listing_id"],
        )
        version = self.module.params["listing_resource_version"]
        matches = filter_resources_by_response_field(resources, "listing_resource_version", version)
        return matches[0] if matches else None

    def get_resource_response(self, resource_id):
        """Reject unsupported direct subscription lookup.

        OCI provides a list operation for subscription lookup.

        Args:
            resource_id: The ID used for direct lookup by the base class.

        Raises:
            NotImplementedError: If the base class attempts a direct lookup.
        """
        raise NotImplementedError("App Catalog subscriptions have no get operation")

    def create_resource(self):
        """Accept the listing terms and create the subscription.

        Returns:
            The created App Catalog subscription model.
        """
        details = build_model(
            self.module.params,
            oci.core.models.CreateAppCatalogSubscriptionDetails,
            keys=(
                "compartment_id",
                "listing_id",
                "listing_resource_version",
                "oracle_terms_of_use_link",
                "eula_link",
                "time_retrieved",
                "signature",
            ),
        )
        # The SDK keeps one retry token for the create operation and its retries.
        response = self.client.create_app_catalog_subscription(
            create_app_catalog_subscription_details=details,
        )
        return response.data

    def delete_resource(self, resource):
        """Delete the selected subscription.

        Args:
            resource: The subscription model selected by listing and version.
        """
        self.call_with_retry(
            self.client.delete_app_catalog_subscription,
            listing_id=resource.listing_id,
            compartment_id=resource.compartment_id,
            resource_version=resource.listing_resource_version,
        )


def main():
    """Run the App Catalog subscription module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        compartment_id=dict(type="str", required=True),
        listing_id=dict(type="str", required=True),
        listing_resource_version=dict(type="str", required=True),
        signature=dict(type="str", no_log=True),
        time_retrieved=dict(type="str"),
        oracle_terms_of_use_link=dict(type="str"),
        eula_link=dict(type="str"),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    OciAppCatalogSubscriptionModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
