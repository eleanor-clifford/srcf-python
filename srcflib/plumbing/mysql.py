"""
MySQL user and database management.
"""

import logging
from typing import List, Optional

from pymysql.cursors import Cursor

from .common import Password


LOG = logging.getLogger(__name__)


def _format(query: str, *literals: str) -> str:
    # PyMySQL won't format values normally enclosed in backticks, so handle these ourselves.
    params = ("`{}`".format(lit.replace("`", "``")) for lit in literals)
    return query.format(*params)


def _exec(cursor: Cursor, query: str, *args: str) -> int:
    LOG.debug("Query: %r %% %r", query, args)
    return bool(cursor.execute(query, args))


def create_user(cursor: Cursor, name: str) -> Optional[Password]:
    """
    Create a MySQL user with a random password, if a user with that name doesn't already exist.
    """
    pwd = Password.new()
    new = _exec(cursor, "CREATE USER IF NOT EXISTS %s@'%%' IDENTIFIED BY %s", name, pwd.value)
    return pwd if new else None


def reset_user_password(cursor: Cursor, name: str) -> Password:
    """
    Reset the password of the given MySQL user.
    """
    pwd = Password.new()
    reset = _exec(cursor, "SET PASSWORD FOR %s@'%%' = %s", name, pwd.value)
    if reset:
        return pwd
    else:
        raise LookupError("No MySQL user {!r} to reset password".format(name))


def drop_user(cursor: Cursor, name: str) -> bool:
    """
    Drop a MySQL user and all of its grants.
    """
    return _exec(cursor, "DROP USER IF EXISTS %s@'%%'", name)


def grant_user_database(cursor: Cursor, user: str, db: str) -> bool:
    """
    Grant all permissions for the user to create, manage and delete this database.
    """
    return _exec(cursor, _format("GRANT ALL ON {}.* TO %s@'%%'", db), user)


def revoke_user_database(cursor: Cursor, user: str, db: str) -> bool:
    """
    Remove any permissions for the user to create, manage and delete this database.
    """
    return _exec(cursor, _format("REVOKE ALL ON {}.* FROM %s@'%%'", db), user)


def create_database(cursor: Cursor, name: str) -> bool:
    """
    Create a MySQL database.  No permissions are granted.
    """
    # Always returns one row; emits a warning if the database already exist.
    _exec(cursor, _format("CREATE DATABASE IF NOT EXISTS {}", name))
    return True


def list_databases(cursor: Cursor, like: str="%") -> List:
    """
    Fetch names of all databases matching the given pattern.
    """
    _exec(cursor, "SHOW DATABASES LIKE %s", like)
    return [db[0] for db in cursor]


def drop_database(cursor: Cursor, name: str) -> bool:
    """
    Drop a MySQL database and all of its tables.
    """
    # Always returns zero rows; emits a warning if the database doesn't exist.
    _exec(cursor, _format("DROP DATABASE IF EXISTS {}", name))
    return True
