"""
Each function in this module should:

- perform a single action, idempotently where possible
- return a falsy value (``False`` or ``None``) if no change was made
- return a truthy value (``True`` or a result object) if a successful change was made
- raise an exception on any failures
"""

from .common import command, get_members, Hosts, Owner, owner_name, Password, require_host

from . import bespoke, mailman, mysql, pgsql, unix
