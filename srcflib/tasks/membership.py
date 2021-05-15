"""
Creation and management of member and society accounts.
"""

import os
from typing import Optional, Set, Tuple

from sqlalchemy.orm import Session as SQLASession

from srcf.database import MailHandler, Member, Society
from srcf.database.queries import get_member, get_society

from ..email import send
from ..plumbing import bespoke, pgsql as pgsql_p, unix
from ..plumbing.common import Collect, Password, Result, State, Unset
from . import mailman, mysql, pgsql


@Result.collect
def create_member(crsid: str, preferred_name: str, surname: str, email: str,
                  mail_handler: MailHandler, is_member: bool = True,
                  is_user: bool = True, social: bool = False,
                  new_passwd: bool = False) -> Collect[Tuple[Member, Optional[Password]]]:
    """
    Register and provision a new member of the SRCF.
    """
    with bespoke.context() as sess:
        res_record = yield from bespoke.ensure_member(sess, crsid, preferred_name, surname, email,
                                                      mail_handler, is_member, is_user)
        member = res_record.value
    res_user = yield from unix.ensure_user(crsid, uid=member.uid, system=True,
                                           home_dir=os.path.join("/home", crsid),
                                           real_name=member.name)
    new_user = res_user.state == State.created
    user = res_user.value
    yield unix.ensure_group(crsid, gid=member.gid, system=True)
    if new_user or new_passwd:
        res_passwd = yield from unix.reset_password(user)
        passwd = res_passwd.value
    else:
        passwd = None
    if res_user or passwd:
        yield bespoke.update_nis(new_user)
    yield unix.create_home(user, os.path.join("/public/home", crsid), True)
    yield bespoke.set_home_exim_acl(member)
    yield bespoke.populate_home_dir(member)
    if res_record:
        yield bespoke.update_quotas()
    if mail_handler == MailHandler.pip:
        yield bespoke.create_forwarding_file(member)
    yield bespoke.create_legacy_mailbox(member)
    res_web = yield from bespoke.enable_website(member)
    if new_user:
        yield bespoke.queue_list_subscription(member, "maintenance")
        if social:
            yield bespoke.queue_list_subscription(member, "social")
    if res_web:
        yield bespoke.generate_apache_groups()
    if res_record:
        yield bespoke.export_members()
    if new_user:
        send(member, "/tasks/member_create.j2", {"password": passwd})
    return (member, passwd)


@Result.collect
def create_sysadmin(member: Member, new_passwd: bool = False) -> Collect[Optional[Password]]:
    """
    Create an administrative account for an existing member.
    """
    if not member.user:
        raise ValueError("{!r} is not an active user")
    username = "{}-adm".format(member.crsid)
    real_name = "{} (Sysadmin Account)".format(member.name)
    res_user = yield from unix.ensure_user(username, real_name=real_name)
    new_user = res_user.state == State.created
    user = res_user.value
    if new_user or new_passwd:
        res_passwd = yield from unix.reset_password(user)
        passwd = res_passwd.value
    else:
        passwd = None
    if res_user or passwd:
        yield bespoke.update_nis(new_user)
    yield unix.add_to_group(user, unix.get_group("sysadmins"))
    yield unix.add_to_group(user, unix.get_group("adm"))
    yield unix.grant_netgroup(user, "sysadmins")
    for soc in ("executive", "srcf-admin", "srcf-web"):
        yield add_society_admin(member, get_society(soc))
    with pgsql.context() as cursor:
        yield pgsql_p.ensure_user(cursor, username)
        yield pgsql_p.grant_role(cursor, username, pgsql_p.get_role(cursor, "sysadmins"))
    return passwd


@Result.collect
def reset_password(member: Member) -> Collect[Password]:
    """
    Reset the password of a member's shell account.
    """
    user = unix.get_user(member.crsid)
    res_passwd = yield from unix.reset_password(user)
    passwd = res_passwd.value
    yield from bespoke.update_nis()
    send(member, "/tasks/member_password.j2", {"password": passwd})
    return passwd


@Result.collect
def update_member_name(member: Member, preferred_name: str, surname: str) -> Collect[Member]:
    """
    Update a member's registered name.
    """
    with bespoke.context() as sess:
        res_record = yield from bespoke.ensure_member(sess=sess, crsid=member.crsid,
                                                      preferred_name=preferred_name,
                                                      surname=surname,
                                                      email=member.email,
                                                      mail_handler=MailHandler[member.mail_handler],
                                                      is_member=member.member,
                                                      is_user=member.user)
        member = res_record.value
    user = unix.get_user(member.crsid)
    res_name = yield from unix.set_real_name(user, member.name)
    if res_name:
        yield bespoke.update_nis()
        send(member, "tasks/member_rename.j2")
    return member


@Result.collect
def _add_society_admin(sess: SQLASession, member: Member, society: Society,
                       group: unix.Group) -> Collect[None]:
    yield bespoke.add_to_society(sess, member, society)
    yield unix.add_to_group(unix.get_user(member.crsid), group)
    yield bespoke.link_soc_home_dir(member, society)


@Result.collect
def _remove_society_admin(sess: SQLASession, member: Member, society: Society,
                          group: unix.Group) -> Collect[None]:
    yield bespoke.remove_from_society(sess, member, society)
    yield unix.remove_from_group(unix.get_user(member.crsid), group)
    yield bespoke.link_soc_home_dir(member, society)


@Result.collect
def _sync_society_admins(sess: SQLASession, society: Society, admins: Set[str]) -> Collect[None]:
    if society.admin_crsids == admins:
        return
    group = unix.get_group(society.society)
    for crsid in admins - society.admin_crsids:
        member = get_member(crsid, sess)
        yield _add_society_admin(sess, member, society, group)
    for crsid in society.admin_crsids - admins:
        member = get_member(crsid, sess)
        yield _remove_society_admin(sess, member, society, group)
    with mysql.context() as cursor:
        yield mysql.sync_society_roles(cursor, society)
    with pgsql.context() as cursor:
        yield pgsql.sync_society_roles(cursor, society)


@Result.collect
def create_society(name: str, description: str, admins: Set[str],
                   role_email: Optional[str] = None) -> Collect[Society]:
    """
    Register a new SRCF society account.
    """
    with bespoke.context() as sess:
        res_record = yield from bespoke.ensure_society(sess, name, description, role_email)
        society = res_record.value
    res_user = yield from unix.ensure_user(name, uid=society.uid, system=True, active=False,
                                           home_dir=os.path.join("/societies", name),
                                           real_name=description)
    new_user = res_user.state == State.created
    user = res_user.value
    yield unix.ensure_group(name, gid=society.gid, system=True)
    if res_user:
        yield bespoke.update_nis(res_user.state == State.created)
    yield unix.create_home(user, os.path.join("/public/societies", name), True)
    yield bespoke.set_home_exim_acl(society)
    if res_record:
        yield bespoke.update_quotas()
    with bespoke.context() as sess:
        res_admins = yield _sync_society_admins(sess, society, admins)
    res_web = yield bespoke.enable_website(society)
    if res_web:
        yield bespoke.generate_apache_groups()
    if res_admins:
        yield bespoke.generate_sudoers()
    if res_record:
        yield bespoke.export_members()
    if new_user:
        send(society, "tasks/society_create.j2")
    return society


@Result.collect
def add_society_admin(member: Member, society: Society) -> Collect[None]:
    """
    Promote a member to a society account admin.
    """
    with bespoke.context() as sess:
        # Re-fetch under current session for transaction safety.
        member = get_member(member.crsid, sess)
        society = get_society(society.society, sess)
        group = unix.get_group(society.society)
        res_add = yield _add_society_admin(sess, member, society, group)
    with mysql.context() as cursor:
        yield mysql.sync_society_roles(cursor, society)
    with pgsql.context() as cursor:
        yield pgsql.sync_society_roles(cursor, society)
    if res_add:
        # Temporarily remove the new admin when emailing the short notification.
        society.admins.remove(member)
        send(society, "tasks/society_admin_add.j2", {"member": member})
        society.admins.add(member)
        send(member, "tasks/society_admin_join.j2", {"society": society})


@Result.collect
def remove_society_admin(member: Member, society: Society) -> Collect[None]:
    """
    Demote a member from a society account's list of admins.
    """
    with bespoke.context() as sess:
        # Re-fetch under current session for transaction safety.
        member = get_member(member.crsid, sess)
        society = get_society(society.society, sess)
        group = unix.get_group(society.society)
        res_remove = yield _remove_society_admin(sess, member, society, group)
    with mysql.context() as cursor:
        yield mysql.sync_society_roles(cursor, society)
    with pgsql.context() as cursor:
        yield pgsql.sync_society_roles(cursor, society)
    if res_remove:
        send(society, "tasks/society_admin_remove.j2", {"member": member})
        send(member, "tasks/society_admin_leave.j2", {"society": society})


def _scrub_society_user(society: Society) -> Result[Unset]:
    try:
        user = unix.get_user(society.society)
    except KeyError:
        return Result(State.unchanged)
    else:
        return unix.rename_user(user, "exsoc{}".format(society.uid))


def _scrub_society_group(society: Society) -> Result[Unset]:
    try:
        group = unix.get_group(society.society)
    except KeyError:
        return Result(State.unchanged)
    else:
        return unix.rename_group(group, "exsoc{}".format(society.gid))


@Result.collect
def delete_society(society: Society) -> Collect[None]:
    """
    Archive and delete all traces of a society account.
    """
    with bespoke.context() as sess:
        yield _sync_society_admins(sess, society, set())
    yield bespoke.slay_user(society)
    # TODO: for server in {"cavein", "doom", "sinkhole"}: bespoke.slay_user(society)
    yield bespoke.archive_society_files(society)
    yield bespoke.delete_society_files(society)
    with mysql.context() as cursor:
        yield mysql.drop_all_databases(cursor, society)
        yield mysql.drop_account(cursor, society)
    with pgsql.context() as cursor:
        yield pgsql.drop_all_databases(cursor, society)
        yield pgsql.drop_account(cursor, society)
    for mlist in mailman.get_list_suffixes(society):
        yield mailman.remove_list(society, mlist)
    yield _scrub_society_user(society)
    yield _scrub_society_group(society)
    with bespoke.context() as sess:
        for domain in bespoke.get_custom_domains(sess, society):
            yield bespoke.remove_custom_domain(sess, society, domain.domain)
        yield bespoke.delete_society(sess, society)
    yield bespoke.export_members()


@Result.collect
def update_society_description(society: Society, description: str) -> Collect[Society]:
    """
    Update a society's description ('full name').
    """
    with bespoke.context() as sess:
        res_record = yield from bespoke.ensure_society(sess=sess, name=society.society,
                                                       description=description,
                                                       admins=society.admin_crsids,
                                                       role_email=society.role_email)
        society = res_record.value
    user = unix.get_user(society.society)
    res_name = yield from unix.set_real_name(user, society.description)
    if res_name:
        yield bespoke.update_nis()
        send(society, "tasks/society_rename.j2")
    return society
