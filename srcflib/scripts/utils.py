"""
Helpers for converting methods into scripts, and filling in arguments with database objects.
"""

from functools import wraps
from inspect import cleandoc
import os.path
import sys

from docopt import docopt

from srcf.database.queries import get_member, get_society


ENTRYPOINTS = []


def entrypoint(fn):
    """
    Decorator to make an entrypoint out of a generic function.

    This uses `docopt` to parse arguments according to the method docstring, and will be formatted
    with `{script}` set to the script name.  At minimum, it should contain `Usage: {script}`.

    The function itself should accept one argument, a `dict` of console parameters, unless using
    the `with_*` helpers to add additional arguments.
    """
    @wraps(fn)
    def wrap(opts=None):
        if opts is None:
            name = os.path.basename(sys.argv[0])
            doc = cleandoc(fn.__doc__.format(script=name))
            opts = docopt(doc)
        return fn(opts)
    wrap.__doc__ = wrap.__doc__.format(script=fn.__name__)
    # Create a console script line for setup.
    label = "srcflib-{}-{}".format(fn.__module__.rsplit(".", 1)[-1],
                                   fn.__qualname__).replace("_", "-")
    target = "{}:{}".format(fn.__module__, fn.__qualname__)
    ENTRYPOINTS.append("{}={}".format(label, target))
    return wrap


def confirm(msg="Are you sure?"):
    """
    Prompt for confirmation before destructive actions.
    """
    yn = input("{} [yN] ".format(msg))
    if yn.lower() not in ("y", "yes"):
        error("Aborted!")


def error(msg=None, code=1):
    """
    Print an error message and exit.
    """
    if msg:
        print(msg, file=sys.stderr)
    sys.exit(code)


def with_member(fn):
    """
    Decorator to resolve a `CRSID` parameter into a `Member` argument for the function.

    Use `{member}` to place the argument in the usage line.
    """
    @wraps(fn)
    def wrap(opts, *args):
        member = None
        if "CRSID" in opts:
            try:
                member = get_member(opts["CRSID"])
            except KeyError:
                error("Member {!r} doesn't exist".format(opts["CRSID"]))
        return fn(opts, member=member, *args)
    wrap.__doc__ = wrap.__doc__.replace("{member}", "CRSID")
    return wrap


def with_society(fn):
    """
    Decorator to resolve a `SOCIETY` parameter into a `Society` argument for the function.

    Use `{society}` to place the argument in the usage line.
    """
    @wraps(fn)
    def wrap(opts, *args):
        society = None
        if "SOCIETY" in opts:
            try:
                society = get_society(opts["SOCIETY"])
            except KeyError:
                error("Society {!r} doesn't exist".format(opts["SOCIETY"]))
        return fn(opts, society=society, *args)
    wrap.__doc__ = wrap.__doc__.replace("{society}", "SOCIETY")
    return wrap


def with_owner(fn):
    """
    Decorator to resolve `member CRSID` or `society SOCIETY` parameter pairs into `Member` or
    `Society` arguments for the function.

    Use `{owner}` to place the argument in the usage line.
    """
    @wraps(fn)
    def wrap(opts, *args):
        owner = None
        if opts.get("member") and "CRSID" in opts:
            try:
                owner = get_member(opts["CRSID"])
            except KeyError:
                error("Member {!r} doesn't exist".format(opts["CRSID"]))
        elif opts.get("society") and "SOCIETY" in opts:
            try:
                owner = get_society(opts["SOCIETY"])
            except KeyError:
                error("Society {!r} doesn't exist".format(opts["SOCIETY"]))
        return fn(opts, owner=owner, *args)
    wrap.__doc__ = wrap.__doc__.replace("{owner}", "(member CRSID | society SOCIETY)")
    return wrap
