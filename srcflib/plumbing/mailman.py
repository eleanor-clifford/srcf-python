"""
Mailman mailing list management.
"""

import logging
import os.path
import re

from .common import command, Hosts, Password, require_host


# Type alias for external callers, who need not be aware of the internal structure when chaining
# calls (e.g. get_list/new_list -> reset_password).
List = str


LOG = logging.getLogger(__name__)


def get_list(name: str) -> List:
    """
    Test if a list of the given name has been created.
    """
    if os.path.isdir(os.path.join("/var/lib/mailman/lists", name)):
        return name
    else:
        raise KeyError(name)


@require_host(Hosts.LIST)
def new_list(name: str, owner: str) -> List:
    """
    Create a new mailing list for the owning email address, with a random password.
    """
    try:
        get_list(name)
    except KeyError:
        pass
    else:
        raise ValueError("List {!r} already exists".format(name))
    if not re.match(r"^[A-Za-z0-9\-]+$", name):
        raise ValueError("Invalid list name {!r}".format(name))
    elif name.rsplit("-", 1)[-1] in ("admin", "bounces", "confirm", "join", "leave", "owner",
                                     "request", "subscribe", "unsubscribe"):
        raise ValueError("List name {!r} suffixed with reserved keyword".format(name))
    passwd = Password.new()
    command(["/usr/bin/sshpass", "/usr/sbin/newlist", name, owner], passwd)
    return name


@require_host(Hosts.LIST)
def set_owner(mlist: List, *owners: str) -> bool:
    """
    Overwrite the owners of a list.
    """
    data = "owner = {}".format(repr(list(owners)))
    command(["/usr/sbin/config_list", "--inputfile", "/dev/stdin", mlist], data)
    return True


@require_host(Hosts.LIST)
def reset_password(mlist: List) -> bool:
    """
    Let Mailman generate a new admin password for a list.
    """
    command(["/usr/lib/mailman/bin/change_pw", "--listname", mlist])
    return True


def create_list(name: str, owner: str) -> List:
    """
    Create a new mailing list, or ensure the owner of an existing list is set.
    """
    try:
        mlist = get_list(name)
    except KeyError:
        return new_list(name, owner)
    else:
        set_owner(name, owner)
        return mlist
