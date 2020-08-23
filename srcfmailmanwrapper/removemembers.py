#!/usr/bin/python3

"""Remove members from a list.
(SRCF wrapper around Mailman's remove_members, but note different options.)

Usage: srcf-mailman-remove [options] listname [addr1 ...]

Options:

    --stdin
    -s
        Remove member addresses read from stdin.

    --all
    -a
        Remove all members of the mailing list.

    --nouserack
    -n
        Don't send the user acknowledgements.  If not specified, the list
        default value is used.

    --noadminack
    -N
        Don't send the admin acknowledgements.  If not specified, the list
        default value is used.

    --help
    -h
        Print this help message and exit.

    listname is the name of the mailing list to use.

    addr1 ... are additional addresses to remove.
"""

import sys, getopt, os
from srcfmailmanwrapper import util

def main():

	targetscript = "/usr/lib/mailman/bin/remove_members"

	shortopts = "sanNh"
	longopts = ["stdin", "all", "nouserack", "noadminack", "help"]

	try:
		opts, args = getopt.gnu_getopt(sys.argv[1:], shortopts, longopts)
	except getopt.error as e:
		raise util.GetoptError(e)

	mailmanargs = [targetscript]

	for opt, arg in opts:
		if opt in ("-h", "--help"):
			print(__doc__)
			sys.exit(0)
		elif opt in ("-s", "--stdin"):
			mailmanargs += ["-f", "-"]
		elif opt in ("-a", "--all"):
			mailmanargs += ["-a"]
		elif opt in ("-n", "--nouserack"):
			mailmanargs += ["-n"]
		elif opt in ("-N", "--noadminack"):
			mailmanargs += ["-N"]
		else:
			# only reached if we missed something above
			raise util.UnhandledArgumentError(opt)

	mailmanargs += [util.getlistname(args)]
	if len(args) > 0:
		mailmanargs += args

	os.execv(targetscript, mailmanargs)

if __name__=="__main__":
	try:
		main()
	except util.Error as e:
		print(e)
		if e.printusage:
			print("-----\n%s" % __doc__, file=sys.stderr)
		sys.exit(1)

