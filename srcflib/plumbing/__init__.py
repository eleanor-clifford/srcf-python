"""
Low-level APIs for fine-grained service management.

Each function in this module should:

- perform a single action idempotently
- return a `Result` object
- raise an exception on any failures
"""

from .common import (command, get_members, Hosts, Owner, owner_name, Password, require_host,
                     Result, ResultSet, State)

from . import bespoke, mailman, mysql, pgsql, unix
