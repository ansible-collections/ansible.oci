from __future__ import absolute_import, division, print_function
__metaclass__ = type

from types import SimpleNamespace
from unittest.mock import create_autospec

import oci
import pytest

from ansible_collections.ansible.oci.plugins.module_utils.oci_dns import (
    OciDnsRecordsInfo,
    OciDnsRecordsResource,
)
from .conftest import DummyModule, ExitJsonCalled


def make_record(domain="www.example.com", rtype="A", rdata="192.0.2.10", ttl=300, **extra):
    """Build a DNS response model from the installed OCI SDK."""
    return oci.dns.models.Record(
        domain=domain,
        rtype=rtype,
        rdata=rdata,
        ttl=ttl,
        **extra,
    )


def make_resource(kind, params):
    """Build a resource helper without creating an OCI client."""
    helper = OciDnsRecordsResource.__new__(OciDnsRecordsResource)
    helper.scope_kind = kind
    helper.module = DummyModule(params)
    helper.client = create_autospec(oci.dns.DnsClient, instance=True, spec_set=True)
    helper.zone_name = params["zone_name_or_id"]
    helper.scope = params.get("scope", "GLOBAL").upper()
    helper.view_id = params.get("view_id")
    helper.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    return helper


@pytest.mark.parametrize(
    "kind,method,details_name,details_param,extra_params",
    [
        ("zone", "update_zone_records", "UpdateZoneRecordsDetails", "update_zone_records_details", {}),
        ("domain", "update_domain_records", "UpdateDomainRecordsDetails", "update_domain_records_details", {"domain": "www.example.com"}),
        ("rrset", "update_rr_set", "UpdateRRSetDetails", "update_rr_set_details", {"domain": "www.example.com", "rtype": "A"}),
    ],
)
def test_update_uses_sdk_details_and_record_models(kind, method, details_name, details_param, extra_params):
    """Check every update call uses the installed SDK request models and names."""
    protected = make_record(
        domain="www.example.com",
        rtype="A",
        rdata="192.0.2.5",
        ttl=60,
        record_hash="protected-hash",
        is_protected=True,
        rrset_version="version-1",
    )
    desired = {
        "domain": "www.example.com",
        "rtype": "a",
        "rdata": "OCI; opaque MiXeD data",
        "ttl": 300,
    }
    params = {"zone_name_or_id": "example.com", "update_items": [desired]}
    params.update(extra_params)
    helper = make_resource(kind, params)
    details_type = getattr(oci.dns.models, details_name)
    record_details_type = oci.dns.models.RecordDetails
    expected_kwargs = {
        "zone_name_or_id": "example.com",
        "scope": "GLOBAL",
        "view_id": None,
        **extra_params,
    }

    def update_side_effect(**kwargs):
        assert set(kwargs) == set(expected_kwargs) | {details_param}
        assert {key: kwargs[key] for key in expected_kwargs} == expected_kwargs
        details = kwargs[details_param]
        assert isinstance(details, details_type)
        assert all(isinstance(item, record_details_type) for item in details.items)
        assert [item.rdata for item in details.items] == ["OCI; opaque MiXeD data", "192.0.2.5"]
        assert [item.rtype for item in details.items] == ["A", "A"]
        assert details.items[1].is_protected is True
        assert details.items[1].record_hash == "protected-hash"
        return SimpleNamespace(data=SimpleNamespace(items=details.items))

    getattr(helper.client, method).side_effect = update_side_effect
    result = helper.update_resource([protected])

    assert len(result) == 2
    getattr(helper.client, method).assert_called_once()


def test_record_set_passes_an_unlisted_record_type_to_the_sdk():
    """Pass an unfamiliar record type through to the OCI SDK."""
    helper = make_resource("rrset", {
        "zone_name_or_id": "example.com", "domain": "www.example.com",
        "rtype": "futuretype", "update_items": [{
            "domain": "www.example.com", "rtype": "futuretype",
            "rdata": "opaque data", "ttl": 300,
        }],
    })
    helper.client.update_rr_set.return_value = SimpleNamespace(data=SimpleNamespace(items=[]))

    helper.update_resource([])

    kwargs = helper.client.update_rr_set.call_args.kwargs
    assert kwargs["rtype"] == "FUTURETYPE"
    assert kwargs["update_rr_set_details"].items[0].rtype == "FUTURETYPE"
    assert kwargs["update_rr_set_details"].items[0].rdata == "opaque data"


@pytest.mark.parametrize(
    "kind,method,extra_params",
    [
        ("domain", "delete_domain_records", {"domain": "www.example.com"}),
        ("rrset", "delete_rr_set", {"domain": "www.example.com", "rtype": "A"}),
    ],
)
def test_delete_uses_sdk_operation_and_scope_params(kind, method, extra_params):
    """Check domain and RRset deletion use the OCI SDK operations."""
    params = {"zone_name_or_id": "example.com", **extra_params}
    helper = make_resource(kind, params)
    expected = {
        "zone_name_or_id": "example.com",
        "scope": "GLOBAL",
        "view_id": None,
        **extra_params,
    }
    getattr(helper.client, method).side_effect = lambda **kwargs: (
        pytest.fail("Unexpected delete arguments") if kwargs != expected else None
    )

    helper.delete_resource([])

    getattr(helper.client, method).assert_called_once()


def test_zone_info_uses_sdk_pagination_filters_and_private_scope():
    """Check info requests follow SDK pages and pass DNS filters with private scope."""
    params = {
        "zone_name_or_id": "private.example.com",
        "scope": "private",
        "view_id": "ocid1.dnsview.oc1..example",
        "domain_contains": "example.com",
        "rtype": "a",
        "zone_version": "version-4",
        "sort_by": "domain",
        "sort_order": "desc",
    }
    helper = OciDnsRecordsInfo.__new__(OciDnsRecordsInfo)
    helper.scope_kind = "zone"
    helper.module = DummyModule(params)
    helper.client = create_autospec(oci.dns.DnsClient, instance=True, spec_set=True)
    helper.zone_name = params["zone_name_or_id"]
    helper.scope = "PRIVATE"
    helper.view_id = params["view_id"]
    helper.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    first = make_record(domain="www.example.com", rdata="192.0.2.3")
    second = make_record(domain="api.example.com", rdata="192.0.2.2")
    calls = []

    def list_zone_records(zone_name_or_id, **kwargs):
        calls.append((zone_name_or_id, dict(kwargs)))
        page = kwargs.pop("page", None)
        common = {
            "scope": "PRIVATE",
            "view_id": params["view_id"],
            "domain_contains": "example.com",
            "rtype": "A",
            "zone_version": "version-4",
            "sort_by": "domain",
            "sort_order": "DESC",
        }
        assert zone_name_or_id == "private.example.com"
        assert kwargs == common

        if page is None:
            return oci.Response(
                200,
                {"opc-next-page": "page-2"},
                oci.dns.models.RecordCollection(items=[first]),
                None,
            )

        assert page == "page-2"
        return oci.Response(
            200,
            {},
            oci.dns.models.RecordCollection(items=[second]),
            None,
        )

    helper.client.get_zone_records.side_effect = list_zone_records

    records = helper.fetch_resources()

    assert [record.domain for record in records] == ["www.example.com", "api.example.com"]
    assert len(calls) == 2
    assert calls[1][1]["page"] == "page-2"
    helper.client.get_zone.assert_not_called()


@pytest.mark.parametrize(
    "kind,method,model,params,expected",
    [
        ("domain", "get_domain_records", oci.dns.models.RecordCollection,
         {"domain": "www.example.com", "rtype": "aaaa", "zone_version": "v1",
          "sort_by": "ttl", "sort_order": "desc"},
         {"domain": "www.example.com", "rtype": "AAAA", "zone_version": "v1",
          "sort_by": "ttl", "sort_order": "DESC"}),
        ("rrset", "get_rr_set", oci.dns.models.RRSet,
         {"domain": "www.example.com", "rtype": "aaaa", "zone_version": "v1"},
         {"domain": "www.example.com", "rtype": "AAAA", "zone_version": "v1"}),
    ],
)
def test_scoped_info_passes_selectors_and_filters_to_sdk(kind, method, model, params, expected):
    """Keep domain and record-set SDK selectors and filters distinct."""
    helper = OciDnsRecordsInfo.__new__(OciDnsRecordsInfo)
    helper.scope_kind = kind
    helper.module = DummyModule(params)
    helper.client = create_autospec(oci.dns.DnsClient, instance=True, spec_set=True)
    helper.zone_name = "example.com"
    helper.scope = None
    helper.view_id = None
    item = make_record(rtype="AAAA", rdata="2001:db8::1")
    operation = getattr(helper.client, method)
    operation.return_value = oci.Response(200, {}, model(items=[item]), None)

    assert helper.fetch_resources() == [item]
    operation.assert_called_once_with(
        zone_name_or_id="example.com", scope=None, view_id=None, **expected
    )
    helper.client.get_zone.assert_not_called()


def test_update_uses_requested_ttl_for_matching_protected_record():
    """Do not add a second protected record when its requested TTL changes."""
    protected = make_record(is_protected=True, ttl=60)
    helper = make_resource("domain", {
        "zone_name_or_id": "example.com", "domain": "www.example.com",
        "update_items": [{"domain": "www.example.com", "rtype": "a",
                          "rdata": "192.0.2.10", "ttl": 300}],
    })
    helper.client.update_domain_records.return_value = SimpleNamespace(data=SimpleNamespace(items=[]))

    helper.update_resource([protected])

    items = helper.client.update_domain_records.call_args.kwargs["update_domain_records_details"].items
    assert len(items) == 1
    assert items[0].ttl == 300


def test_update_returns_request_models_when_response_has_no_items():
    """Keep the SDK record models when the response has no item collection."""
    helper = make_resource("domain", {
        "zone_name_or_id": "example.com", "domain": "www.example.com",
        "update_items": [{"domain": "www.example.com", "rtype": "a",
                          "rdata": "192.0.2.10", "ttl": 300}],
    })
    helper.client.update_domain_records.return_value = SimpleNamespace(data=object())

    items = helper.update_resource([])

    assert isinstance(items[0], oci.dns.models.RecordDetails)
    assert items[0].rtype == "A"


def test_record_comparison_normalizes_domain_and_type_but_keeps_rdata_exact():
    """Check OCI field comparison preserves the exact record data string."""
    upper_name = make_record(domain="WWW.Example.COM.", rdata="192.0.2.10")
    lower_name = make_record(domain="www.example.com", rdata="192.0.2.10")
    assert OciDnsRecordsResource.records_equal([upper_name], [lower_name])

    upper_text = make_record(rtype="TXT", rdata='"MiXeD"')
    lower_text = make_record(rtype="TXT", rdata='"mixed"')
    assert not OciDnsRecordsResource.records_equal([upper_text], [lower_text])


def test_check_mode_reports_unchanged_for_matching_record_fields():
    """Check matching writable fields make a repeated run unchanged."""
    current = make_record(domain="WWW.Example.COM.", rdata="192.0.2.10")
    helper = make_resource(
        "domain",
        {
            "zone_name_or_id": "example.com",
            "domain": "www.example.com",
            "state": "present",
            "update_items": [
                {"domain": "www.example.com", "rtype": "a", "rdata": "192.0.2.10", "ttl": 300}
            ],
        },
    )
    helper.check_mode = True
    helper.fetch_records = lambda: [current]

    with pytest.raises(ExitJsonCalled) as result:
        helper.execute_resource_module()

    assert result.value.payload["changed"] is False
    assert result.value.payload["resource"]["items"][0]["domain"] == current.domain
    helper.client.update_domain_records.assert_not_called()


@pytest.mark.parametrize("check_mode", [True, False])
def test_update_diff_preserves_old_data_and_excludes_generated_fields(check_mode):
    """Keep the old value in the diff before both real and predicted updates."""
    helper = make_resource("domain", {
        "zone_name_or_id": "example.com", "domain": "www.example.com",
        "state": "present", "update_items": [{
            "domain": "www.example.com", "rtype": "a",
            "rdata": "192.0.2.20", "ttl": 300,
        }],
    })
    helper.check_mode = check_mode
    helper.module._diff = True
    helper.fetch_records = lambda: [make_record(record_hash="generated")]
    helper.client.update_domain_records.return_value = SimpleNamespace(
        data=oci.dns.models.RecordCollection(items=[make_record(rdata="192.0.2.20")]),
    )
    with pytest.raises(ExitJsonCalled) as result:
        helper.execute_resource_module()
    diff = result.value.payload["diff"]
    assert diff["before"][0]["rdata"] == "192.0.2.10"
    assert diff["after"][0]["rdata"] == "192.0.2.20"
    assert set(diff["before"][0]) == {"domain", "rtype", "rdata", "ttl"}
    assert set(diff["after"][0]) == set(diff["before"][0])
    assert helper.client.update_domain_records.call_count == int(not check_mode)


def test_unchanged_diff_ignores_record_presentation_and_generated_fields():
    """Return equal diff lists when domain case and trailing dots differ."""
    helper = make_resource("domain", {
        "zone_name_or_id": "example.com", "domain": "www.example.com",
        "state": "present", "update_items": [{
            "domain": "www.example.com", "rtype": "a",
            "rdata": "192.0.2.10", "ttl": 300,
        }],
    })
    helper.check_mode = True
    helper.module._diff = True
    helper.fetch_records = lambda: [make_record(domain="WWW.Example.COM.", record_hash="generated")]
    with pytest.raises(ExitJsonCalled) as result:
        helper.execute_resource_module()
    assert result.value.payload["changed"] is False
    assert result.value.payload["diff"]["before"] == result.value.payload["diff"]["after"]


def test_write_read_treats_only_initial_scoped_404_as_absent(monkeypatch):
    """Check a first-page 404 separately from a later page failure."""
    helper = make_resource("domain", {
        "zone_name_or_id": "example.com", "domain": "www.example.com",
        "update_items": [],
    })
    zone_calls = []
    helper.zone = lambda: zone_calls.append(True)

    class NotFound(Exception):
        status = 404

    def initial_404(*args, **kwargs):
        raise NotFound()

    monkeypatch.setattr(oci.pagination, "list_call_get_all_results_generator", initial_404)
    assert helper.fetch_records() == []
    assert zone_calls == [True]

    def later_404(*args, **kwargs):
        yield SimpleNamespace(headers={}, has_next_page=True,
                              next_page="p2", data=SimpleNamespace(items=[]))
        raise NotFound()

    monkeypatch.setattr(oci.pagination, "list_call_get_all_results_generator", later_404)
    with pytest.raises(NotFound):
        helper.fetch_records()


@pytest.mark.parametrize("kind,method,extra", [
    ("domain", "update_domain_records", {"domain": "www.example.com"}),
    ("rrset", "update_rr_set", {"domain": "www.example.com", "rtype": "A"}),
])
def test_missing_collection_can_be_created(monkeypatch, kind, method, extra):
    """Create records when the first read returns 404."""
    params = {"zone_name_or_id": "example.com", "state": "present", "update_items": [
        {"domain": "www.example.com", "rtype": "A", "rdata": "192.0.2.10", "ttl": 300},
    ], **extra}
    helper = make_resource(kind, params)
    helper.check_mode = False
    helper.zone = lambda: None

    class NotFound(Exception):
        status = 404

    def missing_page(*args, **kwargs):
        raise NotFound()

    monkeypatch.setattr(oci.pagination, "list_call_get_all_results_generator", missing_page)
    getattr(helper.client, method).return_value = SimpleNamespace(data=SimpleNamespace(items=[make_record()]))

    with pytest.raises(ExitJsonCalled) as result:
        helper.execute_resource_module()

    assert result.value.payload["changed"] is True
    getattr(helper.client, method).assert_called_once()
