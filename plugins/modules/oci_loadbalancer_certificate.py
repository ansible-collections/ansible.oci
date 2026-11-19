# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_loadbalancer_certificate
short_description: Manage a certificate bundle on an OCI load balancer
description:
  - Create or delete a certificate bundle on an OCI load balancer.
version_added: "1.3.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_wait_options
options:
  load_balancer_id:
    description: OCID of the load balancer that contains the certificate bundle.
    type: str
    required: true
  name:
    description:
      - Unique name of the certificate bundle.
      - OCI does not allow the name to be changed.
    type: str
    required: true
  public_certificate:
    description:
      - Public certificate in PEM format.
      - Required when creating a certificate bundle.
      - If supplied for an existing bundle, this value must match the public certificate in OCI.
    type: str
  ca_certificate:
    description:
      - Certificate authority or intermediate certificate in PEM format.
      - If supplied for an existing bundle, this value must match the CA certificate in OCI.
    type: str
  private_key:
    description:
      - Private key in PEM format.
      - Supply the key when the load balancer terminates TLS.
      - The module uses this value only when it creates a bundle.
    type: str
  passphrase:
    description:
      - Passphrase for an encrypted private key.
      - The module uses this value only when it creates a bundle.
    type: str
  state:
    description:
      - Desired state of the certificate bundle.
      - Before deletion, remove the bundle from all listeners and backend sets.
    type: str
    choices: [present, absent]
    default: present
notes:
  - >-
    Use M(ansible.oci.oci_loadbalancer_info) with O(load_balancer_id) to read the certificate bundles.
    Each load balancer in C(load_balancers) has a C(certificates) map keyed by bundle name.
  - To rotate a certificate, upload a bundle with a new name.
  - Configure the listeners and backend sets to use the new name before deleting the old bundle.
"""

EXAMPLES = r"""
- name: Upload a certificate bundle
  ansible.oci.oci_loadbalancer_certificate:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    name: api-example-com-2026
    public_certificate: "{{ lookup('ansible.builtin.file', 'api.example.com.pem') }}"
    ca_certificate: "{{ lookup('ansible.builtin.file', 'intermediate-ca.pem') }}"
    private_key: "{{ vault_api_private_key }}"
    state: present
  no_log: true

- name: Configure the HTTPS listener to use the new bundle
  ansible.oci.oci_loadbalancer_listener:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    name: api-https
    default_backend_set_name: api-backends
    port: 443
    protocol: http
    ssl_configuration:
      certificate_name: api-example-com-2026

- name: Remove an unused certificate bundle
  ansible.oci.oci_loadbalancer_certificate:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    name: api-example-com-old
    state: absent
"""

RETURN = r"""
resource:
  description:
    - Current certificate bundle.
    - When O(wait=false), the module returns only the name if OCI has yet to expose the new bundle.
    - The private key and passphrase are write-only inputs.
  returned: when O(state=present) succeeds, except when check mode predicts creation
  type: dict
  contains:
    name:
      description: Certificate bundle name.
      type: str
      returned: always
    public_certificate:
      description: Public certificate in PEM format, or C(null) if OCI omits it.
      type: str
      returned: when OCI returns the bundle
    ca_certificate:
      description: Certificate authority or intermediate certificate in PEM format, or C(null) if OCI omits it.
      type: str
      returned: when OCI returns the bundle
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    OCI_WAIT_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_loadbalancer import (
    OciLoadBalancerSubresourceBase,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    UpdateFieldSpec,
)

oci = import_oci_sdk()[0]


class OciLoadBalancerCertificateModule(OciLoadBalancerSubresourceBase):
    """Manage one certificate bundle under a Load Balancer."""

    create_model_name = "CreateCertificateDetails"
    create_method_name = "create_certificate_and_wait_for_state"
    create_details_name = "create_certificate_details"
    delete_method_name = "delete_certificate_and_wait_for_state"
    create_resource_name = "certificate bundle"
    create_required_fields = ("public_certificate",)
    field_param_aliases = {"certificate_name": "name"}

    update_field_specs = (
        UpdateFieldSpec(
            param_name="public_certificate",
            is_mutable=False,
            immutable_reason="OCI requires a new bundle name for a different certificate",
        ),
        UpdateFieldSpec(
            param_name="ca_certificate",
            is_mutable=False,
            immutable_reason="OCI requires a new bundle name for a different certificate",
        ),
    )

    def get_resource_response(self, resource_id):
        """Fetch a certificate bundle from the parent load balancer.

        Args:
            resource_id: Certificate bundle name.

        Returns:
            Response containing the selected certificate bundle.

        Raises:
            oci.exceptions.ServiceError: If the parent request fails.
        """
        response = self.call_with_retry(
            self.client.get_load_balancer,
            load_balancer_id=self.module.params["load_balancer_id"],
        )
        certificates = getattr(response.data, "certificates", None) or {}
        return oci.response.Response(200, {}, certificates.get(resource_id), None)

    @staticmethod
    def build_resource_model(model_name, fields):
        """Build a certificate model with the module name mapped to the SDK field.

        Args:
            model_name: SDK model name.
            fields: Module parameters.

        Returns:
            Typed OCI certificate model.
        """
        model_fields = dict(fields, certificate_name=fields["name"])
        return OciLoadBalancerSubresourceBase.build_resource_model(
            model_name, model_fields
        )

    def mutation_kwargs(self, operation):
        """Add the certificate name required by the SDK delete call.

        Args:
            operation: Lifecycle operation name.

        Returns:
            SDK keyword arguments for the mutation.
        """
        kwargs = super(OciLoadBalancerCertificateModule, self).mutation_kwargs(
            operation
        )
        if operation == "delete":
            kwargs["certificate_name"] = self.resource_name
        return kwargs

    def compare_update_field_values(self, current_value, desired_value, compare=None):
        """Compare PEM values with the same line endings and outer whitespace.

        Args:
            current_value: Value returned by OCI.
            desired_value: Value supplied by the caller.
            compare: Shared comparison strategy.

        Returns:
            True when the certificate values differ.
        """
        if current_value is not None:
            current_value = current_value.replace("\r\n", "\n").strip()
        desired_value = desired_value.replace("\r\n", "\n").strip()
        return super(OciLoadBalancerCertificateModule, self).compare_update_field_values(
            current_value, desired_value, compare
        )


def main():
    """Build the argument specification and run the certificate module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_WAIT_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        load_balancer_id=dict(type="str", required=True),
        name=dict(type="str", required=True),
        public_certificate=dict(type="str"),
        ca_certificate=dict(type="str"),
        private_key=dict(type="str", no_log=True),
        passphrase=dict(type="str", no_log=True),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    OciLoadBalancerCertificateModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
