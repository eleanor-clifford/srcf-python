"""
Mailman mailing list management.
"""

import logging
import os.path
import re

from .common import command, Hosts, Password, require_host


LOG = logging.getLogger(__name__)


def list_exists(name: str) -> bool:
    """
    Test if a list of the given name has been created.
    """
    return os.path.isdir(os.path.join("/var/lib/mailman/lists", name))


@require_host(Hosts.LIST)
def new_list(name: str, owner: str) -> bool:
    """
    Create a new mailing list for the owning email address, with a random password.
    """
    if list_exists(name):
        raise ValueError("List {!r} already exists".format(name))
    elif not re.match(r"^[A-Za-z0-9\-]+$", name):
        raise ValueError("Invalid list name {!r}".format(name))
    elif name.rsplit("-", 1)[-1] in ("admin", "bounces", "confirm", "join", "leave", "owner",
                                     "request", "subscribe", "unsubscribe"):
        raise ValueError("List name {!r} suffixed with reserved keyword".format(name))
    passwd = Password.new()
    command(["/usr/bin/sshpass", "/usr/sbin/newlist", name, owner], passwd)
    return True


@require_host(Hosts.LIST)
def set_owner(name: str, *owners: str) -> bool:
    """
    Overwrite the owners of a list.
    """
    data = "owner = {}".format(repr(list(owners)))
    command(["/usr/sbin/config_list", "--inputfile", "/dev/stdin", name], data)
    return True


@require_host(Hosts.LIST)
def reset_password(name: str) -> bool:
    """
    Let Mailman generate a new admin password for a list.
    """
    command(["/usr/lib/mailman/bin/change_pw", "--listname", name])
    return True


def create_list(name: str, owner: str) -> bool:
    """
    Create a new mailing list, or ensure the owner of an existing list is set.
    """
    if list_exists(name):
        return set_owner(name, owner)
    else:
        return new_list(name, owner)
