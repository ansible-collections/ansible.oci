"""Helpers shared by OCI Identity Domains resource and info modules."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from functools import partial

from ansible.module_utils.basic import missing_required_lib

from ansible_collections.ansible.oci.plugins.module_utils.oci_auth import (
    create_service_client,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    import_oci_sdk,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]

CORE_USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
PATCH_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:PatchOp"
OCI_TAGS_SCHEMA = "urn:ietf:params:scim:schemas:oracle:idcs:extension:OCITags"

OCI_IDENTITY_DOMAIN_ARGS = {
    "domain_id": dict(type="str"),
    "domain_url": dict(type="str"),
}


def escape_scim_filter_value(value):
    """Escape a string embedded in a quoted SCIM filter value."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def resolve_domain_url(module):
    """Return the explicit domain URL or resolve a domain OCID to its URL."""
    domain_url = module.params.get("domain_url")
    if domain_url:
        return domain_url.rstrip("/")

    domain_id = module.params.get("domain_id")
    identity_client = create_service_client(module, oci.identity.IdentityClient)
    response = oci.retry.DEFAULT_RETRY_STRATEGY.make_retrying_call(
        identity_client.get_domain,
        domain_id=domain_id,
    )
    domain_url = getattr(response.data, "url", None)
    if not domain_url:
        module.fail_json(msg=f"Identity domain {domain_id} does not expose a service URL")
    return domain_url.rstrip("/")


class OciIdentityDomainsMixin:
    """Create a domain-scoped client and normalize SCIM list pagination."""

    def __init__(self, module):
        if not HAS_OCI_SDK:
            module.fail_json(msg=missing_required_lib("oci"))
        self.identity_domain_url = resolve_domain_url(module)
        super(OciIdentityDomainsMixin, self).__init__(module)

    @property
    def client_class(self):
        return partial(
            oci.identity_domains.IdentityDomainsClient,
            service_endpoint=self.identity_domain_url,
        )

    def list_all_resources(self, list_fn, *args, **kwargs):
        resources = []
        request_kwargs = dict(kwargs)
        while True:
            response = self.call_with_retry(list_fn, *args, **request_kwargs)
            resources.extend(getattr(response.data, "resources", None) or [])
            next_page = getattr(response, "next_page", None)
            if not next_page:
                next_page = (getattr(response, "headers", None) or {}).get(
                    "opc-next-page"
                )
            if not next_page:
                return resources
            request_kwargs["page"] = next_page


def build_schemas(core_schema, include_tags=False):
    schemas = [core_schema]
    if include_tags:
        schemas.append(OCI_TAGS_SCHEMA)
    return schemas


def build_tags_extension(freeform_tags=None, defined_tags=None):
    freeform_models = None
    if freeform_tags is not None:
        freeform_models = [
            oci.identity_domains.models.FreeformTags(key=key, value=value)
            for key, value in sorted(freeform_tags.items())
        ]
    defined_models = None
    if defined_tags is not None:
        defined_models = [
            oci.identity_domains.models.DefinedTags(
                namespace=namespace,
                key=key,
                value=value,
            )
            for namespace, values in sorted(defined_tags.items())
            for key, value in sorted(values.items())
        ]
    if freeform_models is None and defined_models is None:
        return None
    return oci.identity_domains.models.ExtensionOCITags(
        freeform_tags=freeform_models,
        defined_tags=defined_models,
    )


def normalize_freeform_tags(extension):
    return {
        tag.key: tag.value
        for tag in (getattr(extension, "freeform_tags", None) or [])
    }


def normalize_defined_tags(extension):
    result = {}
    for tag in getattr(extension, "defined_tags", None) or []:
        result.setdefault(tag.namespace, {})[tag.key] = tag.value
    return result


def work_email(user):
    emails = getattr(user, "emails", None) or []
    selected = next(
        (email for email in emails if getattr(email, "type", None) == "work"), None
    )
    return getattr(selected, "value", None)


def serialize_user(user):
    name = getattr(user, "name", None)
    tags = getattr(
        user,
        "urn_ietf_params_scim_schemas_oracle_idcs_extension_oci_tags",
        None,
    )
    meta = getattr(user, "meta", None)
    return {
        "id": getattr(user, "id", None),
        "ocid": getattr(user, "ocid", None),
        "domain_id": getattr(user, "domain_ocid", None),
        "user_name": getattr(user, "user_name", None),
        "name": getattr(user, "display_name", None),
        "given_name": getattr(name, "given_name", None),
        "family_name": getattr(name, "family_name", None),
        "email": work_email(user),
        "description": getattr(user, "description", None),
        "active": getattr(user, "active", None),
        "freeform_tags": normalize_freeform_tags(tags),
        "defined_tags": normalize_defined_tags(tags),
        "time_created": getattr(meta, "created", None),
        "time_modified": getattr(meta, "last_modified", None),
    }


def build_patch_op(operations):
    return oci.identity_domains.models.PatchOp(
        schemas=[PATCH_SCHEMA],
        operations=operations,
    )


def build_operation(op, path, value=None):
    return oci.identity_domains.models.Operations(op=op, path=path, value=value)
