"""
Creation and management of member and society accounts.
"""

import os
from typing import Set

from srcf.database import Member, Society
from srcf.database.queries import get_member, get_society

from ..plumbing import bespoke, mailman, pgsql as pgsql_p, ResultSet, unix
from ..plumbing.mysql import context as mysql_context
from . import mysql, pgsql


def create_member(crsid: str, preferred_name: str, surname: str, email: str,
                  mail_handler: str, is_member: bool=True, is_user: bool=True,
                  social: bool=False) -> ResultSet[Member]:
    """
    Register and provision a new member of the SRCF.
    """
    results = ResultSet[Member]()
    with bespoke.context() as sess:
        result = bespoke.create_member(sess, crsid, preferred_name, surname, email,
                                       mail_handler, is_member, is_user)
        mem = results.add(result, True).value
    user = results.add(unix.create_user(crsid, uid=mem.uid, real_name=mem.name)).value
    results.extend(unix.create_home(user, os.path.join("/public/home", crsid)),
                   bespoke.set_home_exim_acl(mem))
    if mail_handler == "pip":
        results.extend(bespoke.create_forwarding_file(mem))
    results.extend(bespoke.set_quota(mem),
                   bespoke.set_web_status(mem, "subdomain"),
                   bespoke.queue_list_subscription(mem, "maintenance"))
    if social:
        results.extend(bespoke.queue_list_subscription(mem, "social"))
    results.extend(bespoke.generate_apache_groups(),
                   bespoke.export_members(),
                   bespoke.make_yp())
    # TODO: adduser.local
    return results


def create_sysadmin(member: Member) -> ResultSet:
    """
    Create an administrative account for an existing member.
    """
    if not member.user:
        raise ValueError("{!r} is not an active user")
    username = "{}-adm".format(member.crsid)
    real_name = "{} (Sysadmin Account)".format(member.name)
    results = ResultSet()
    user = results.add(unix.create_user(username, real_name=real_name)).value
    results.extend(unix.add_to_group(user, unix.get_group("sysadmins")),
                   unix.add_to_group(user, unix.get_group("adm")))
    # TODO: sed -i~ -re "/^sysadmin/ s/$/ (,$admuser,)/" /etc/netgroup
    for soc in ("executive", "srcf-admin", "srcf-web"):
        results.extend(add_society_admin(member, get_society(soc)))
    with pgsql_p.context() as cursor:
        results.extend(pgsql_p.create_user(cursor, username),
                       pgsql_p.grant_role(cursor, username, pgsql_p.get_role(cursor, "sysadmins")))
    return results


def create_society(name: str, description: str, admins: Set[str],
                   role_email: str=None) -> ResultSet[Society]:
    """
    Register a new SRCF society account.
    """
    results = ResultSet[Society]()
    with bespoke.context() as sess:
        soc = results.add(bespoke.create_society(sess, name, description, admins,
                                                 role_email), True).value
    user = results.add(unix.create_user(name, uid=soc.uid, system=True, active=False,
                                        home_dir=os.path.join("/societies", name),
                                        real_name=description)).value
    group = results.add(unix.create_group(name, gid=soc.gid, system=True)).value
    results.add(unix.create_home(user, os.path.join("/public/societies", name)))
    for admin in admins:
        results.extend(unix.add_to_group(unix.get_user(admin), group),
                       bespoke.link_soc_home_dir(get_member(admin), soc))
    results.extend(bespoke.set_home_exim_acl(soc),
                   bespoke.set_quota(soc),
                   bespoke.set_web_status(soc, "subdomain"),
                   bespoke.generate_apache_groups(),
                   bespoke.generate_sudoers(),
                   bespoke.export_members(),
                   bespoke.make_yp())
    # TODO: Welcome email
    # TODO: Existing admins email
    return results


def add_society_admin(member: Member, society: Society) -> ResultSet:
    """
    Promote a member to a society account admin.
    """
    with bespoke.context() as sess:
        # Re-fetch under current session for transaction safety.
        member = get_member(member.crsid, sess)
        society = get_society(society.society, sess)
        results = ResultSet(bespoke.add_to_society(sess, member, society))
    results.extend(unix.add_to_group(unix.get_user(member.crsid), unix.get_group(society.society)),
                   bespoke.link_soc_home_dir(member, society))
    with mysql_context() as cursor:
        results.extend(mysql.sync_society_roles(cursor, member))
    with pgsql_p.context() as cursor:
        results.extend(pgsql.sync_society_roles(cursor, member))
    return results


def remove_society_admin(member: Member, society: Society) -> ResultSet:
    """
    Demote a member from a society account's list of admins.
    """
    with bespoke.context() as sess:
        member = get_member(member.crsid, sess)
        society = get_society(society.society, sess)
        results = ResultSet(bespoke.remove_from_society(sess, member, society))
    results.extend(unix.remove_from_group(unix.get_user(member.crsid),
                                          unix.get_group(society.society)),
                   bespoke.link_soc_home_dir(member, society))
    with mysql_context() as cursor:
        results.extend(mysql.sync_society_roles(cursor, member))
    with pgsql_p.context() as cursor:
        results.extend(pgsql.sync_society_roles(cursor, member))
    return results


def delete_society(society: Society) -> ResultSet:
    """
    Archive and delete all traces of a society account.
    """
    results = ResultSet()
    for mem in society.admins:
        results.extend(remove_society_admin(mem, society))
    results.extend(bespoke.slay_user(society),
                   # TODO: for server in {"cavein", "sinkhole"}: bespoke.slay_user(society)
                   bespoke.archive_society_files(society),
                   bespoke.delete_society_files(society))
    with mysql_context() as cursor:
        mysql.drop_all_databases(cursor, society)
        mysql.drop_account(cursor, society)
    with pgsql_p.context() as cursor:
        pgsql.drop_all_databases(cursor, society)
        pgsql.drop_account(cursor, society)
    for mlist in bespoke.get_mailman_lists(society):
        mailman.remove_list(mlist)
    # TODO: Unix user/group
    with bespoke.session() as sess:
        results.extend(bespoke.delete_society(sess, society))
    results.extend(bespoke.export_members())
    return results
