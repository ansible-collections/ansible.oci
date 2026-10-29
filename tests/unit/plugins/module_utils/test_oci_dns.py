"""Test shared OCI DNS record helpers."""

from __future__ import absolute_import, division, print_function

import types

import pytest

from .conftest import load_collection_module


dns_helper = load_collection_module("oci_dns")


class ModuleExit(Exception):
    """Store an Ansible module result for a focused helper test."""

    def __init__(self, payload):
        self.payload = payload


class DummyModule:
    """Provide the small Ansible module interface used by DNS helpers."""

    def __init__(self, params, check_mode=False, diff=False):
        self.params = params
        self.check_mode = check_mode
        self._diff = diff

    def exit_json(self, **kwargs):
        raise ModuleExit(kwargs)

    def fail_json(self, **kwargs):
        raise ModuleExit(kwargs)


def record(domain, rtype, rdata, ttl=300, is_protected=False):
    """Build one SDK-like DNS record model."""
    return types.SimpleNamespace(
        domain=domain, rtype=rtype, rdata=rdata, ttl=ttl,
        is_protected=is_protected,
    )


def test_argument_spec_accepts_record_types_as_text():
    """Accept record types without a fixed list of choices."""
    spec = dns_helper.build_dns_argument_spec("rrset")

    assert spec["scope"]["choices"] == ["global", "private"]
    assert spec["zone_name_or_id"]["required"] is True
    assert spec["update_items"]["options"]["ttl"]["type"] == "int"
    assert spec["rtype"] == {"type": "str", "required": True}
    assert spec["update_items"]["options"]["rtype"] == {"type": "str", "required": True}
    assert dns_helper.build_dns_argument_spec("zone", info=True)["rtype"] == {"type": "str"}
    assert dns_helper.build_dns_argument_spec("domain", info=True)["rtype"] == {"type": "str"}


@pytest.mark.parametrize("kind", ["zone", "domain", "rrset"])
def test_info_argument_spec_supports_each_scope_kind(kind):
    """Build info arguments for each DNS scope kind."""
    spec = dns_helper.build_dns_argument_spec(kind, info=True)

    assert spec["zone_name_or_id"]["required"] is True
    assert "scope" in spec
    assert "zone_version" in spec


def test_argument_spec_rejects_unknown_scope_kind():
    """Reject a scope kind that has no DNS API mapping."""
    with pytest.raises(ValueError):
        dns_helper.build_dns_argument_spec("record")


def test_private_scope_requires_view_for_zone_name(monkeypatch):
    """Require a view ID when private scope uses a zone name."""
    monkeypatch.setattr(
        dns_helper.OciModuleBase,
        "__init__",
        lambda self, module: setattr(self, "module", module),
    )

    module = DummyModule({"scope": "private", "zone_name_or_id": "example.com"})
    with pytest.raises(ModuleExit) as result:
        dns_helper.OciDnsRecordsResource(module, "zone")

    assert "view_id is required" in result.value.payload["msg"]


def test_private_scope_accepts_view_and_zone_ocid(monkeypatch):
    """Normalize private scope and accept the view ID with a zone OCID."""
    monkeypatch.setattr(
        dns_helper.OciModuleBase,
        "__init__",
        lambda self, module: setattr(self, "module", module),
    )
    helper = dns_helper.OciDnsRecordsResource(
        DummyModule({
            "scope": "private", "zone_name_or_id": "ocid1.dns-zone.test",
            "view_id": None,
        }),
        "zone",
    )

    assert helper.scope == "PRIVATE"


def test_record_comparison_normalizes_domain_and_type_but_keeps_rdata_exact():
    """Normalize domain and type fields while keeping OCI record data exact."""
    before = [record("WWW.Example.COM.", "AAAA", "OCI; opaque MiXeD data")]
    desired = [{"domain": "www.example.com", "rtype": "aaaa", "rdata": "OCI; opaque MiXeD data", "ttl": 300}]

    assert dns_helper.OciDnsRecordsResource.records_equal(before, desired)


def test_record_comparison_preserves_case_sensitive_txt_data():
    """Keep TXT payload case when the helper compares record data."""
    before = [record("example.com.", "TXT", '"MixedCase"')]
    desired = [{"domain": "example.com", "rtype": "txt", "rdata": '"mixedcase"', "ttl": 300}]

    assert not dns_helper.OciDnsRecordsResource.records_equal(before, desired)


@pytest.mark.parametrize(
    "item,scope,expected",
    [
        ({"domain": "", "rtype": "a", "rdata": "192.0.2.1", "ttl": 300}, "domain", "match the selected domain"),
        ({"domain": "example.com", "rtype": "aaaa", "rdata": "::1", "ttl": 300}, "rrset", "match the selected rtype"),
    ],
)
def test_create_request_rejects_invalid_record_items(item, scope, expected):
    """Reject records outside the selected scope."""
    helper = object.__new__(dns_helper.OciDnsRecordsResource)
    helper.scope_kind = scope
    helper.module = DummyModule({
        "update_items": [item], "domain": "example.com", "rtype": "a",
    })

    with pytest.raises(ModuleExit) as result:
        helper.validate_create_request()

    assert expected in result.value.payload["msg"]


def test_record_fields_preserve_arbitrary_oci_rdata():
    """Keep an OCI record data string unchanged in comparison fields."""
    value = "OCI; opaque MiXeD data"
    fields = dns_helper.OciDnsRecordsResource.record_fields({
        "domain": "example.com", "rtype": "txt", "rdata": value, "ttl": 300,
    })

    assert fields[2] == value
    assert not dns_helper.OciDnsRecordsResource.records_equal(
        [record("example.com", "TXT", value)],
        [{"domain": "example.com", "rtype": "txt", "rdata": value.lower(), "ttl": 300}],
    )


def test_resource_check_mode_reports_diff_without_writing():
    """Report the desired record change in check mode without an API write."""
    helper = object.__new__(dns_helper.OciDnsRecordsResource)
    helper.module = DummyModule(
        {"state": "present", "update_items": [
            {"domain": "www.example.com.", "rtype": "a", "rdata": "192.0.2.2", "ttl": 300},
        ]}, check_mode=True, diff=True,
    )
    helper.check_mode = True
    helper.scope_kind = "domain"
    helper.fetch_records = lambda: [record("www.example.com", "A", "192.0.2.1")]
    helper.validate_create_request = lambda: None
    helper.update_resource = lambda unused: pytest.fail("check mode must not write")

    with pytest.raises(ModuleExit) as result:
        helper.execute_resource_module()

    assert result.value.payload["changed"] is True
    assert result.value.payload["diff"]["before"][0]["rdata"] == "192.0.2.1"
    assert result.value.payload["diff"]["after"][0]["rdata"] == "192.0.2.2"


def test_resource_check_mode_is_idempotent_for_unordered_records():
    """Return unchanged when current and desired record order differs."""
    helper = object.__new__(dns_helper.OciDnsRecordsResource)
    helper.module = DummyModule(
        {"state": "present", "update_items": [
            {"domain": "b.example.com", "rtype": "a", "rdata": "192.0.2.2", "ttl": 300},
            {"domain": "a.example.com", "rtype": "a", "rdata": "192.0.2.1", "ttl": 300},
        ]}, check_mode=True,
    )
    helper.check_mode = True
    helper.scope_kind = "zone"
    helper.fetch_records = lambda: [
        record("a.example.com", "A", "192.0.2.1"),
        record("b.example.com", "A", "192.0.2.2"),
    ]
    helper.validate_create_request = lambda: None

    with pytest.raises(ModuleExit) as result:
        helper.execute_resource_module()

    assert result.value.payload["changed"] is False


def test_record_fetch_unwraps_paginated_collection(monkeypatch):
    """Use the shared pagination helper and return collection items."""
    helper = object.__new__(dns_helper.OciDnsRecordsInfo)
    helper.scope_kind = "domain"
    helper.zone_name = "example.com"
    helper.scope = "GLOBAL"
    helper.view_id = None
    helper.module = types.SimpleNamespace(params={"domain": "www.example.com", "zone_version": "v1"})
    helper.client = types.SimpleNamespace(get_domain_records=lambda **kwargs: kwargs)
    expected = [record("www.example.com", "A", "192.0.2.1")]

    def response_pages(fn, mode, **kwargs):
        assert mode == "response"
        fn(**kwargs)
        yield types.SimpleNamespace(data=types.SimpleNamespace(items=expected), has_next_page=False)

    monkeypatch.setattr(dns_helper.oci.pagination, "list_call_get_all_results_generator", response_pages)
    assert helper.fetch_records() == expected


@pytest.mark.parametrize("kind", ["zone", "domain", "rrset"])
def test_record_fetch_uses_matching_sdk_operation(kind, monkeypatch):
    """Select the OCI list operation for each DNS record scope."""
    helper = object.__new__(dns_helper.OciDnsRecordsInfo)
    helper.scope_kind = kind
    helper.zone_name = "example.com"
    helper.scope = None
    helper.view_id = None
    helper.module = types.SimpleNamespace(params={"domain": "www.example.com", "rtype": "a"})
    calls = []

    def capture(**kwargs):
        calls.append(kwargs)
        return None

    helper.client = types.SimpleNamespace(
        get_zone_records=capture,
        get_domain_records=capture,
        get_rr_set=capture,
    )
    helper.collect_list_filters = lambda filters: {}
    expected = [record("www.example.com", "A", "192.0.2.1")]

    def response_pages(fn, mode, **kwargs):
        assert mode == "response"
        fn(**kwargs)
        yield types.SimpleNamespace(data=types.SimpleNamespace(items=expected), has_next_page=False)

    monkeypatch.setattr(dns_helper.oci.pagination, "list_call_get_all_results_generator", response_pages)
    assert helper.fetch_records() == expected
    assert len(calls) == 1

    if kind != "zone":
        assert calls[0]["domain"] == "www.example.com"

    if kind == "rrset":
        assert calls[0]["rtype"] == "A"


def test_record_fetch_returns_empty_when_scoped_record_is_missing(monkeypatch):
    """Treat a missing domain record collection as empty after zone lookup."""
    helper = object.__new__(dns_helper.OciDnsRecordsInfo)
    helper.scope_kind = "domain"
    helper.zone_name = "example.com"
    helper.scope = None
    helper.view_id = None
    helper.module = types.SimpleNamespace(params={"domain": "www.example.com"})
    helper.client = types.SimpleNamespace(get_domain_records=lambda **kwargs: None)
    zone_lookups = []
    helper.zone = lambda: zone_lookups.append(True)
    helper.collect_list_filters = lambda filters: {}

    class NotFound(Exception):
        status = 404

    def missing_page(*args, **kwargs):
        raise NotFound()

    monkeypatch.setattr(dns_helper.oci.pagination, "list_call_get_all_results_generator", missing_page)
    assert helper.fetch_records() == []
    assert zone_lookups == [True]


def test_update_resource_builds_sdk_record_models():
    """Build record and request models for a domain replacement call."""
    helper = object.__new__(dns_helper.OciDnsRecordsResource)
    helper.scope_kind = "domain"
    helper.zone_name = "example.com"
    helper.scope = None
    helper.view_id = None
    helper.module = types.SimpleNamespace(
        params={"domain": "www.example.com", "update_items": [
            {"domain": "www.example.com", "rtype": "a", "rdata": "192.0.2.1", "ttl": 300},
        ]}
    )
    calls = []
    result = types.SimpleNamespace(items=[])
    helper.client = types.SimpleNamespace(update_domain_records=lambda **kwargs: calls.append(kwargs) or types.SimpleNamespace(data=result))
    helper.call_with_retry = lambda fn, **kwargs: fn(**kwargs)

    assert helper.update_resource([]) == []
    request = calls[0]["update_domain_records_details"]
    assert request.items[0].rtype == "A"
    assert calls[0]["zone_name_or_id"] == "example.com"


def test_absent_state_check_mode_does_not_delete_records():
    """Predict an absent operation in check mode without calling delete."""
    helper = object.__new__(dns_helper.OciDnsRecordsResource)
    helper.module = DummyModule({"state": "absent", "domain": "www.example.com"}, check_mode=True, diff=True)
    helper.check_mode = True
    helper.scope_kind = "domain"
    helper.fetch_records = lambda: [record("www.example.com", "A", "192.0.2.1")]
    helper.delete_resource = lambda unused: pytest.fail("check mode must not delete")

    with pytest.raises(ModuleExit) as result:
        helper.execute_resource_module()

    assert result.value.payload["changed"] is True


def test_info_execution_serializes_records():
    """Return records under the shared info result key."""
    helper = object.__new__(dns_helper.OciDnsRecordsInfo)
    helper.results_key = "records"
    helper.module = DummyModule({})
    helper.fetch_resources = lambda: [record("example.com", "A", "192.0.2.1")]

    with pytest.raises(ModuleExit) as result:
        helper.execute_info_module()

    assert result.value.payload["changed"] is False
    assert result.value.payload["records"][0]["rdata"] == "192.0.2.1"


@pytest.mark.parametrize("zone_status", [404, 403])
def test_missing_record_lookup_checks_zone_and_propagates_errors(zone_status, monkeypatch):
    """Fail when the zone is missing or the zone lookup is not permitted."""
    helper = object.__new__(dns_helper.OciDnsRecordsInfo)
    helper.scope_kind = "domain"
    helper.zone_name = "example.com"
    helper.scope = "GLOBAL"
    helper.view_id = None

    class ServiceError(Exception):
        def __init__(self, status):
            self.status = status

    helper.client = types.SimpleNamespace(
        get_domain_records=lambda **kwargs: None,
        get_zone=lambda **kwargs: (unused for unused in ()).throw(ServiceError(zone_status)),
    )
    helper.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    helper.module = DummyModule({"domain": "www.example.com"})

    def missing_page(*args, **kwargs):
        raise ServiceError(404)

    monkeypatch.setattr(dns_helper.oci.pagination, "list_call_get_all_results_generator", missing_page)

    if zone_status == 404:
        with pytest.raises(ModuleExit) as result:
            helper.fetch_records()
        assert "zone was not found" in result.value.payload["msg"]
    else:
        with pytest.raises(ServiceError) as result:
            helper.fetch_records()
        assert result.value.status == 403


def test_check_mode_reports_changed_records():
    """Report a planned change in check mode."""
    helper = object.__new__(dns_helper.OciDnsRecordsResource)
    helper.module = DummyModule({"state": "present", "update_items": [
        {"domain": "www.example.com", "rtype": "A", "rdata": "192.0.2.2", "ttl": 300},
    ]}, check_mode=True)
    helper.check_mode = True
    helper.scope_kind = "domain"
    helper.fetch_records = lambda: [record("www.example.com", "A", "192.0.2.1")]
    helper.validate_create_request = lambda: None

    with pytest.raises(ModuleExit) as result:
        helper.execute_resource_module()

    assert result.value.payload["changed"] is True


@pytest.mark.parametrize("scope,view_id,expected", [
    ("GLOBAL", None, {"zone_name_or_id": "example.com", "scope": "GLOBAL"}),
    ("PRIVATE", "ocid1.dnsview.oc1..example", {
        "zone_name_or_id": "example.com", "scope": "PRIVATE", "view_id": "ocid1.dnsview.oc1..example",
    }),
])
def test_zone_lookup_passes_only_set_selectors(scope, view_id, expected):
    """Omit an unset view ID and keep the private view ID."""
    helper = object.__new__(dns_helper.OciDnsRecordsInfo)
    helper.zone_name = "example.com"
    helper.scope = scope
    helper.view_id = view_id
    calls = []
    helper.client = types.SimpleNamespace(get_zone=lambda **kwargs: calls.append(kwargs))
    helper.call_with_retry = lambda fn, **kwargs: fn(**kwargs)

    helper.get_resource_response("example.com")

    assert calls == [expected]
