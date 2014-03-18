#!/usr/bin/env python

"""SRCF python library for common actions in maintenance scripts"""

# Python 2 & 3 compatability
import six as __six

# Canonical locations of various things
MEMBERLIST = "/societies/sysadmins/admin/memberlist"
SOCLIST = "/societies/sysadmins/admin/soclist"

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
from srcf.compat import Member, MemberSet
from srcf.compat import Society, SocietySet
from srcf.compat import get_members, get_member
from srcf.compat import get_users, get_user
from srcf.compat import get_societies, get_society
from srcf.compat import members, members_and_socs
from srcf.compat import societies

__all__ += [
    'Member', 'MemberSet',
    'Society', 'SocietySet',
    'get_members', 'get_member',
    'get_users', 'get_user',
    'get_societies', 'get_society',
    'members', 'members_and_socs',
    'societies'
    ]

# Local Variables:
# mode: python
# coding: utf-8
# tab-width: 4
# indent-tabs-mode: nil
# End:
