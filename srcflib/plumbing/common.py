from functools import wraps
import logging
import platform
import subprocess
from typing import Set, Union

from srcf import pwgen
from srcf.database import Member, Session, Society


LOG = logging.getLogger(__name__)


Owner = Union[Member, Society]


def owner_name(owner: Owner) -> str:
    """
    Return a ``Member`` CRSid, or a ``Society`` short name.
    """
    if isinstance(owner, Member):
        return owner.crsid
    elif isinstance(owner, Society):
        return owner.society
    else:
        raise TypeError(owner)


def get_members(sess: Session, *crsids: str) -> Set:
    """
    Fetch multiple ``Member`` objects by their CRSids.
    """
    users = sess.query(Member).filter(Member.crsid.in_(crsids)).all()
    missing = set(crsids) - {user.crsid for user in users}
    if missing:
        raise KeyError("Missing members: {}".format(", ".join(sorted(missing))))
    else:
        return set(users)


class Password:
    """
    Container of randomly generated passwords.  Use ``str(passwd)`` to get the actual value.
    """

    def __init__(self, value, template="{}"):
        self._value = value
        self._template = template

    def __str__(self):
        return self._template.format(self._value)

    def __repr__(self):
        return "<{}: {!r}>".format(self.__class__.__name__, self._template.format("***"))

    @classmethod
    def new(cls):
        """
        Generate a fresh new password.

        Returns:
            .Password
        """
        return cls(pwgen().decode("utf-8"))

    def wrap(self, template):
        """
        Embed a plaintext password into a larger string, and wrap that as a ``Password``:

            >>> passwd = Password("secret")
            >>> line = passwd.wrap("username:{}")
            >>> line
            <Password: 'username:***'>
            >>> str(line)
            'username:secret'
        """
        return self.__class__(self._value, template.format(self._template))


class Hosts:
    USER = "pip"
    LIST = "pip"


def require_host(*hosts: str):
    """
    Only allow a function to be called on the given hosts, identified by hostname:

        >>> @require_hosts(Hosts.USER)
        ... def create_user(username): ...
    """
    def outer(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            host = platform.node()
            if host not in hosts:
                raise RuntimeError("{}() can't be used on host {}, requires {}"
                                   .format(fn.__name__, host, "/".join(hosts)))
            return fn(*args, **kwargs)
        return inner
    return outer


def command(args, input_=None):
    """
    Create a subprocess to execute an external command.
    """
    if input_:
        LOG.debug("Exec: %r <<< %r", args, input_)
    else:
        LOG.debug("Exec: %r", args)
    subprocess.run(args, input=str(input_).encode("utf-8") if input_ else None, check=True)
