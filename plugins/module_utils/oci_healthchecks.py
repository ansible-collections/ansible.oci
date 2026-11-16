"""Shared OCI Health Checks operation metadata."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

MONITOR_TYPES = {
    "http": {
        "create": "create_http_monitor",
        "get": "get_http_monitor",
        "update": "update_http_monitor",
        "delete": "delete_http_monitor",
        "list": "list_http_monitors",
        "create_model": "CreateHttpMonitorDetails",
        "update_model": "UpdateHttpMonitorDetails",
    },
    "ping": {
        "create": "create_ping_monitor",
        "get": "get_ping_monitor",
        "update": "update_ping_monitor",
        "delete": "delete_ping_monitor",
        "list": "list_ping_monitors",
        "create_model": "CreatePingMonitorDetails",
        "update_model": "UpdatePingMonitorDetails",
    },
}
