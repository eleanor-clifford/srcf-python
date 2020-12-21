#!/usr/bin/python3

"""List all the members of a mailing list.
(SRCF wrapper around Mailman's list_members, but note different options.)

Usage: srcf-mailman-list [options] listname

Options:

    --regular / -r
        Print just the regular (non-digest) members.

    --digest / -d
        Print just the digest members.  Optional argument can be "mime" or
        "plain" which prints just the digest members receiving that kind of
        digest.

    --digest-type=kind / -D kind
        Print just the members receiving digests of a specific type: "mime"
        or "plain".

    --nomail / -n
        Print the members that have delivery disabled.

    --nomail-reason[=why] / -N [why]
        Print the members that have delivery disabled for a given reason:
        "byadmin", "byuser", "bybounce", or "unknown".  The argument can also
        be "enabled" which prints just those member for whom delivery is
        enabled.

    --fullnames / -f
        Include the full names in the output.

    --preserve / -p
        Output member addresses case preserved the way they were added to the
        list.  Otherwise, addresses are printed in all lowercase.

    --invalid / -i
        Print only the addresses in the membership list that are invalid.
        Ignores -r, -d, -D, -n, -N.

    --unicode / -u
        Print addresses which are stored as Unicode objects instead of normal
        string objects.  Ignores -r, -d, -D, -n, -N.

    --help / -h
        Print this help message and exit.

    listname is the name of the mailing list to use.

Note that if neither -r or -d is supplied, both regular members are printed
first, followed by digest members, but no indication is given as to address
status.
"""

import sys
import getopt
import os
from srcfmailmanwrapper import util


def main():

    targetscript = "/usr/lib/mailman/bin/list_members"

    shortopts = "rdD:nN:fpiuh"
    longopts = ["regular", "digest", "digest-type=", "nomail",
                "nomail-reason=", "fullnames", "preserve", "invalid", "unicode", "help"]

    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], shortopts, longopts)
    except getopt.error as e:
        raise util.GetoptError(e)

    mailmanargs = [targetscript]

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
        elif opt in ("-r", "--regular"):
            mailmanargs += ["-r"]
        elif opt in ("-d", "--digest"):
            mailmanargs += ["-d"]
        elif opt in ("-D", "--digest-type"):
            if arg not in ("mime", "plain"):
                raise util.InvalidArgumentValueError(opt, arg)
            mailmanargs += ["-d", arg]
        elif opt in ("-n", "--nomail"):
            mailmanargs += ["-n"]
        elif opt in ("-N", "--nomail-reason"):
            if arg not in ("byadmin", "byuser", "bybounce", "unknown", "enabled"):
                raise util.InvalidArgumentValueError(opt, arg)
            mailmanargs += ["-n", arg]
        elif opt in ("-f", "--fullnames"):
            mailmanargs += ["-f"]
        elif opt in ("-p", "--preserve"):
            mailmanargs += ["-p"]
        elif opt in ("-i", "--invalid"):
            mailmanargs += ["-i"]
        elif opt in ("-u", "--unicode"):
            mailmanargs += ["-u"]
        else:
            # only reached if we missed something above
            raise util.UnhandledArgumentError(opt)

    mailmanargs += [util.getlistname(args)]
    if (len(args) > 0):
        raise util.TooManyArgsError()

    os.execv(targetscript, mailmanargs)


if __name__ == "__main__":
    try:
        main()
    except util.Error as e:
        print(e)
        if e.printusage:
            print("-----\n%s" % __doc__, file=sys.stderr)
        sys.exit(1)
