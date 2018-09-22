#!/usr/bin/python

"""
SRCF python library:

pwgen(): Generates a password
"""

from subprocess import check_output

def pwgen(*argl, **kwargs):
    return check_output(['/usr/local/bin/local_pwgen']).rstrip()
