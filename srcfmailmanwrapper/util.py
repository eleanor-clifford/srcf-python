#!/usr/bin/python

"Utility functions for SRCF Mailman wrapping utilities."

import grp, pwd, os, sys

def getlistname(args):

	if (len(args) == 0):
		raise NoListNameError()

	listname = args[0]
	del args[0]

	try:
		socname, suffix = listname.split("-", 1)
	except ValueError:
		# no hyphen in list name!
		socname = listname
	try:
		username = pwd.getpwuid(os.getuid()).pw_name
	except KeyError:
		raise NonexistantUidError(os.getuid())

	# root controls all
	if username == "root":
		return listname

	# personal lists: crsid-foo
	if socname == username:
		return listname

	try:
		group = grp.getgrnam(socname)
	except KeyError:
		raise NonexistantSocietyError(socname)

	if username not in group.gr_mem:
		raise PermissionDeniedError(socname)

	return listname


class Error(Exception):
	"Base class for exceptions in this module."
	message = "unknown error!  Please contact sysadmins@srcf.ucam.org."
	prefix = "Error: "
	printusage = 0

	def __str__(self):
		return "%s%s" % (self.prefix, self.message)

class ArgumentError(Error):
	prefix = "Error parsing arguments: "
	printusage = 1

class GetoptError(ArgumentError):
	def __init__(self, msg):
		self.message = msg

class UnhandledArgumentError(ArgumentError):
	def __init__(self, arg):
		self.message = "unhandled argument: %s" % arg

class NoListNameError(ArgumentError):
	message = "no list name specified!"

class TooManyArgsError(ArgumentError):
	message = "only one list name may be specified!"

class InvalidArgumentValueError(ArgumentError):
	def __init__(self, arg, val):
		self.message = "'%s' is not a valid value for %s" % (val, arg)

class NonexistantUidError(Error):
	def __init__(self, uid):
		self.message = "you (uid %d) appear not to exist!\nPlease ask sysadmins@srcf.ucam.org for help finding yourself." % uid

class NonexistantSocietyError(Error):
	def __init__(self, socname):
		self.message = "society '%s' appears not to exist!  Please check your typing." % socname

class PermissionDeniedError(Error):
	def __init__(self, socname):
		self.message = "you are not an administrator of society '%s'." % socname
