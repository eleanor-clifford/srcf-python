from os import getenv, getuid
from pwd import getpwnam, getpwuid
from subprocess import Popen, PIPE

# pseudoconstant
SYSADMINEMAIL = 'soc-srcf-admin@lists.cam.ac.uk'

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
    from will be "Ben Millwood <bm380@srcf.net>" – i.e. take SUDO_USER (or
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
        '-a', 'From: {0} <{1}>'.format(myname, fromaddr),
        'SRCF sysadmins <{0}>'.format(SYSADMINEMAIL)],
        stdin = PIPE)
    mail.stdin.write(body)
    mail.stdin.close()
    return mail.wait()
