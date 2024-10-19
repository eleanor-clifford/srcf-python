"""
Scripts to manage Mailman mailing lists.
"""

from typing import Optional

from .utils import confirm, DocOptArgs, entrypoint
from ..email import send, SYSADMINS
from ..plumbing.common import Owner
from ..tasks import mailman


@entrypoint
def create(opts: DocOptArgs, owner: Owner, suffix: Optional[str]):
    """
    Create a Mailman mailing list.

    If SUFFIX is omitted, the list will be named after its owner, without a suffix.

    Usage: {script} OWNER [SUFFIX]
    """
    name, admin = mailman._list_name_owner(owner, suffix)
    print("List address: {}@srcf.net{}".format(name, "" if suffix else " (!)"))
    print("Owner: {}".format(admin))
    exists = suffix in mailman.get_list_suffixes(owner)
    confirm("Reset this list's owner?" if exists else "Create this list?")
    result = mailman.create_list(owner, suffix)
    if result:
        _, password = result.value
        send(SYSADMINS, "scripts/mailman_create.j2", {"name": name, "created": bool(password)})


@entrypoint
def delete(opts: DocOptArgs, owner: Owner, suffix: Optional[str]):
    """
    Delete a Mailman mailing list, and optionally its archives.

    Usage: {script} OWNER [SUFFIX] [--archives]
    """
    name, _ = mailman._list_name_owner(owner, suffix)
    archives = opts["--archives"]
    print("List address: {}@srcf.net".format(name))
    confirm("Delete this list{}?".format(" and its archives" if archives else ""))
    if mailman.remove_list(owner, suffix, archives):
        send(SYSADMINS, "scripts/mailman_delete.j2", {"name": name})
