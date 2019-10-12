"""
Mailman mailing list management.
"""

import logging
import os.path
import re
from typing import List

from .common import command, Hosts, Password, require_host, Result, State


# Type alias for external callers, who need not be aware of the internal structure when chaining
# calls (e.g. get_list/new_list -> reset_password).
MailList = str


LOG = logging.getLogger(__name__)


@require_host(Hosts.LIST)
def get_list(name: str) -> MailList:
    """
    Test if a list of the given name has been created.
    """
    if os.path.isdir(os.path.join("/var/lib/mailman/lists", name)):
        return name
    else:
        raise KeyError(name)


@require_host(Hosts.LIST)
def get_owners(mlist: MailList) -> List[str]:
    """
    Look up all owner email addresses of a mailing list.
    """
    proc = command(["/usr/lib/mailman/bin/list_owners", mlist], output=True)
    return list(proc.stdout.decode("utf-8").split("\n"))


@require_host(Hosts.LIST)
def new_list(name: str, owner: str) -> Result[Password]:
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
    command(["/usr/bin/sshpass", "/usr/sbin/newlist", "--quiet", name, owner], passwd)
    return Result(State.success, passwd)


@require_host(Hosts.LIST)
def set_owner(mlist: MailList, *owners: str) -> Result:
    """
    Overwrite the owners of a list.
    """
    current = get_owners(mlist)
    if set(current) == set(owners):
        return Result(State.unchanged)
    data = "owner = {}".format(repr(list(owners)))
    command(["/usr/sbin/config_list", "--inputfile", "/dev/stdin", mlist], data)
    return Result(State.success)


@require_host(Hosts.LIST)
def reset_password(mlist: MailList) -> Result[Password]:
    """
    Let Mailman generate a new admin password for a list.
    """
    proc = command(["/usr/lib/mailman/bin/change_pw", "--quiet", "--listname", mlist], output=True)
    for line in proc.stdout.decode("utf-8").split("\n"):
        if line.startswith("New {} password: ".format(mlist)):
            passwd = Password(line.split(": ", 1)[1])
            return Result(State.success, passwd)
    else:
        raise ValueError("Couldn't find password in output")


def create_list(name: str, owner: str) -> Result[MailList]:
    """
    Create a new mailing list, or ensure the owner of an existing list is set.
    """
    try:
        mlist = get_list(name)
    except KeyError:
        return new_list(name, owner)
    else:
        result = set_owner(name, owner)
        result.value = mlist
        return result


@require_host(Hosts.LIST)
def remove_list(name: str, remove_archive: bool=False) -> Result:
    """
    Delete an existing mailing list, and optionally its message archives.
    """
    config = os.path.exists(os.path.join("/var/lib/mailman/lists", name))
    archive = os.path.exists(os.path.join("/var/lib/mailman/archives/private", name))
    if not (config or (remove_archive and archive)):
        return Result(State.unchanged)
    args = ["/usr/sbin/rmlist", name]
    if remove_archive:
        args[1:1] = ["--archives"]
    command(args)
    return Result(State.success)
