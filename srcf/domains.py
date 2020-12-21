"""
srcf.domains: Utilities for verifying domain ownership.
"""

from binascii import hexlify
from contextlib import contextmanager
from http.client import HTTPConnection
import os
import socket
from tempfile import NamedTemporaryFile


HOST_DOMAIN = "srcf.societies.cam.ac.uk"

WELL_KNOWN = "/public/societies/srcf-admin/srcf-well-known"


@contextmanager
def make_challenge(domain):
    # Generate a random challenge value to ensure we're talking to ourselves.
    challenge = hexlify(os.urandom(32))
    proof = NamedTemporaryFile(prefix="domain-{}-".format(domain), dir=WELL_KNOWN)
    try:
        # Temp files are 0600 by default.  As it'll be owned by srcf-admin or
        # root, Apache won't have permission to read it as the site user.
        os.chmod(proof.name, 0o644)
        proof.write(challenge)
        proof.flush()
        yield challenge, os.path.basename(proof.name)
    finally:
        proof.close()


def get_server_ips():
    server = "{}.{}".format(socket.gethostname(), HOST_DOMAIN)
    raw = socket.getaddrinfo(server, "http", proto=socket.IPPROTO_TCP)
    for family, *_, (ip, *_) in raw:
        yield family, ip


def verify(domain):
    """
    Check if the given domain is correctly configured to serve an SRCF website.
    A one-off challenge will be created and retrieved via /.well-known/srcf.

    Returns a tuple of values, `(IPv4, IPv6)`, where a given value can be
    `True` if valid, `False` if not, or `None` if we couldn't connect.
    """
    with make_challenge(domain) as (challenge, filename):
        # Read the temp file back via the given domain.
        path = "/.well-known/srcf/{}".format(filename)
        results = {}
        for family, source in get_server_ips():
            if family in results:
                continue
            try:
                conn = HTTPConnection(domain, timeout=5, source_address=(source, 0))
                conn.request("GET", path)
                resp = conn.getresponse().read()
                results[family] = resp == challenge
            except socket.error:
                results[family] = None
        return results.get(socket.AF_INET), results.get(socket.AF_INET6)
