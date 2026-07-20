from pathlib import Path


COLLECTION_ROOT = Path(__file__).resolve().parents[4]


def test_upstream_module_utils_file_set_is_present():
    expected_paths = [
        "plugins/module_utils/__init__.py",
        "plugins/module_utils/oci_auth.py",
        "plugins/module_utils/oci_common.py",
        "plugins/module_utils/oci_resource.py",
        "plugins/module_utils/oci_wait.py",
    ]

    missing_paths = [
        path for path in expected_paths if not (COLLECTION_ROOT / path).is_file()
    ]

    assert missing_paths == []
