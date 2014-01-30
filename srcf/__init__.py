#!/usr/bin/env python

"""SRCF python library for common actions in maintenance scripts"""

__all__ = [
    ]

# Compatibility magic until all callers are updated
from srcf.compat import MEMBERLIST, SOCLIST
from srcf.compat import Member, MemberSet
from srcf.compat import Society, SocietySet
from srcf.compat import get_members, get_member
from srcf.compat import get_users, get_user
from srcf.compat import get_societies, get_society
from srcf.compat import members, members_and_socs
from srcf.compat import societies, pwgen

__all__ += [
    'MEMBERLIST', 'SOCLIST',
    'Member', 'MemberSet',
    'Society', 'SocietySet',
    'get_members', 'get_member',
    'get_users', 'get_user',
    'get_societies', 'get_society',
    'members', 'members_and_socs',
    'societies', 'pwgen'
    ]

# Local Variables:
# mode: python
# coding: utf-8
# tab-width: 4
# indent-tabs-mode: nil
# End:
