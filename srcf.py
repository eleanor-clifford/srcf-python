from __future__ import with_statement


MEMBERLIST="/societies/sysadmins/admin/memberlist"
SOCLIST="/societies/sysadmins/admin/soclist"


class _StringyObject(object):
	"""An object which pretends to be a string as far as equality and hashing is
	   concerned.  Not intended to be used directly.  Subclasses should implement
	   __str__ (and it should be static for a given object: no mutability please!)."""

	def __eq__(self, other):
		return str(self) == str(other)

	def __ne__(self, other):
		return str(self) <> str(other)

	def __hash__(self):
		return hash(str(self))


class Member(_StringyObject):
	"A SRCF memberlist entry, containing metadata about a member"

	def __init__(self, crsid, surname, firstname, initials, email, status, joindate):
		self.crsid = crsid
		self.surname = surname
		self.firstname = firstname
		self.name = "%s %s" % (firstname, surname)
		self.initials = initials
		self.email = email
		self.status = status
		self.joindate = joindate

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


class Society(_StringyObject):
	"A SRCF soclist entry, containing metadata about a society account"

	def __init__(self, name, description, admins, joindate):
		self.name = name
		self.description = description
		self.joindate = joindate
		self.admin_crsids = []
		for admin in admins:
			self.admin_crsids += list(get_members(crsid=admin))
		self.admins = MemberSet(self.admin_crsids)

	def __str__(self):
		return self.name


def get_members(crsid=None):
	"""Return a generator representing the complete SRCF memberlist, or just the
	   memberlist entry for the given CRSID"""
	with open(MEMBERLIST, 'r') as f:
		for line in f:
			fields = line.strip().split(":")
			if crsid == None or crsid == fields[0]:
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
	try:
		members = get_members(crsid)
		member = members.next()
		members.close()
		return member
	except StopIteration:
		raise KeyError(crsid)


def get_users():
	"""Return a generator representing those SRCF memberlist entries for which
	   the status is recorded as 'user'.

	   NB: does not treat honorary members as users.  In practice, they may be."""
	for member in get_members():
		if member.status == "user":
			yield member


def get_societies(name=None):
	"""Return a generator representing the complete SRCF soclist, or just the
	   soclist entry for the given society short name."""
	with open(SOCLIST, 'r') as f:
		for line in f:
			fields = line.strip().split(":")
			if name == None or name == fields[0]:
				yield Society(
						name=fields[0],
						description=fields[1],
						admins=MemberSet(fields[2].split(",")),
						joindate=fields[3]
					)

