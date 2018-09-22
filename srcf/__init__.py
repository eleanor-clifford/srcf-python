#!/usr/bin/python

"""SRCF python library for common actions in maintenance scripts"""

# Python 2 & 3 compatability
import six as __six

# Users of the SRCF library beware
import warnings
warnings.filterwarnings("once", category=DeprecationWarning)

# Canonical locations of various things
MEMBERLIST = "/societies/sysadmins/admin/memberlist"
SOCLIST = "/societies/sysadmins/admin/soclist"
SOCQUEUE = "/societies/srcf/admin/socqueue"

from srcf.passwords import pwgen

__all__ = [
    'MEMBERLIST', 'SOCLIST',
    'pwgen',
    ]

# No argcomplete for py3 yet
if not __six.PY3:
    from srcf.argcompletors import complete_member, complete_user
    from srcf.argcompletors import complete_soc, complete_activesoc
    from srcf.argcompletors import complete_socadmin

    __all__ += [
        'complete_member', 'complete_user', 'complete_soc',
        'complete_activesoc', 'complete_socadmin',
        ]

# Compatibility magic until all callers are updated
from .compat import *
from . import compat

__all__ += compat.__all__
