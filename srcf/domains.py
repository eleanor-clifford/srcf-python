"""
srcf.domains: Utilities for verifying domain ownership.
"""

import binascii
import os
import tempfile
from tempfile import NamedTemporaryFile

import requests

from srcf.database import Domain, Session


WELL_KNOWN = "/public/societies/srcf-admin/srcf-well-known"


def verify(domain):
    """
    Check if the given domain is correctly configured to serve an SRCF site.

    A one-off challenge will be created and retrieved via /.well-known/srcf.

    Returns `True` if valid, `False` if not, `None` if we couldn't connect.
    """
    # Generate a random challenge value to ensure we're talking to ourselves.
    challenge = binascii.hexlify(os.urandom(32))
    proof = tempfile.NamedTemporaryFile(prefix="domain-{}-".format(domain),
                                        dir=WELL_KNOWN)
    try:
        # Temp files are 0600 by default.  As it'll be owned by srcf-admin or
        # root, Apache won't have permission to read it as the site user.
        os.chmod(proof.name, 0o644)
        proof.write(challenge)
        proof.flush()
        # Read the temp file back via the given domain.
        url = ("http://{}/.well-known/srcf/{}"
               .format(domain, os.path.basename(proof.name)))
        try:
            response = requests.get(url, timeout=5)
            return response.content == challenge
        except requests.ConnectionError:
            return None
    finally:
        proof.close()
