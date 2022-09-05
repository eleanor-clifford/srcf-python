"""
Scripts to manage groups and their membership.
"""

from sqlalchemy.orm import Session

from srcf.database.schema import Member, Society
from srcf.mail import SYSADMINS

from .utils import confirm, entrypoint, error
from ..email import send
from ..tasks import membership


@entrypoint
def grant(sess: Session, member: Member, society: Society):
    """
    Add a member to a group account's admins.

    Usage: {script} MEMBER SOCIETY
    """
    if member.crsid in society.admin_crsids:
        error("Warning: {} is already an admin of {}".format(member.crsid, society.society))
    confirm("Add {} to {}?".format(member.name, society.description))
    if membership.add_society_admin(sess, member, society):
        send(SYSADMINS, "scripts/group_grant.j2", {"member": member, "society": society})


@entrypoint
def revoke(sess: Session, member: Member, society: Society):
    """
    Remove a member from a group account's admins.

    Usage: {script} MEMBER SOCIETY
    """
    if member.crsid not in society.admin_crsids:
        error("Warning: {} is not an admin of {}".format(member.crsid, society.society))
    elif society.admin_crsids == {member.crsid}:
        error("Warning: removing the only remaining admin")
    confirm("Remove {} from {}?".format(member.name, society.description))
    if membership.remove_society_admin(sess, member, society):
        send(SYSADMINS, "scripts/group_revoke.j2", {"member": member, "society": society})


@entrypoint
def delete(sess: Session, society: Society):
    """
    Delete a group account.

    Usage: {script} SOCIETY
    """
    confirm("Delete {}?".format(society.description))
    membership.delete_society(sess, society)
