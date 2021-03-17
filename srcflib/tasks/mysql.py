"""
MySQL accounts and databases for members and societies.
"""

from typing import List, Optional, Set, Tuple, Union

from pymysql.cursors import Cursor

from srcf.database import Member, Society
from srcf.database.queries import get_member, get_society

from ..plumbing import mysql, Owner, owner_name, Password, Result, ResultSet

# Re-export connection plumbing to avoid unnecessary imports elsewhere.
connect = mysql.connect
context = mysql.context


def _user_name(owner: Owner) -> str:
    return owner_name(owner).replace("-", "_")


def _user_name_rev(name: str) -> str:
    return name.replace("_", "-")


def _database_name(name: Union[str, Owner], suffix: str = None) -> str:
    if not isinstance(name, str):
        name = _user_name(name)
    if suffix:
        name = "{}/{}".format(name, suffix)
    return name


def _database_name_rev(name: str) -> str:
    return _user_name_rev(name.split("/", 1)[0])


def get_owned_databases(cursor: Cursor, owner: Owner) -> List[str]:
    """
    Find all MySQL databases belonging to a given owner.
    """
    return (mysql.get_matched_databases(cursor, _database_name(owner)) +
            mysql.get_matched_databases(cursor, _database_name(owner, "%")))


def new_account(cursor: Cursor, owner: Owner) -> ResultSet[Optional[Password]]:
    """
    Create a MySQL user account for a given member or society.

    For members, grants are added to all society databases for which they are a member.
    """
    user = _user_name(owner)
    results = ResultSet[Optional[Password]]()
    results.add(mysql.create_user(cursor, user), True)
    results.extend(mysql.grant_database(cursor, user, _database_name(owner)),
                   mysql.grant_database(cursor, user, _database_name(owner, "%")))
    if isinstance(owner, Member):
        results.add(sync_member_roles(cursor, owner))
    elif isinstance(owner, Society):
        results.add(sync_society_roles(cursor, owner))
    return results


def _sync_roles(cursor: Cursor, current: Set[Tuple[str, str]],
                needed: Set[Tuple[str, str]]) -> ResultSet:
    results = ResultSet()
    for user, database in needed - current:
        results.extend(mysql.grant_database(cursor, user, database))
    for user, database in current - needed:
        results.extend(mysql.revoke_database(cursor, user, database))
    return results


def sync_member_roles(cursor: Cursor, member: Member) -> ResultSet:
    """
    Adjust grants for society roles to match the given member's memberships.
    """
    user = _user_name(member)
    current = set()
    seen = set()
    for database in mysql.get_user_databases(cursor, user):
        name = _database_name_rev(database)
        # Filter active roles to those owned by society accounts.
        if name == member.crsid:
            continue
        if name not in seen:
            try:
                get_society(name)
            except KeyError:
                continue
            else:
                seen.add(name)
        if name in seen:
            current.add((user, database))
    needed = set()
    for role in mysql.get_users(cursor, *(_user_name(soc) for soc in member.societies)):
        databases = (_database_name(role), _database_name(role, "%"))
        needed.update({(user, database) for database in databases})
    return _sync_roles(cursor, current, needed)


def sync_society_roles(cursor: Cursor, society: Society) -> ResultSet:
    """
    Adjust grants for member roles to match the given society's admins.
    """
    databases = (_database_name(society), _database_name(society, "%"))
    current = set()
    for database in databases:
        for user in mysql.get_database_users(cursor, database):
            # Filter active roles to those owned by society accounts.
            username = _user_name_rev(user)
            if username == society.society:
                continue
            try:
                get_member(username)
            except KeyError:
                continue
            else:
                current.add((user, database))
    needed = set()
    for user in mysql.get_users(cursor, *society.admin_crsids):
        needed.update({(user, database) for database in databases})
    return _sync_roles(cursor, current, needed)


def reset_password(cursor: Cursor, owner: Owner) -> Result[Password]:
    """
    Reset the password of a member's or society's MySQL user account.
    """
    return mysql.reset_password(cursor, _user_name(owner))


def drop_account(cursor: Cursor, owner: Owner) -> ResultSet:
    """
    Drop a MySQL user account for a given member or society.

    For members, grants are removed from all society databases for which they are a member.
    """
    if get_owned_databases(cursor, owner):
        raise ValueError("Drop databases for {} first".format(owner))
    user = _user_name(owner)
    results = ResultSet(mysql.revoke_database(cursor, user, _database_name(owner)),
                        mysql.revoke_database(cursor, user, _database_name(owner, "%")))
    if isinstance(owner, Member):
        for soc in owner.societies:
            results.extend(mysql.revoke_database(cursor, user, _database_name(soc)),
                           mysql.revoke_database(cursor, user, _database_name(soc, "%")))
    results.extend(mysql.drop_user(cursor, user))
    return results


def create_database(cursor: Cursor, owner: Owner, suffix: str = None) -> Result[str]:
    """
    Create a new MySQL database for the owner, either the primary name or a suffixed alternative.
    """
    name = _database_name(owner, suffix)
    result = mysql.create_database(cursor, name)
    result.value = name
    return result


def drop_database(cursor: Cursor, owner: Owner, suffix: str = None) -> Result[str]:
    """
    Drop either the primary or a suffixed secondary MySQL database belonging to the owner.
    """
    name = _database_name(owner, suffix)
    result = mysql.drop_database(cursor, name)
    result.value = name
    return result


def drop_all_databases(cursor: Cursor, owner: Owner) -> ResultSet:
    """
    Drop all databases belonging to the owner.
    """
    results = ResultSet()
    for database in get_owned_databases(cursor, owner):
        results.extend(mysql.drop_database(cursor, database))
    return results


def create_account(cursor: Cursor, owner: Owner) -> ResultSet[Tuple[Optional[Password], str]]:
    """
    Create a MySQL user account and initial database for a member or society.
    """
    results = ResultSet(new_account(cursor, owner),
                        create_database(cursor, owner))
    results.value = tuple(inner.value if inner else None for inner in results.results)
    return results
