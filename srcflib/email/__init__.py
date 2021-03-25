"""
Notification email machinery, for tasks to send credentials and instructions to users.

Email templates placed inside the `templates` directory of this module should:

- extend from `layout`
- provide `subject` and `body` blocks
"""

from enum import Enum
import os.path

from jinja2 import Environment, FileSystemLoader

from sqlalchemy.orm import Session as SQLASession

from srcf.database import Member, Society
from srcf.mail import send_mail

from ..plumbing.common import Owner, owner_desc, owner_name, owner_website


ENV = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
                  trim_blocks=True, lstrip_blocks=True)

ENV.filters.update({"is_member": lambda mem: isinstance(mem, Member),
                    "is_society": lambda soc: isinstance(soc, Society),
                    "owner_name": owner_name,
                    "owner_desc": owner_desc,
                    "owner_website": owner_website})


CURRENT_WRAPPER = None


class Layout(Enum):
    """
    Base layout template to be inherited by an email-specific template.
    """

    SUBJECT = "/common/subject.j2"
    """
    Subject line of the email.
    """
    BODY = "/common/body.j2"
    """
    Main content of the email.
    """


class EmailWrapper:
    """
    Context manager for email sending, used to augment emails with additional metadata.
    """

    def __init__(self, subject: str = None, body: str = None, context: dict = None):
        self._layouts = {Layout.SUBJECT: subject, Layout.BODY: body}
        self._context = context

    def render(self, template: str, layout: Layout, target: Owner, context: dict = None) -> str:
        """
        Render an email template with Jinja using the provided context.
        """
        context = dict(context or (), layout=layout.value, target=target)
        out = ENV.get_template(template).render(context)
        custom = self._layouts.get(layout)
        if custom:
            if self._context:
                context.update(self._context)
            out = custom.format(out, **context)
        if layout == Layout.SUBJECT:
            out = " ".join(out.split())
        return out

    def __enter__(self):
        global CURRENT_WRAPPER
        if CURRENT_WRAPPER:
            raise RuntimeError("Another context is already active")
        CURRENT_WRAPPER = self

    def __exit__(self, exception_type, exception_value, traceback):
        global CURRENT_WRAPPER
        CURRENT_WRAPPER = None


DEFAULT_WRAPPER = EmailWrapper(subject="[SRCF] {}")


def send(target: Owner, template: str, context: dict = None, session: SQLASession = None):
    """
    Render and send an email to the target member or society.
    """
    wrapper = CURRENT_WRAPPER or DEFAULT_WRAPPER
    subject = wrapper.render(template, Layout.SUBJECT, target, context)
    body = wrapper.render(template, Layout.BODY, target, context)
    recipient = (owner_desc(target, True), target.email)
    send_mail(recipient, subject, body, copy_sysadmins=False, session=session)
