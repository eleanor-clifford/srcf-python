"""
Scripts to manage users.
"""

from srcf.database.schema import Member

from .utils import confirm, entrypoint
from ..tasks import membership


@entrypoint
def passwd(member: Member):
    """
    Reset a user's SRCF password.

    Usage: {script} MEMBER
    """
    confirm("Reset {}'s password?".format(member.crsid))
    membership.reset_password(member)
    print("Password changed")
