from __future__ import with_statement


SYSADMINLIST="/societies/sysadmins/admin/sysadminlist"
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


class Sysadmin(Member):
	"""A SRCF sysadminlist entry, containing metadata about a sysadmin.

	Userful additional fields:
		user
		"""

	def __init__(self,user):
		details = user.split("-")
		if details[1] != 'adm':
			raise ValueError(user)
		member = get_member(details[0])
		Member.__init__(
			self, 
			member.crsid, 
			member.surname, 
			member.firstname, 
			member.initals,
			member.email,
			member.status,
			member.joindate
		)
		self.name = "%s %s (Sysadmin Account)" % (member.firstname, member.surname)
		self.user = user

	def __new__(cls, user):
		return str.__new__(cls,user)

	def __str__(self):
		return self.user


class MemberSet(frozenset):
	"A set of SRCF members"

	def __str__(self):
		"Return pretty formatting of the set of usernames and CRSIDs"
		maxlen = 0
		outlines = []
		for user in self:
			maxlen = max(maxlen, len(user.name))
		for user in sorted(self):
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
		self.admins = MemberSet(get_socadmins(admins=admins))

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
	"""Return the Member object for the given crsid."""
	try:
		members = get_members(crsids=[crsid])
		member = members.next()
		members.close()
		return member
	except StopIteration:
		raise KeyError(crsid)


def get_users(crsids=None):
	"""Return a generator for Member objects representing those SRCF memberlist
	   entries for which the status is recorded as 'user'.

	   NB: does not treat honorary members as users.  In practice, they may be."""
	for member in get_members(crsids):
		if member.status == "user":
			yield member

def get_user(crsid):
	"""Return the Member object for the given user."""
	try:
		users = get_users(crsids=[crsid])
		user = members.next()
		users.close()
		return user
	except StopIteration:
		raise KeyError(crsid)

def get_sysadmins(users=None):
	"""Return a generator representing the complete list of SRCF sysadmins, or 
	   the entry for the given sysadmin"""
	get_all = (users is None)
	with open(SYSADMINLIST, 'r') as f:
		for line in f:
			fields = line.strip().split(":")
			if get_all or fields[0] in users:
				# Return the member entry for the sysadmin
				yield Sysadmin(fields[0])

def get_sysadmin(user):
	"""Return the Sysadmin object for the given user."""
	try:
		admins = get_sysadmins(users=[user])
		admin = admins.next()
		admins.close()
		return admin
	except StopIteration:
		raise KeyError(user)


def get_socadmins(admins=None):
	"""Return the list of society admins"""
	for member in get_members(crsids=admins):
		yield member
	for admin in get_sysadmins(users=admins):
		yield (admin.member)


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

