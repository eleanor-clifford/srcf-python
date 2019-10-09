from contextlib import contextmanager
from typing import Optional, Tuple

from psycopg2.extensions import connection as Connection, cursor as Cursor

from srcf.database import Member
from srcf.database.queries import get_society

from srcflib.plumbing import Owner, owner_name, Password, pgsql, Result, ResultSet


def connect(db: str=None) -> Connection:
    """
    Connect to the PostgreSQL server using ident authentication.
    """
    return pgsql.connect("postgres.internal", db or "sysadmins")


@contextmanager
def context(conn: Connection=None, db: str=None) -> Tuple[Connection, Cursor]:
    """
    Run multiple MySQL commands in a single connection:

        >>> with context() as conn, cursor:
        ...     create_account(cursor, owner)
        ...     create_database(cursor, owner)
    """
    conn = conn or connect(db)
    try:
        yield conn, conn.cursor()
    finally:
        conn.close()


def create_account(cursor: Cursor, owner: Owner) -> ResultSet[Optional[Password]]:
    """
    Create a PostgreSQL user account for a given member or society.

    For members, grants are added to all society roles for which they are a member.
    """
    username = owner_name(owner)
    results = ResultSet(pgsql.add_user(cursor, username))
    results.value = results.last.value
    if isinstance(owner, Member):
        results.add(sync_society_roles(cursor, owner))
    return results


def sync_society_roles(cursor: Cursor, member: Member) -> ResultSet:
    """
    Adjust grants for society roles to match account membership.
    """
    username = owner_name(member)
    current = set()
    for role in pgsql.get_user_roles(cursor, username):
        # Filter active roles to those owned by society accounts.
        if role[0] == member.crsid:
            continue
        try:
            get_society(role[0])
        except KeyError:
            continue
        else:
            current.add(role)
    needed = set(pgsql.get_roles(cursor, *(soc.society for soc in member.societies)))
    results = ResultSet()
    for role in needed - current:
        results.add(pgsql.grant_role(cursor, username, role))
    for role in current - needed:
        results.add(pgsql.revoke_role(cursor, username, role))
    return results


def reset_password(cursor: Cursor, owner: Owner) -> Result:
    """
    Reset the password of a member's or society's PostgreSQL user account.
    """
    return pgsql.reset_password(cursor, owner_name(owner))
