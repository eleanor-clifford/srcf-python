"""
Scripts to manage Mailman mailing lists.
"""

from .utils import confirm, DocOptArgs, entrypoint
from ..plumbing.common import Owner
from ..tasks import mailman


@entrypoint
def create(opts: DocOptArgs, owner: Owner):
    """
    Create a Mailman mailing list.

    If SUFFIX is omitted, the list will be named after its owner, without a suffix.

    Usage: {script} OWNER [SUFFIX]
    """
    name, admin = mailman._list_name_owner(owner, opts["SUFFIX"])
    print("List address: {}@srcf.net{}".format(name, "" if opts["SUFFIX"] else " (!)"))
    print("Owner: {}".format(admin))
    confirm("Create this list?")
    result = mailman.create_list(owner, opts["SUFFIX"])
    if result:
        _, password = result.value
        if password:
            print("Created Mailman list {!r} owned by {}".format(name, admin))
        else:
            print("Reset owner of list {!r} to {}".format(name, admin))


@entrypoint
def delete(opts: DocOptArgs, owner: Owner):
    """
    Delete a Mailman mailing list, and optionally its archives.

    Usage: {script} OWNER [SUFFIX] [--archives]
    """
    name, _ = mailman._list_name_owner(owner, opts["SUFFIX"])
    archives = opts["--archives"]
    print("List address: {}@srcf.net".format(name))
    confirm("Delete this list{}?".format(" and its archives" if archives else ""))
    if mailman.remove_list(owner, opts["SUFFIX"], archives):
        print("Deleted Mailman list {!r}".format(name))
