from glob import glob
import os.path

from setuptools import find_packages, setup


README = os.path.join(os.path.abspath(os.path.dirname(__file__)), "README.rst")


def _entrypoints(mapping):
    return {"console_scripts": ["srcflib-{0}-{1}=srcflib.scripts.{0}:{2}"
                                .format(module, method.replace("_", "-"), method)
                                for module, methods in mapping.items() for method in methods]}


setup(name="srcf",
      version="0.0.8",
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
      entry_points=_entrypoints({"mysql": ["create"]}))
