"""
Mailman mailing lists for members and societies.
"""

from typing import List, Optional, Tuple

from srcf.database import Member

from ..plumbing import bespoke, mailman, Owner, owner_name, Password, Result


def _list_name_owner(owner: Owner, suffix: str = None) -> Tuple[str, str]:
    username = owner_name(owner)
    name = "{}-{}".format(username, suffix) if suffix else username
    admin = "{}@srcf.net".format(username) if isinstance(owner, Member) else owner.email
    return name, admin


def get_list_suffixes(owner: Owner) -> List[Optional[str]]:
    """
    Find the suffixes of all lists belonging to a given owner.
    """
    lists = bespoke.get_mailman_lists(owner)
    return [name.split("-", 1)[1] if "-" in name else None for name in lists]


@Result.collect
def create_list(owner: Owner, suffix: str = None):
    """
    Create a new mailing list for a user or society.
    """
    name, admin = _list_name_owner(owner, suffix)
    if name.endswith(("-post", "-admin", "-bounces", "-confirm", "-join", "-leave", "-owner",
                      "-request", "-subscribe", "-unsubscribe")):
        raise ValueError("List name {!r} ends with reserved suffix".format(name))
    passwd = yield mailman.create_list(name, admin)  # type: Optional[Password]
    yield bespoke.configure_mailing_list(name)
    yield bespoke.generate_mailman_aliases()
    return (name, passwd)


@Result.collect
def reset_owner_password(owner: Owner, suffix: str = None):
    """
    Reset a list's owner to match its name, and generate a new admin password.
    """
    name, admin = _list_name_owner(owner, suffix)
    yield mailman.set_owner(name, admin)
    passwd = yield mailman.reset_password(name)  # type: Password
    return passwd


@Result.collect
def remove_list(owner: Owner, suffix: str = None, remove_archive: bool = False):
    """
    Delete an existing mailing list, and optionally its message archives.
    """
    name, _ = _list_name_owner(owner, suffix)
    yield mailman.remove_list(name, remove_archive)
    yield bespoke.generate_mailman_aliases()
