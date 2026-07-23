# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


class ModuleDocFragment(object):
    DOCUMENTATION = r"""
options:
  wait:
    description:
      - Whether to wait for OCI operations to complete before returning.
    type: bool
    default: true
  wait_timeout:
    description:
      - Maximum number of seconds to wait for OCI operations to complete.
    type: int
    default: 1200
  wait_interval:
    description:
      - Number of seconds between waiter polls while waiting for OCI operations.
    type: int
    default: 30
"""
