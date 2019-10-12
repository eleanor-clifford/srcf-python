from contextlib import contextmanager
from typing import Generator, Optional

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
def context(conn: Connection=None, db: str=None) -> Generator[Cursor, None, None]:
    """
    Run multiple MySQL commands in a single connection:

        >>> with context() as conn, cursor:
        ...     create_account(cursor, owner)
        ...     create_database(cursor, owner)
    """
    conn = conn or connect(db)
    try:
        yield conn.cursor()
    finally:
        conn.close()


def create_account(cursor: Cursor, owner: Owner) -> ResultSet[Optional[Password]]:
    """
    Create a PostgreSQL user account for a given member or society.

    For members, grants are added to all society roles for which they are a member.
    """
    username = owner_name(owner)
    results = ResultSet[Optional[Password]]()
    results.add(pgsql.add_user(cursor, username), True)
    if isinstance(owner, Member):
        results.extend(sync_society_roles(cursor, owner))
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
            current.add((username, role))
    roles = pgsql.get_roles(cursor, *(soc.society for soc in member.societies))
    needed = set((username, role) for role in roles)
    results = ResultSet()
    for username, role in needed - current:
        results.extend(pgsql.grant_role(cursor, username, role))
    for username, role in current - needed:
        results.extend(pgsql.revoke_role(cursor, username, role))
    return results


def reset_password(cursor: Cursor, owner: Owner) -> Result:
    """
    Reset the password of a member's or society's PostgreSQL user account.
    """
    return pgsql.reset_password(cursor, owner_name(owner))
