import srcf
import srcf.mail
import srcf.database

SYSADMINEMAIL = srcf.mail.SYSADMINS[1]


def mailtosysadmins(subject, body):
    """Send a mail to SYSADMINEMAIL with the given subject and body,
    which should both be strings."""

    srcf.mail.send_mail(srcf.mail.SYSADMINS, subject, body,
                        copy_sysadmins=False)


def mailtouser(user, subject, body, cc_sysadmins=False):
    """Send a mail to a user's registered email address with the given
    subject and body, which should both be strings.  The user can be a
    Member object or a string, in which case it is interpreted as a
    CRSid.  A KeyError is thrown if the CRSid is not that of a valid
    user.

    If the optional argument cc_sysadmins is set to True (default
    False), SYSADMINEMAIL is cc'ed in.
    """

    # Convert the CRSid to a Member object, if necessary
    if not isinstance(user, srcf.database.Member):
        user = srcf.get_user(user)

    recipient = (user.name, user.email)
    srcf.mail.send_mail(recipient, subject, body, copy_sysadmins=cc_sysadmins)


def mailtosocadmins(society, subject, body, cc_sysadmins=False):
    """Send a mail to a ${SOC}-admins@srcf.net with the given subject
    and body, which should both be strings.  The society can be a
    Society object or a string, in which case it is interpreted as a
    society short name.  A KeyError is thrown if the string is not a
    valid short name.

    If the optional argument cc_sysadmins is set to True (default
    False), SYSADMINEMAIL is cc'ed in.
    """

    # Convert the short name to a Society object, if necessary
    if not isinstance(society, srcf.database.Society):
        society = srcf.get_society(society)

    recipient = (society.description + " Admins", society.email)
    srcf.mail.send_mail(recipient, subject, body, copy_sysadmins=cc_sysadmins)
