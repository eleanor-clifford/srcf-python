#!/usr/bin/python3

"""Add members to a list from the command line.
(SRCF wrapper around Mailman's add_members, but note different options.)

Usage: srcf-mailman-add [options] listname

Options:

    --digest
    -d
        New members will be added as digest members, rather than the
        non-digest members as is the default.

    --welcome-msg=<y|n>
    -w <y|n>
        Set whether or not to send the list members a welcome message,
        overriding whatever the list's `send_welcome_msg' setting is.

    --admin-notify=<y|n>
    -a <y|n>
        Set whether or not to send the list administrators a notification on
        the success/failure of these subscriptions, overriding whatever the
        list's `admin_notify_mchanges' setting is.

    --help
    -h
        Print this help message and exit.

    listname
        The name of the Mailman list you are adding members to.  It must
        already exist.

The list of addresses to add is read from stdin.
"""

import sys, getopt, os
from srcfmailmanwrapper import util

def main():

	targetscript = "/usr/lib/mailman/bin/add_members"

	shortopts = "dw:a:h"
	longopts = ["digest", "welcome-msg=", "admin-notify=", "help"]

	try:
		opts, args = getopt.gnu_getopt(sys.argv[1:], shortopts, longopts)
	except getopt.error as e:
		raise util.GetoptError(e)

	mailmanargs = [targetscript]
	type = "-r"

	for opt, arg in opts:
		if opt in ("-h", "--help"):
			print(__doc__)
			sys.exit(0)
		elif opt in ("-d", "--digest"):
			type = "-d"
		elif opt in ("-w", "--welcome-msg"):
			if arg not in ("y", "n"):
				raise util.InvalidArgumentValueError(opt, arg)
			mailmanargs += ["-w", arg]
		elif opt in ("-a", "--admin-notify"):
			if arg not in ("y", "n"):
				raise util.InvalidArgumentValueError(opt, arg)
			mailmanargs += ["-a", arg]
		else:
			# only reached if we missed something above
			raise util.UnhandledArgumentError(opt)

	mailmanargs += [type, "-", util.getlistname(args)]
	if (len(args) > 0):
		raise util.TooManyArgsError()

	os.execv(targetscript, mailmanargs)

if __name__=="__main__":
	try:
		main()
	except util.Error as e:
		print(e)
		if e.printusage:
			print("-----\n%s" % __doc__, file=sys.stderr)
		sys.exit(1)

