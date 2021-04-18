"""
Mailman mailing lists for members and societies.
"""

from typing import List, Optional, Tuple

from srcf.database import Member

from ..plumbing import bespoke, mailman
from ..plumbing.common import Collect, Owner, State, owner_name, Password, Result


def _list_name_owner(owner: Owner, suffix: Optional[str] = None) -> Tuple[str, str]:
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
def create_list(owner: Owner, suffix: Optional[str] = None) -> Collect[Tuple[str, Optional[Password]]]:
    """
    Create a new mailing list for a user or society.
    """
    name, admin = _list_name_owner(owner, suffix)
    if name.endswith(("-post", "-admin", "-bounces", "-confirm", "-join", "-leave", "-owner",
                      "-request", "-subscribe", "-unsubscribe")):
        raise ValueError("List name {!r} ends with reserved suffix".format(name))
    res_create = yield from mailman.ensure_list(name, admin)
    if res_create.state == State.created:
        yield bespoke.configure_mailing_list(name)
        yield bespoke.generate_mailman_aliases()
    return (name, res_create.value)


@Result.collect
def reset_owner_password(owner: Owner, suffix: Optional[str] = None) -> Collect[Password]:
    """
    Reset a list's owner to match its name, and generate a new admin password.
    """
    name, admin = _list_name_owner(owner, suffix)
    yield mailman.set_owner(name, admin)
    res_passwd = yield from mailman.reset_password(name)
    return res_passwd.value


@Result.collect
def remove_list(owner: Owner, suffix: Optional[str] = None, remove_archive: bool = False) -> Collect[None]:
    """
    Delete an existing mailing list, and optionally its message archives.
    """
    name, _ = _list_name_owner(owner, suffix)
    res_remove = yield from mailman.remove_list(name, remove_archive)
    if res_remove:
        yield bespoke.generate_mailman_aliases()
