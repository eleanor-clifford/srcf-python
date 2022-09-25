import email.mime.text
import smtplib
import warnings

from email.header import Header
from email.utils import formatdate, make_msgid
from email.utils import formataddr as original_formataddr

from srcf.misc import get_current_context


SYSADMINS = ('SRCF Sysadmins', 'soc-srcf-admin@lists.cam.ac.uk')
SUPPORT = ('SRCF Support', 'support@srcf.net')


def formataddr(pair):
    name, email = pair
    if name:
        name = Header(name, 'utf-8').encode()
    return original_formataddr((name, email))


def send_mail(recipient, subject, body, copy_sysadmins=True,
              reply_to=SYSADMINS, reply_to_support=False, session=None):
    """
    Send `body` to `recipient`, which should be a (name, email) tuple,
    or a list of multiple tuples. Name may be None.
    """

    try:
        user, admin = get_current_context(session=session)
    except (EnvironmentError, KeyError):
        sender = SYSADMINS
    else:
        sender = (user.name, '{}{}@srcf.net'.format(user.crsid, '-admin' if admin else ''))

    if isinstance(recipient, tuple):
        recipient = [recipient]

    message = email.mime.text.MIMEText(body, _charset='utf-8')
    message["Message-Id"] = make_msgid("srcf-mailto")
    message["Date"] = formatdate(localtime=True)
    message["From"] = formataddr(sender)
    message["To"] = ", ".join([formataddr(x) for x in recipient])
    message["Subject"] = subject
    if reply_to_support:
        warnings.warn("reply_to_support=True is deprecated, use "
                      "reply_to=srcf.mail.SUPPORT instead", DeprecationWarning)
        message["Reply-To"] = formataddr(SUPPORT)
    elif reply_to:
        message["Reply-To"] = formataddr(reply_to)

    all_emails = [x[1] for x in recipient]
    if copy_sysadmins:
        all_emails.append(SYSADMINS[1])
        message["Cc"] = formataddr(SYSADMINS)

    s = smtplib.SMTP('localhost')
    s.sendmail(sender[1], all_emails, message.as_string())
    s.quit()


def mail_sysadmins(subject, body, reply_to=None, session=None):
    """Mail `body` to the sysadmins"""
    send_mail(SYSADMINS, subject, body, copy_sysadmins=False,
              reply_to=reply_to, session=session)
