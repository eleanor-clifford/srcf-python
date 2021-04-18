"""
Scripts to manage PostgreSQL users and databases.
"""

from .utils import confirm, DocOptArgs, entrypoint
from ..plumbing.common import Owner, owner_name
from ..tasks import pgsql


@entrypoint
def create(opts: DocOptArgs, owner: Owner):
    """
    Create a PostgreSQL database for a member or society.

    A corresponding PostgreSQL account will also be created if needed.

    Usage: {script} OWNER [DATABASE]
    """
    name = owner_name(owner)
    database = opts["DATABASE"]
    if database == name:
        database = None
    print("User: {}".format(name))
    print("Databases: {}{}".format(name, ", {}".format(database) if database else ""))
    confirm("Create these?")
    with pgsql.context() as cursor:
        result = pgsql.create_account(cursor, owner)
        create_user, create_db = result.parts
        if create_user:
            print("Created account")
        else:
            print("Account already exists")
        if create_db:
            print("Created default database {!r}".format(result.value[1]))
        else:
            print("Default database {!r} already exists".format(result.value[1]))
        if database:
            result = pgsql.create_database(cursor, owner, database)
            if result:
                print("Created database {!r}".format(result.value))
            else:
                print("Database {!r} already exists".format(result.value))


@entrypoint
def drop(opts: DocOptArgs, owner: Owner):
    """
    Drop a PostgreSQL user and all their databases.

    Usage: {script} OWNER
    """
    name = owner_name(owner)
    with pgsql.context() as cursor:
        dbs = pgsql.get_owned_databases(cursor, owner)
    print("User: {}".format(name))
    if dbs:
        print("Databases: {}".format(", ".join(dbs)))
    confirm("Delete these?")
    with pgsql.context() as cursor:
        if pgsql.drop_all_databases(cursor, owner):
            print("Dropped databases")
        if pgsql.drop_account(cursor, owner):
            print("Dropped user")
