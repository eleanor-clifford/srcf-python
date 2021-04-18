"""
PostgreSQL user and database management.
"""

from contextlib import contextmanager
import logging
from typing import Generator, List, NewType, Optional, Tuple, Union

from psycopg2 import connect as psycopg2_connect, errorcodes, ProgrammingError
from psycopg2.extensions import connection as Connection, cursor as Cursor
from psycopg2.extras import NamedTupleCursor

from .common import Collect, Password, Result, State


LOG = logging.getLogger(__name__)

# Type alias for external callers, who need not be aware of the internal structure when chaining
# calls (e.g. get_user/create_user -> reset_password).
Role = NewType("Role", Tuple[str, bool])

_ROLE_SELECT = "SELECT rolname, rolcanlogin FROM pg_roles"


def _format(sql: str, *literals: str) -> str:
    # Psycopg2 won't format values normally enclosed in double quotes, so handle these ourselves.
    if any('"' in lit for lit in literals):
        raise ValueError("Double quotes forbidden in identifiers")
    params = ('"{}"'.format(lit) for lit in literals)
    return sql.format(*params)


def connect(host: str, db: Optional[str] = None) -> Connection:
    """
    Create a PostgreSQL connection using Psycopg2 and namedtuple cursors.
    """
    conn = psycopg2_connect(host=host, database=(db or "template1"),
                            cursor_factory=NamedTupleCursor)
    conn.autocommit = True
    return conn


@contextmanager
def context(conn: Optional[Connection] = None,
            db: Optional[str] = None) -> Generator[Cursor, None, None]:
    """
    Run multiple PostgreSQL commands in a single connection:

        with context() as cursor:
            create_account(cursor, owner)
            create_database(cursor, owner)
    """
    conn = conn or connect(db)
    try:
        yield conn.cursor()
    finally:
        conn.close()


def query(cursor: Cursor, sql: str, *args: Union[str, Tuple[str, ...], Password]) -> None:
    """
    Run a SQL query against a database cursor.
    """
    LOG.debug("Query: %r %% %r", sql, args)
    cursor.execute(sql, [str(arg) if isinstance(arg, Password) else arg for arg in args])


def get_roles(cursor: Cursor, *names: str) -> List[Role]:
    """
    Look up existing roles by name.
    """
    if not names:
        return []
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


def get_user_roles(cursor: Cursor, name: str) -> List[Role]:
    """
    Look up all roles that the given user is a member of.
    """
    query(cursor, "{} WHERE pg_has_role(%s, oid, 'member')".format(_ROLE_SELECT), name)
    return cursor.fetchall()


def get_role_users(cursor: Cursor, role: Role) -> List[str]:
    """
    Look up all user names that are members of the given role.
    """
    query(cursor, "SELECT u.usename FROM pg_user u, pg_auth_members m, pg_roles r "
                  "WHERE u.usesysid = m.member AND m.roleid = r.oid AND r.rolname = %s", role[0])
    return [row[0] for row in cursor]


def get_role_databases(cursor: Cursor, owner: Role) -> List[str]:
    """
    Check if the given user has their own database.
    """
    query(cursor, "SELECT datname FROM pg_database d, pg_user u "
                  "WHERE d.datdba = u.usesysid AND u.usename = %s", owner[0])
    return [row[0] for row in cursor]


def _create_user(cursor: Cursor, name: str) -> Result[Password]:
    """
    Create a PostgreSQL user with a random password, if a user with that name doesn't already exist.
    """
    passwd = Password.new()
    query(cursor, _format("CREATE USER {} ENCRYPTED PASSWORD %s "
                          "NOCREATEDB NOCREATEUSER", name), passwd)
    return Result(State.created, passwd)


def reset_password(cursor: Cursor, name: str) -> Result[Password]:
    """
    Reset the password of the given PostgreSQL user.
    """
    passwd = Password.new()
    query(cursor, _format("ALTER USER {} PASSWORD %s", name), passwd)
    return Result(State.success, passwd)


def drop_user(cursor: Cursor, name: str) -> Result[None]:
    """
    Drop a PostgreSQL user and all of its grants.
    """
    query(cursor, _format("DROP USER IF EXISTS {}", name))
    return Result(State.success)


def enable_role(cursor: Cursor, role: Role) -> Result[Role]:
    """
    Add the LOGIN privilege to a role.
    """
    if role[1]:
        return Result(State.unchanged)
    query(cursor, _format("ALTER ROLE {} LOGIN", role[0]))
    return Result(State.success, Role((role[0], True)))


def disable_role(cursor: Cursor, role: Role) -> Result[Role]:
    """
    Remove the LOGIN privilege from a role.
    """
    if not role[1]:
        return Result(State.unchanged)
    query(cursor, _format("ALTER ROLE {} NOLOGIN", role[0]))
    return Result(State.success, Role((role[0], False)))


def grant_role(cursor: Cursor, name: str, role: Role) -> Result[None]:
    """
    Add the user to a secondary role.
    """
    if role[0] in {owned[0] for owned in get_user_roles(cursor, name)}:
        return Result(State.unchanged)
    query(cursor, _format("GRANT {} TO {}", role[0], name))
    return Result(State.success)


def revoke_role(cursor: Cursor, name: str, role: Role) -> Result[None]:
    """
    Remove the user from a secondary role.
    """
    if role[0] not in {owned[0] for owned in get_user_roles(cursor, name)}:
        return Result(State.unchanged)
    query(cursor, _format("REVOKE {} FROM {}", role[0], name))
    return Result(State.success)


@Result.collect
def ensure_user(cursor: Cursor, name: str) -> Collect[Optional[Password]]:
    """
    Create a new PostgreSQL user if it doesn't yet exist, or enable a currently disabled role.
    """
    try:
        role = get_role(cursor, name)
    except KeyError:
        res_create = yield from _create_user(cursor, name)
        return res_create.value
    else:
        yield enable_role(cursor, role)
        return None


def create_database(cursor: Cursor, name: str, owner: Role) -> Result[None]:
    """
    Create a new database owned by the given role.

    Note: this must be run outside of a transaction.
    """
    try:
        query(cursor, _format("CREATE DATABASE {} OWNER {}", name, owner[0]))
    except ProgrammingError as ex:
        if ex.pgcode == errorcodes.DUPLICATE_DATABASE:
            return Result(State.unchanged)
        else:
            raise
    else:
        return Result(State.created)


def drop_database(cursor: Cursor, name: str) -> Result[None]:
    """
    Create a new database owned by the given role.

    Note: this must be run outside of a transaction.
    """
    if '"' in name:
        raise ValueError("Double quotes forbidden in identifiers")
    try:
        query(cursor, _format("DROP DATABASE {}", name))
    except ProgrammingError as ex:
        if ex.pgcode == errorcodes.INVALID_CATALOG_NAME:
            return Result(State.unchanged)
        else:
            raise
    else:
        return Result(State.success)
