"""
Mailman mailing lists for members and societies.
"""

from typing import Optional, Tuple

from srcf.database import Member

from ..plumbing import bespoke, mailman, Owner, owner_name, Password, ResultSet


def _list_name_owner(owner: Owner, suffix: str = None) -> Tuple[str, str]:
    username = owner_name(owner)
    name = "{}-{}".format(username, suffix) if suffix else username
    admin = "{}@srcf.net".format(username) if isinstance(owner, Member) else owner.email
    return name, admin


def create_list(owner: Owner, suffix: str = None) -> ResultSet[Tuple[mailman.MailList,
                                                                     Optional[Password]]]:
    """
    Create a new mailing list for a user or society.
    """
    name, admin = _list_name_owner(owner, suffix)
    if name.endswith(("-post", "-admin", "-bounces", "-confirm", "-join", "-leave", "-owner",
                      "-request", "-subscribe", "-unsubscribe")):
        raise ValueError("List name {!r} ends with reserved suffix".format(name))
    results = ResultSet(mailman.create_list(name, admin),
                        bespoke.configure_mailing_list(name),
                        bespoke.generate_mailman_aliases())
    results.value = (name, results.results[0].value)
    return results


def reset_owner_password(owner: Owner, suffix: str = None) -> ResultSet[Password]:
    """
    Reset a list's owner to match its name, and generate a new admin password.
    """
    name, admin = _list_name_owner(owner, suffix)
    results = ResultSet[Password](mailman.set_owner(name, admin))
    results.add(mailman.reset_password(name), True)
    return results


def remove_list(owner: Owner, suffix: str = None, remove_archive: bool = False) -> ResultSet:
    """
    Delete an existing mailing list, and optionally its message archives.
    """
    name, _ = _list_name_owner(owner, suffix)
    return ResultSet(mailman.remove_list(name, remove_archive),
                     bespoke.generate_mailman_aliases())
