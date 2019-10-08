from typing import Tuple

from srcf.database import Member

from srcflib.plumbing import bespoke, mailman, Owner, owner_name, ResultSet


def _list_name_owner(owner: Owner, suffix: str=None) -> Tuple[str, str]:
    username = owner_name(owner)
    name = "{}-{}".format(username, suffix) if suffix else username
    admin = "{}@srcf.net".format(username) if isinstance(owner, Member) else owner.email
    return name, admin


def create_list(owner: Owner, suffix: str=None) -> ResultSet:
    """
    Create a new mailing list for a user or society.
    """
    name, admin = _list_name_owner(owner, suffix)
    return ResultSet(mailman.create_list(name, admin),
                     bespoke.configure_mailing_list(name))


def reset_owner_password(owner: Owner, suffix: str=None) -> ResultSet:
    """
    Reset a list's owner to match its name, and generate a new admin password.
    """
    name, admin = _list_name_owner(owner, suffix)
    return ResultSet(mailman.set_owner(name, admin),
                     mailman.reset_password(name))
