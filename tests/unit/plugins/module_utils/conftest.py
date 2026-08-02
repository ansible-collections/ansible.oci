from __future__ import absolute_import, division, print_function
__metaclass__ = type

import importlib
import sys


def load_collection_module(module_name, plugin_dir="module_utils"):
    qualified_name = f"ansible_collections.oracle.oci.plugins.{plugin_dir}.{module_name}"
    sys.modules.pop(qualified_name, None)
    return importlib.import_module(qualified_name)


def raising(exception):
    """Return a callable that raises ``exception`` when invoked, ignoring any arguments.

    Handy as a ``monkeypatch.setattr`` replacement for methods that should
    not be called during a given test path.
    """

    def implementation(*args, **kwargs):
        raise exception

    return implementation
