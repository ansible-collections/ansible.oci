import importlib
import sys


def load_collection_module(module_name, plugin_dir="module_utils"):
    qualified_name = f"ansible_collections.oracle.oci.plugins.{plugin_dir}.{module_name}"
    sys.modules.pop(qualified_name, None)
    return importlib.import_module(qualified_name)
