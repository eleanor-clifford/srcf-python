"""
Scripts to manage users.
"""

from typing import Optional, Sequence

from sqlalchemy.orm import Session

from srcf.database.schema import Member

from .utils import confirm, entrypoint
from ..email import send, SYSADMINS
from ..tasks import membership


@entrypoint
def passwd(member: Member):
    """
    Reset a user's SRCF password.

    Usage: {script} MEMBER
    """
    confirm("Reset {}'s password?".format(member.crsid))
    if membership.reset_password(member):
        send(SYSADMINS, "scripts/member_passwd.j2", {"member": member})


@entrypoint
def cancel(sess: Session, members: Sequence[Member], unset_member: bool, keep_contactable: bool):
    """
    Cancel a user account.

    Usage: {script} MEMBERS... [--unset-member] [--keep-contactable]
    """
    if len(members) > 1:
        print("Cancelling:")
        for member in members:
            print("- {}".format(member.name))
        confirm("Cancel {} members?".format(len(members)))
    else:
        confirm("Cancel {}?".format(members[0].name))
    is_member = False if unset_member else None
    is_contactable = None if keep_contactable else False
    for member in members:
        membership.cancel_member(sess, member, is_member, is_contactable)


@entrypoint
def reactivate(sess: Session, member: Member, email: Optional[str]):
    """
    Reinstate a user account.

    Usage: {script} MEMBER [EMAIL]
    """
    if not email:
        email = member.email
        print("Keeping existing email address: {}".format(email))
    confirm("Reactivate {}?".format(member.name))
    membership.reactivate_member(sess, member, email)
