import os
from typing import Set

from srcf.database import Member, Society
from srcf.database.queries import get_member, get_society

from srcflib.plumbing import bespoke, unix


def create_member(crsid: str, preferred_name: str, surname: str, email: str, mail_handler: str,
                  is_member: bool=True, is_user: bool=True, social: bool=False):
    """
    Register and provision a new member of the SRCF.
    """
    with bespoke.context() as sess:
        mem = bespoke.create_member(sess, crsid, preferred_name, surname, email, mail_handler,
                                    is_member, is_user)
    user = unix.create_user(crsid, uid=mem.uid, real_name=mem.name)
    unix.create_home(user, os.path.join("/public/home", crsid))
    bespoke.set_home_exim_acl(mem)
    if mail_handler == "pip":
        bespoke.create_forwarding_file(mem)
    bespoke.set_quota(mem)
    bespoke.set_web_status(mem, "subdomain")
    bespoke.queue_list_subscription(mem, "maintenance")
    if social:
        bespoke.queue_list_subscription(mem, "social")
    bespoke.generate_apache_groups()
    bespoke.export_members()
    bespoke.make_yp()
    # TODO: adduser.local
    # TODO: Welcome email


def create_sysadmin(member: Member):
    """
    Create an administrative account for an existing member.
    """
    if not member.user:
        raise ValueError("{!r} is not an active user")
    username = "{}-adm".format(member.crsid)
    user = unix.create_user(username, real_name="{} (Sysadmin Account)".format(member.name))
    unix.add_to_group(user, unix.get_group("sysadmins"))
    unix.add_to_group(user, unix.get_group("adm"))
    # TODO: sed -i~ -re "/^sysadmin/ s/$/ (,$admuser,)/" /etc/netgroup
    for soc in ("executive", "srcf-admin", "srcf-web"):
        add_society_admin(member, get_society(soc))
    # TODO: psql -h postgres sysadmins -c "CREATE ROLE \"$admuser\" LOGIN IN ROLE sysadmins;"


def create_society(name: str, description: str, admins: Set, role_email: str=None):
    """
    Register a new SRCF society account.
    """
    with bespoke.context() as sess:
        soc = bespoke.create_society(sess, name, description, admins, role_email)
    user = unix.create_user(name, uid=soc.uid, system=True, active=False,
                            home_dir=os.path.join("/societies", name), real_name=description)
    group = unix.create_group(name, system=True)
    unix.create_home(user, os.path.join("/public/societies", name))
    for admin in admins:
        unix.add_to_group(unix.get_user(admin), group)
        bespoke.link_soc_home_dir(get_member(admin), soc)
    bespoke.set_home_exim_acl(soc)
    bespoke.set_quota(soc)
    bespoke.set_web_status(soc, "subdomain")
    bespoke.generate_apache_groups()
    bespoke.generate_sudoers()
    bespoke.export_members()
    bespoke.make_yp()
    # TODO: Welcome email
    # TODO: Existing admins email


def add_society_admin(member: Member, society: Society):
    with bespoke.context() as sess:
        bespoke.add_to_society(sess, member, society)
    unix.add_to_group(unix.get_user(member.crsid), unix.get_group(society.society))
    bespoke.link_soc_home_dir(member, society)


def remove_society_admin(member: Member, society: Society):
    with bespoke.context() as sess:
        bespoke.remove_from_society(sess, member, society)
    unix.remove_from_group(unix.get_user(member.crsid), unix.get_group(society.society))
    bespoke.link_soc_home_dir(member, society)
