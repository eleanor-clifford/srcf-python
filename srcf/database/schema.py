from __future__ import print_function, unicode_literals

import os
import warnings
import pwd

import six

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum
from sqlalchemy import event
#from sqlalchemy.dialects.postgresql import HSTORE
from .hstore import HSTORE
from sqlalchemy.schema import Table, FetchedValue, CheckConstraint, \
        ForeignKey, DDL, PrimaryKeyConstraint
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property

from .compat import MemberCompat, SocietyCompat, AdminsSetCompat


__all__ = ["Member", "Society", "PendingAdmin",
           "POSTGRES_USER", "RESTRICTED"]

if __name__ == "__main__":
    # we're dumping the schema---we want the whole thing
    POSTGRES_USER = "root"
    RESTRICTED = False
    R_CAN_SEE = {
        "notes": True,
        "log": True,
        "danger": True,
        "pending-admins": True,
        "jobs": True
    }
else:
    # Should we make the notes & danger flags, and pending-admins
    # tables available?

    # These postgres roles have special permissions / are mentioned
    # in the schema. Everyone else should connect as 'nobody'
    schema_users = ("root", "srcf-admin")

    # When connecting over a unix socket, postgres uses `getpeereid`
    # for authentication; this is the number that matters:
    euid_name = pwd.getpwuid(os.geteuid()).pw_name
    if euid_name in schema_users:
        POSTGRES_USER = euid_name
    else:
        POSTGRES_USER = "nobody"
    is_root = POSTGRES_USER == "root"
    is_webapp = POSTGRES_USER == "srcf-admin"

    RESTRICTED = not is_root
    R_CAN_SEE = {
        "notes": is_root,
        "log": is_root,
        "danger": is_root or is_webapp,
        "pending-admins": is_root or is_webapp,
        "jobs": is_root or is_webapp
    }


CRSID_TYPE = String(7)
SOCIETY_TYPE = String(16)

Base = declarative_base()


class Member(Base, MemberCompat):
    __tablename__ = 'members'

    crsid = Column(CRSID_TYPE, CheckConstraint('crsid = lower(crsid)'),
                   primary_key=True)
    surname = Column(String(100))
    preferred_name = Column(String(100))
    email = Column(String(100), CheckConstraint("email ~ E'@'"), unique=True)
    # FetchedValue: these columns are set by triggers (see below)
    joined = Column(DateTime(timezone=True), FetchedValue())
    modified = Column(DateTime(timezone=True), FetchedValue())
    member = Column(Boolean, nullable=False)
    user = Column(Boolean, nullable=False)
    if R_CAN_SEE["danger"]:
        danger = Column(Boolean, nullable=False, server_default='f')
    if R_CAN_SEE["notes"]:
        notes = Column(Text, nullable=False, server_default='')

    __table_args__ = (
        CheckConstraint("""
            (NOT member OR (surname IS NOT NULL AND
                            preferred_name IS NOT NULL AND
                            email IS NOT NULL AND
                            joined IS NOT NULL))
        """, name="members_must_have_details"),
        CheckConstraint('member OR NOT "user"', name="users_must_be_members"),
    )

    def __str__(self):
        return self.crsid

    def __repr__(self):
        m = ' member' if self.member else ' ex-member'
        u = ' user' if self.user else ''
        flags = m + u
        r = '<Member {0} {1} {2}{3}>'\
            .format(self.crsid, self.name, self.email, flags)
        if not six.PY3:
            r = r.encode("utf8")
        return r

    def __eq__(self, other):
        if not isinstance(other, Member):
            return False
        else:
            return self.crsid == other.crsid

    def __hash__(self):
        return hash(self.crsid)

    @hybrid_property
    def name(self):
        """Joins :attr:`preferred_name` and :attr:`surname`"""
        return self.preferred_name + " " + self.surname


society_admins = Table(
    'society_admins', Base.metadata,
    Column('crsid', CRSID_TYPE,
           ForeignKey('members.crsid'), primary_key=True),
    Column('society', SOCIETY_TYPE,
           ForeignKey('societies.society'), primary_key=True),
)

class Society(Base, SocietyCompat):
    __tablename__ = "societies"

    society = Column(SOCIETY_TYPE, CheckConstraint('society = lower(society)'),
                     primary_key=True)
    description = Column(String(100), nullable=False)
    joined = Column(DateTime(timezone=True), FetchedValue())
    modified = Column(DateTime(timezone=True), FetchedValue())
    if R_CAN_SEE["danger"]:
        danger = Column(Boolean, nullable=False, server_default='f')
    if R_CAN_SEE["notes"]:
        notes = Column(Text, nullable=False, server_default='')

    admins = relationship("Member",
            secondary=society_admins, collection_class=AdminsSetCompat,
            backref=backref("societies", collection_class=set))

    if R_CAN_SEE["pending-admins"]:
        pending_admins = relationship("PendingAdmin",
                backref=backref("society"))

    def __str__(self):
        return self.society

    def __repr__(self):
        orphaned = '' if self.admins else ' orphaned'
        return '<Society {0}{1}>'.format(self.society, orphaned)

    def __eq__(self, other):
        if not isinstance(other, Society):
            return False
        else:
            return self.society == other.society

    def __hash__(self):
        return hash(self.society)

    def __contains__(self, other):
        if isinstance(other, Member):
            return other in self.admins
        elif isinstance(other, six.string_types):
            return other in self.admin_crsids
        else:
            return False

    @property
    def admin_crsids(self):
        """:attr:`admins`, as a set of strings (crsids)"""
        return frozenset(m.crsid for m in self.admins)

    @hybrid_property
    def email(self):
        """society-admins@srcf.net address"""
        return self.society + "-admins@srcf.net"


if R_CAN_SEE["pending-admins"]:
    class PendingAdmin(Base):
        __tablename__ = "pending_society_admins"

        # There is no ForeignKey constraint here because this table exists to
        # reference users that don't exist yet.
        crsid = Column(CRSID_TYPE, CheckConstraint('crsid = lower(crsid)'),
                       primary_key=True)
        society_society = Column(SOCIETY_TYPE,
                                 ForeignKey('societies.society'),
                                 name="society",
                                 primary_key=True)

        def __str__(self):
            return "{0} {1}".format(self.crsid, self.society.society)

        def __repr__(self):
            return '<PendingAdmin {0} {1}>'\
                        .format(self.crsid, self.society.society)
else:
    PendingAdmin = None


if R_CAN_SEE["log"]:
    LogLevel = Enum('debug', 'info', 'warning', 'error', 'critical',
                    name='log_level')

    class LogRecord(Base):
        __tablename__ = "log"

        record_id = Column(Integer, primary_key=True)
        created = Column(DateTime(timezone=True), FetchedValue())
        level = Column(LogLevel)
        logger = Column(Text)
        message = Column(Text)

        # "Tag" rows with the member/society they pertain to, so that relevant
        # log lines may be quickly retrieved
        crsid = Column(CRSID_TYPE, ForeignKey('members.crsid'))
        society = Column(SOCIETY_TYPE, ForeignKey('societies.society'))

else:
    LogLevel = LogRecord = None


if R_CAN_SEE["jobs"]:
    JobState = Enum('unapproved', 'queued', 'running', 'done', 'failed',
                    name='job_state')
    LogType = Enum('approved', 'rejected', 'progress', 'done', 'failed',
                   name='log_type')

    event.listen(
        Base.metadata,
        "before_create",
        DDL("CREATE EXTENSION hstore")
    )

    class Job(Base):
        __tablename__ = 'jobs'
        job_id = Column(Integer, primary_key=True)
        owner_crsid = Column(CRSID_TYPE, ForeignKey("members.crsid"))
        owner = relationship("Member")
        state = Column(JobState, nullable=False, server_default='unapproved')
        state_message = Column(Text)
        type = Column(String(100), nullable=False)
        args = Column(HSTORE, nullable=False)

    class JobLog(Base):
        __tablename__ = 'job_log'
        log_id = Column(Integer, primary_key=True)
        job_id = Column(Integer, ForeignKey("jobs.job_id"))
        time = Column(DateTime)
        type = Column(LogType)
        message = Column(Text)

else:
    JobState = Job = None


def dump_schema():
    from sqlalchemy import create_engine
    import os.path

    directory = os.path.dirname(__file__)
    with open(os.path.join(directory, "triggers.sql")) as f:
        triggers = f.read()
    with open(os.path.join(directory, "grants.sql")) as f:
        grants = f.read()

    event.listen(
        Base.metadata,
        "after_create",
        DDL(triggers)
    )

    event.listen(
        Base.metadata,
        "after_create",
        DDL(grants)
    )

    def dump(sql, *multiparams, **params):
        print(sql.compile(dialect=engine.dialect), ";")
    engine = create_engine('postgresql://', strategy='mock', executor=dump)
    Base.metadata.create_all(engine, checkfirst=False)

if __name__ == "__main__":
    dump_schema()
