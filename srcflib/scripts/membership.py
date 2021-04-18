"""
Scripts to manage user and group membership.
"""

from srcf.database.schema import Member, Society

from .utils import confirm, DocOptArgs, entrypoint, error
from ..tasks import membership


@entrypoint
def grant(opts: DocOptArgs, member: Member, society: Society):
    """
    Add a member to a society account's admins.

    Usage: {script} MEMBER SOCIETY
    """
    if member.crsid in society.admin_crsids:
        error("Warning: {} is already an admin of {}".format(member.crsid, society.society))
    confirm("Add {} to {}?".format(member.name, society.description))
    membership.add_society_admin(member, society)

@entrypoint
def revoke(opts: DocOptArgs, member: Member, society: Society):
    """
    Remove a member from a society account's admins.

    Usage: {script} MEMBER SOCIETY
    """
    if member.crsid not in society.admin_crsids:
        error("Warning: {} is not an admin of {}".format(member.crsid, society.society))
    elif society.admin_crsids == {member.crsid}:
        error("Warning: removing the only remaining admin")
    confirm("Remove {} from {}?".format(member.name, society.description))
    membership.remove_society_admin(member, society)
