from __future__ import absolute_import, division, print_function
__metaclass__ = type

from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest
from oci.core.models import AppCatalogListing, AppCatalogListingSummary
from oci.response import Response

from .conftest import ExitJsonCalled, load_collection_module, make_module_instance


@pytest.mark.parametrize("name, expected_ids", [(None, ["first", "second"]), ("Exact name", ["second"])])
def test_listings_follow_oci_pages(name, expected_ids):
    """Verify name filtering after OCI pagination.

    Args:
        name: The optional listing name filter.
        expected_ids: The IDs returned after filtering.
    """
    module = load_collection_module("oci_app_catalog_info")
    list_listings = Mock(__name__="list_app_catalog_listings", side_effect=[
        Response(200, {"opc-next-page": "second"}, [AppCatalogListingSummary(listing_id="first", display_name="exact name")], None),
        Response(200, {}, [AppCatalogListingSummary(listing_id="second", display_name="Exact name")], None),
    ])
    instance = make_module_instance(
        module,
        "OciAppCatalogInfoModule",
        {"name": name},
        SimpleNamespace(list_app_catalog_listings=list_listings),
        check_mode=True,
    )
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_info_module()
    assert list_listings.call_args_list == [call(), call(page="second")]
    assert result.value.payload["changed"] is False
    assert [item["listing_id"] for item in result.value.payload["listings"]] == expected_ids
    assert result.value.payload["listings"][-1]["name"] == "Exact name"


def test_listing_get_returns_detail_fields():
    """Verify that the get operation returns the full listing model."""
    module = load_collection_module("oci_app_catalog_info")
    listing = AppCatalogListing(
        listing_id="listing", display_name="Example", contact_url="https://example.com",
    )
    get_listing = Mock(__name__="get_app_catalog_listing", return_value=Response(200, {}, listing, None))
    instance = make_module_instance(
        module, "OciAppCatalogInfoModule", {"listing_id": "listing"},
        SimpleNamespace(get_app_catalog_listing=get_listing),
    )
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_info_module()
    get_listing.assert_called_once_with(listing_id="listing")
    assert result.value.payload["changed"] is False
    returned = result.value.payload["listings"][0]
    assert set(returned) == (set(listing.swagger_types) - {"display_name"}) | {"name"}
    assert returned["name"] == "Example"
    assert returned["contact_url"] == "https://example.com"
