from typing import Tuple

from srcf.database import Member

from srcflib.plumbing import bespoke, mailman, Owner, owner_name, Password, Result, ResultSet


def _list_name_owner(owner: Owner, suffix: str=None) -> Tuple[str, str]:
    username = owner_name(owner)
    name = "{}-{}".format(username, suffix) if suffix else username
    admin = "{}@srcf.net".format(username) if isinstance(owner, Member) else owner.email
    return name, admin


def create_list(owner: Owner, suffix: str=None) -> ResultSet[Password]:
    """
    Create a new mailing list for a user or society.
    """
    name, admin = _list_name_owner(owner, suffix)
    results = ResultSet(mailman.create_list(name, admin))
    results.value = results.last.value
    results.add(bespoke.configure_mailing_list(name),
                bespoke.generate_mailman_aliases())
    return results


def reset_owner_password(owner: Owner, suffix: str=None) -> ResultSet[Password]:
    """
    Reset a list's owner to match its name, and generate a new admin password.
    """
    name, admin = _list_name_owner(owner, suffix)
    results = ResultSet(mailman.set_owner(name, admin),
                        mailman.reset_password(name))
    results.value = results.last.value
    return results


def remove_list(owner: Owner, suffix: str=None, remove_archive: bool=False) -> ResultSet:
    """
    Delete an existing mailing list, and optionally its message archives.
    """
    name, _ = _list_name_owner(owner, suffix)
    return ResultSet(mailman.remove_list(name, remove_archive),
                     bespoke.generate_mailman_aliases())
