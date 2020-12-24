#!/usr/bin/python

"""SRCF python library for common actions in maintenance scripts"""

import warnings

# Python 2 & 3 compatability
import six

from srcf.passwords import pwgen

from . import compat
from .compat import *


# Users of the SRCF library beware
warnings.filterwarnings("once", category=DeprecationWarning)

# Canonical locations of various things
MEMBERLIST = "/societies/sysadmins/admin/memberlist"
SOCLIST = "/societies/sysadmins/admin/soclist"
SOCQUEUE = "/societies/srcf/admin/socqueue"

# No argcomplete for py3 yet
if not six.PY3:
    from srcf.argcompletors import complete_member, complete_user
    from srcf.argcompletors import complete_soc, complete_activesoc
    from srcf.argcompletors import complete_socadmin
else:
    complete_member = complete_user = complete_soc = complete_activesoc = complete_socadmin = None

__all__ = [
    'MEMBERLIST', 'SOCLIST', 'pwgen',
    'complete_member', 'complete_user', 'complete_soc',
    'complete_activesoc', 'complete_socadmin',
]

# Compatibility magic until all callers are updated
__all__ += compat.__all__
