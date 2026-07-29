from conftest import load_collection_module


def test_collection_namespace_smoke_imports():
    module_names = [
        "oci_auth",
        "oci_common",
        "oci_info",
        "oci_resource",
    ]

    imported_modules = {
        module_name: load_collection_module(module_name) for module_name in module_names
    }

    assert imported_modules["oci_resource"].OciResourceBase.__name__ == "OciResourceBase"
