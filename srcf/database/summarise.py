from __future__ import unicode_literals

from . import Member, Society

def summarise_member(member):
    """
    Returns a str summarising `member`

    Contains the member's details (name, crsid, email, status, join date,
    societies) in human-readable form.
    """

    if member.societies:
        socs = "Societies:\n" + \
               _pretty_name_list((s.description, s.society)
                                 for s in member.societies)
    else:
        socs = "No society memberships."

    joined = member.joined.strftime("%Y/%m")

    return '%s (%s)\n%s\nMember: %s\nUser: %s\nJoined: %s\n%s' % (
            member.name, member.crsid,
            member.email,
            member.member, member.user,
            joined,
            socs)

def summarise_society(society):
    """Returns a str summarising `society`"""
    if society.admins:
        admins = "Admins:\n" + \
                 _pretty_name_list((u.name, u.crsid) for u in society.admins)
    else:
        admins = 'Orphaned (no admins).'

    joined = society.joined.strftime("%Y/%m")

    return '%s: %s\nJoined: %s\n%s' % (
        society.society, society.description, joined, admins)

def summarise(thing):
    if isinstance(thing, Society):
        return summarise_society(thing)

    if isinstance(thing, Member):
        return summarise_member(thing)

    try:
        return _pretty_thing_list(thing)
    except TypeError:
        pass

    return str(thing)

def _pretty_thing_list(things):
    def f(thing):
        if isinstance(thing, Society):
            return thing.description, thing.society
        elif isinstance(thing, Member):
            return thing.name, thing.crsid
        else:
            raise TypeError("things should contain Societies and Members")

    return _pretty_name_list(map(f, things))

def _pretty_name_list(names):
	"""Given a list of (a,b) pairs, output aligned columns with the
	items of the second column parenthised.

	Used for pretty-printing e.g. name (crsid) or socname (socid) lists.
	"""
	# might be given an iterator, need a list, might as well sort it
	nameList = sorted(names)
	try:
		maxlen = max(len(col1) for (col1,col2) in nameList)
	except ValueError: # empty sequence
		return ''

	return '\n'.join('  %-*s  (%s)' % (maxlen, col1, col2)
		for (col1, col2) in nameList)
