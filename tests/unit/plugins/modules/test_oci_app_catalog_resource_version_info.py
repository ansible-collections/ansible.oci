from __future__ import absolute_import, division, print_function
__metaclass__ = type

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from oci.core.models import AppCatalogListingResourceVersion, AppCatalogListingResourceVersionSummary
from oci.response import Response

from .conftest import ExitJsonCalled, load_collection_module, make_module_instance


@pytest.mark.parametrize("version", [None, "1.0"])
def test_version_info_returns_image_id(version):
    """Verify version discovery returns the image ID for both operations.

    Args:
        version: The version to fetch, or None for a list operation.
    """
    module = load_collection_module("oci_app_catalog_resource_version_info")
    summary = AppCatalogListingResourceVersionSummary(listing_resource_id="image")
    detail = AppCatalogListingResourceVersion(listing_resource_id="image")
    client = SimpleNamespace(
        list_app_catalog_listing_resource_versions=Mock(__name__="list_app_catalog_listing_resource_versions", return_value=Response(200, {}, [summary], None)),
        get_app_catalog_listing_resource_version=Mock(__name__="get_app_catalog_listing_resource_version", return_value=Response(200, {}, detail, None)),
    )
    instance = make_module_instance(
        module, "OciAppCatalogResourceVersionInfoModule",
        {"listing_id": "listing", "listing_resource_version": version}, client, check_mode=True,
    )
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_info_module()
    if version is None:
        client.list_app_catalog_listing_resource_versions.assert_called_once_with(listing_id="listing")
        client.get_app_catalog_listing_resource_version.assert_not_called()
    else:
        client.get_app_catalog_listing_resource_version.assert_called_once_with(listing_id="listing", resource_version=version)
        client.list_app_catalog_listing_resource_versions.assert_not_called()
    assert result.value.payload["changed"] is False
    returned = result.value.payload["listing_resource_versions"][0]
    assert returned["listing_resource_id"] == "image"
    assert set(returned) == set((summary if version is None else detail).swagger_types)
