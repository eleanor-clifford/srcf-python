import os
from typing import Set

from srcf.database import Member, Society
from srcf.database.queries import get_member, get_society

from srcflib.plumbing import bespoke, ResultSet, unix


def create_member(crsid: str, preferred_name: str, surname: str, email: str, mail_handler: str,
                  is_member: bool=True, is_user: bool=True, social: bool=False) -> ResultSet:
    """
    Register and provision a new member of the SRCF.
    """
    with bespoke.context() as sess:
        results = ResultSet(bespoke.create_member(sess, crsid, preferred_name, surname, email,
                                                  mail_handler, is_member, is_user))
        mem = results.last.value
    results.add(unix.create_user(crsid, uid=mem.uid, real_name=mem.name))
    user = results.last.value
    results.add(unix.create_home(user, os.path.join("/public/home", crsid)),
                bespoke.set_home_exim_acl(mem))
    if mail_handler == "pip":
        results.add(bespoke.create_forwarding_file(mem))
    results.add(bespoke.set_quota(mem),
                bespoke.set_web_status(mem, "subdomain"),
                bespoke.queue_list_subscription(mem, "maintenance"))
    if social:
        results.add(bespoke.queue_list_subscription(mem, "social"))
    results.add(bespoke.generate_apache_groups(),
                bespoke.export_members(),
                bespoke.make_yp())
    # TODO: adduser.local
    # TODO: Welcome email
    return results


def create_sysadmin(member: Member) -> ResultSet:
    """
    Create an administrative account for an existing member.
    """
    if not member.user:
        raise ValueError("{!r} is not an active user")
    username = "{}-adm".format(member.crsid)
    real_name = "{} (Sysadmin Account)".format(member.name)
    results = ResultSet(unix.create_user(username, real_name=real_name))
    user = results.last.value
    results.add(unix.add_to_group(user, unix.get_group("sysadmins")),
                unix.add_to_group(user, unix.get_group("adm")))
    # TODO: sed -i~ -re "/^sysadmin/ s/$/ (,$admuser,)/" /etc/netgroup
    for soc in ("executive", "srcf-admin", "srcf-web"):
        results.add(add_society_admin(member, get_society(soc)))
    # TODO: psql -h postgres sysadmins -c "CREATE ROLE \"$admuser\" LOGIN IN ROLE sysadmins;"
    return results


def create_society(name: str, description: str, admins: Set[str],
                   role_email: str=None) -> ResultSet:
    """
    Register a new SRCF society account.
    """
    with bespoke.context() as sess:
        results = ResultSet(bespoke.create_society(sess, name, description, admins, role_email))
        soc = results.last.value
    results.add(unix.create_user(name, uid=soc.uid, system=True, active=False,
                                 home_dir=os.path.join("/societies", name), real_name=description))
    user = results.last.value
    results.add(unix.create_group(name, gid=soc.gid, system=True))
    group = results.last.value
    results.add(unix.create_home(user, os.path.join("/public/societies", name)))
    for admin in admins:
        results.add(unix.add_to_group(unix.get_user(admin), group),
                    bespoke.link_soc_home_dir(get_member(admin), soc))
    results.add(bespoke.set_home_exim_acl(soc),
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
    results.add(unix.add_to_group(unix.get_user(member.crsid), unix.get_group(society.society)),
                bespoke.link_soc_home_dir(member, society))
    return results


def remove_society_admin(member: Member, society: Society) -> ResultSet:
    """
    Demote a member from a society account's list of admins.
    """
    with bespoke.context() as sess:
        member = get_member(member.crsid, sess)
        society = get_society(society.society, sess)
        results = ResultSet(bespoke.remove_from_society(sess, member, society))
    results.add(unix.remove_from_group(unix.get_user(member.crsid),
                                       unix.get_group(society.society)),
                bespoke.link_soc_home_dir(member, society))
    return results
