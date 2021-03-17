"""
Shared helper methods and base classes.
"""

from enum import Enum
from functools import wraps
import inspect
import logging
import platform
import subprocess
from typing import Any, Callable, Generator, Generic, List, Optional, Set, TypeVar, Union

from sqlalchemy.orm import Session as SQLASession

from srcf import pwgen
from srcf.database import Member, Society


LOG = logging.getLogger(__name__)


Owner = Union[Member, Society]

V = TypeVar("V")
R = TypeVar("R")


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


def owner_desc(owner: Owner, admins: bool = False) -> str:
    """
    Return a `Member` full name, or a `Society` description optionally addressing its admins.
    """
    if isinstance(owner, Member):
        return owner.name
    elif isinstance(owner, Society):
        if admins:
            return "{} admins".format(owner.description)
        else:
            return owner.description
    else:
        raise TypeError(owner)


def owner_website(owner: Owner):
    """
    Return a member or society's default website address.
    """
    if isinstance(owner, Member):
        key = "user"
    elif isinstance(owner, Society):
        key = "soc"
    else:
        raise TypeError(owner)
    return "https://{}.{}.srcf.net".format(owner_name(owner), key)


def get_members(sess: SQLASession, *crsids: str) -> Set[str]:
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


class Result(Generic[V]):
    """
    State and optional accompanying value from a unit of work.
    """

    @classmethod
    def collect(cls, fn: Callable[..., Generator["Result", Any, R]]) -> Callable[..., "Result[R]"]:
        """
        Decorator: build a `Result` from `yield`ed parts, in order to capture or log in real time:

            @Result.collect
            def task():
                value = yield plumb_a()
                yield plumb_b()
                return value

        If a `Result` includes a value, it will be available via `yield` assignment to re-capture
        it.  The return value of the function will become the outermost `Result`'s value.
        """
        @wraps(fn)
        def inner(*args, **kwargs) -> Result[R]:
            state = None
            value = None
            parts = []
            gen = fn(*args, **kwargs)
            while True:
                try:
                    try:
                        prev = parts[-1].value
                    except (IndexError, ValueError):
                        result = next(gen)
                    else:
                        result = gen.send(prev)
                except StopIteration as ex:
                    value = ex.value
                    break
                parts.append(result)
            return cls(state, value, parts, fn)
        return inner

    def __init__(self, state: Optional[State] = None, value: Optional[V] = None,
                 parts: Optional[List["Result"]] = None, caller: Callable = None):
        self._state = state
        self._value = value
        self.parts = list(parts) if parts else []
        self.caller = "<unknown>"
        # Inspection magic to log the calling method, e.g. `module.sub:Class.method`.
        name = None
        if not caller:
            frame = inspect.currentframe()
            try:
                name = frame.f_back.f_code.co_name
                caller = frame.f_back.f_globals[name]
            except (AttributeError, KeyError):
                pass
        if caller:
            self.caller = "{}:{}".format(caller.__module__, caller.__qualname__)
        elif name:
            self.caller = name

    @property
    def state(self) -> State:
        if self._state:
            return self._state
        elif self.parts and any(result.state is State.success for result in self.parts):
            return State.success
        else:
            return State.unchanged

    @state.setter
    def state(self, state: State) -> None:
        self._state = state

    @property
    def value(self) -> V:
        if self._value is None:
            raise ValueError("No value set")
        return self._value

    @value.setter
    def value(self, value: V) -> None:
        self._value = value

    def append(self, result: "Result[R]") -> "Result[R]":
        """
        Include an additional result into the set, optionally using it as the overall value, and
        return that result for chaining.
        """
        self.parts.append(result)
        return result

    def extend(self, results: List["Result"]) -> None:
        """
        Include additional results into the set.
        """
        self.parts.extend(results)

    def __bool__(self) -> bool:
        return self.state is State.success

    def __repr__(self) -> str:
        return "{}({}{}{})".format(self.__class__.__name__, self.state,
                                   ", {!r}".format(self._value) if self._value else "",
                                   ", <{} parts>".format(len(self.parts)) if self.parts else "")

    def __str__(self) -> str:
        tree = "{}: {}{}".format(self.caller, self.state,
                                 " {!r}".format(self._value) if self._value else "")
        if self.parts:
            for result in self.parts:
                tree += "\n    {}".format(str(result).replace("\n", "\n    "))
        return tree


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


def require_host(*hosts: str):
    """
    Only allow a function to be called on the given hosts, identified by hostname:

        >>> @require_hosts(Hosts.USER)
        ... def create_user(username): ...
    """
    def outer(fn: Callable[..., R]) -> Callable[..., R]:
        @wraps(fn)
        def inner(*args, **kwargs):
            host = platform.node()
            if host not in hosts:
                raise RuntimeError("{}() can't be used on host {}, requires {}"
                                   .format(fn.__name__, host, "/".join(hosts)))
            return fn(*args, **kwargs)
        return inner
    return outer


def command(args, input_=None, output=False) -> subprocess.CompletedProcess:
    """
    Create a subprocess to execute an external command.
    """
    if input_:
        LOG.debug("Exec: %r <<< %r", args, input_)
    else:
        LOG.debug("Exec: %r", args)
    return subprocess.run(args, input=str(input_).encode("utf-8") if input_ else None,
                          stdout=subprocess.PIPE if output else None, check=True)
