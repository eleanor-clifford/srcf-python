"""
Unix user management.

Most methods identify users and groups using the `pwd` and `grp` module structs.
"""

import grp
import logging
import os
import pwd

# Expose these here for now, so that other parts of SRCFLib can reference them locally, but keep a
# single implementation in case it needs revising.  TODO: Move here as part of control migration.
from srcf.controllib.utils import copytree_chown_chmod, nfs_aware_chown  # noqa: F401

from .common import Collect, command, Password, require_host, Result, State
from . import hosts


LOG = logging.getLogger(__name__)

# Type aliases for external callers, who need not be aware of the internal structure when chaining
# calls (e.g. get_user/create_user -> reset_password).
User = pwd.struct_passwd
Group = grp.struct_group

_NOLOGIN_SHELLS = ("/bin/false", "/usr/sbin/nologin")


def get_user(username: str) -> User:
    """
    Look up an existing user by name.
    """
    return pwd.getpwnam(username)


def get_group(username: str) -> Group:
    """
    Look up an existing group by name.
    """
    return grp.getgrnam(username)


@require_host(hosts.USER)
def _create_user(username: str, uid: int = None, system: bool = False, active: bool = True,
                 home_dir: str = None, real_name: str = "") -> Result[User]:
    """
    Create a new user account.  System users are created with an empty home directory, whereas
    regular users inherit from ``/etc/skel``.
    """
    try:
        get_user(username)
    except KeyError:
        pass
    else:
        raise ValueError("Username {!r} is already in use".format(username))
    args = ["/usr/sbin/adduser", "--disabled-password", "--no-create-home", username]
    if uid:
        try:
            user = pwd.getpwuid(uid)
        except KeyError:
            # Don't set --gid, this implies an existing group -- uid == gid by default.
            args[-1:-1] = ["--uid", str(uid)]
        else:
            raise ValueError("UID {} is already in use by {!r}".format(uid, user.pw_name))
    if system:
        # Don't auto-create home directory as it will clone from /etc/skel.
        args[-1:-1] = ["--system", "--no-create-home"]
    if not active:
        args[-1:-1] = ["--shell", _NOLOGIN_SHELLS[0]]
    if home_dir:
        args[-1:-1] = ["--home", home_dir]
    if real_name:
        args[-1:-1] = ["--gecos", real_name]
    command(args)
    user = get_user(username)
    if system and home_dir:
        create_home(user, home_dir)
    return Result(State.created, user)


@require_host(hosts.USER)
def enable_user(user: User, active: bool = True) -> Result[None]:
    """
    Change the default shell for this user, using a no-login shell to disable, and bash to enable.
    """
    login = user.pw_shell not in _NOLOGIN_SHELLS
    if login and not active:
        command(["/usr/bin/chsh", "--shell", "/bin/bash", user.pw_name])
        return Result(State.success)
    elif active and not login:
        command(["/usr/bin/chsh", "--shell", _NOLOGIN_SHELLS[0], user.pw_name])
        return Result(State.success)
    else:
        return Result(State.unchanged)


@require_host(hosts.USER)
def set_real_name(user: User, real_name: str = "") -> Result[None]:
    """
    Update a user's GECOS name field.
    """
    current, *rest = user.pw_gecos.split(",")
    if current == real_name:
        return Result(State.unchanged)
    command(["/usr/bin/chfn", "--full-name", real_name, user.pw_name])
    return Result(State.success)


@require_host(hosts.USER)
def reset_password(user: User) -> Result[Password]:
    """
    Set the user's password to a new random value.
    """
    passwd = Password.new()
    command(["/usr/sbin/chpasswd"], passwd.wrap("{}:{{}}".format(user.pw_name)))
    return Result(State.success, passwd)


@require_host(hosts.USER)
def set_home_dir(user: User, home: str) -> Result[None]:
    if user.pw_dir == home:
        return Result(State.unchanged)
    command(["/usr/bin/usermod", "--home", home, user.pw_name])
    return Result(State.success)


def create_home(user: User, path: str, world_read: bool = False) -> Result[None]:
    """
    Create an empty home directory owned by the given user.
    """
    state = State.unchanged
    try:
        os.mkdir(path, 0o2775 if world_read else 0o2770)
    except FileExistsError:
        pass
    else:
        state = State.created
    stat = os.stat(path)
    if stat.st_uid != user.pw_uid or stat.st_gid != user.pw_gid:
        nfs_aware_chown(path, user.pw_uid, user.pw_gid)
        state = state or State.success
    return Result(state)


@Result.collect
def ensure_user(username: str, uid: int = None, system: bool = False, active: bool = True,
                home_dir: str = None, real_name: str = "") -> Collect[User]:
    """
    Create a new user account, or enable/disable an existing one.
    """
    try:
        user = get_user(username)
    except KeyError:
        res_user = yield from _create_user(username, uid, system, active, home_dir, real_name)
        return res_user.value
    else:
        if user.pw_uid != uid:
            raise ValueError("User {!r} has UID {}, expected {}".format(username, user.pw_uid, uid))
        yield enable_user(user, active)
        yield set_home_dir(user, home_dir)
        yield set_real_name(user, real_name)
        return user


@require_host(hosts.USER)
def _create_group(username: str, gid: int = None, system: bool = False) -> Result[Group]:
    """
    Create a new group.
    """
    try:
        get_group(username)
    except KeyError:
        pass
    else:
        raise ValueError("Username {!r} is already in use".format(username))
    args = ["/usr/sbin/addgroup", username]
    if gid:
        try:
            group = grp.getgrgid(gid)
        except KeyError:
            args[-1:-1] = ["--gid", str(gid)]
        else:
            raise ValueError("GID {} is already in use by {!r}".format(gid, group.gr_name))
    if system:
        args[-1:-1] = ["--system"]
    command(args)
    return Result(State.created, get_group(username))


@require_host(hosts.USER)
def add_to_group(user: User, group: Group) -> Result[None]:
    """
    Add a user to a secondary group.
    """
    if user.pw_name in group.gr_mem:
        return Result(State.unchanged)
    command(["/usr/sbin/addgroup", user.pw_name, group.gr_name])
    group.gr_mem.append(user.pw_name)
    return Result(State.success)


@require_host(hosts.USER)
def remove_from_group(user: User, group: Group) -> Result[None]:
    """
    Remove a user from a secondary group.
    """
    if user.pw_name not in group.gr_mem:
        return Result(State.unchanged)
    command(["/usr/sbin/deluser", user.pw_name, group.gr_name])
    group.gr_mem.remove(user.pw_name)
    return Result(State.success)


@Result.collect
def ensure_group(username: str, gid: int = None, system: bool = False) -> Collect[Group]:
    """
    Create a new or retrieve an existing group.
    """
    try:
        group = get_group(username)
    except KeyError:
        res_group = yield from _create_group(username, gid, system)
        return res_group.value
    else:
        if group.gr_gid != gid:
            raise ValueError("Group {!r} has GID {}, expected {}"
                             .format(username, group.gr_gid, gid))
        return group


_ACL_ALIASES = {"R": "rntcy", "W": "watTNcCyD", "X": "xtcy"}


def _unalias_acl(perms: str) -> str:
    for alias, expansion in _ACL_ALIASES.items():
        perms = perms.replace(alias, expansion)
    return "".join(sorted(set(perms)))


def get_nfs_acl(path: str, user: str) -> str:
    raw = command(["/usr/bin/nfs4_getfacl", path], output=True).stdout.decode("utf-8")
    allowed = set()
    denied = set()
    for line in raw.splitlines():
        if line.startswith("#"):
            continue
        type_, _, principal, perms = line.split(":")
        if principal != user:
            continue
        if type_ == "A":
            allowed.update(perms)
        elif type_ == "D":
            denied.update(perms)
    return "".join(sorted(allowed - denied))


def set_nfs_acl(path: str, user: str, perms: str) -> Result[None]:
    acl = get_nfs_acl(path, user)
    perms = _unalias_acl(perms)
    if set(acl) >= set(perms):
        return Result(State.unchanged)
    command(["/usr/bin/nfs4_setfacl", "-a", "A::{}:{}".format(user, perms), path])
    return Result(State.success)
