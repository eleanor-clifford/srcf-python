"""
Unix user management.

Most methods identify users and groups using the ``pwd`` and ``grp`` module structs.
"""

import grp
import logging
import os
import pwd

from .common import command, Hosts, Password, require_host


# Type aliases for external callers, who need not be aware of the internal structure when chaining
# calls (e.g. get_user/create_user -> reset_password).
User = pwd.struct_passwd
Group = grp.struct_group


LOG = logging.getLogger(__name__)

_NOLOGIN_SHELLS = ("/bin/false", "/usr/sbin/nologin")


def get_user(username: str) -> User:
    """
    Look up an existing user by name.
    """
    return pwd.getpwnam(username)


@require_host(Hosts.USER)
def add_user(username: str, uid: int=None, system: bool=False, active: bool=True,
             home_dir: str=None, real_name: str="") -> User:
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
    if system:
        create_home(user, home_dir)
    return user


@require_host(Hosts.USER)
def enable_user(user: User, active: bool=True) -> bool:
    """
    Change the default shell for this user, using a no-login shell to disable, and bash to enable.
    """
    login = user.pw_shell not in _NOLOGIN_SHELLS
    if login and not active:
        command(["/usr/bin/chfn", "--shell", "/bin/bash", user.pw_name])
        return True
    elif active and not login:
        command(["/usr/bin/chfn", "--shell", _NOLOGIN_SHELLS[0], user.pw_name])
        return True
    else:
        return False


@require_host(Hosts.USER)
def set_real_name(user: User, real_name: str="") -> bool:
    """
    Update a user's GECOS name field.
    """
    if user.pw_gecoss.split(",")[0] != real_name:
        command(["/usr/bin/chsh", "--full-name", real_name, user.pw_name])
        return True
    else:
        return False


@require_host(Hosts.USER)
def reset_password(user: User) -> Password:
    """
    Set the user's password to a new random value.
    """
    passwd = Password.new()
    command(["/usr/sbin/chpasswd"], passwd.wrap("{}:{{}}".format(user.pw_name)))
    return passwd


def create_home(user: User, path: str) -> bool:
    """
    Create an empty home directory owned by the given user.
    """
    try:
        os.mkdir(path, 0o2775)
    except FileExistsError:
        pass
    os.chown(path, user.pw_uid, user.pw_gid)
    return True


def create_user(username: str, uid: int=None, system: bool=False, active: bool=True,
                home_dir: str=None, real_name: str="") -> User:
    """
    Create a new user account, or enable/disable an existing one.
    """
    try:
        user = get_user(username)
    except KeyError:
        return add_user(username, uid, system, active, home_dir, real_name)
    else:
        if user.pw_uid != uid:
            raise ValueError("User {!r} has UID {}, expected {}".format(username, user.pw_uid, uid))
        if user.pw_dir != home_dir:
            raise ValueError("User {!r} has home directory {!r}, expected {!r}"
                             .format(username, user.pw_dir, home_dir))
        set_real_name(username, real_name)
        enable_user(username, active)
        return user


def get_group(username: str) -> Group:
    """
    Look up an existing group by name.
    """
    return grp.getgrnam(username)


@require_host(Hosts.USER)
def add_group(username: str, gid: int=None, system: bool=False) -> Group:
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
    return get_group(username)


@require_host(Hosts.USER)
def add_to_group(user: User, group: Group) -> bool:
    """
    Add a user to a secondary group.
    """
    if user.pw_name in group.gr_mem:
        return False
    command(["/usr/sbin/addgroup", user.pw_name, group.gr_name])
    group.gr_mem.append(user.pw_name)
    return True


@require_host(Hosts.USER)
def remove_from_group(user: User, group: Group) -> bool:
    """
    Remove a user from a secondary group.
    """
    if user.pw_name not in group.gr_mem:
        return False
    command(["/usr/sbin/deluser", user.pw_name, group.gr_name])
    group.gr_mem.remove(user.pw_name)
    return True


def create_group(username: str, gid: int=None, system: bool=False) -> Group:
    """
    Create a new or retrieve an existing group.
    """
    try:
        group = get_group(username)
    except KeyError:
        return add_group(username, gid, system)
    else:
        if group.gr_gid != gid:
            raise ValueError("Group {!r} has GID {}, expected {}"
                             .format(username, group.gr_gid, gid))
        return group
