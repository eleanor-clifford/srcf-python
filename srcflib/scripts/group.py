"""
Scripts to manage groups and their membership.
"""

from typing import Optional

from sqlalchemy.orm import Session

from srcf.database.schema import Member, Society
from srcf.mail import SYSADMINS

from .utils import confirm, entrypoint, error
from ..email import send
from ..tasks import membership


@entrypoint
def grant(sess: Session, member: Member, society: Society, actor: Optional[Member]):
    """
    Add a member to a group account's admins.

    Usage: {script} MEMBER SOCIETY [ACTOR]

    An actor, if given, will appear in user-facing emails as the person who requested the change.
    """
    if member.crsid in society.admin_crsids:
        error("Warning: {} is already an admin of {}".format(member.crsid, society.society))
    if not actor:
        error("Warning: no actor given")
    elif actor.crsid not in society.admin_crsids:
        error("Warning: actor {} is not an admin of {}".format(actor.crsid, society.society))
    confirm("Add {} to {}?".format(member.name, society.description))
    if membership.add_society_admin(sess, member, society, actor):
        send(SYSADMINS, "scripts/group_grant.j2", {"member": member, "society": society})


@entrypoint
def revoke(sess: Session, member: Member, society: Society, actor: Optional[Member]):
    """
    Remove a member from a group account's admins.

    Usage: {script} MEMBER SOCIETY [ACTOR]

    An actor, if given, will appear in user-facing emails as the person who requested the change.
    """
    if member.crsid not in society.admin_crsids:
        error("Warning: {} is not an admin of {}".format(member.crsid, society.society))
    elif society.admin_crsids == {member.crsid}:
        error("Warning: removing the only remaining admin")
    if not actor:
        error("Warning: no actor given")
    elif actor.crsid not in society.admin_crsids:
        error("Warning: actor {} is not an admin of {}".format(actor.crsid, society.society))
    confirm("Remove {} from {}?".format(member.name, society.description))
    if membership.remove_society_admin(sess, member, society, actor):
        send(SYSADMINS, "scripts/group_revoke.j2", {"member": member, "society": society})


@entrypoint
def delete(sess: Session, society: Society):
    """
    Delete a group account.

    Usage: {script} SOCIETY
    """
    confirm("Delete {}?".format(society.description))
    membership.delete_society(sess, society)
