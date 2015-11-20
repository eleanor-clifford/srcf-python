import warnings

from . import Member, Society, Session


_global_session = None
_auto_create_global_session = True

# We can't create temporary session objects since this breaks lazy loading.
# When the session goes out of scope, the Member/Society objects seem to lose
# it (? weakrefs) so can't lazy load (.admins, .societies)
def _sess(session=None):
    global _global_session, _auto_create_global_session
    if session:
        return session
    elif _global_session:
        return _global_session
    elif _auto_create_global_session:
        _global_session = Session()
        return _global_session
    else:
        raise RuntimeError("Auto global session creation is disabled")

def disable_automatic_session(and_use_this_one_instead=None):
    global _global_session, _auto_create_global_session

    if _global_session:
        raise RuntimeError("Too slow(!), the global session already exists")

    _global_session = and_use_this_one_instead
    _auto_create_global_session = False


def list_members(session=None):
    return _sess(session).query(Member)

def get_member(crsid, session=None):
    m = _sess(session).query(Member).get(crsid)
    if m:
        return m
    else:
        raise KeyError(crsid)

def list_users(session=None):
    return _sess(session).query(Member).filter(Member.user==True)

def get_user(crsid, session=None):
    m = get_member(crsid, session)
    if not m.user:
        raise KeyError(crsid)
    else:
        return m

def list_societies(session=None):
    return _sess(session).query(Society)

def get_society(name, session=None):
    s = _sess(session).query(Society).get(name)
    if s:
        return s
    else:
        raise KeyError(name)

def dict_users(session = None):
    return {m.crsid: m for m in _sess(session).query(Member).filter(Member.user == True)}

def dict_members(session=None):
    return {m.crsid: m for m in _sess(session).query(Member)}

def dict_societies(session=None):
    return {m.society: m for m in _sess(session).query(Society)}
