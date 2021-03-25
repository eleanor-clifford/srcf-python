"""
SRCF-specific tools.

Most methods identify users and groups using the `Member` and `Society` database models.
"""

from contextlib import contextmanager
from datetime import date
import logging
import os
import pwd
import shutil
import time
from typing import Generator, List, Optional

from requests import Session as RequestsSession

from sqlalchemy.orm import Session as SQLASession
from sqlalchemy.orm.exc import NoResultFound

from srcf.database import Domain, HTTPSCert, Member, Session, Society
from srcf.database.queries import get_member, get_society
from srcf.database.summarise import summarise_society

from .common import Collect, command, Owner, owner_name, require_host, Result, State
from .mailman import MailList
from . import hosts, unix


LOG = logging.getLogger(__name__)


@contextmanager
def context(sess: SQLASession = None) -> Generator[SQLASession, None, None]:
    """
    Run multiple database commands and commit at the end:

        with context() as sess:
            for ... in data:
                create_member(sess, ...)
    """
    sess = sess or Session()
    try:
        yield sess
    except Exception:
        sess.rollback()
        raise
    finally:
        sess.commit()


def get_crontab(owner: Owner) -> Optional[str]:
    """
    Fetch the owning user's crontab, if one exists on the current server.
    """
    proc = command(["/usr/bin/crontab", "-u", owner_name(owner), "-l"], output=True)
    return proc.stdout.decode("utf-8") if proc.stdout else None


def get_mailman_lists(owner: Owner, sess: RequestsSession = RequestsSession()) -> List[MailList]:
    """
    Query mailing lists owned by the given member or society.
    """
    prefix = owner_name(owner)
    resp = sess.get("https://lists.srcf.net/getlists.cgi", params={"prefix": prefix})
    return resp.text.splitlines()


def _create_member(sess: SQLASession, crsid: str, preferred_name: str, surname: str, email: str,
                   mail_handler: str = "forward", is_member: bool = True,
                   is_user: bool = True) -> Result[Member]:
    member = Member(crsid=crsid,
                    preferred_name=preferred_name,
                    surname=surname,
                    email=email,
                    mail_handler=mail_handler,
                    member=is_member,
                    user=is_user)
    sess.add(member)
    return Result(State.created, member)


def _update_member(sess: SQLASession, member: Member, preferred_name: str, surname: str,
                   email: str, mail_handler: str = "forward", is_member: bool = True,
                   is_user: bool = True) -> Result[None]:
    member.preferred_name = preferred_name
    member.surname = surname
    member.email = email
    member.mail_handler = mail_handler
    member.member = is_member
    member.user = is_user
    return Result(State.success if sess.is_modified(member) else State.unchanged)


@Result.collect
def ensure_member(sess: SQLASession, crsid: str, preferred_name: str, surname: str, email: str,
                  mail_handler: str = "forward", is_member: bool = True,
                  is_user: bool = True) -> Collect[Member]:
    """
    Register or update a member in the database.
    """
    try:
        member = get_member(crsid, sess)
    except KeyError:
        res_record = yield from _create_member(sess, crsid, preferred_name, surname, email,
                                               mail_handler, is_member, is_user)
        member = res_record.value
    else:
        yield _update_member(sess, member, preferred_name, surname, email, mail_handler,
                             is_member, is_user)
    return member


def _create_society(sess: SQLASession, name: str, description: str,
                    role_email: Optional[str] = None) -> Result[Society]:
    society = Society(society=name,
                      description=description,
                      role_email=role_email)
    sess.add(society)
    return Result(State.created, society)


def _update_society(sess: SQLASession, society: Society, description: str,
                    role_email: Optional[str]) -> Result[None]:
    society.description = description
    society.role_email = role_email
    return Result(State.success if sess.is_modified(society) else State.unchanged)


def delete_society(sess: SQLASession, society: Society) -> Result[None]:
    """
    Drop a society record from the database.
    """
    if society.admins:
        raise ValueError("Remove society admins for {} first".format(society))
    sess.delete(society)
    return Result(State.success)


@Result.collect
def ensure_society(sess: SQLASession, name: str, description: str,
                   role_email: Optional[str] = None) -> Collect[Society]:
    """
    Register or update a society in the database.

    For existing societies, this will synchronise member relations with the given list of admins.
    """
    try:
        society = get_society(name, sess)
    except KeyError:
        res_record = yield from _create_society(sess, name, description, role_email)
        society = res_record.value
    else:
        yield _update_society(sess, society, description, role_email)
    return society


def add_to_society(sess: SQLASession, member: Member, society: Society) -> Result[None]:
    """
    Add a new admin to a society account.
    """
    if member in society.admins:
        return Result(State.unchanged)
    society.admins.add(member)
    sess.add(society)
    return Result(State.success)


def remove_from_society(sess: SQLASession, member: Member, society: Society) -> Result[None]:
    """
    Remove an existing admin from a society account.
    """
    if member not in society.admins:
        return Result(State.unchanged)
    society.admins.remove(member)
    sess.add(society)
    return Result(State.success)


def populate_home_dir(member: Member):
    """
    Copy the contents of ``/etc/skel`` to a new user's home directory.

    This must be done before creating anything else in the directory.
    """
    target = os.path.join("/home", member.crsid)
    if os.listdir(target):
        # Avoid potentially clobbering existing files.
        return Result(State.unchanged)
    unix.copytree_chown_chmod("/etc/skel", os.path.join("/home", member.crsid),
                              member.uid, member.gid)
    return Result(State.success)


def link_soc_home_dir(member: Member, society: Society) -> Result[None]:
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
    state = State.unchanged
    if valid == needed:
        # Includes if they're no longer an admin, and something other than the usual link exists
        # where we'd normally put this link, in which case we leave it be.
        pass
    elif needed:
        try:
            os.symlink(target, link)
        except FileExistsError:
            LOG.warning("Not overwriting existing file %r", link)
        except OSError:
            LOG.warning("Couldn't symlink %r", link, exc_info=True)
        else:
            state = State.success
    else:
        try:
            os.unlink(link)
        except OSError:
            LOG.warning("Couldn't remove symlink %r", link, exc_info=True)
        else:
            state = State.success
    return Result(state)


@Result.collect
def set_home_exim_acl(owner: Owner) -> Collect[None]:
    """
    Grant access to the user's ``.forward`` file for Exim.
    """
    name = owner_name(owner)
    path = pwd.getpwnam(name).pw_dir
    yield unix.set_nfs_acl(path, "Debian-exim@srcf.net", "RX")


def create_forwarding_file(owner: Owner) -> Result[None]:
    """
    Write a default ``.forward`` file matching the user's external email address.
    """
    user = pwd.getpwnam(owner_name(owner))
    path = os.path.join(user.pw_dir, ".forward")
    if os.path.exists(path):
        return Result(State.unchanged)
    with open(path, "w") as f:
        f.write("{}\n".format(owner.email))
    os.chown(path, user.pw_uid, user.pw_gid)
    return Result(State.success)


def update_quotas() -> Result[None]:
    """
    Apply quotas from member and society limits to the filesystem.
    """
    # TODO: Port to SRCFLib, replace with entrypoint.
    command(["/usr/local/sbin/srcf-update-quotas"])
    return Result(State.success)


def enable_website(owner: Owner, status: str = "subdomain", replace: bool = False) -> Result[str]:
    """
    Initialise the owner's website, so that it will be included in Apache configuration.

    An existing website's type won't be changed unless `replace` is set.
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
        if current == status or not replace:
            return Result(State.unchanged, current)
        else:
            data[i] = "{}:{}".format(username, status)
            break
    else:
        data.append("{}:{}".format(username, status))
    with open(path, "w") as f:
        for line in data:
            f.write("{}\n".format(line))
    return Result(State.success, status)


def add_custom_domain(sess: SQLASession, owner: Owner, name: str,
                      root: str = None) -> Result[Domain]:
    """
    Assign a domain name to a member or society website.
    """
    if isinstance(owner, Member):
        class_ = "user"
    elif isinstance(owner, Society):
        class_ = "soc"
    else:
        raise TypeError(owner)
    try:
        domain = sess.query(Domain).filter(Domain.domain == name).one()
    except NoResultFound:
        domain = Domain(domain=name,
                        class_=class_,
                        owner=owner_name(owner),
                        root=root)
        sess.add(domain)
        state = State.created
    else:
        domain.class_ = class_
        domain.owner = owner_name(owner)
        domain.root = root
        state = State.success if sess.is_modified(domain) else State.unchanged
    return Result(state, domain)


def queue_https_cert(sess: SQLASession, domain: str) -> Result[HTTPSCert]:
    """
    Add an existing domain to the queue for requesting an HTTPS certificate.
    """
    assert sess.query(Domain).filter(Domain.domain == domain).count()
    try:
        cert = sess.query(HTTPSCert).filter(HTTPSCert.domain == domain).one()
    except NoResultFound:
        cert = HTTPSCert(domain=domain)
        sess.add(cert)
        state = State.created
    else:
        state = State.unchanged
    return Result(state, cert)


@require_host(hosts.WEB)
def generate_apache_groups() -> Result[None]:
    """
    Synchronise the Apache groups file, providing ``srcfmembers`` and ``srcfusers`` groups.
    """
    # TODO: Port to SRCFLib, replace with entrypoint.
    command(["/usr/local/sbin/srcf-updateapachegroups"])
    return Result(State.success)


def queue_list_subscription(member: Member, *lists: str) -> Result[None]:
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


def generate_sudoers() -> Result[None]:
    """
    Update sudo permissions to allow admins to exdcute commands under their society accounts.
    """
    # TODO: Port to SRCFLib, replace with entrypoint.
    command(["/usr/local/sbin/srcf-generate-society-sudoers"])
    return Result(State.success)


def export_members() -> Result[None]:
    """
    Regenerate the legacy membership lists.
    """
    # TODO: Port to SRCFLib, replace with entrypoint.
    command(["/usr/local/sbin/srcf-memberdb-export"])
    return Result(State.success)


@require_host(hosts.USER)
def update_nis(wait: bool = False) -> Result[None]:
    """
    Synchronise UNIX users and passwords over NIS.

    If a new user or group has just been created, and is about to be used, set ``wait`` to avoid
    the caching of non-existent UIDs or GIDs.
    """
    command(["/usr/bin/make", "-C", "/var/yp"])
    if wait:
        time.sleep(16)
    return Result(State.success)


@require_host(hosts.LIST)
def configure_mailing_list(name: str) -> Result[None]:
    """
    Apply default options to a new mailing list, and create the necessary mail aliases.
    """
    command(["/usr/sbin/config_list", "--inputfile", "/root/mailman-newlist-defaults", name])
    return Result(State.success)


@require_host(hosts.LIST)
def generate_mailman_aliases() -> Result[None]:
    """
    Refresh the Exim alias file for Mailman lists.
    """
    # TODO: Port to SRCFLib, replace with entrypoint.
    command(["/usr/local/sbin/srcf-generate-mailman-aliases"])
    return Result(State.success)


def archive_society_files(society: Society) -> Result[str]:
    """
    Create a backup of the society under /archive/societies.
    """
    home = os.path.join("/societies", society.society)
    public = os.path.join("/public/societies", society.society)
    root = os.path.join("/archive/societies", society.society)
    os.mkdir(root)
    tar = os.path.join(root, "soc-{}-{}.tar.bz2".format(society.society,
                                                        date.today().strftime("%Y%m%d")))
    command(["/bin/tar", "cjf", tar, home, public])
    crontab = get_crontab(society)
    if crontab:
        with open(os.path.join(root, "crontab"), "w") as f:
            f.write(crontab)
    # TOOD: for host in {"cavein", "sinkhole"}: get_crontab(society)
    with open(os.path.join(root, "society_info"), "w") as f:
        f.write(summarise_society(society))
    return Result(State.success, tar)


@Result.collect
def delete_society_files(society: Society):
    """
    Remove all public and private files of a society in /home.
    """
    home = os.path.join("/societies", society.society)
    public = os.path.join("/public/societies", society.society)
    for path in (home, public):
        if os.path.exists(path):
            shutil.rmtree(home)
            yield Result(State.success)
        else:
            yield Result(State.unchanged)


def slay_user(owner: Owner) -> Result[None]:
    """
    Kill all processes belonging to the given account.
    """
    proc = command(["/usr/local/sbin/srcf-slay", owner_name(owner)], output=True)
    return Result(State.success if proc.stdout else State.unchanged)
