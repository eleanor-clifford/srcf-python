"""
MySQL user and database management.
"""

from contextlib import contextmanager
import logging
import re
from typing import Generator, List, Optional, Tuple, Union

from pymysql import connect as pymysql_connect
from pymysql.connections import Connection
from pymysql.constants import ER
from pymysql.cursors import Cursor
from pymysql.err import DatabaseError

from .common import Password, Result, State, Unset


LOG = logging.getLogger(__name__)

HOST = "%"


def _format(sql: str, *literals: str) -> str:
    # PyMySQL won't format values normally enclosed in backticks, so handle these ourselves.
    params = ("`{}`".format(lit.replace("%", "%%").replace("`", "``")) for lit in literals)
    return sql.format(*params)


def connect() -> Connection:
    """
    Connect to the MySQL database according to a .my.cnf config file.
    """
    return pymysql_connect(read_default_file="~/.my.cnf")


@contextmanager
def context(conn: Optional[Connection] = None) -> Generator[Cursor, None, None]:
    """
    Run multiple MySQL commands in a single connection:

        with context() as cursor:
            create_account(cursor, owner)
            create_database(cursor, owner)
    """
    conn = conn or connect()
    try:
        yield conn.cursor()
    finally:
        conn.close()


def query(cursor: Cursor, sql: str, *args: Union[str, Tuple[str, ...], Password]) -> bool:
    """
    Run a SQL query against a database cursor, and return whether rows were affected.
    """
    LOG.debug("Ran query: %r %% %r", sql, args)
    cursor.execute(sql, [str(arg) if isinstance(arg, Password) else arg for arg in args])
    return bool(cursor.rowcount)


def get_users(cursor: Cursor, *names: str) -> List[str]:
    """
    Look up existing users by name.
    """
    if not names:
        return []
    query(cursor, "SELECT User FROM mysql.user WHERE User IN %s", names)
    return [user[0] for user in cursor.fetchall()]


def get_user_grants(cursor: Cursor, user: str) -> List[str]:
    """
    Look up all grants that the given user has.
    """
    query(cursor, "SHOW GRANTS FOR %s@%s", user, HOST)
    databases: List[str] = []
    for grant in cursor.fetchall():
        match = re.match(r"GRANT (.+) ON (?:\*|(['`\"])(.*?)\2)\.\*", grant[0])
        if match:
            if "ALL PRIVILEGES" in match.group(1).split(", "):
                database = match.group(3) or "*"
                databases.append(database.replace("\\_", "_"))
        else:
            LOG.warning("Ignoring non-parsable grant: %r", grant)
    return databases


def get_matched_databases(cursor: Cursor, like: str = "%") -> List[str]:
    """
    Fetch names of all databases matching the given pattern.
    """
    query(cursor, "SHOW DATABASES LIKE %s", like)
    return [db[0] for db in cursor.fetchall()]


def get_user_databases(cursor: Cursor, user: str) -> List[str]:
    """
    Look up all databases that the given user has access to.
    """
    query(cursor, "SELECT Db FROM mysql.db WHERE User = %s AND Host = %s", user, HOST)
    return [db[0].replace("\\_", "_") for db in cursor.fetchall()]


def get_database_users(cursor: Cursor, database: str) -> List[str]:
    """
    Look up all users with access to the given database.
    """
    query(cursor, "SELECT User FROM mysql.db WHERE Host = %s AND Db = %s",
          HOST, database.replace("_", "\\_"))
    return [db[0] for db in cursor.fetchall()]


def ensure_user(cursor: Cursor, name: str) -> Result[Optional[Password]]:
    """
    Create a MySQL user with a random password, if a user with that name doesn't already exist.
    """
    if get_users(cursor, name):
        return Result(State.unchanged, None)
    passwd = Password.new()
    try:
        query(cursor, "CREATE USER %s@%s IDENTIFIED BY %s", name, HOST, passwd)
    except DatabaseError as ex:
        if ex.args[0] == ER.CANNOT_USER:
            return Result(State.unchanged, None)
        else:
            raise
    return Result(State.created, passwd)


def reset_password(cursor: Cursor, name: str) -> Result[Password]:
    """
    Reset the password of the given MySQL user.
    """
    passwd = Password.new()
    # Always returns zero rows; does nothing if the user doesn't exist.
    query(cursor, "SET PASSWORD FOR %s@%s = %s", name, HOST, passwd)
    return Result(State.success, passwd)


def drop_user(cursor: Cursor, name: str) -> Result[Unset]:
    """
    Drop a MySQL user and all of its grants.
    """
    if not get_users(cursor, name):
        return Result(State.unchanged)
    try:
        # Always returns zero rows; throws an error if the database doesn't exist.
        query(cursor, "DROP USER %s@%s", name, HOST)
    except DatabaseError as ex:
        if ex.args[0] == ER.CANNOT_USER:
            return Result(State.unchanged)
        else:
            raise
    else:
        return Result(State.success)


def grant_database(cursor: Cursor, user: str, db: str) -> Result[Unset]:
    """
    Grant all permissions for the user to create, manage and delete this database.
    """
    if db in get_user_grants(cursor, user):
        return Result(State.unchanged)
    # Always returns zero rows; does nothing if already granted.
    query(cursor, _format("GRANT ALL ON {}.* TO %s@%s", db), user, HOST)
    return Result(State.success)


def revoke_database(cursor: Cursor, user: str, db: str) -> Result[Unset]:
    """
    Remove any permissions for the user to create, manage and delete this database.
    """
    if db not in get_user_grants(cursor, user):
        return Result(State.unchanged)
    try:
        # Returns zero rows; throws an error if not granted.
        query(cursor, _format("REVOKE ALL ON {}.* FROM %s@%s", db), user, HOST)
    except DatabaseError as ex:
        if ex.args[0] == ER.NONEXISTING_GRANT:
            return Result(State.unchanged)
        else:
            raise
    else:
        return Result(State.success)


def create_database(cursor: Cursor, name: str) -> Result[Unset]:
    """
    Create a MySQL database.  No permissions are granted.
    """
    try:
        # Returns one row; throws an error if the database already exists.
        query(cursor, _format("CREATE DATABASE {}", name))
    except DatabaseError as ex:
        if ex.args[0] == ER.DB_CREATE_EXISTS:
            return Result(State.unchanged)
        else:
            raise
    else:
        return Result(State.created)


def drop_database(cursor: Cursor, name: str) -> Result[Unset]:
    """
    Drop a MySQL database and all of its tables.
    """
    try:
        # Returns one row; throws an error if the database doesn't exists.
        query(cursor, _format("DROP DATABASE {}", name))
    except DatabaseError as ex:
        if ex.args[0] == ER.DB_DROP_EXISTS:
            return Result(State.unchanged)
        else:
            raise
    else:
        return Result(State.success)
