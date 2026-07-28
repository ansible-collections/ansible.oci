"""Base helpers for OCI info modules and list-style lookups."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.oracle.oci.plugins.module_utils.oci_base import OciModuleBase


class OciInfoBase(OciModuleBase):
    """Shared implementation for OCI ``*_info`` modules.

    Subclasses declare the OCI client type and either resource-get metadata,
    list metadata, or both. The base class handles client creation, pagination,
    optional local name filtering, and serialization of OCI models into
    Ansible-friendly result payloads.
    """

    client_class = None
    results_key = "resources"
    resource_id_param = None
    resource_id_kwarg = None
    resource_get_method = None
    list_resource_method = None
    list_filter_params = ()
    name_filter_param = "name"

    def fetch_resources(self):
        """Return resources using the subclass-declared get/list metadata.

        When the caller supplies ``resource_id_param``, this method fetches a
        single resource and returns it as a one-item list. Otherwise it runs the
        configured list operation, applies supported list filters, and performs
        the optional local display-name filter before returning the resources.
        """
        resource_id = (
            self.module.params.get(self.resource_id_param)
            if self.resource_id_param
            else None
        )
        if resource_id:
            if self.resource_get_method is None:
                raise NotImplementedError(
                    f"{type(self).__name__} must define fetch_resources() or class metadata"
                )
            resource_id_kwarg = self.resource_id_kwarg or self.resource_id_param
            return self.get_resource_by_id(
                resource_id,
                getattr(self.client, self.resource_get_method),
                **{resource_id_kwarg: resource_id},
            )

        if self.list_resource_method is None:
            raise NotImplementedError(
                f"{type(self).__name__} must define fetch_resources() or class metadata"
            )
        resources = self.list_all_resources(
            getattr(self.client, self.list_resource_method),
            **self.collect_list_filters(self.list_filter_params),
        )
        return self.filter_resources_by_display_name(
            resources,
            self.module.params.get(self.name_filter_param),
        )

    def get_resource_by_id(self, resource_id, get_fn, **kwargs):
        """Fetch one OCI resource and normalize the result to list form.

        ``get_fn`` is the OCI SDK getter to call with ``kwargs``. A successful
        lookup returns ``[response.data]`` so callers can treat get and list
        flows uniformly, while a 404 returns ``[]`` instead of failing.
        """
        if not resource_id:
            return None

        try:
            response = self.call_with_retry(get_fn, **kwargs)
            return [response.data]
        except Exception as exc:
            if getattr(exc, "status", None) == 404:
                return []
            raise

    def execute_info_module(self):
        """Execute the info module and exit with serialized resources.

        The result payload is emitted under ``results_key`` and always reports
        ``changed=False`` because info modules do not mutate OCI resources.
        """
        resources = self.fetch_resources()
        serialized_resources = [
            self.serialize_result_resource(resource) for resource in resources
        ]
        self.module.exit_json(
            changed=False,
            **{self.results_key: serialized_resources},
        )
