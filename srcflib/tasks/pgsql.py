"""
PostgreSQL accounts and databases for members and societies.
"""

from functools import wraps
from typing import Optional, List, Set, Tuple, Union

from psycopg2.extensions import connection as Connection, cursor as Cursor

from srcf.database import Member, Society
from srcf.database.queries import get_member, get_society

from ..email import send
from ..plumbing import pgsql
from ..plumbing.common import Collect, Owner, State, owner_name, Password, Result, Unset


def connect(db: Optional[str] = None) -> Connection:
    """
    Connect to the PostgreSQL server using ident authentication.
    """
    return pgsql.connect("postgres.internal", db or "sysadmins")


@wraps(pgsql.context)
def context(db: Optional[str] = None):
    """
    Run multiple PostgreSQL commands in a single connection:

        with context() as cursor:
            create_account(cursor, owner)
            create_database(cursor, owner)
    """
    return pgsql.context(connect(db))


def get_owned_databases(cursor: Cursor, owner: Owner) -> List[str]:
    """
    Find all PostgreSQL databases belonging to a given owner.
    """
    try:
        role = pgsql.get_role(cursor, owner_name(owner))
    except KeyError:
        return []
    else:
        return pgsql.get_role_databases(cursor, role)


@Result.collect
def new_account(cursor: Cursor, owner: Owner) -> Collect[Optional[Password]]:
    """
    Create a PostgreSQL user account for a given member or society.

    For members, grants are added to all society roles for which they are a member.
    """
    username = owner_name(owner)
    res_passwd = yield from pgsql.ensure_user(cursor, username)
    if isinstance(owner, Member):
        yield sync_member_roles(cursor, owner)
    elif isinstance(owner, Society):
        yield sync_society_roles(cursor, owner)
    return res_passwd.value


def _sync_roles(cursor: Cursor, current: Set[Tuple[str, pgsql.Role]],
                needed: Set[Tuple[str, pgsql.Role]]):
    for username, role in needed - current:
        yield pgsql.grant_role(cursor, username, role)
    for username, role in current - needed:
        yield pgsql.revoke_role(cursor, username, role)


@Result.collect
def sync_member_roles(cursor: Cursor, member: Member) -> Collect[None]:
    """
    Adjust grants for society roles to match the given member's memberships.
    """
    if not member.societies:
        return
    username = owner_name(member)
    current: Set[Tuple[str, pgsql.Role]] = set()
    for role in pgsql.get_user_roles(cursor, username):
        # Filter active roles to those owned by society accounts.
        if role[0] == member.crsid:
            continue
        try:
            get_society(role[0])
        except KeyError:
            continue
        else:
            current.add((username, role))
    roles = pgsql.get_roles(cursor, *(soc.society for soc in member.societies))
    needed = set((username, role) for role in roles)
    yield from _sync_roles(cursor, current, needed)


@Result.collect
def sync_society_roles(cursor: Cursor, society: Society) -> Collect[None]:
    """
    Adjust grants for member roles to match the given society's admins.
    """
    try:
        role = pgsql.get_role(cursor, owner_name(society))
    except KeyError:
        return
    current: Set[Tuple[str, pgsql.Role]] = set()
    for username in pgsql.get_role_users(cursor, role):
        # Filter active roles to those owned by member accounts.
        try:
            get_member(username)
        except KeyError:
            continue
        else:
            current.add((username, role))
    needed = set((user[0], role) for user in pgsql.get_roles(cursor, *society.admin_crsids))
    yield from _sync_roles(cursor, current, needed)


def reset_password(cursor: Cursor, owner: Owner) -> Result[Password]:
    """
    Reset the password of a member's or society's PostgreSQL user account.
    """
    result = pgsql.reset_password(cursor, owner_name(owner))
    send(owner, "tasks/pgsql_password.j2", {"username": owner_name(owner),
                                            "password": result.value})
    return result


def drop_account(cursor: Cursor, owner: Owner) -> Result[Unset]:
    """
    Drop a PostgreSQL user account for a given member or society.
    """
    if get_owned_databases(cursor, owner):
        raise ValueError("Drop databases for {} first".format(owner))
    return pgsql.drop_user(cursor, owner_name(owner))


@Result.collect
def create_database(cursor: Cursor, owner: Owner, name: Optional[str] = None) -> Collect[str]:
    """
    Create a new PostgreSQL database for the owner, defaulting to one matching their username.
    """
    role = pgsql.get_role(cursor, owner_name(owner))
    name = name or role[0]
    yield pgsql.create_database(cursor, name, role)
    return name


@Result.collect
def drop_database(cursor: Cursor, target: Union[Owner, str]) -> Collect[str]:
    """
    Drop the named, or owner-named, PostgreSQL database.
    """
    name = target if isinstance(target, str) else owner_name(target)
    yield pgsql.drop_database(cursor, name)
    return name


@Result.collect
def drop_all_databases(cursor: Cursor, owner: Owner) -> Collect[None]:
    """
    Drop all databases belonging to the owner.
    """
    for database in get_owned_databases(cursor, owner):
        yield pgsql.drop_database(cursor, database)


@Result.collect
def create_account(cursor: Cursor, owner: Owner) -> Collect[Tuple[Optional[Password], str]]:
    """
    Create a PostgreSQL user account and initial database for a member or society.
    """
    res_account = yield from new_account(cursor, owner)
    res_db = yield from create_database(cursor, owner)
    if res_account.state == State.created:
        send(owner, "tasks/pgsql_create.j2", {"username": owner_name(owner),
                                              "password": res_account.value,
                                              "database": res_db.value})
    return (res_account.value, res_db.value)
