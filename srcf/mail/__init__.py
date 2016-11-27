import email.mime.text
import smtplib

from email.header import Header
from email.utils import formatdate, make_msgid
from email.utils import formataddr as original_formataddr

from srcf.misc import get_current_user


SYSADMINS = ('SRCF Sysadmins', 'soc-srcf-admin@lists.cam.ac.uk')
SUPPORT = ('SRCF Support', 'support@srcf.net')


def formataddr(pair):
    name, email = pair
    if name:
        name = Header(name, 'utf-8').encode()
    return original_formataddr((name, email))

def send_mail(recipient, subject, body,
              copy_sysadmins=True, reply_to_support=False, session=None):
    """
    Send `body` to `recipient`, which should be a (name, email) tuple,
    or a list of multiple tuples. Name may be None.
    """

    try:
        u = get_current_user(session=session)
    except (EnvironmentError, KeyError):
        sender = SYSADMINS
    else:
        sender = (u.name, u.crsid + '@srcf.net')

    if isinstance(recipient, tuple):
    	recipient = [recipient]

    message = email.mime.text.MIMEText(body, _charset='utf-8')
    message["Message-Id"] = make_msgid("srcf-mailto")
    message["Date"] = formatdate(localtime=True)
    message["From"] = formataddr(sender)
    message["To"] = ", ".join([formataddr(x) for x in recipient])
    message["Subject"] = subject
    if reply_to_support:
        message["Reply-To"] = formataddr(SUPPORT)
    else:
        message["Reply-To"] = formataddr(SYSADMINS)

    all_emails = [x[1] for x in recipient]
    if copy_sysadmins:
        all_emails.append(SYSADMINS[1])
        message["Cc"] = formataddr(SYSADMINS)

    s = smtplib.SMTP('localhost')
    s.sendmail(sender[1], all_emails, message.as_string())
    s.quit()

def mail_sysadmins(subject, body, session=None):
    """Mail `body` to the sysadmins"""
    send_mail(SYSADMINS, subject, body, copy_sysadmins=False, session=session)
