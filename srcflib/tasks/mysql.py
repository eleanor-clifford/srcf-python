from contextlib import contextmanager
from typing import Generator, List, Optional

from pymysql import connect as pymysql_connect
from pymysql.cursors import Cursor
from pymysql.connections import Connection

from srcf.database import Member
from srcf.database.queries import get_society

from srcflib.plumbing import mysql, Owner, owner_name, Password, Result, ResultSet


def _root_passwd() -> str:
    with open("/root/mysql-root-password", "r") as f:
        return f.readline().rstrip()


def _user_name(owner: Owner) -> str:
    return owner_name(owner).replace("-", "_")


def _database_name(owner: Owner, suffix: str=None) -> str:
    name = _user_name(owner)
    if suffix:
        name = "{}/{}".format(name, suffix)
    return name


def _database_name_rev(name: str) -> str:
    return name.split("/", 1)[0].replace("_", "-")


def connect_config() -> Connection:
    """
    Connect to the MySQL database according to a .my.cnf config file.
    """
    return pymysql_connect(read_default_file="~/.my.cnf")


def connect_root() -> Connection:
    """
    Connect to the MySQL database as root.
    """
    return pymysql_connect(user="root", host="mysql.internal", passwd=_root_passwd(), db="mysql")


@contextmanager
def context(conn: Connection=None) -> Generator[Cursor, None, None]:
    """
    Run multiple MySQL commands in a single connection:

        >>> with context() as conn, cursor:
        ...     create_account(cursor, owner)
        ...     create_database(cursor, owner)
    """
    conn = conn or connect_config()
    try:
        yield conn.cursor()
    finally:
        conn.close()


def list_databases(cursor: Cursor, owner: Owner) -> List[str]:
    """
    Find all MySQL databases belonging to a given owner.
    """
    return (mysql.list_databases(cursor, _database_name(owner)) +
            mysql.list_databases(cursor, _database_name(owner, "%")))


def create_account(cursor: Cursor, owner: Owner) -> ResultSet[Optional[Password]]:
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
        results.add(sync_society_roles(cursor, owner))
    return results


def sync_society_roles(cursor: Cursor, member: Member) -> ResultSet:
    """
    Adjust grants for society roles to match account membership.
    """
    user = _user_name(member)
    current = set()
    seen = set()
    for grant in mysql.get_user_grants(cursor, user):
        # Filter active roles to those owned by society accounts.
        root = _database_name_rev(grant)
        if root == member.crsid:
            continue
        if root not in seen:
            try:
                get_society(root)
            except KeyError:
                continue
            else:
                seen.add(root)
        if root in seen:
            current.add(grant)
    needed = set()
    for name in mysql.get_users(cursor, *(_database_name(soc) for soc in member.societies)):
        needed.update({name, "{}/%".format(name)})
    results = ResultSet()
    for database in needed - current:
        results.extend(mysql.grant_database(cursor, user, database))
    for database in current - needed:
        results.extend(mysql.revoke_database(cursor, user, database))
    return results


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
    if list_databases(cursor, owner):
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


def create_database(cursor: Cursor, owner: Owner, suffix: str=None) -> Result:
    """
    Create a new MySQL database for the owner, either the primary name or a suffixed alternative.
    """
    return mysql.create_database(cursor, _database_name(owner, suffix))


def drop_database(cursor: Cursor, owner: Owner, suffix: str=None) -> Result:
    """
    Drop either the primary or a suffixed secondary MySQL database belonging to the owner.
    """
    return mysql.drop_database(cursor, _database_name(owner, suffix))
