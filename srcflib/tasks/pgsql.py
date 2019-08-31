from contextlib import contextmanager
from typing import Tuple

from psycopg2.extensions import connection as Connection, cursor as Cursor

from srcf.database import Member

from srcflib.plumbing import Owner, owner_name, pgsql


def connect(db: str="sysadmins") -> Connection:
    """
    Connect to the PostgreSQL server using ident authentication.
    """
    return pgsql.connect("postgres.internal", db)


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


def create_account(cursor: Cursor, owner: Owner) -> bool:
    """
    Create a PostgreSQL user account for a given member or society.

    For members, grants are added to all society roles for which they are a member.
    """
    username = owner_name(owner)
    done = [bool(pgsql.add_user(cursor, username))]
    if isinstance(owner, Member):
        roles = pgsql.get_roles(cursor, *(soc.society for soc in owner.societies))
        done.extend([pgsql.grant_role(cursor, username, role) for role in roles])
    return any(done)


def reset_password(cursor: Cursor, owner: Owner) -> bool:
    """
    Reset the password of a member's or society's PostgreSQL user account.
    """
    return pgsql.reset_password(cursor, owner_name(owner))
