#!/usr/bin/python
# PYTHON_ARGCOMPLETE_OK

from __future__ import print_function

import argcomplete, argparse
from srcf import *

# Somewhat manual - try swapping different complete_$FOO functions below
parser = argparse.ArgumentParser()

parser.add_argument('user',
                    help="New user to add"
                    ).completer = complete_user
parser.add_argument('soc',
                    help="Society to add new user to"
                    ).completer = complete_activesoc
parser.add_argument('admin',
                    help="Existing society admin who requested addition"
                    ).completer = complete_socadmin

argcomplete.autocomplete(parser)

if __name__ == "__main__":
    print(parser.parse_args())
