from contextlib import contextmanager

from . import Member, Society, Session


_global_session = None
_auto_create_global_session = True

# We can't create temporary session objects since this breaks lazy loading.
# When the session goes out of scope, the Member/Society objects seem to lose
# it (? weakrefs) so can't lazy load (.admins, .societies)
#
# We only do read-only actions here, and don't want to leave a transaction
# open indefinitely, so we use autocommit.  Note documented caveats at
# https://docs.sqlalchemy.org/en/13/orm/session_transaction.html#autocommit-mode
# -- mas90 asserts that our use case here falls under "framework integrations
# that wish to control specifically when the 'begin' state occurs".
#
# Because we use autocommit, we REALLY OUGHT TO explicitly start transactions
# for EVERY query (and yes, it's OK to do so even if we're already in a
# transaction in an external session -- SQLAlchemy supports nested transactions).


@contextmanager
def _sess(session=None):
    global _global_session, _auto_create_global_session
    if session:
        with session.begin(nested=session.is_active):
            yield session
    elif _global_session:
        with _global_session.begin(nested=_global_session.is_active):
            yield _global_session
    elif _auto_create_global_session:
        _global_session = Session(autocommit=True)
        with _global_session.begin(nested=_global_session.is_active):
            yield _global_session
    else:
        raise RuntimeError("Auto global session creation is disabled")


def disable_automatic_session(and_use_this_one_instead=None):
    global _global_session, _auto_create_global_session

    if _global_session:
        raise RuntimeError("Too slow(!), the global session already exists")

    _global_session = and_use_this_one_instead
    _auto_create_global_session = False


def list_members(session=None):
    with _sess(session) as sess:
        return sess.query(Member)


def get_member(crsid, session=None):
    with _sess(session) as sess:
        m = sess.query(Member).get(crsid)
        if m:
            return m
        else:
            raise KeyError(crsid)


def list_users(session=None):
    with _sess(session) as sess:
        return sess.query(Member).filter(Member.user == True)


def get_user(crsid, session=None):
    m = get_member(crsid, session)
    if not m.user:
        raise KeyError(crsid)
    else:
        return m


def list_societies(session=None):
    with _sess(session) as sess:
        return sess.query(Society)


def get_society(name, session=None):
    with _sess(session) as sess:
        s = sess.query(Society).get(name)
        if s:
            return s
        else:
            raise KeyError(name)


def get_member_or_society(name, session=None):
    try:
        return get_member(name, session)
    except KeyError:
        return get_society(name, session)


def dict_users(session=None):
    with _sess(session) as sess:
        return {m.crsid: m for m in sess.query(Member).filter(Member.user == True)}


def dict_members(session=None):
    with _sess(session) as sess:
        return {m.crsid: m for m in sess.query(Member)}


def dict_societies(session=None):
    with _sess(session) as sess:
        return {m.society: m for m in sess.query(Society)}
