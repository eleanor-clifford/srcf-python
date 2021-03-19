"""
Creation and management of member and society accounts.
"""

import os
from typing import Set, Tuple

from srcf.database import Member, Society
from srcf.database.queries import get_member, get_society

from ..plumbing import bespoke, pgsql as pgsql_p, unix
from ..plumbing.common import Collect, Password, Result
from . import mailman, mysql, pgsql


@Result.collect
def create_member(crsid: str, preferred_name: str, surname: str, email: str,
                  mail_handler: str, is_member: bool = True, is_user: bool = True,
                  social: bool = False) -> Collect[Tuple[Member, Password]]:
    """
    Register and provision a new member of the SRCF.
    """
    with bespoke.context() as sess:
        res_record = yield from bespoke.create_member(sess, crsid, preferred_name, surname, email,
                                                      mail_handler, is_member, is_user)
        member = res_record.value
    res_user = yield from unix.create_user(crsid, uid=member.uid, system=True,
                                           home_dir=os.path.join("/home", crsid),
                                           real_name=member.name)
    user = res_user.value
    res_passwd = yield from unix.reset_password(user)
    yield bespoke.update_nis(True)
    yield unix.create_home(user, os.path.join("/public/home", crsid), True)
    yield bespoke.set_home_exim_acl(member)
    yield bespoke.populate_home_dir(member)
    yield bespoke.update_quotas()
    if mail_handler == "pip":
        yield bespoke.create_forwarding_file(member)
    # TODO: Legacy mailbox creation
    yield bespoke.set_web_status(member, "subdomain")
    yield bespoke.queue_list_subscription(member, "maintenance")
    if social:
        yield bespoke.queue_list_subscription(member, "social")
    yield bespoke.generate_apache_groups()
    yield bespoke.export_members()
    # TODO: Welcome email
    return (member, res_passwd.value)


@Result.collect
def create_sysadmin(member: Member) -> Collect[Password]:
    """
    Create an administrative account for an existing member.
    """
    if not member.user:
        raise ValueError("{!r} is not an active user")
    username = "{}-adm".format(member.crsid)
    real_name = "{} (Sysadmin Account)".format(member.name)
    res_user = yield from unix.create_user(username, real_name=real_name)
    user = res_user.value
    res_passwd = yield from unix.reset_password(user)
    yield unix.add_to_group(user, unix.get_group("sysadmins"))
    yield unix.add_to_group(user, unix.get_group("adm"))
    # TODO: sed -i~ -re "/^sysadmin/ s/$/ (,$admuser,)/" /etc/netgroup
    for soc in ("executive", "srcf-admin", "srcf-web"):
        yield add_society_admin(member, get_society(soc))
    with pgsql.context() as cursor:
        yield pgsql_p.create_user(cursor, username)
        yield pgsql_p.grant_role(cursor, username, pgsql_p.get_role(cursor, "sysadmins"))
    return res_passwd.value


@Result.collect
def update_member_name(member: Member, preferred_name: str, surname: str) -> Collect[Member]:
    """
    Update a member's registered name.
    """
    with bespoke.context() as sess:
        res_record = yield from bespoke.create_member(sess=sess, crsid=member.crsid,
                                                      preferred_name=preferred_name,
                                                      surname=surname,
                                                      email=member.email,
                                                      mail_handler=member.mail_handler,
                                                      is_member=member.member,
                                                      is_user=member.user)
        member = res_record.value
    user = unix.get_user(member.crsid)
    res_name = yield from unix.set_real_name(user, member.name)
    if res_name:
        yield bespoke.update_nis()
    return member


@Result.collect
def create_society(name: str, description: str, admins: Set[str],
                   role_email: str = None) -> Collect[Society]:
    """
    Register a new SRCF society account.
    """
    with bespoke.context() as sess:
        res_record = yield from bespoke.create_society(sess, name, description, admins, role_email)
        society = res_record.value
    res_user = yield from unix.create_user(name, uid=society.uid, system=True, active=False,
                                           home_dir=os.path.join("/societies", name),
                                           real_name=description)
    res_group = yield from unix.create_group(name, gid=society.gid, system=True)
    user, group = res_user.value, res_group.value
    yield bespoke.update_nis(True)
    yield unix.create_home(user, os.path.join("/public/societies", name), True)
    yield bespoke.set_home_exim_acl(society)
    yield bespoke.update_quotas()
    for admin in admins:
        yield unix.add_to_group(unix.get_user(admin), group)
        yield bespoke.link_soc_home_dir(get_member(admin), society)
    yield bespoke.set_web_status(society, "subdomain")
    yield bespoke.generate_apache_groups()
    yield bespoke.generate_sudoers()
    yield bespoke.export_members()
    # TODO: Welcome email
    # TODO: Existing admins email
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
        yield bespoke.add_to_society(sess, member, society)
    yield unix.add_to_group(unix.get_user(member.crsid), unix.get_group(society.society))
    yield bespoke.link_soc_home_dir(member, society)
    with mysql.context() as cursor:
        yield mysql.sync_society_roles(cursor, member)
    with pgsql.context() as cursor:
        yield pgsql.sync_society_roles(cursor, member)


@Result.collect
def remove_society_admin(member: Member, society: Society) -> Collect[None]:
    """
    Demote a member from a society account's list of admins.
    """
    with bespoke.context() as sess:
        member = get_member(member.crsid, sess)
        society = get_society(society.society, sess)
        yield bespoke.remove_from_society(sess, member, society)
    yield unix.remove_from_group(unix.get_user(member.crsid), unix.get_group(society.society))
    yield bespoke.link_soc_home_dir(member, society)
    with mysql.context() as cursor:
        yield mysql.sync_society_roles(cursor, member)
    with pgsql.context() as cursor:
        yield pgsql.sync_society_roles(cursor, member)


@Result.collect
def delete_society(society: Society) -> Collect[None]:
    """
    Archive and delete all traces of a society account.
    """
    for mem in society.admins:
        yield remove_society_admin(mem, society)
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
    # TODO: Unix user/group
    with bespoke.context() as sess:
        yield bespoke.delete_society(sess, society)
    yield bespoke.export_members()


@Result.collect
def update_society_description(society: Society, description: str) -> Collect[Society]:
    """
    Update a society's description ('full name').
    """
    with bespoke.context() as sess:
        res_record = yield from bespoke.create_society(sess=sess, name=society.society,
                                                       description=description,
                                                       admins=society.admin_crsids,
                                                       role_email=society.role_email)
        society = res_record.value
    user = unix.get_user(society.society)
    res_name = yield from unix.set_real_name(user, society.description)
    if res_name:
        yield bespoke.update_nis()
    return society
