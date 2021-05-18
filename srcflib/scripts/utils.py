"""
Helpers for converting methods into scripts, and filling in arguments with database objects.
"""

from functools import wraps
from inspect import cleandoc, signature
from itertools import islice
import sys
from typing import Any, Callable, Dict, List, Optional, Union

from docopt import docopt

from srcf.database import Member, Society
from srcf.database.queries import get_member, get_member_or_society, get_society

from ..plumbing.common import Owner


DocOptArgs = Dict[str, Union[bool, str, List[str]]]


ENTRYPOINTS: List[str] = []


def entrypoint(fn: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to make an entrypoint out of a generic function.

    This uses `docopt` to parse arguments according to the method docstring, and will be formatted
    with `{script}` set to the script name.  At minimum, it should contain `Usage: {script}`.

    The function being decorated should accept at least one argument, a `dict` of input parameters.
    Additional arguments must be type-annotated, and will be filled in by looking up objects of the
    corresponding types (`Member`, `Society`, or `Owner`).  For example:

        @entrypoint
        def grant(opts: DocOptArgs, member: Member, society: Society):
            \"""
            Add the member to the society.

            Usage: {script} MEMBER SOCIETY
            \"""
    """
    label = "srcflib-{}-{}".format(fn.__module__.rsplit(".", 1)[-1],
                                   fn.__qualname__).replace("_", "-")
    @wraps(fn)
    def wrap(opts: Optional[DocOptArgs] = None):
        extra: Dict[str, Any] = {}
        if opts is None:
            doc = cleandoc(fn.__doc__.format(script=label))
            opts = docopt(doc)
        # Detect resolvable-typed arguments and fill in their values.
        sig = signature(fn)
        ok = True
        for param in islice(sig.parameters.values(), 1, None):
            name = param.name
            cls = param.annotation
            try:
                value = opts[name.upper()]
            except KeyError:
                raise RuntimeError("Missing parameter {!r}".format(name))
            try:
                if cls in (Member, "Member"):
                    extra[name] = get_member(value)
                elif cls in (Society, "Society"):
                    extra[name] = get_society(value)
                elif cls in (Owner, "Owner"):
                    extra[name] = get_member_or_society(value)
                else:
                    raise RuntimeError("Bad parameter {!r} type {!r}".format(name, cls))
            except KeyError:
                ok = False
                error("{!r} is not valid for parameter {!r}".format(value, name), colour="1")
        if ok:
            return fn(opts, **extra)
        else:
            sys.exit(1)
    wrap.__doc__ = wrap.__doc__.format(script=fn.__name__)
    # Create a console script line for setup.
    target = "{}:{}".format(fn.__module__, fn.__qualname__)
    ENTRYPOINTS.append("{}={}".format(label, target))
    return wrap


def confirm(msg: str = "Are you sure?"):
    """
    Prompt for confirmation before destructive actions.
    """
    yn = input("\033[96m{} [yN]\033[0m ".format(msg))
    if yn.lower() not in ("y", "yes"):
        error("Aborted!", exit=1)


def error(msg: Optional[str] = None, *, exit: Optional[int] = None, colour: Optional[str] = None):
    """
    Print an error message and/or exit.
    """
    if msg:
        colour = colour or ("1" if exit else "3")
        print("\033[9{}m{}\033[0m".format(colour, msg), file=sys.stderr)
    if exit is not None:
        sys.exit(exit)
