from contextlib import contextmanager
from typing import List, Optional, Tuple

from pymysql import connect as pymysql_connect
from pymysql.cursors import Cursor
from pymysql.connections import Connection

from srcf.database import Member

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
def context(conn: Connection=None) -> Tuple[Connection, Cursor]:
    """
    Run multiple MySQL commands in a single connection:

        >>> with context() as conn, cursor:
        ...     create_account(cursor, owner)
        ...     create_database(cursor, owner)
    """
    conn = conn or connect_config()
    try:
        yield conn, conn.cursor()
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
    results = ResultSet(mysql.create_user(cursor, user))
    results.value = results.last.value
    results.add(mysql.grant_database(cursor, user, _database_name(owner)),
                mysql.grant_database(cursor, user, _database_name(owner, "%")))
    if isinstance(owner, Member):
        for soc in owner.societies:
            results.add(mysql.grant_database(cursor, user, _database_name(soc)),
                        mysql.grant_database(cursor, user, _database_name(soc, "%")))
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
            results.add(mysql.revoke_database(cursor, user, _database_name(soc)),
                        mysql.revoke_database(cursor, user, _database_name(soc, "%")))
    results.add(mysql.drop_user(cursor, user))
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
