"""
Scripts to manage MySQL users and databases.
"""

from .utils import confirm, entrypoint, with_owner
from ..tasks import mysql


@entrypoint
@with_owner
def create(opts, owner):
    """
    Create a MySQL database for a member or society.

    A corresponding MySQL account will also be created if needed.

    Usage: {script} {owner} [SUFFIX]
    """
    name = mysql._user_name(owner)
    suffix = opts["SUFFIX"]
    print("User: {}".format(name))
    print("Databases: {}{}".format(name, ", {}/{}".format(name, suffix) if suffix else ""))
    confirm("Create these?")
    with mysql.context() as cursor:
        result = mysql.create_account(cursor, owner)
        passwd, database = result.value
        if passwd:
            print("Created account")
        if database:
            print("Created default database {!r}".format(database))
        if suffix:
            result = mysql.create_database(owner, suffix)
            if result:
                print("Created database {!r}".format(result.value))


@entrypoint
@with_owner
def drop(opts, owner):
    """
    Drop a MySQL user and all their databases.

    Usage: {script} {owner}
    """
    name = mysql._user_name(owner)
    with mysql.context() as cursor:
        dbs = mysql.get_owned_databases(cursor, owner)
    print("User: {}".format(name))
    if dbs:
        print("Databases: {}".format(", ".join(dbs)))
    confirm("Delete these?")
    with mysql.context() as cursor:
        if mysql.drop_all_databases(cursor, owner):
            print("Dropped databases")
        if mysql.drop_account(cursor, owner):
            print("Dropped user")
