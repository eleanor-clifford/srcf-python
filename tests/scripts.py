from srcf.database import Member, Society

from srcflib.plumbing.common import Owner
from srcflib.scripts.utils import DocOptArgs, entrypoint


@entrypoint
def no_args(opts: DocOptArgs):
    """
    Usage: {script}
    """


@entrypoint
def with_member_society(opts: DocOptArgs, member: Member, society: Society):
    """
    Usage: {script} MEMBER SOCIETY
    """
    return (member, society)


@entrypoint
def with_owner(opts: DocOptArgs, owner: Owner):
    """
    Usage: {script} OWNER
    """
    return owner
