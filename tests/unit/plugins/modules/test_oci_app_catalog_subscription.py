from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from oci.core.models import AppCatalogSubscription
from oci.response import Response

from .conftest import (
    ExitJsonCalled,
    FailJsonCalled,
    FakeModel,
    FakeResponse,
    load_collection_module,
    make_module_instance,
)


def make_subscription(module_obj, params, client=None, check_mode=False):
    """Build a module instance for a focused unit test."""
    return make_module_instance(
        module_obj,
        "OciAppCatalogSubscriptionModule",
        params,
        client=client,
        check_mode=check_mode,
    )


def test_create_validates_agreement_fields():
    """Require the agreement values before a present create."""
    module_obj = load_collection_module("oci_app_catalog_subscription")
    instance = make_subscription(
        module_obj,
        {"compartment_id": "c", "listing_id": "l", "listing_resource_version": "1"},
    )
    with pytest.raises(FailJsonCalled) as failure:
        instance.validate_create_request()
    assert "signature" in failure.value.payload["msg"]
    assert "time_retrieved" in failure.value.payload["msg"]
    assert "oracle_terms_of_use_link" in failure.value.payload["msg"]


def test_resolve_target_matches_version_across_list(monkeypatch):
    """Match only the requested version from the scoped subscription list."""
    module_obj = load_collection_module("oci_app_catalog_subscription")
    resources = [FakeModel(listing_resource_version="0.9"), FakeModel(listing_resource_version="1.0")]
    calls = []
    client = types.SimpleNamespace(
        list_app_catalog_subscriptions=lambda **kwargs: calls.append(kwargs) or FakeResponse(resources)
    )
    instance = make_subscription(
        module_obj,
        {"compartment_id": "c", "listing_id": "l", "listing_resource_version": "1.0"},
        client,
    )
    monkeypatch.setattr(instance, "list_all_resources", lambda fn, **kwargs: fn(**kwargs).data)
    assert instance.resolve_target_resource() is resources[1]
    assert calls == [{"compartment_id": "c", "listing_id": "l"}]


def test_create_subscription_returns_resource():
    """Check the create request and the returned subscription."""
    module_obj = load_collection_module("oci_app_catalog_subscription")
    time_created = datetime(2026, 1, 1, tzinfo=timezone.utc)
    subscription = AppCatalogSubscription(
        publisher_name="Oracle",
        listing_id="l",
        listing_resource_version="1.0",
        listing_resource_id="image",
        display_name="Example",
        summary="Example image listing",
        compartment_id="c",
        time_created=time_created,
    )
    client = types.SimpleNamespace(
        list_app_catalog_subscriptions=Mock(
            __name__="list_app_catalog_subscriptions",
            return_value=Response(200, {}, [], None),
        ),
        create_app_catalog_subscription=Mock(return_value=Response(201, {}, subscription, None)),
    )
    instance = make_subscription(
        module_obj,
        {
            "compartment_id": "c",
            "listing_id": "l",
            "listing_resource_version": "1.0",
            "signature": "sig",
            "time_retrieved": "2026-01-01T00:00:00+00:00",
            "oracle_terms_of_use_link": "https://oracle.example/terms",
            "eula_link": "https://example/eula",
        },
        client,
    )
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload == {
        "changed": True,
        "resource": {
            "publisher_name": "Oracle",
            "listing_id": "l",
            "listing_resource_version": "1.0",
            "listing_resource_id": "image",
            "name": "Example",
            "summary": "Example image listing",
            "compartment_id": "c",
            "time_created": time_created,
        },
    }
    client.create_app_catalog_subscription.assert_called_once()
    details = client.create_app_catalog_subscription.call_args.kwargs[
        "create_app_catalog_subscription_details"
    ]
    assert {field: getattr(details, field) for field in details.swagger_types} == {
        "compartment_id": "c",
        "listing_id": "l",
        "listing_resource_version": "1.0",
        "oracle_terms_of_use_link": "https://oracle.example/terms",
        "eula_link": "https://example/eula",
        "time_retrieved": "2026-01-01T00:00:00+00:00",
        "signature": "sig",
    }


def test_check_mode_does_not_create(monkeypatch):
    """Report a pending create without an OCI write in check mode."""
    module_obj = load_collection_module("oci_app_catalog_subscription")
    instance = make_subscription(
        module_obj,
        {
            "compartment_id": "c",
            "listing_id": "l",
            "listing_resource_version": "1.0",
            "signature": "sig",
            "time_retrieved": "2026-01-01T00:00:00+00:00",
            "oracle_terms_of_use_link": "https://oracle.example/terms",
        },
        types.SimpleNamespace(create_app_catalog_subscription=Mock()),
        check_mode=True,
    )
    monkeypatch.setattr(instance, "resolve_target_resource", lambda: None)
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload == {"changed": True}
    instance.client.create_app_catalog_subscription.assert_not_called()


def test_delete_uses_listing_and_version():
    """Delete the selected listing resource version."""
    module_obj = load_collection_module("oci_app_catalog_subscription")
    calls = []
    client = types.SimpleNamespace(
        delete_app_catalog_subscription=lambda **kwargs: calls.append(kwargs) or FakeResponse(None)
    )
    instance = make_subscription(
        module_obj,
        {"compartment_id": "c", "listing_id": "l", "listing_resource_version": "1.0"},
        client,
    )
    instance.delete_resource(FakeModel(listing_id="l", compartment_id="c", listing_resource_version="1.0"))
    assert calls == [{"listing_id": "l", "compartment_id": "c", "resource_version": "1.0"}]


def test_check_mode_does_not_delete_existing_subscription():
    """Report a pending deletion and leave the subscription in OCI."""
    module_obj = load_collection_module("oci_app_catalog_subscription")
    subscription = AppCatalogSubscription(
        compartment_id="c", listing_id="l", listing_resource_version="1.0"
    )
    client = types.SimpleNamespace(
        list_app_catalog_subscriptions=Mock(
            __name__="list_app_catalog_subscriptions",
            return_value=Response(200, {}, [subscription], None),
        ),
        delete_app_catalog_subscription=Mock(),
    )
    instance = make_subscription(
        module_obj,
        {
            "state": "absent",
            "compartment_id": "c",
            "listing_id": "l",
            "listing_resource_version": "1.0",
        },
        client,
        check_mode=True,
    )
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload == {"changed": True}
    client.delete_app_catalog_subscription.assert_not_called()


@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize("state", ["present", "absent"])
def test_subscription_unchanged(monkeypatch, state, check_mode):
    """Check that a subscription in the requested state needs no write.

    Args:
        monkeypatch: The fixture for mock SDK operations.
        state: The requested subscription state.
        check_mode: Whether to run the module in check mode.
    """
    module_obj = load_collection_module("oci_app_catalog_subscription")
    existing = FakeModel(listing_resource_version="1.0", display_name="Example")
    resources = [existing] if state == "present" else []
    client = types.SimpleNamespace(
        list_app_catalog_subscriptions=Mock(return_value=FakeResponse(resources)),
        create_app_catalog_subscription=Mock(),
        delete_app_catalog_subscription=Mock(),
    )
    instance = make_subscription(
        module_obj,
        {"state": state, "compartment_id": "c", "listing_id": "l", "listing_resource_version": "1.0"},
        client,
        check_mode=check_mode,
    )
    monkeypatch.setattr(instance, "list_all_resources", lambda fn, **kwargs: fn(**kwargs).data)
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    expected = {"changed": False}
    if state == "present":
        expected["resource"] = {"listing_resource_version": "1.0", "name": "Example"}
    assert result.value.payload == expected
    client.create_app_catalog_subscription.assert_not_called()
    client.delete_app_catalog_subscription.assert_not_called()
