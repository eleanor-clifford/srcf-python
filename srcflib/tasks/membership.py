"""
Creation and management of member and society accounts.
"""

from datetime import datetime
import logging
import os
from typing import Optional, Set, Tuple

from sqlalchemy.orm import Session as SQLASession

from srcf.database import MailHandler, Member, Society
from srcf.database.queries import get_member, get_society

from ..email import send
from ..plumbing import bespoke, pgsql as pgsql_p, unix
from ..plumbing.common import Collect, Password, Result, State, owner_home
from . import mailman, mysql, pgsql


LOG = logging.getLogger(__name__)


@Result.collect_value
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
    yield unix.ensure_group(crsid, gid=member.gid, system=True)
    res_user = yield from unix.ensure_user(crsid, uid=member.uid, system=True, gid=member.gid,
                                           home_dir=os.path.join("/home", crsid),
                                           real_name=member.name)
    new_user = res_user.state == State.created
    user = res_user.value
    passwd = None
    if new_user or new_passwd:
        res_passwd = yield from unix.reset_password(user)
        passwd = res_passwd.value
    if res_user or passwd:
        yield bespoke.update_nis(new_user)
    yield unix.create_home(user, owner_home(member))
    yield unix.create_home(user, owner_home(member, True), True)
    yield bespoke.populate_home_dir(member)
    yield bespoke.set_home_exim_acl(member)
    yield bespoke.create_public_html(member)
    if res_record:
        yield bespoke.update_quotas()
    if mail_handler == MailHandler.pip:
        yield bespoke.create_forwarding_file(member)
    yield bespoke.create_legacy_mailbox(member)
    yield bespoke.enable_website(member)
    if new_user:
        yield bespoke.queue_list_subscription(member, "maintenance")
        if social:
            yield bespoke.queue_list_subscription(member, "social")
    if res_record:
        yield bespoke.export_members()
    if passwd:
        yield send(member, "/tasks/member_create.j2", {"password": passwd})
    return (member, passwd)


@Result.collect_value
def create_sysadmin(member: Member, new_passwd: bool = False) -> Collect[Optional[Password]]:
    """
    Create an administrative account for an existing member.
    """
    if not member.user:
        raise ValueError("{!r} is not an active user")
    username = "{}-adm".format(member.crsid)
    real_name = "{} (Sysadmin Account)".format(member.name)
    res_group = yield from unix.ensure_group(username)
    group = res_group.value
    res_user = yield from unix.ensure_user(username, gid=group.gr_gid, real_name=real_name)
    new_user = res_user.state == State.created
    user = res_user.value
    if new_user or new_passwd:
        res_passwd = yield from unix.reset_password(user)
        passwd = res_passwd.value
    else:
        passwd = None
    if res_user or passwd:
        yield bespoke.update_nis(new_user)
    yield unix.create_home(user, os.path.join("/home", username))
    yield unix.create_home(user, os.path.join("/public/home", username), True)
    yield bespoke.populate_home_dir(member)
    yield unix.add_to_group(user, unix.get_group("sysadmins"))
    yield unix.add_to_group(user, unix.get_group("adm"))
    yield unix.grant_netgroup(user, "sysadmins")
    for soc in ("executive", "srcf-admin", "srcf-web"):
        yield add_society_admin(member, get_society(soc))
    with pgsql.context() as cursor:
        yield pgsql_p.ensure_user(cursor, username)
        yield pgsql_p.grant_role(cursor, username, pgsql_p.get_role(cursor, "sysadmins"))
    return passwd


@Result.collect_value
def reset_password(member: Member) -> Collect[Password]:
    """
    Reset the password of a member's shell account.
    """
    user = unix.get_user(member.crsid)
    res_passwd = yield from unix.reset_password(user)
    passwd = res_passwd.value
    yield from bespoke.update_nis()
    yield send(member, "/tasks/member_password.j2", {"password": passwd})
    return passwd


@Result.collect_value
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
        yield send(member, "tasks/member_rename.j2")
    return member


@Result.collect
def _sync_society_admins(sess: SQLASession, society: Society, admins: Set[str]) -> Collect[None]:
    society = get_society(society.society, sess)
    if society.admin_crsids == admins:
        return
    group = unix.get_group(society.society)
    for crsid in admins - society.admin_crsids:
        member = get_member(crsid, sess)
        yield bespoke.add_society_admin(sess, member, society, group)
    for crsid in society.admin_crsids - admins:
        member = get_member(crsid, sess)
        yield bespoke.remove_society_admin(sess, member, society, group)
    with mysql.context() as cursor:
        yield mysql.sync_society_roles(cursor, society)
    with pgsql.context() as cursor:
        yield pgsql.sync_society_roles(cursor, society)


@Result.collect_value
def create_society(name: str, description: str, admins: Set[str],
                   role_email: Optional[str] = None) -> Collect[Society]:
    """
    Register a new SRCF society account.
    """
    with bespoke.context() as sess:
        res_record = yield from bespoke.ensure_society(sess, name, description, role_email)
    society = res_record.value
    yield unix.ensure_group(name, gid=society.gid, system=True)
    res_user = yield from unix.ensure_user(name, uid=society.uid, system=True,
                                           gid=society.gid, active=False,
                                           home_dir=os.path.join("/societies", name),
                                           real_name=description)
    new_user = res_user.state == State.created
    user = res_user.value
    if res_user:
        yield bespoke.update_nis(res_user.state == State.created)
    yield unix.create_home(user, owner_home(society))
    yield unix.create_home(user, owner_home(society, True), True)
    yield bespoke.set_home_exim_acl(society)
    yield bespoke.create_public_html(society)
    with bespoke.context() as sess:
        res_admins = yield _sync_society_admins(sess, society, admins)
    if res_record:
        yield bespoke.update_quotas()
    yield bespoke.enable_website(society)
    if res_admins:
        yield bespoke.generate_sudoers()
    if res_record:
        yield bespoke.export_members()
    if new_user:
        yield send(society, "tasks/society_create.j2")
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
        res_add = yield from bespoke.add_society_admin(sess, member, society, group)
    with mysql.context() as cursor:
        yield mysql.sync_society_roles(cursor, society)
    with pgsql.context() as cursor:
        yield pgsql.sync_society_roles(cursor, society)
    if res_add:
        # Temporarily remove the new admin when emailing the short notification.
        society.admins.remove(member)
        yield send(society, "tasks/society_admin_add.j2", {"member": member})
        society.admins.add(member)
        yield send(member, "tasks/society_admin_join.j2", {"society": society})


@Result.collect
def remove_society_admin(member: Member, society: Society,
                         notify_removed: bool = True) -> Collect[None]:
    """
    Demote a member from a society account's list of admins.
    """
    with bespoke.context() as sess:
        # Re-fetch under current session for transaction safety.
        member = get_member(member.crsid, sess)
        society = get_society(society.society, sess)
        group = unix.get_group(society.society)
        res_remove = yield from bespoke.remove_society_admin(sess, member, society, group)
    with mysql.context() as cursor:
        yield mysql.sync_society_roles(cursor, society)
    with pgsql.context() as cursor:
        yield pgsql.sync_society_roles(cursor, society)
    if res_remove:
        yield send(society, "tasks/society_admin_remove.j2", {"member": member})
        if notify_removed:
            yield send(member, "tasks/society_admin_leave.j2", {"society": society})


@Result.collect
def cancel_member(member: Member, keep_groups: bool = False) -> Collect[None]:
    """
    Suspend the user account of a member.
    """
    user = unix.get_user(member.uid)
    yield unix.enable_user(user, False)
    yield bespoke.clear_crontab(member)
    yield bespoke.slay_user(member)
    # TODO: for server in {"cavein", "doom", "sinkhole"}:
    #   bespoke.clear_crontab(member); bespoke.slay_user(member)
    yield bespoke.archive_website(member)
    with bespoke.context() as sess:
        yield bespoke.ensure_member(sess, member.crsid, member.preferred_name, member.surname,
                                    member.email, MailHandler[member.mail_handler], member.member,
                                    False)
    with mysql.context() as cursor:
        yield mysql.drop_account(cursor, member)
    with pgsql.context() as cursor:
        yield pgsql.drop_account(cursor, member)
    if not keep_groups:
        for society in member.societies:
            yield remove_society_admin(member, society, False)


@Result.collect
def delete_member(member: Member) -> Collect[None]:
    """
    Delete all traces of a member account.
    """
    yield cancel_member(member)
    with bespoke.context() as sess:
        res_member = yield from bespoke.ensure_member(sess, member.crsid, None, None, None,
                                                      MailHandler[member.mail_handler], False,
                                                      False)
        member = res_member.value
        note = "User account erased: {}".format(datetime.now().strftime("%Y-%m-%d %H:%M"))
        if member.notes:
            member.notes = "{}\n{}".format(member.notes, note)
        else:
            member.notes = note
        yield bespoke.scrub_member_jobs(sess, member)
    with mysql.context() as cursor:
        yield mysql.drop_all_databases(cursor, member)
    with pgsql.context() as cursor:
        yield pgsql.drop_all_databases(cursor, member)
    for mlist in mailman.get_list_suffixes(member):
        yield mailman.remove_list(member, mlist, True)
    yield bespoke.empty_legacy_mailbox(member)
    # TODO: hades mail
    yield bespoke.scrub_user(member)
    yield bespoke.scrub_group(member)
    yield bespoke.delete_files(member)


@Result.collect
def delete_society(society: Society) -> Collect[None]:
    """
    Archive and delete all traces of a society account.
    """
    with bespoke.context() as sess:
        yield _sync_society_admins(sess, society, set())
    yield bespoke.clear_crontab(society)
    yield bespoke.slay_user(society)
    # TODO: for server in {"cavein", "doom", "sinkhole"}:
    #   bespoke.clear_crontab(society); bespoke.slay_user(society)
    yield bespoke.archive_society_files(society)
    yield bespoke.delete_files(society)
    with mysql.context() as cursor:
        yield mysql.drop_all_databases(cursor, society)
        yield mysql.drop_account(cursor, society)
    with pgsql.context() as cursor:
        yield pgsql.drop_all_databases(cursor, society)
        yield pgsql.drop_account(cursor, society)
    for mlist in mailman.get_list_suffixes(society):
        yield mailman.remove_list(society, mlist)
    yield bespoke.scrub_user(society)
    yield bespoke.scrub_group(society)
    with bespoke.context() as sess:
        for domain in bespoke.get_custom_domains(sess, society):
            yield bespoke.remove_custom_domain(sess, society, domain.domain)
        yield bespoke.delete_society(sess, society)
    yield bespoke.export_members()


@Result.collect_value
def update_society_description(society: Society, description: str) -> Collect[Society]:
    """
    Update a society's description ('full name').
    """
    with bespoke.context() as sess:
        res_record = yield from bespoke.ensure_society(sess=sess, name=society.society,
                                                       description=description,
                                                       role_email=society.role_email)
        society = res_record.value
    user = unix.get_user(society.society)
    res_name = yield from unix.set_real_name(user, society.description)
    if res_name:
        yield bespoke.update_nis()
        yield send(society, "tasks/society_rename.j2")
    return society
