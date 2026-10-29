from __future__ import absolute_import, division, print_function
__metaclass__ = type

import importlib.util
import types
from pathlib import Path
from unittest.mock import Mock

import pytest


LIBRARY_FILE = Path(__file__).parents[3] / "integration" / "targets" / "oci_dns_records" / "library" / "oci_dns_test_zone.py"
FIXTURE_SPEC = importlib.util.spec_from_file_location("oci_dns_test_zone_fixture", LIBRARY_FILE)
fixture = importlib.util.module_from_spec(FIXTURE_SPEC)
FIXTURE_SPEC.loader.exec_module(fixture)


def _oci():
    return types.SimpleNamespace(
        pagination=types.SimpleNamespace(
            list_call_get_all_results=Mock(return_value=types.SimpleNamespace(data=[]))
        ),
        dns=types.SimpleNamespace(models=types.SimpleNamespace(
            CreateViewDetails=lambda **kwargs: kwargs,
            CreateZoneDetails=lambda **kwargs: kwargs,
        )),
        wait_until=Mock(),
    )


def _params(scope="global"):
    return {
        "scope": scope,
        "zone_name": "fixture.example",
        "view_name": "fixture-view",
        "compartment_id": "compartment",
    }


def test_existing_zone_name_fails_before_create():
    client = types.SimpleNamespace(
        list_zones=Mock(), list_views=Mock(), create_zone=Mock()
    )
    oci = _oci()
    oci.pagination.list_call_get_all_results.return_value.data = [types.SimpleNamespace(id="existing")]

    params = _params()
    with pytest.raises(RuntimeError, match="already exists"):
        fixture._create_fixture(client, oci, params)

    client.create_zone.assert_not_called()


def test_partial_create_error_returns_all_owned_ids():
    client = types.SimpleNamespace(
        list_zones=Mock(), list_views=Mock(),
        create_view=Mock(return_value=types.SimpleNamespace(data=types.SimpleNamespace(id="view-owned"))),
        create_zone=Mock(return_value=types.SimpleNamespace(data=types.SimpleNamespace(id="zone-owned"))),
    )
    oci = _oci()
    oci.wait_until.side_effect = [
        types.SimpleNamespace(data=types.SimpleNamespace(lifecycle_state="ACTIVE")),
        RuntimeError("zone activation failed"),
    ]

    params = _params("private")
    with pytest.raises(fixture.FixtureCreationError) as error:
        fixture._create_fixture(client, oci, params)

    assert error.value.zone_id == "zone-owned"
    assert error.value.view_id == "view-owned"
    assert len(oci.wait_until.call_args_list) == 2
    for waiter_call in oci.wait_until.call_args_list:
        assert len(waiter_call.args) == 2
        assert "evaluate_response" in waiter_call.kwargs
        assert waiter_call.kwargs["evaluate_response"](
            types.SimpleNamespace(data=types.SimpleNamespace(lifecycle_state="ACTIVE"))
        )
        assert waiter_call.kwargs["evaluate_response"](
            types.SimpleNamespace(data=types.SimpleNamespace(lifecycle_state="FAILED"))
        )
        assert not waiter_call.kwargs["evaluate_response"](
            types.SimpleNamespace(data=types.SimpleNamespace(lifecycle_state="CREATING"))
        )


def test_cleanup_uses_only_exact_owned_ids():
    client = types.SimpleNamespace(
        list_zones=Mock(), list_views=Mock(),
        get_zone=Mock(return_value=types.SimpleNamespace(data=types.SimpleNamespace(lifecycle_state="ACTIVE"))),
        delete_zone=Mock(),
        get_view=Mock(return_value=types.SimpleNamespace(data=types.SimpleNamespace(lifecycle_state="ACTIVE"))),
        delete_view=Mock(),
    )
    oci = _oci()
    oci.wait_until.return_value = None

    fixture._remove_fixture(client, oci, dict(_params("private"), zone_id="zone-owned", view_id="view-owned"))

    client.get_zone.assert_called_once_with("zone-owned", scope="PRIVATE")
    client.delete_zone.assert_called_once_with("zone-owned", scope="PRIVATE")
    client.get_view.assert_called_once_with("view-owned")
    client.delete_view.assert_called_once_with("view-owned")
    oci.pagination.list_call_get_all_results.assert_not_called()
