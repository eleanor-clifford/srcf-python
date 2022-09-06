"""
Notification email machinery, for tasks to send credentials and instructions to users.

Email templates placed inside the `templates` directory of this module should:

- extend from `layout` (a template variable, not a string)
- provide `subject` and `body` blocks

The following Jinja2 filters are available to templates:

- `owner_name`, `owner_desc` and `owner_website` for common account attributes
- `is_member` and `is_society` for testing owner types
"""

from enum import Enum
import logging
import os.path
from typing import Any, Mapping, Optional, Tuple, Union

from jinja2 import Environment, FileSystemLoader

from sqlalchemy.orm import Session as SQLASession

from srcf.database import Member, Society
from srcf.mail import send_mail

from ..plumbing.common import Owner, owner_desc, owner_name, owner_website, Result, State, Unset


LOG = logging.getLogger(__name__)

ENV = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
                  trim_blocks=True, lstrip_blocks=True)

ENV.filters.update({"is_member": lambda mem: isinstance(mem, Member),
                    "is_society": lambda soc: isinstance(soc, Society),
                    "owner_name": owner_name,
                    "owner_desc": owner_desc,
                    "owner_website": owner_website})

CURRENT_WRAPPER = None

Recipient = Union[Owner, Tuple[str, str], str]
"""
Target recipient of an email; can be either a `Member` or `Society`, a `(name, email)` pair, or a
bare email address.
"""


class Layout(Enum):
    """
    Base layout template to be inherited by an email-specific template.
    """

    subject = 1
    """
    Subject line of the email.
    """
    body = 2
    """
    Main content of the email.
    """


def _make_recipient(target: Recipient) -> Tuple[Optional[str], str]:
    if isinstance(target, (Member, Society)):
        return (owner_desc(target, True), target.email)
    elif isinstance(target, str):
        return (None, target)
    else:
        return target


class EmailWrapper:
    """
    Context manager for email sending, used to augment emails with additional metadata.
    """

    def __init__(self, prefix: Optional[str] = "[SRCF]", footer: Optional[str] = None):
        self._prefix = prefix
        self._footer = footer

    def render(self, template: str, layout: Layout, target: Optional[Owner], recipient: Recipient,
               extra_context: Optional[Mapping[str, Any]] = None) -> str:
        """
        Render an email template with Jinja using the provided context.
        """
        context = {"layout": "/layouts/{}.j2".format(layout.name), "target": target,
                   "prefix": self._prefix, "footer": self._footer}
        if extra_context:
            context.update(extra_context)
        out = ENV.get_template(template).render(context)
        if layout == Layout.subject:
            out = " ".join(out.split())
        return out

    def send(self, target: Recipient, template: str, context: Optional[Mapping[str, Any]] = None,
             session: Optional[SQLASession] = None) -> Result[Unset]:
        """
        Render and send an email to the target member or society, or a specific email address.
        """
        owner = target if isinstance(target, (Member, Society)) else None
        subject = self.render(template, Layout.subject, owner, target, context)
        body = self.render(template, Layout.body, owner, context)
        recipient = _make_recipient(target)
        LOG.debug("Sending email %r to %s", template, recipient)
        send_mail(recipient, subject, body, copy_sysadmins=False, session=session)
        return Result(State.success)

    def __enter__(self):
        global CURRENT_WRAPPER
        if CURRENT_WRAPPER:
            raise RuntimeError("Another context is already active")
        CURRENT_WRAPPER = self

    def __exit__(self, exception_type, exception_value, traceback):
        global CURRENT_WRAPPER
        CURRENT_WRAPPER = None


DEFAULT_WRAPPER = EmailWrapper()


class SuppressEmails(EmailWrapper):
    """
    When being used as a context, no emails will be sent by tasks.
    """

    def send(self, target: Recipient, template: str, context: Optional[Mapping[str, Any]] = None,
             session: Optional[SQLASession] = None) -> Result[Unset]:
        recipient = _make_recipient(target)
        LOG.debug("Suppressing email %r to %r", template, recipient)
        return Result(State.unchanged)


def send(target: Recipient, template: str, context: Optional[Mapping[str, Any]] = None,
         session: Optional[SQLASession] = None) -> Result[Unset]:
    """
    Render and send an email using the currently-enabled email wrapper -- see `EmailWrapper.send`.
    """
    wrapper = CURRENT_WRAPPER or DEFAULT_WRAPPER
    return wrapper.send(target, template, context, session)
