"""
MySQL user and database management.
"""

import logging
from typing import List, Optional

from pymysql.cursors import Cursor

from .common import Password


LOG = logging.getLogger(__name__)


def _format(sql: str, *literals: str) -> str:
    # PyMySQL won't format values normally enclosed in backticks, so handle these ourselves.
    params = ("`{}`".format(lit.replace("`", "``")) for lit in literals)
    return sql.format(*params)


def query(cursor: Cursor, sql: str, *args: str) -> bool:
    """
    Run a SQL query against a database cursor, and return whether rows were affected.
    """
    LOG.debug("Query: %r %% %r", sql, args)
    return bool(cursor.execute(sql, [str(arg) if isinstance(arg, Password) else arg
                                     for arg in args]))


def create_user(cursor: Cursor, name: str) -> Optional[Password]:
    """
    Create a MySQL user with a random password, if a user with that name doesn't already exist.
    """
    passwd = Password.new()
    new = query(cursor, "CREATE USER IF NOT EXISTS %s@'%%' IDENTIFIED BY %s", name, passwd)
    return passwd if new else None


def reset_password(cursor: Cursor, name: str) -> Password:
    """
    Reset the password of the given MySQL user.
    """
    passwd = Password.new()
    reset = query(cursor, "SET PASSWORD FOR %s@'%%' = %s", name, passwd)
    if reset:
        return passwd
    else:
        raise LookupError("No MySQL user {!r} to reset password".format(name))


def drop_user(cursor: Cursor, name: str) -> bool:
    """
    Drop a MySQL user and all of its grants.
    """
    return query(cursor, "DROP USER IF EXISTS %s@'%%'", name)


def grant_database(cursor: Cursor, user: str, db: str) -> bool:
    """
    Grant all permissions for the user to create, manage and delete this database.
    """
    return query(cursor, _format("GRANT ALL ON {}.* TO %s@'%%'", db), user)


def revoke_database(cursor: Cursor, user: str, db: str) -> bool:
    """
    Remove any permissions for the user to create, manage and delete this database.
    """
    return query(cursor, _format("REVOKE ALL ON {}.* FROM %s@'%%'", db), user)


def create_database(cursor: Cursor, name: str) -> bool:
    """
    Create a MySQL database.  No permissions are granted.
    """
    # Always returns one row; emits a warning if the database already exist.
    query(cursor, _format("CREATE DATABASE IF NOT EXISTS {}", name))
    return True


def list_databases(cursor: Cursor, like: str="%") -> List:
    """
    Fetch names of all databases matching the given pattern.
    """
    query(cursor, "SHOW DATABASES LIKE %s", like)
    return [db[0] for db in cursor]


def drop_database(cursor: Cursor, name: str) -> bool:
    """
    Drop a MySQL database and all of its tables.
    """
    # Always returns zero rows; emits a warning if the database doesn't exist.
    query(cursor, _format("DROP DATABASE IF EXISTS {}", name))
    return True
