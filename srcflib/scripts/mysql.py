from .utils import entrypoint, with_owner
from ..tasks import mysql


@entrypoint
@with_owner
def create(opts, owner):
    """
    Create a MySQL user account and initial database for a member or society.

    Usage: {script} {owner}
    """
    print("Creating MySQL user/database for {}".format(owner))
    with mysql.context() as cursor:
        result = mysql.create_account(cursor, owner)
        passwd, database = result.value
        if passwd:
            print("New account created")
        else:
            print("Using existing account")
        if database:
            print("Database name: {!r}".format(database))
