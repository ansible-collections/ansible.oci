"""Shared helpers for OCI DNS record modules."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from collections import Counter

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    serialize_oci_model,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase
from ansible_collections.ansible.oci.plugins.module_utils.oci_base import OciModuleBase, oci


def _dns_common_argument_spec():
    """Return argument declarations that all DNS modules use.

    Returns:
        Common DNS argument declarations.
    """
    spec = dict(OCI_AUTH_ARGS)
    spec.update(
        scope=dict(type="str", choices=["global", "private"]),
        zone_name_or_id=dict(type="str", required=True),
        view_id=dict(type="str"),
    )
    return spec


def _dns_kind_argument_spec(kind):
    """Return selectors for a DNS collection kind.

    Args:
        kind: One of ``zone``, ``domain``, or ``rrset``.

    Returns:
        Selectors for the requested collection kind.
    """
    spec = {}
    if kind in ("domain", "rrset"):
        spec["domain"] = dict(type="str", required=True)

    if kind == "rrset":
        spec["rtype"] = dict(type="str", required=True)

    return spec


def _dns_info_argument_spec(kind):
    """Return list filters for a DNS info module.

    Args:
        kind: One of ``zone``, ``domain``, or ``rrset``.

    Returns:
        Info filter declarations.
    """
    if kind == "zone":
        return dict(
            domain=dict(type="str"), domain_contains=dict(type="str"),
            rtype=dict(type="str"), zone_version=dict(type="str"),
            sort_by=dict(type="str", choices=["domain", "rtype", "ttl"]),
            sort_order=dict(type="str", choices=["asc", "desc"]),
        )

    if kind == "domain":
        return dict(
            rtype=dict(type="str"), zone_version=dict(type="str"),
            sort_by=dict(type="str", choices=["rtype", "ttl"]),
            sort_order=dict(type="str", choices=["asc", "desc"]),
        )

    return dict(zone_version=dict(type="str"))


def _dns_resource_argument_spec(kind):
    """Return writable record arguments and resource state.

    Args:
        kind: One of ``zone``, ``domain``, or ``rrset``.

    Returns:
        Resource argument declarations.
    """
    spec = dict(update_items=dict(type="list", elements="dict", options={
        "domain": dict(type="str", required=True),
        "rtype": dict(type="str", required=True),
        "rdata": dict(type="str", required=True),
        "ttl": dict(type="int", required=True),
    }))
    choices = ["present"] if kind == "zone" else ["present", "absent"]
    spec["state"] = dict(type="str", choices=choices, default="present")
    return spec


def build_dns_argument_spec(kind, info=False):
    """Build the arguments that all DNS record modules use.

    Args:
        kind: One of ``zone``, ``domain``, or ``rrset``.
        info: Set to True for an info module.

    Returns:
        A dictionary of Ansible argument declarations.
    """
    if kind not in ("zone", "domain", "rrset"):
        raise ValueError("kind must be zone, domain, or rrset")

    spec = _dns_common_argument_spec()
    spec.update(_dns_kind_argument_spec(kind))
    spec.update(_dns_info_argument_spec(kind) if info else _dns_resource_argument_spec(kind))
    return spec


class _DnsRecordsBase:
    """Provide common scope lookup, record retrieval, and record comparison."""

    client_class = None
    scope_kind = None

    def __init__(self, module, scope_kind=None):
        """Initialize the SDK client and validate private-zone lookup parameters.

        Args:
            module: Active Ansible module.
            scope_kind: Optional collection kind supplied by a subclass.
        """
        super(_DnsRecordsBase, self).__init__(module)
        self.scope_kind = scope_kind or getattr(type(self), "scope_kind", self.scope_kind)
        scope = module.params.get("scope")
        self.scope = scope.upper() if scope else None
        self.zone_name = module.params.get("zone_name_or_id")
        self.view_id = module.params.get("view_id")

        if self.scope == "PRIVATE" and not self.view_id and not str(self.zone_name).startswith("ocid1.dns-zone."):
            module.fail_json(msg="view_id is required when scope is private")

    def get_resource_response(self, resource_id):
        """Read the parent zone through the inherited resource interface.

        Args:
            resource_id: Zone name or OCID.

        Returns:
            The OCI response for the parent zone.
        """
        params = self._request_selectors()
        params["zone_name_or_id"] = resource_id
        return self.call_with_retry(self.client.get_zone, **params)

    def zone(self):
        """Check that the parent zone exists after a record lookup returns 404.

        Returns:
            The parent zone model.
        """
        try:
            return self.get_resource_response(self.zone_name).data
        except Exception as exc:
            if getattr(exc, "status", None) == 404:
                self.module.fail_json(msg="The requested DNS zone was not found")

            raise

    def _record_request(self):
        """Return the selected list operation and its filters."""
        params = self._request_selectors()
        filters = {
            "zone": ("domain", "domain_contains", "rtype", "zone_version", "sort_by", "sort_order"),
            "domain": ("rtype", "zone_version", "sort_by", "sort_order"),
            "rrset": ("zone_version",),
        }[self.scope_kind]
        params.update(self.collect_list_filters(filters))

        if params.get("rtype"):
            params["rtype"] = params["rtype"].upper()

        if params.get("sort_order"):
            params["sort_order"] = params["sort_order"].upper()

        return self._select_operation("get", params)

    def fetch_records(self):
        """Read all pages through the shared OCI pagination helper."""
        fn, params = self._record_request()
        return self._list_records(fn, params)

    def _request_selectors(self):
        """Return selectors shared by DNS record operations."""
        params = {"zone_name_or_id": self.zone_name}
        if self.scope is not None:
            params["scope"] = self.scope
        if self.view_id is not None:
            params["view_id"] = self.view_id
        return params

    def _select_operation(self, action, params):
        """Select an SDK operation and add its required record selectors.

        Args:
            action: One of ``get``, ``update``, or ``delete``.
            params: Base request selectors to extend.

        Returns:
            The SDK method and its request selectors.
        """
        operations = {
            "zone": {"get": "get_zone_records", "update": "update_zone_records"},
            "domain": {"get": "get_domain_records", "update": "update_domain_records",
                       "delete": "delete_domain_records"},
            "rrset": {"get": "get_rr_set", "update": "update_rr_set", "delete": "delete_rr_set"},
        }
        fn = getattr(self.client, operations[self.scope_kind][action])

        if self.scope_kind in ("domain", "rrset"):
            params["domain"] = self.module.params["domain"]

        if self.scope_kind == "rrset":
            params["rtype"] = self.module.params["rtype"].upper()

        return fn, params

    def _list_records(self, fn, params):
        """Read all pages and handle an initial scoped 404."""
        records = []
        page_count = 0

        try:
            for response in oci.pagination.list_call_get_all_results_generator(fn, "response", **params):
                page_count += 1
                records.extend(getattr(response.data, "items", None) or [])
        except Exception as exc:
            if getattr(exc, "status", None) == 404 and self.scope_kind != "zone" and page_count == 0:
                self.zone()
                return []

            raise

        return records

    @staticmethod
    def record_fields(record):
        """Return writable record fields for OCI field comparison.

        Args:
            record: Record model or dictionary.

        Returns:
            Normalized domain and type, exact OCI record data, and TTL.
        """
        item = record if isinstance(record, dict) else serialize_oci_model(record)
        domain = (item.get("domain") or "").rstrip(".").lower()
        rtype = (item.get("rtype") or "").upper()
        return domain, rtype, item.get("rdata"), item.get("ttl")

    @classmethod
    def records_equal(cls, left, right):
        """Compare collections without record order or generated OCI metadata.

        Args:
            left: Current records.
            right: Desired records.

        Returns:
            True when both collections contain the same records.
        """
        left_values = [cls.record_fields(item) for item in left]
        right_values = [cls.record_fields(item) for item in right]
        return Counter(left_values) == Counter(right_values)

    def serialize_records(self, records):
        """Serialize each record through the collection serializer.

        Args:
            records: Record models.

        Returns:
            Record dictionaries.
        """
        return [self.serialize_result_resource(item) for item in records]


class OciDnsRecordsResource(_DnsRecordsBase, OciModuleBase):
    """Reconcile record items for one OCI DNS zone, domain, or RRset."""

    client_class = oci.dns.DnsClient if oci else None

    def __init__(self, module, scope_kind=None):
        super(OciDnsRecordsResource, self).__init__(module, scope_kind)
        self.check_mode = module.check_mode

    def validate_create_request(self):
        """Validate collection selectors because DNS has no create-only operation."""
        selected_domain = self.module.params.get("domain")

        for item in self.module.params["update_items"]:
            if selected_domain and item["domain"].rstrip(".").lower() != selected_domain.rstrip(".").lower():
                self.module.fail_json(msg="Every item domain must match the selected domain")

            if self.scope_kind == "rrset" and item["rtype"].upper() != self.module.params["rtype"].upper():
                self.module.fail_json(msg="Every item rtype must match the selected rtype")

    def effective_desired(self, resource):
        """Preserve protected records omitted from the requested replacement.

        Args:
            resource: Current record models.

        Returns:
            Desired record dictionaries with omitted protected records included.
        """
        desired = list(self.module.params["update_items"])
        identities = {self.record_fields(item)[:3] for item in desired}
        desired.extend(
            self.serialize_result_resource(item) for item in resource
            if getattr(item, "is_protected", False)
            and self.record_fields(item)[:3] not in identities
        )
        return desired

    def update_resource(self, resource):
        """Replace the selected DNS collection.

        Args:
            resource: Current record models.

        Returns:
            The updated record models.
        """
        desired = self.effective_desired(resource)
        model = self._build_update_model(desired)
        params = self._request_selectors()
        fn, params = self._select_operation("update", params)
        argument_name = {
            "zone": "update_zone_records_details",
            "domain": "update_domain_records_details",
            "rrset": "update_rr_set_details",
        }[self.scope_kind]
        response = self.call_with_retry(fn, **dict(params, **{argument_name: model}))

        return getattr(response.data, "items", model.items)

    def _build_update_model(self, desired):
        """Build the OCI request model for a DNS record replacement.

        Args:
            desired: Desired record dictionaries.

        Returns:
            The collection-specific OCI update model.
        """
        details_name = {
            "zone": "UpdateZoneRecordsDetails",
            "domain": "UpdateDomainRecordsDetails",
            "rrset": "UpdateRRSetDetails",
        }[self.scope_kind]
        records = [
            oci.dns.models.RecordDetails(**dict(item, rtype=item["rtype"].upper()))
            for item in desired
        ]
        return getattr(oci.dns.models, details_name)(items=records)

    def delete_resource(self, resource):
        """Delete records through the SDK collection operation.

        Args:
            resource: Current records selected for deletion.
        """
        del resource

        if self.scope_kind == "zone":
            self.module.fail_json(msg="state=absent is not supported for zone records")

        params = self._request_selectors()
        fn, params = self._select_operation("delete", params)
        self.call_with_retry(fn, **params)

    def build_diff(self, before, after):
        """Exclude generated metadata from the before and after record lists.

        Args:
            before: Current records.
            after: Desired records.

        Returns:
            Diff lists containing only writable record fields.
        """
        result = {}
        for label, records in (("before", before), ("after", after)):
            items = self.serialize_records(records)
            result[label] = [
                dict(domain=item["domain"], rtype=item["rtype"].upper(),
                     rdata=item["rdata"], ttl=item["ttl"])
                for item in items
            ]
        return result

    def execute_absent(self, records):
        """Delete the selected collection in absent state.

        Args:
            records: Current record models.
        """
        changed = bool(records)

        result = {"changed": changed}
        if getattr(self.module, "_diff", False):
            result["diff"] = self.build_diff(records, [])

        if changed and not self.check_mode:
            self.delete_resource(records)

        self.module.exit_json(**result)

    def execute_present(self, records):
        """Reconcile the selected collection in present state.

        Args:
            records: Current record models.
        """
        self.validate_create_request()
        before = self.serialize_records(records)
        desired = self.effective_desired(records)
        changed = not self.records_equal(records, desired)

        result = {"changed": changed}
        if getattr(self.module, "_diff", False):
            result["diff"] = self.build_diff(before, desired if changed else before)

        if changed and not self.check_mode:
            records = self.update_resource(records)

        result["resource"] = {"items": self.serialize_records(records)}
        self.module.exit_json(**result)

    def execute_resource_module(self):
        """Reconcile DNS records with a page-aware read."""
        records = self.fetch_records()

        if self.module.params.get("state", "present") == "absent":
            self.execute_absent(records)

        self.execute_present(records)


class OciDnsRecordsInfo(_DnsRecordsBase, OciInfoBase):
    """Return DNS record items for one OCI zone, domain, or RRset."""

    client_class = oci.dns.DnsClient if oci else None
    results_key = "records"

    def fetch_resources(self):
        """Adapt DNS collections because the inherited reader expects ID lookups.

        Returns:
            All records selected by the SDK operation and filters.
        """
        return self.fetch_records()
