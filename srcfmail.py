from os import getenv, getuid
from pwd import getpwnam, getpwuid
from subprocess import Popen, PIPE

import email.utils
import srcf

# pseudoconstant
SYSADMINEMAIL = 'soc-srcf-admin@lists.cam.ac.uk'
FORMATTEDSYSADMINEMAIL = email.utils.formataddr(('SRCF system administrators', 'soc-srcf-admin@lists.cam.ac.uk'))

def whoami():
    """Return a pwd struct for the invoking user, as determined by
    SUDO_USER or getuid()."""

    user = getenv('SUDO_USER')

    if user is None:
        return getpwuid(getuid())
    else:
        return getpwnam(user)

def pretty_sysadmin_name(name):
    """Trim after the first comma and the first parenthesis in the name.

    Examples:
      "Ben Millwood (Sysadmin Account),,," => "Ben Millwood"
      "SRCF server (pip),,," => "SRCF server" """

    return name.split(',')[0].split('(')[0].rstrip()

def mailtosysadmins(subject, body):
    """Send a mail to SYSADMINEMAIL with the given subject and body,
    which should both be strings.

    From: if bm380-adm does 'sudo srcf-mailtosysadmins subject' then the
    from will be "Ben Millwood <bm380@srcf.net>" - i.e. take SUDO_USER (or
    getuid), strip -adm if present, add @srcf.net, lookup name and apply
    pretty_sysadmin_name.

    Note that this differs from e.g. the srcf-mailtouser script, which puts
    soc-srcf-admin in the From field (even though it *does* work out who you
    are, so it can sign emails as you).
    
    Content-type: text/plain; format=flowed; charset=UTF-8"""
    sender = whoami()
    fromaddr = sender.pw_name.replace('-adm','') + '@srcf.net'
    myname = pretty_sysadmin_name(sender.pw_gecos)

    mail = Popen(['/usr/bin/env', 'mail', '-s', subject,
        '-a', 'Content-type: text/plain; format=flowed; charset=UTF-8',
        '-a', 'From: %s' % email.utils.formataddr((myname, fromaddr)),
        FORMATTEDSYSADMINEMAIL],
        stdin = PIPE)

    _, _ = mail.communicate(body)
    return mail.returncode

def mailtouser(user, subject, body, cc_sysadmins=False):
    """Send a mail to a user's registered email address with the given
    subject and body, which should both be strings.  The user can be a
    Member object or a string, in which case it is interpreted as a
    CRSid.  A KeyError is thrown if the CRSid is not that of a valid
    user.

    If the optional argument cc_sysadmins is set to True (default
    False), SYSADMINEMAIL is cc'ed in.

    From: if bm380-adm does 'sudo srcf-mailtosysadmins subject' then the
    from will be "Ben Millwood <bm380@srcf.net>" - i.e. take SUDO_USER (or
    getuid), strip -adm if present, add @srcf.net, lookup name and apply
    pretty_sysadmin_name.

    Note that this differs from e.g. the srcf-mailtouser script, which puts
    soc-srcf-admin in the From field (even though it *does* work out who you
    are, so it can sign emails as you).
    
    Content-type: text/plain; format=flowed; charset=UTF-8"""

    # Convert the CRSid to a Member object, if necessary
    if not isinstance(user, srcf.Member):
        user = srcf.get_user(user)

    sender = whoami()
    fromaddr = sender.pw_name.replace('-adm','') + '@srcf.net'
    myname = pretty_sysadmin_name(sender.pw_gecos)

    mailargs = ['/usr/bin/env', 'mail', '-s', subject,
        '-a', 'Content-type: text/plain; format=flowed; charset=UTF-8',
        '-a', 'From: %s' % email.utils.formataddr((myname, fromaddr))]
    if (cc_sysadmins):
        mailargs.append('-c')
        mailargs.append(FORMATTEDSYSADMINEMAIL)
    mailargs.append(email.utils.formataddr((user.name, user.email)))

    mail = Popen(mailargs, stdin = PIPE)
    _, _ = mail.communicate(body)
    return mail.returncode

def mailtosocadmins(society, subject, body, cc_sysadmins=False):
    """Send a mail to a ${SOC}-admins@srcf.net with the given subject
    and body, which should both be strings.  The society can be a
    Society object or a string, in which case it is interpreted as a
    society short name.  A KeyError is thrown if the string is not a
    valid short name.

    If the optional argument cc_sysadmins is set to True (default
    False), SYSADMINEMAIL is cc'ed in.

    From: if bm380-adm does 'sudo srcf-mailtosysadmins subject' then the
    from will be "Ben Millwood <bm380@srcf.net>" - i.e. take SUDO_USER (or
    getuid), strip -adm if present, add @srcf.net, lookup name and apply
    pretty_sysadmin_name.

    Note that this differs from e.g. the srcf-mailtouser script, which puts
    soc-srcf-admin in the From field (even though it *does* work out who you
    are, so it can sign emails as you).
    
    Content-type: text/plain; format=flowed; charset=UTF-8"""

    # Convert the short name to a Society object, if necessary
    if not isinstance(society, srcf.Society):
        society = srcf.get_society(society)

    sender = whoami()
    fromaddr = sender.pw_name.replace('-adm','') + '@srcf.net'
    myname = pretty_sysadmin_name(sender.pw_gecos)

    mailargs = ['/usr/bin/env', 'mail', '-s', subject,
        '-a', 'Content-type: text/plain; format=flowed; charset=UTF-8',
        '-a', 'From: %s' % email.utils.formataddr((myname, fromaddr))]
    if (cc_sysadmins):
        mailargs.append('-c')
        mailargs.append(FORMATTEDSYSADMINEMAIL)
    mailargs.append("%s-admins@srcf.net" % society.name)
    
    mail = Popen(mailargs, stdin = PIPE)
    _, _ = mail.communicate(body)
    return mail.returncode
