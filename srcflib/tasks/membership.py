"""
Creation and management of member and society accounts.
"""

import os
from typing import Set

from srcf.database import Member, Society
from srcf.database.queries import get_member, get_society

from ..plumbing import bespoke, pgsql as pgsql_p, unix
from ..plumbing.common import Password, Result
from . import mailman, mysql, pgsql


@Result.collect
def create_member(crsid: str, preferred_name: str, surname: str, email: str,
                  mail_handler: str, is_member: bool = True, is_user: bool = True,
                  social: bool = False):
    """
    Register and provision a new member of the SRCF.
    """
    with bespoke.context() as sess:
        member = yield bespoke.create_member(sess, crsid, preferred_name, surname, email,
                                             mail_handler, is_member, is_user)  # type: Member
    user = yield unix.create_user(crsid, uid=member.uid, system=True,
                                  home_dir=os.path.join("/home", crsid),
                                  real_name=member.name)  # type: unix.User
    passwd = yield unix.reset_password(user)  # type: Password
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
    return (member, passwd)


@Result.collect
def create_sysadmin(member: Member):
    """
    Create an administrative account for an existing member.
    """
    if not member.user:
        raise ValueError("{!r} is not an active user")
    username = "{}-adm".format(member.crsid)
    real_name = "{} (Sysadmin Account)".format(member.name)
    user = yield unix.create_user(username, real_name=real_name)  # type: unix.User
    passwd = yield unix.reset_password(user)  # type: Password
    yield unix.add_to_group(user, unix.get_group("sysadmins"))
    yield unix.add_to_group(user, unix.get_group("adm"))
    # TODO: sed -i~ -re "/^sysadmin/ s/$/ (,$admuser,)/" /etc/netgroup
    for soc in ("executive", "srcf-admin", "srcf-web"):
        yield add_society_admin(member, get_society(soc))
    with pgsql.context() as cursor:
        yield pgsql_p.create_user(cursor, username)
        yield pgsql_p.grant_role(cursor, username, pgsql_p.get_role(cursor, "sysadmins"))
    return passwd


@Result.collect
def update_member_name(member: Member, preferred_name: str, surname: str):
    """
    Update a member's registered name.
    """
    with bespoke.context() as sess:
        member = yield bespoke.create_member(sess=sess, crsid=member.crsid,
                                             preferred_name=preferred_name,
                                             surname=surname,
                                             email=member.email,
                                             mail_handler=member.mail_handler,
                                             is_member=member.member,
                                             is_user=member.user)
    user = unix.get_user(member.crsid)
    rename = unix.set_real_name(user, member.name)
    yield rename
    if rename:
        yield bespoke.update_nis()
    return member


@Result.collect
def create_society(name: str, description: str, admins: Set[str], role_email: str = None):
    """
    Register a new SRCF society account.
    """
    with bespoke.context() as sess:
        society = yield bespoke.create_society(sess, name, description, admins,
                                               role_email)  # type: Society
    user = yield unix.create_user(name, uid=society.uid, system=True, active=False,
                                  home_dir=os.path.join("/societies", name),
                                  real_name=description)  # type: unix.User
    group = yield unix.create_group(name, gid=society.gid, system=True)  # type: unix.Group
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
def add_society_admin(member: Member, society: Society):
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
def remove_society_admin(member: Member, society: Society):
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
def delete_society(society: Society):
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
def update_society_description(society: Society, description: str):
    """
    Update a society's description ('full name').
    """
    with bespoke.context() as sess:
        society = yield bespoke.create_society(sess=sess, name=society.society,
                                               description=description,
                                               admins=society.admin_crsids,
                                               role_email=society.role_email)
    user = unix.get_user(society.society)
    rename = unix.set_real_name(user, society.description)
    yield rename
    if rename:
        yield bespoke.update_nis()
    return society
