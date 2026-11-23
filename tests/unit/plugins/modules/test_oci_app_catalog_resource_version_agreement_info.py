from __future__ import absolute_import, division, print_function
__metaclass__ = type

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from oci.core.models import AppCatalogListingResourceVersionAgreements
from oci.exceptions import ServiceError
from oci.response import Response

from .conftest import ExitJsonCalled, load_collection_module, make_module_instance


@pytest.mark.parametrize("status", [200, 403, 404])
def test_agreement_info_retrieval(status):
    """Verify agreement retrieval and OCI error handling.

    Args:
        status: The OCI HTTP response status.
    """
    module = load_collection_module("oci_app_catalog_resource_version_agreement_info")
    agreement = AppCatalogListingResourceVersionAgreements(
        listing_id="listing",
        listing_resource_version="1.0",
        signature="signature",
        time_retrieved=datetime(2026, 1, 1, tzinfo=timezone.utc),
        oracle_terms_of_use_link="https://example.com/oracle",
        eula_link="https://example.com/eula",
    )
    get_agreement = Mock(__name__="get_app_catalog_listing_agreements", return_value=Response(status, {}, agreement, None))
    if status != 200:
        get_agreement.side_effect = ServiceError(status, "ExampleError", {}, "Example failure")
    instance = make_module_instance(
        module, "OciAppCatalogResourceVersionAgreementInfoModule",
        {"listing_id": "listing", "listing_resource_version": "1.0"},
        SimpleNamespace(get_app_catalog_listing_agreements=get_agreement), check_mode=True,
    )
    if status == 403:
        with pytest.raises(ServiceError) as result:
            instance.execute_info_module()
        assert result.value.status == 403
    else:
        with pytest.raises(ExitJsonCalled) as result:
            instance.execute_info_module()
        assert result.value.payload["changed"] is False
        assert result.value.payload["agreements"] == ([{
            field: getattr(agreement, field) for field in agreement.swagger_types
        }] if status == 200 else [])
    get_agreement.assert_called_once_with(listing_id="listing", resource_version="1.0")
