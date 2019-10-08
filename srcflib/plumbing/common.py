"""
Shared helper methods and base classes.
"""

from enum import Enum
from functools import wraps
import logging
import platform
import subprocess
from typing import Generic, Set, Tuple, TypeVar, Union

from sqlalchemy.orm import Session as SESSION_TYPE

from srcf import pwgen
from srcf.database import Member, Society


LOG = logging.getLogger(__name__)


Owner = Union[Member, Society]


def owner_name(owner: Owner) -> str:
    """
    Return a `Member` CRSid, or a `Society` short name.
    """
    if isinstance(owner, Member):
        return owner.crsid
    elif isinstance(owner, Society):
        return owner.society
    else:
        raise TypeError(owner)


def get_members(sess: SESSION_TYPE, *crsids: str) -> Set[str]:
    """
    Fetch multiple `Member` objects by their CRSids.
    """
    users = sess.query(Member).filter(Member.crsid.in_(crsids)).all()
    missing = set(crsids) - {user.crsid for user in users}
    if missing:
        raise KeyError("Missing members: {}".format(", ".join(sorted(missing))))
    else:
        return set(users)


class State(Enum):
    """
    Enumeration used by `Result` to declare whether the action happened.
    """

    unchanged = 0
    """
    No action required, the request and current state are consistent.
    """
    success = 1
    """
    The action was completed without issues.
    """


V = TypeVar("V")


class Result(Generic[V]):
    """
    State and optional accompanying object from a unit of work.

    Mulitple results can be combined into a `ResultSet`.
    """

    def __init__(self, state: State, value: V=None):
        self.state = state
        self.value = value

    def __bool__(self) -> bool:
        return self.state is State.success

    def __repr__(self) -> str:
        return "{}({}{})".format(self.__class__.__name__, self.state,
                                 ", {}".format(self.value) if self.value else "")


class ResultSet(Result[V]):
    """
    `Result` instance combining multiple results into one.  `state` and `value` are derived from
    the inner results unless set manually.
    """

    def __init__(self, *results: Result):
        self._state = None
        super().__init__(State.unchanged)
        self._results = []
        for result in results:
            if isinstance(result, ResultSet):
                self._results.extend(result._results)
            else:
                self._results.append(result)

    @property
    def state(self) -> State:
        if self._state:
            return self._state
        elif any(result.state is State.success for result in self._results):
            return State.success
        else:
            return State.unchanged

    @state.setter
    def state(self, state: State) -> None:
        self._state = state

    @property
    def values(self) -> Tuple:
        """
        Filtered set of non-``None`` result values.
        """
        return tuple(result.value for result in self._results if result.value)

    @property
    def last(self) -> Result:
        """
        Most recently added result.
        """
        return self._results[-1]

    def add(self, *results: Result) -> None:
        """
        Include an additional result into the set.
        """
        self._results.extend(results)


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
    def new(cls) -> "Password":
        """
        Generate a fresh new password.
        """
        return cls(pwgen().decode("utf-8"))

    def wrap(self, template) -> "Password":
        """
        Embed a plaintext password into a larger string, and wrap that as a `Password`:

            >>> passwd = Password("secret")
            >>> line = passwd.wrap("username:{}")
            >>> line
            <Password: 'username:***'>
            >>> str(line)
            'username:secret'
        """
        return self.__class__(self._value, template.format(self._template))


class Hosts:
    """
    Hostnames used to restricted sets of plumbing commands.
    """

    USER = "pip"
    """
    Server providing an authoritative user database.
    """
    LIST = "pip"
    """
    Server running Mailman, with its utilities installed.
    """


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
