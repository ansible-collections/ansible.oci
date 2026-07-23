# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


class ModuleDocFragment(object):
    DOCUMENTATION = r"""
options:
  display_name:
    description:
      - Filter listed resources by display name.
      - Only used when C(compartment_id) is provided.
    type: str
  lifecycle_state:
    description:
      - Filter listed resources by lifecycle state.
      - Only used when C(compartment_id) is provided.
    type: str
"""
