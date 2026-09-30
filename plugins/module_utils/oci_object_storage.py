"""Shared Object Storage namespace helpers for OCI modules."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type


class OciObjectStorageNamespaceMixin(object):
    """Resolve and cache the namespace used by Object Storage API calls."""

    @property
    def namespace_name(self):
        """Return the explicit namespace or resolve it once from Object Storage."""
        namespace_name = self.module.params.get("namespace_name")
        if namespace_name:
            return namespace_name

        namespace_name = getattr(self, "_namespace_name", None)
        if namespace_name is None:
            namespace_name = self.call_with_retry(self.client.get_namespace).data
            self._namespace_name = namespace_name
        return namespace_name
