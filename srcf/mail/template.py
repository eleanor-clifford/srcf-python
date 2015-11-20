#!/usr/bin/env python3

"""
Patterns that are substituted:

Misc:
  %sysadmin% - the person sending the email

When mailing a user:
  %crsid%
  %preferred_name%
  %surname%
  %email%

... and for backwards compatibility:
  %firstname%
  %initials%
  %status% (i.e. member, user, etc)
  %joindate%

When mailing a society:
  %society%
  %description%
  %admins%
  %email%

... and for backwards compatibility:
  %socid%
  %soclongname%
  %socadminlist%
  %socprettyadminlist%
  %joindate%

"""

import sys
import codecs

from ..database.summarise import summarise

def from_stdin(keys):
    """Get an email template from stdin, and invoke `replace`"""
    stdin = sys.stdin
    if hasattr(stdin, 'detach'):
        stdin = stdin.detach()
    stdin = codecs.getreader("utf-8")(stdin)
    return replace(stdin.read(), keys)

def replace(body, keys):
    """For each key and value, replace '%key%' with value"""
    for key, value in keys.items():
        body = body.replace("%" + key + "%", value)
    return body

def substitutions(obj):
    """
    Return a dict of standard substitutions (see module documentation)
    
    obj should be a srcf.database.Member or Society
    """

    if hasattr(obj, "crsid"):   # if it looks like a duck...
        keys = ["crsid", "preferred_name", "surname", "email"]
        keys += ["firstname", "initials", "status", "joindate"]
        keys = {k: getattr(obj, k) for k in keys}
    else:
        keys = {
            "society": obj.society,
            "description": obj.description,
            "admins": ', '.join(sorted(obj.admin_crsids)),
            "email": obj.society + "-admins@srcf.net",

            "socid": obj.society,
            "soclongname": obj.description,
            "socadminlist": ','.join(sorted(obj.admin_crsids)),
            "socprettyadminlist": summarise(obj.admins),
            "joindate": obj.joindate
        }

    return keys
