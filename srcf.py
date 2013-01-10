import random # for pwgen

MEMBERLIST="/societies/sysadmins/admin/memberlist"
SOCLIST="/societies/sysadmins/admin/soclist"

__all__ = [
	'MEMBERLIST', 'SOCLIST',
	'Member', 'MemberSet',
	'Society', 'SocietySet',
	'get_members', 'get_member',
	'get_users', 'get_user',
	'get_societies', 'get_society',
	'members', 'members_and_socs', 'societies',
	'pwgen'
	]


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

	   Useful methods:
	       socs():
	          returns a SocietySet object of societies this member
	          administrates.
	       summary():
	          returns a human-readable summary of member details.
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

	def __repr__(self):
		return 'Member' + repr((self.crsid, self.surname, self.firstname,
			self.initials, self.email, self.status, self.joindate))

	def __str__(self):
		return self.crsid

	def socs(self, socs = None):
		"""member.socs([soclist]): returns a SocietySet object listing
		the societies this member administrates:
		   - if there is a cached result, that is returned
		   - otherwise, if soclist is provided, scans through it for socs
		     such that 'self in soc' returns true
		   - otherwise, reads the soclist and uses that."""
		try:
			return self.soc_set
		except AttributeError:
			if socs is None:
				socs = get_societies(admin = self)
			self.soc_set = SocietySet(soc for soc in socs if self in soc)
			return self.soc_set
	
	def summary(self):
		"""member.summary(): returns a str that summarises the member
		details (name, crsid, email, status, join date, societies) in
		human-readable form."""
		socs = self.socs()
		return '%s (%s)\n%s\nStatus: %s\nJoined: %s\nSocieties:\n%s' % (
				self.name, self.crsid,
				self.email,
				self.status,
				self.joindate,
				socs if socs else '  No society memberships.')


class MemberSet(frozenset):
	"""A set for Member objects that has a pretty-printing __str__ method."""

	def __str__(self):
		return pretty_name_list(
			(user.name, user.crsid) for user in self)


class Society(str):
	"""A SRCF soclist entry, containing metadata about a society account.

	   Useful fields:
	       name .......... "foosoc"
	       description ... "CU Foo Society"
	       joindate ...... "1970/01"
	       admin_crsids .. a frozenset of strings

	   Useful methods:
	       admins(): returns a MemberSet corresponding to admin_crsids
	       summary(): returns a human-readable summary of society details.
	"""

	def __init__(self, name, description, admin_crsids, joindate):
		self.name = name
		self.description = description
		self.joindate = joindate
		self.admin_crsids = admin_crsids

	def __new__(cls, name, description, admin_crsids, joindate):
		return str.__new__(cls, name)

	def __contains__(self, other):
		return other in self.admin_crsids

	def __repr__(self):
		return 'Society' + repr((self.name, self.description,
			self.admin_crsids, self.joindate))

	def __str__(self):
		return self.name

	def admins(self, memberdict = None):
		"""soc.admins([memberdict]): returns a MemberSet object listing
		the administrators of the society:
		   - if there is a cached result, that is returned
		   - otherwise, if memberdict is provided, looks up
		     self.admin_crsids in it
		   - otherwise, looks up self.admin_crsids in the member list.
		Raises KeyError(admin) if the admin does not exist."""
		try:
			return self.admin_set
		except AttributeError:
			if memberdict is not None:
				self.admin_set = MemberSet(memberdict[mem]
					for mem in self.admin_crsids)
			else:
				self.admin_set = MemberSet(
					get_members(crsids=self.admin_crsids))

				# produce KeyError if lookup failed: this for will loop
				# at most once
				for admin in self.admin_crsids - self.admin_set:
					raise KeyError(admin)
			return self.admin_set
	
	def summary(self):
		admins = self.admins()
		return '%s: %s\nJoined: %s\n%s' % (
			self.name, self.description,
			self.joindate,
			'Admins:\n%s' % admins if admins else 'Orphaned (no admins).')


class SocietySet(frozenset):
	"""A set for Society objects that has a pretty-printing __str__ method."""

	def __str__(self):
		return pretty_name_list(
			(soc.description, soc.name) for soc in self)


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


def pretty_name_list(names):
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


def get_societies(name=None, admin=None):
	"""Return a generator for Society objects representing the complete SRCF soclist,
	   or just the soclist entry for the given society short name, or the soclist
	   entries for societies with the given administrator."""
	with open(SOCLIST, 'r') as f:
		for line in f:
			fields = line.strip().split(":")
			if name is None or name == fields[0]:
				admin_crsids = frozenset(fields[2].split(",")
					if fields[2] else [])
				if admin is None or admin in admin_crsids:
					yield Society(
							name=fields[0],
							description=fields[1],
							admin_crsids=admin_crsids,
							joindate=fields[3]
						)


def get_society(name):
	"""Return the Society object for the given society short name."""
	try:
		socs = get_societies(name)
		soc = socs.next()
		socs.close()
		return soc
	except StopIteration:
		raise KeyError(name)


def members_and_socs():
	"""Return a pair of dictionaries (mems, socs), where mems maps crsids
	to Member objects, and socs maps society shortnames to Society objects.

	Equivalent to, but more efficient than, (members(), societies())."""
	mems = {}
	socs = {}

	for mem in get_members():
		mems[mem.crsid] = mem

	for soc in get_societies():
		# since the memberlist dictionary is handy, might as well
		# look up the admins and cache the result
		soc.admins(mems)

		socs[soc.name] = soc

	# cache the member societies as well
	soclist = socs.values()
	for mem in mems.values():
		mem.socs(soclist)

	return (mems, socs)


def members():
	"""Return a dictionary mapping crsids to Member objects."""
	(mems, socs) = members_and_socs()
	return mems


def societies():
	"""Return a dictionary mapping society shortnames to Society objects."""
	(mems, socs) = members_and_socs()
	return socs


#TODO(drt24), the constant 8 should not be hardcoded everywhere this function is used
def pwgen(pwlen):
    """pwgen creates a neat password for the user"""
    text = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ123456789'
    pw = ''
    for x in range(pwlen):
        pw = pw + text[random.randint(0,len(text)-1)]
    return pw

