"""
MySQL user and database management.
"""

from contextlib import contextmanager
import logging
import re
from typing import Generator, List, Optional, Tuple, Union

from pymysql import connect as pymysql_connect
from pymysql.connections import Connection
from pymysql.cursors import Cursor

from .common import Password, Result, State


LOG = logging.getLogger(__name__)


def _format(sql: str, *literals: str) -> str:
    # PyMySQL won't format values normally enclosed in backticks, so handle these ourselves.
    params = ("`{}`".format(lit.replace("`", "``")) for lit in literals)
    return sql.format(*params)


def _truthy(test: bool) -> State:
    return State.success if test else State.unchanged


def connect() -> Connection:
    """
    Connect to the MySQL database according to a .my.cnf config file.
    """
    return pymysql_connect(read_default_file="~/.my.cnf")


@contextmanager
def context(conn: Connection = None) -> Generator[Cursor, None, None]:
    """
    Run multiple MySQL commands in a single connection:

        >>> with context() as conn, cursor:
        ...     create_account(cursor, owner)
        ...     create_database(cursor, owner)
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
    LOG.debug("Query: %r %% %r", sql, args)
    return bool(cursor.execute(sql, [str(arg) if isinstance(arg, Password) else arg
                                     for arg in args]))


def get_users(cursor: Cursor, *names: str) -> List[str]:
    """
    Look up existing users by name.
    """
    query(cursor, "SELECT User FROM mysql.user WHERE User IN %s", names)
    return [user[0] for user in cursor]


def get_user_grants(cursor: Cursor, user: str) -> List[str]:
    """
    Look up all grants that the given user has.
    """
    query(cursor, "SHOW GRANTS FOR %s@'%%'", user)
    databases = []
    for grant in cursor:
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
    return [db[0] for db in cursor]


def get_user_databases(cursor: Cursor, user: str) -> List[str]:
    """
    Look up all databases that the given user has access to.
    """
    query(cursor, "SELECT Db FROM mysql.db WHERE Host = '%%' AND User = %s", user)
    return [db[0].replace("\\_", "_") for db in cursor]


def get_database_users(cursor: Cursor, database: str) -> List[str]:
    """
    Look up all users with access to the given database.
    """
    query(cursor, "SELECT User FROM mysql.db WHERE Host = '%%' AND Db = %s",
          database.replace("_", "\\_"))
    return [db[0] for db in cursor]


def create_user(cursor: Cursor, name: str) -> Result[Optional[Password]]:
    """
    Create a MySQL user with a random password, if a user with that name doesn't already exist.
    """
    passwd = Password.new()
    new = query(cursor, "CREATE USER IF NOT EXISTS %s@'%%' IDENTIFIED BY %s", name, passwd)
    return Result(State.success, passwd) if new else Result(State.unchanged)


def reset_password(cursor: Cursor, name: str) -> Result[Password]:
    """
    Reset the password of the given MySQL user.
    """
    passwd = Password.new()
    reset = query(cursor, "SET PASSWORD FOR %s@'%%' = %s", name, passwd)
    if reset:
        return Result(State.success, passwd)
    else:
        raise LookupError("No MySQL user {!r} to reset password".format(name))


def drop_user(cursor: Cursor, name: str) -> Result:
    """
    Drop a MySQL user and all of its grants.
    """
    return Result(_truthy(query(cursor, "DROP USER IF EXISTS %s@'%%'", name)))


def grant_database(cursor: Cursor, user: str, db: str) -> Result:
    """
    Grant all permissions for the user to create, manage and delete this database.
    """
    db = db.replace("%", "%%")
    return Result(_truthy(query(cursor, _format("GRANT ALL ON {}.* TO %s@'%%'", db), user)))


def revoke_database(cursor: Cursor, user: str, db: str) -> Result:
    """
    Remove any permissions for the user to create, manage and delete this database.
    """
    db = db.replace("%", "%%")
    return Result(_truthy(query(cursor, _format("REVOKE ALL ON {}.* FROM %s@'%%'", db), user)))


def create_database(cursor: Cursor, name: str) -> Result:
    """
    Create a MySQL database.  No permissions are granted.
    """
    if name in get_matched_databases(cursor, name):
        return Result(State.unchanged)
    # Always returns one row; emits a warning if the database already exist.
    query(cursor, _format("CREATE DATABASE IF NOT EXISTS {}", name))
    return Result(State.success)


def drop_database(cursor: Cursor, name: str) -> Result:
    """
    Drop a MySQL database and all of its tables.
    """
    if name not in get_matched_databases(cursor, name):
        return Result(State.unchanged)
    # Always returns zero rows; emits a warning if the database doesn't exist.
    query(cursor, _format("DROP DATABASE IF EXISTS {}", name))
    return Result(State.success)
