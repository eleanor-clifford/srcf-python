"""
SRCF-specific tools.

Most methods identify users and groups using the `Member` and `Society` database models.
"""

from contextlib import contextmanager
import logging
import os.path
import pwd
from typing import Set

import posix1e

from sqlalchemy.orm import Session as SESSION_TYPE

from srcf.database import Member, Session, Society
from srcf.database.queries import get_member, get_society

from .common import (command, get_members, Hosts, Owner, owner_name, require_host, Result,
                     ResultSet, State)


LOG = logging.getLogger(__name__)


@contextmanager
def context(sess: SESSION_TYPE=None):
    """
    Run multiple database commands and commit at the end::

        >>> with context() as sess:
        ...     for ... in data:
        ...         create_member(sess, ...)
    """
    sess = sess or Session()
    try:
        yield sess
    except Exception:
        sess.rollback()
        raise
    finally:
        sess.commit()


def create_member(sess: SESSION_TYPE, crsid: str, preferred_name: str, surname: str, email: str,
                  mail_handler: str="forward", is_member: bool=True,
                  is_user: bool=True) -> Result[Member]:
    """
    Register or update a member in the database.
    """
    try:
        mem = get_member(crsid, sess)
    except KeyError:
        mem = Member(crsid=crsid,
                     preferred_name=preferred_name,
                     surname=surname,
                     email=email,
                     mail_handler=mail_handler,
                     member=is_member,
                     user=is_user)
        sess.add(mem)
        state = State.success
    else:
        mem.preferred_name = preferred_name
        mem.surname = surname
        mem.email = email
        mem.mail_handler = mail_handler
        mem.member = is_member
        mem.user = is_user
        state = State.success if sess.is_modified(mem) else State.unchanged
    return Result(state, mem)


def create_society(sess: SESSION_TYPE, name: str, description: str, admins: Set,
                   role_email: str=None) -> Result[Society]:
    """
    Register or update a society in the database.
    """
    try:
        soc = get_society(name, sess)
    except KeyError:
        soc = Society(society=name,
                      description=description,
                      admins=get_members(sess, *admins),
                      role_email=role_email)
        sess.add(soc)
        state = State.success
    else:
        if admins != soc.admin_crsids:
            raise ValueError("Admins for {!r} are {}, expecting {}"
                             .format(name, soc.admin_crsids, admins))
        soc.description = description
        soc.role_email = role_email
        state = State.success if sess.is_modified(soc) else State.unchanged
    return Result(state, soc)


def add_to_society(sess: SESSION_TYPE, member: Member, society: Society) -> Result:
    """
    Add a new admin to a society account.
    """
    if member in society.admins:
        return Result(State.unchanged)
    society.admins.add(member)
    sess.add(society)
    return Result(State.success)


def remove_from_society(sess: SESSION_TYPE, member: Member, society: Society) -> Result:
    """
    Remove an existing admin from a society account.
    """
    if member not in society.admins:
        return Result(State.unchanged)
    society.admins.remove(member)
    sess.add(society)
    return Result(State.success)


def link_soc_home_dir(member: Member, society: Society) -> Result:
    """
    Add or remove a user's society symlink based on their admin membership.
    """
    link = os.path.join("/home", member.crsid, society.society)
    target = os.path.join("/societies", society.society)
    try:
        current = os.readlink(link)
    except OSError:
        current = None
    valid = current == target
    needed = member in society.admins
    result = Result(State.unchanged)
    if valid == needed:
        # Includes if they're no longer an admin, and something other than the usual link exists
        # where we'd normally put this link, in which case we leave it be.
        return result
    if member in society.admins:
        try:
            os.symlink(link, target)
        except FileExistsError:
            LOG.warning("Not overwriting existing file %r", link)
        except OSError:
            LOG.warning("Couldn't symlink %r", link, exc_info=True)
        else:
            result.state = State.success
    else:
        try:
            os.unlink(link)
        except OSError:
            LOG.warning("Couldn't remove symlink %r", link, exc_info=True)
        else:
            result.state = State.success
    return result


def set_home_exim_acl(owner: Owner) -> ResultSet:
    """
    Grant access to the user's ``.forward`` file for Exim.
    """
    path = pwd.getpwnam(owner_name(owner)).pw_dir
    exim = pwd.getpwnam("Debian-exim").pw_uid
    acl = posix1e.ACL(file=path)
    granted = masked = None
    for entry in acl:
        if entry.tag_type == posix1e.ACL_USER and entry.qualifier == exim:
            granted = entry.permset.execute
        elif entry.tag_type == posix1e.ACL_MASK:
            masked = entry.permset.read and entry.permset.write and entry.permset.execute
    if granted is None:
        grant = acl.append()
        grant.tag_type = posix1e.ACL_USER
        grant.qualifier = exim
        grant.permset.execute = True
    elif not granted:
        LOG.warning("Ignoring invalid home directory grant")
    if masked is None:
        mask = acl.append()
        mask.tag_type = posix1e.ACL_MASK
        mask.permset.read = True
        mask.permset.write = True
        mask.permset.execute = True
    elif not masked:
        LOG.warning("Ignoring invalid home directory mask")
    assert acl.valid()
    acl.applyto(path)
    return ResultSet(Result(State.success if granted is None else State.unchanged),
                     Result(State.success if masked is None else State.unchanged))


def create_forwarding_file(owner: Owner) -> Result:
    """
    Write a default ``.forward`` file matching the user's external email address.
    """
    user = pwd.getpwnam(owner_name(owner))
    path = os.path.join(user.pw_dir, ".forward")
    if os.path.exists(path):
        return Result(State.unchanged)
    with open(path, "w") as f:
        f.write(owner.email + "\n")
    os.chown(path, user.pw_uid, user.pw_gid)
    return Result(State.success)


def set_quota(owner: Owner) -> Result:
    """
    Apply the default quota to the owner's account.
    """
    command(["/usr/local/sbin/set_quota", owner_name(owner)])
    return Result(State.success)


def set_web_status(owner: Owner, status: str) -> Result:
    """
    Add or update the owner's website type, used for Apache configuration.
    """
    username = owner_name(owner)
    key = "member" if isinstance(owner, Member) else "soc"
    path = "/societies/srcf-admin/{}webstatus".format(key)
    with open(path, "r") as f:
        data = f.read().splitlines()
    for i, line in enumerate(data):
        name, current = line.split(":", 1)
        if name != username:
            continue
        if current == status:
            return Result(State.unchanged)
        else:
            data[i] = "{}:{}".format(name, status)
            break
    else:
        data.append("{}:{}".format(name, status))
    with open(path, "w") as f:
        for line in data:
            f.write("{}\n".format(line))
    return Result(State.success)


def generate_apache_groups() -> Result:
    """
    Synchronise the Apache groups file, providing ``srcfmembers`` and ``srcfusers`` groups.
    """
    # TODO: Port to SRCFLib, replace with entrypoint.
    command(["/usr/local/sbin/srcf-updateapachegroups"])
    return Result(State.success)


def queue_list_subscription(member: Member, *lists: str) -> Result:
    """
    Subscribe the user to one or more mailing lists.
    """
    if not lists:
        return Result(State.unchanged)
    # TODO: Port to SRCFLib, replace with entrypoint.
    entry = '"{}" <{}>'.format(member.name, member.email)
    args = ["/usr/local/sbin/srcf-enqueue-mlsub"]
    for name in lists:
        args.append("soc-srcf-{}:{}".format(name, entry))
    command(args)
    return Result(State.success)


def generate_sudoers() -> Result:
    """
    Update sudo permissions to allow admins to exdcute commands under their society accounts.
    """
    # TODO: Port to SRCFLib, replace with entrypoint.
    command(["/usr/local/sbin/srcf-generate-society-sudoers"])
    return Result(State.success)


def export_members() -> Result:
    """
    Regenerate the legacy membership lists.
    """
    # TODO: Port to SRCFLib, replace with entrypoint.
    command(["/usr/local/sbin/srcf-memberdb-export"])
    return Result(State.success)


@require_host(Hosts.USER)
def make_yp() -> Result:
    """
    Synchronise UNIX users and passwords over NIS.
    """
    command(["/usr/bin/make", "-C", "/var/yp"])
    return Result(State.success)


def configure_mailing_list(name: str) -> Result:
    """
    Apply default options to a new mailing list, and create the necessary mail aliases.
    """
    command(["/usr/sbin/config_list", "--inputfile", "/root/mailman-newlist-defaults", name])
    command(["/usr/local/sbin/gen_alias", name])
    return Result(State.success)
