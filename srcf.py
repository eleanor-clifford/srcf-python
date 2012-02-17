from __future__ import with_statement


MEMBERLIST="/societies/sysadmins/admin/memberlist"
SOCLIST="/societies/sysadmins/admin/soclist"


class Member(str):
	"""A SRCF memberlist entry, containing metadata about a member.
	
	   Useful fields:
	       crsid ..... e.g. "spqr2"
	       surname
	       firstname
	       name ...... firstname surname
	       initials .. "S.P.Q."
	       email
	       status .... "member", "user", "honorary"...
	       joindate .. "1970/01"
	"""

	def __init__(self, crsid, surname, firstname, initials, email, status, joindate):
		self.crsid = crsid
		self.surname = surname
		self.firstname = firstname
		self.name = "%s %s" % (firstname, surname)
		self.initials = initials
		self.email = email
		self.status = status
		self.joindate = joindate

	def __new__(cls, crsid, surname, firstname, initials, email, status, joindate):
		return str.__new__(cls, crsid)

	def __str__(self):
		return self.crsid


class MemberSet(frozenset):
	"A set of SRCF members"

	def __str__(self):
		"Return pretty formatting of the set of usernames and CRSIDs"
		maxlen = 0
		outlines = []
		for user in self:
			maxlen = max(maxlen, len(user.name))
		for user in self:
			outlines += ["  %s%s  (%s)" % (user.name, " "*(maxlen-len(user.name)), user.crsid)]
		return "\n".join(outlines)


class Society(str):
	"""A SRCF soclist entry, containing metadata about a society account.

	   Useful fields:
	       name .......... "foosoc"
	       description ... "CU Foo Society"
	       joindate ...... "1970/01"
	       admins ........ a MemberSet object
	"""

	def __init__(self, name, description, admins, joindate):
		self.name = name
		self.description = description
		self.joindate = joindate
		self.admins = MemberSet(get_members(crsids=admins))

	def __new__(cls, name, description, admins, joindate):
		return str.__new__(cls, name)

	def __str__(self):
		return self.name


def get_members(crsids=None):
	"""Return a generator representing the complete SRCF memberlist, or just the
	   memberlist entry for the given CRSID"""
	get_all = (crsids is None)
	with open(MEMBERLIST, 'r') as f:
		for line in f:
			fields = line.strip().split(":")
			if get_all or fields[0] in crsids:
				yield Member(
						crsid=fields[0],
						surname=fields[1],
						firstname=fields[2],
						initials=fields[3],
						email=fields[4],
						status=fields[5],
						joindate=fields[6]
					)


def get_member(crsid):
	"Return the Member object for the given crsid."
	try:
		members = get_members(crsids=[crsid])
		member = members.next()
		members.close()
		return member
	except StopIteration:
		raise KeyError(crsid)


def get_users():
	"""Return a generator for Member objects representing those SRCF memberlist
	   entries for which the status is recorded as 'user'.

	   NB: does not treat honorary members as users.  In practice, they may be."""
	for member in get_members():
		if member.status == "user":
			yield member


def get_societies(name=None, admin=None):
	"""Return a generator for Society objects representing the complete SRCF soclist,
	   or just the soclist entry for the given society short name, or the soclist
	   entries for societies with the given administrator."""
	with open(SOCLIST, 'r') as f:
		for line in f:
			fields = line.strip().split(":")
			if name is None or name == fields[0]:
				admins = MemberSet(fields[2].split(","))
				if admin is None or admin in admins:
					yield Society(
							name=fields[0],
							description=fields[1],
							admins=admins,
							joindate=fields[3]
						)


def get_society(name):
	"Return the Society object for the given society short name."
	try:
		socs = get_societies(name)
		soc = socs.next()
		socs.close()
		return soc
	except StopIteration:
		raise KeyError(name)

