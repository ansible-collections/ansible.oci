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
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]

CORE_USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
CORE_GROUP_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:Group"
CORE_DYNAMIC_GROUP_SCHEMA = "urn:ietf:params:scim:schemas:oracle:idcs:DynamicResourceGroup"
PATCH_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:PatchOp"
OCI_TAGS_SCHEMA = "urn:ietf:params:scim:schemas:oracle:idcs:extension:OCITags"
API_KEY_SCHEMA = "urn:ietf:params:scim:schemas:oracle:idcs:apikey"

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

    scim_response_attributes = ()

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

    def get_scim_response_kwargs(self):
        """Return response attributes required by a SCIM resource.

        Returns:
            Keyword arguments for an Identity Domains response operation.
        """
        if not self.scim_response_attributes:
            return {}
        return {
            "attributes": ",".join(self.scim_response_attributes),
            "attribute_sets": ["default"],
        }

    def list_resources_by_display_name(self, name_value=None):
        """List identity-domain resources with an optional exact display name.

        Args:
            name_value: Optional display name to match exactly.

        Returns:
            Matching SCIM resources from every response page.
        """
        kwargs = self.get_scim_response_kwargs()
        if name_value is not None:
            value = escape_scim_filter_value(name_value)
            kwargs["filter"] = f'displayName eq "{value}"'
        return self.list_all_resources(
            getattr(self.client, self.list_resource_method), **kwargs
        )


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


def serialize_group(group):
    tags = getattr(
        group,
        "urn_ietf_params_scim_schemas_oracle_idcs_extension_oci_tags",
        None,
    )
    meta = getattr(group, "meta", None)
    return {
        "id": getattr(group, "id", None),
        "ocid": getattr(group, "ocid", None),
        "domain_id": getattr(group, "domain_ocid", None),
        "name": getattr(group, "display_name", None),
        "freeform_tags": normalize_freeform_tags(tags),
        "defined_tags": normalize_defined_tags(tags),
        "time_created": getattr(meta, "created", None),
        "time_modified": getattr(meta, "last_modified", None),
    }


def serialize_dynamic_group(group):
    """Serialize a dynamic group and its rule fields.

    Args:
        group: Identity Domains dynamic group model.

    Returns:
        A dictionary with the group fields used by Ansible.
    """
    result = serialize_group(group)
    result["description"] = getattr(group, "description", None)
    result["matching_rule"] = getattr(group, "matching_rule", None)
    return result


def serialize_membership(member, group_id, user_id=None):
    return {
        "group_id": group_id,
        "user_id": user_id or getattr(member, "value", None),
        "user_ocid": getattr(member, "ocid", None),
        "membership_ocid": getattr(member, "membership_ocid", None),
        "display_name": getattr(member, "display", None),
        "type": getattr(member, "type", None),
        "date_added": getattr(member, "date_added", None),
    }


def build_api_key_filter(user_id, fingerprint=None):
    """Build a SCIM filter for API keys owned by one user.

    Args:
        user_id: SCIM identifier of the user.
        fingerprint: Optional server-generated key fingerprint.

    Returns:
        A SCIM filter string.
    """
    conditions = [f'user.value eq "{escape_scim_filter_value(user_id)}"']
    if fingerprint is not None:
        conditions.append(
            f'fingerprint eq "{escape_scim_filter_value(fingerprint)}"'
        )
    return " and ".join(conditions)


def serialize_api_key(resource):
    """Serialize an API key model into the module result shape.

    Args:
        resource: OCI API key model.

    Returns:
        A dictionary with API key fields used by Ansible.
    """
    meta = getattr(resource, "meta", None)
    user = getattr(resource, "user", None)
    return {
        "id": getattr(resource, "id", None),
        "ocid": getattr(resource, "ocid", None),
        "domain_id": getattr(resource, "domain_ocid", None),
        "user_id": getattr(user, "value", None),
        "user_ocid": getattr(user, "ocid", None),
        "key": getattr(resource, "key", None),
        "fingerprint": getattr(resource, "fingerprint", None),
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


def build_tag_patch_operations(params, current):
    """Build SCIM operations for changed OCI tags on a domain resource."""
    operations = []
    for param_name, path in (
        ("freeform_tags", "freeformTags"),
        ("defined_tags", "definedTags"),
    ):
        desired = params.get(param_name)
        if param_name == "defined_tags" and desired is not None:
            oracle_tags = current["defined_tags"].get("Oracle-Tags")
            if oracle_tags and "Oracle-Tags" not in desired:
                desired = {**desired, "Oracle-Tags": oracle_tags}
        if desired is None or desired == current[param_name]:
            continue
        extension = build_tags_extension(**{param_name: desired})
        operations.append(
            build_operation(
                "REPLACE",
                f"{OCI_TAGS_SCHEMA}:{path}",
                getattr(extension, param_name),
            )
        )
    return operations


class OciIdentityDomainResourceBase(OciIdentityDomainsMixin, OciResourceBase):
    """Plan and apply SCIM PATCH updates for identity-domain resources."""

    common_update_field_specs = ()
    update_field_specs = ()
    scim_update_paths = ()
    patch_method_name = None
    resource_id_kwarg = None

    def find_resources_by_name(self):
        """Find resources by an exact SCIM display-name filter.

        The shared OCI lookup filters local results instead of sending a SCIM filter.

        Returns:
            Matching Identity Domains resources, or an empty list without a name.
        """
        if not self.has_name_lookup_request:
            return []
        return self.list_resources_by_display_name(self.name_lookup_value)

    def build_extra_patch_operations(self, resource, current):
        """Return resource-specific operations after scalar field changes."""
        return []

    def build_update_plan(self, resource):
        params = self.module.params
        current = self.serialize_result_resource(resource)
        operations = []
        for param_name, path in self.scim_update_paths:
            desired = params.get(param_name)
            if desired is not None and desired != current[param_name]:
                operations.append(build_operation("REPLACE", path, desired))
        operations.extend(self.build_extra_patch_operations(resource, current))
        operations.extend(build_tag_patch_operations(params, current))
        return {"update_needed": bool(operations), "operations": operations}

    def update_resource(self, resource):
        """Apply planned SCIM changes and return the updated model.

        The inherited update method expects an OCI details model.
        Identity Domains requires SCIM PATCH operations.

        Args:
            resource: Current Identity Domains model.

        Returns:
            The updated model returned by the SCIM PATCH operation.
        """
        operations = self.get_update_plan(resource)["operations"]
        if not operations:
            return resource
        return self.call_with_retry(
            getattr(self.client, self.patch_method_name),
            **{
                self.resource_id_kwarg or self.resource_id_param: resource.id,
                "patch_op": build_patch_op(operations),
                **self.get_scim_response_kwargs(),
            },
        ).data


class OciIdentityDomainInfoBase(OciIdentityDomainsMixin, OciInfoBase):
    """Fetch and list identity-domain resources with SCIM response fields."""

    def fetch_resources(self):
        """Fetch one resource by ID or list resources by optional exact name.

        The shared info flow does not apply Identity Domains SCIM filters or attributes.

        Returns:
            A list of Identity Domains resource models.

        Raises:
            NotImplementedError: If the required get or list method is unset.
        """
        resource_id = (
            self.module.params.get(self.resource_id_param)
            if self.resource_id_param
            else None
        )
        if resource_id:
            if self.resource_get_method is None:
                raise NotImplementedError(
                    f"{type(self).__name__} must define resource_get_method"
                )
            resource_id_kwarg = self.resource_id_kwarg or self.resource_id_param
            return self.get_resource_by_id(
                resource_id,
                getattr(self.client, self.resource_get_method),
                **{
                    resource_id_kwarg: resource_id,
                    **self.get_scim_response_kwargs(),
                },
            )

        if self.list_resource_method is None:
            raise NotImplementedError(
                f"{type(self).__name__} must define list_resource_method"
            )
        return self.list_resources_by_display_name(
            self.module.params.get(self.name_filter_param)
        )
