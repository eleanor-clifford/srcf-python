from glob import glob
import os.path
import re

from setuptools import find_packages, setup

try:
    # Import all script providers so that ENTRYPOINTS gets populated.
    from srcflib.scripts import group, mailman, member, mysql, pgsql  # noqa: F401
    from srcflib.scripts.utils import ENTRYPOINTS
except ImportError:
    # Avoid chicken-and-egg dependency requirements during initial installation.
    # This means you need to re-run setup in order to gain script entrypoints.
    ENTRYPOINTS = {}


README = os.path.join(os.path.abspath(os.path.dirname(__file__)), "README.rst")


def version():
    with open("debian/changelog") as log:
        first = next(l for l in log if l.strip())
    return re.split("[()]", first)[1].replace("~", "")


setup(name="srcf",
      version=version(),
      description="Database schemas and core functionality for the Student-Run Computing Facility.",
      long_description=open(README).read(),
      long_description_content_type="text/x-rst",
      author="SRCF Sysadmins",
      author_email="sysadmins@srcf.net",
      url="https://www.srcf.net",
      platforms=["Any"],
      python_requires=">=3.6",
      install_requires=["argcomplete", "docopt", "jinja2", "ldap3", "psycopg2",
                        "pylibacl", "PyMySQL", "requests", "six", "SQLAlchemy"],
      packages=find_packages(),
      py_modules=["srcfmail"],
      package_data={"srcf.controllib": ["emails/**/*.txt"],
                    "srcflib.email": ["templates/**/*.j2"]},
      scripts=glob("bin/*"),
      entry_points={"console_scripts": ENTRYPOINTS})
