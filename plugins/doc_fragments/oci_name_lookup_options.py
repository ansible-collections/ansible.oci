# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


class ModuleDocFragment(object):
    DOCUMENTATION = r"""
options:
  allow_duplicate_name:
    description:
      - Allow C(state=present) to create an additional resource when exactly one
        existing resource already matches the module's scoped name lookup.
      - Has no effect when the explicit resource ID is provided.
      - Has no effect for C(state=absent).
    type: bool
    default: false
"""
