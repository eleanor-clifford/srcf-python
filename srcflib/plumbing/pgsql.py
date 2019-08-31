"""
PostgreSQL user and database management.
"""

import logging
from typing import List, Optional, Tuple, Union

from psycopg2 import connect as psycopg2_connect
from psycopg2.extensions import connection as Connection, cursor as Cursor
from psycopg2.extras import NamedTupleCursor

from .common import Password


# Type alias for external callers, who need not be aware of the internal structure when chaining
# calls (e.g. get_user/create_user -> reset_password).
Role = Tuple[str, bool]

_ROLE_SELECT = "SELECT rolname, rolcanlogin FROM pg_roles"


LOG = logging.getLogger(__name__)


def connect(host, db="template1") -> Connection:
    """
    Create a PostgreSQL connection using Psycopg2 and namedtuple cursors.
    """
    return psycopg2_connect(host=host, database=db, cursor_factory=NamedTupleCursor)


def query(cursor: Cursor, sql: str, *args: str) -> None:
    """
    Run a SQL query against a database cursor.
    """
    LOG.debug("Query: %r %% %r", sql, args)
    cursor.execute(sql, [str(arg) if isinstance(arg, Password) else arg for arg in args])


def get_roles(cursor: Cursor, *names: str) -> List:
    """
    Look up existing roles by name.
    """
    query(cursor, "{} WHERE rolname IN %s".format(_ROLE_SELECT), names)
    return cursor.fetchall()


def get_role(cursor: Cursor, name: str) -> Role:
    """
    Look up a single role by name.
    """
    query(cursor, "{} WHERE rolname = %s".format(_ROLE_SELECT), name)
    if cursor.rowcount:
        return cursor.fetchone()
    else:
        raise KeyError(name)


def get_user_roles(cursor: Cursor, name: str) -> List:
    """
    Look up all roles that the given user is a member of.
    """
    query(cursor, "{} WHERE pg_has_role(%s, oid, 'member')".format(_ROLE_SELECT), name)
    return cursor.fetchall()


def create_user(cursor: Cursor, name: str) -> Password:
    """
    Create a PostgreSQL user with a random password, if a user with that name doesn't already exist.
    """
    passwd = Password.new()
    query(cursor, "CREATE USER %s ENCRYPTED PASSWORD %s NOCREATEDB NOCREATEUSER", name, passwd)
    return passwd


def add_user(cursor: Cursor, name: str) -> Optional[Union[Password, bool]]:
    """
    Create a new PostgreSQL user if it doesn't yet exist, or enable a currently disabled role.
    """
    try:
        role = get_role(cursor, name)
    except KeyError:
        return create_user(cursor, name)
    else:
        return enable_role(cursor, role)


def reset_password(cursor: Cursor, name: str) -> Password:
    """
    Reset the password of the given PostgreSQL user.
    """
    passwd = Password.new()
    query(cursor, "ALTER USER %s PASSWORD %s", name, passwd)
    return passwd


def drop_user(cursor: Cursor, name: str) -> bool:
    """
    Drop a PostgreSQL user and all of its grants.
    """
    return query(cursor, "DROP USER IF EXISTS %s", name)


def enable_role(cursor: Cursor, role: Role) -> bool:
    """
    Add the LOGIN privilege to a role.
    """
    if role.rolcanlogin:
        return False
    query("ALTER ROLE %s LOGIN", role.rolname)
    role.rolcanlogin = True
    return True


def disable_role(cursor: Cursor, role: Role) -> bool:
    """
    Remove the LOGIN privilege from a role.
    """
    if not role.rolcanlogin:
        return False
    query("ALTER ROLE %s NOLOGIN", role.rolname)
    role.rolcanlogin = False
    return True


def grant_role(cursor: Cursor, name: str, role: Role) -> bool:
    """
    Add the user to a secondary role.
    """
    if role.rolname in {owned.rolname for owned in get_user_roles(cursor, name)}:
        return False
    query("GRANT %s TO %s", role.rolname, name)
    return True


def revoke_role(cursor: Cursor, name: str, role: Role) -> bool:
    """
    Remove the user from a secondary role.
    """
    if role.rolname not in {owned.rolname for owned in get_user_roles(cursor, name)}:
        return False
    query("REVOKE %s FROM %s", role.rolname, name)
    return True


def create_database(cursor: Cursor, name: str, owner: Role) -> bool:
    """
    Create a new database owned by the given role.

    Note: this must be run outside of a transaction.
    """
    query("CREATE DATABASE IF NOT EXISTS %s OWNER %s", name, owner.rolname)
    return True


def drop_database(cursor: Cursor, name: str) -> bool:
    """
    Create a new database owned by the given role.

    Note: this must be run outside of a transaction.
    """
    query("DROP DATABASE IF EXISTS %s", name)
    return True
