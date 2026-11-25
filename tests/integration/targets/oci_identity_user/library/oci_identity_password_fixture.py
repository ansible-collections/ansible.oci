#!/usr/bin/python
"""Set a password on a temporary user for integration tests."""
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from functools import partial
import secrets
import string

from ansible.module_utils.basic import AnsibleModule, missing_required_lib
from ansible_collections.ansible.oci.plugins.module_utils.oci_auth import create_service_client
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import OCI_AUTH_ARGS, import_oci_sdk
from ansible_collections.ansible.oci.plugins.module_utils.oci_identity_domains import PASSWORD_STATE_ATTRIBUTES

oci = import_oci_sdk()[0]


def set_fixture_password(client, user_id):
    """Set a random password and read its state through the SDK.

    Args:
        client: Authenticated Identity Domains client.
        user_id: SCIM ID of the temporary user.

    Returns:
        Password state fields from the SDK response.

    Raises:
        RuntimeError: If OCI returns no password timestamp.
    """
    password = "Aa1!" + "".join(
        secrets.choice(string.ascii_letters + string.digits) for _index in range(24)
    )
    client.put_user_password_changer(
        user_password_changer_id=user_id,
        user_password_changer=oci.identity_domains.models.UserPasswordChanger(
            schemas=["urn:ietf:params:scim:schemas:oracle:idcs:UserPasswordChanger"],
            password=password,
            bypass_notification=True,
        ),
        retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY,
    )
    user = client.get_user(
        user_id=user_id,
        attributes=PASSWORD_STATE_ATTRIBUTES,
        attribute_sets=["default"],
        retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY,
    ).data
    state = getattr(
        user, "urn_ietf_params_scim_schemas_oracle_idcs_extension_password_state_user", None
    )
    if not getattr(state, "last_successful_set_date", None):
        raise RuntimeError("OCI returned no password timestamp after the password was set")
    return {
        name: getattr(state, name, None)
        for name in (
            "cant_change", "cant_expire", "must_change", "expired", "last_successful_set_date"
        )
    }


def main():
    """Prepare password metadata for a temporary integration user."""
    module = AnsibleModule(argument_spec=dict(
        OCI_AUTH_ARGS,
        domain_url=dict(type="str", required=True),
        user_id=dict(type="str", required=True),
    ))
    if oci is None:
        module.fail_json(msg=missing_required_lib("oci"))
    error = None
    state = None
    try:
        client = create_service_client(module, partial(
            oci.identity_domains.IdentityDomainsClient,
            service_endpoint=module.params["domain_url"],
        ))
        state = set_fixture_password(client, module.params["user_id"])
    except Exception:
        error = "Failed to prepare password metadata for the temporary user"
    if error:
        module.fail_json(msg=error)
    module.exit_json(changed=True, password_state=state)


if __name__ == "__main__":
    main()
