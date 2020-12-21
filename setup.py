import os.path

from setuptools import find_packages, setup


README = os.path.join(os.path.abspath(os.path.dirname(__file__)), "README.rst")


setup(name="srcf",
      version="0.0.5",
      description="Database schemas and core functionality for the Student-Run Computing Facility.",
      long_description=open(README).read(),
      long_description_content_type="text/x-rst",
      author="SRCF Sysadmins",
      author_email="sysadmins@srcf.net",
      url="https://www.srcf.net",
      platforms=["Any"],
      python_requires=">=3.5",
      install_requires=["argcomplete", "jinja2", "ldap3", "psycopg2-binary", "PyMySQL", "six", "SQLAlchemy"],
      packages=find_packages(),
      py_modules=["srcfmail"],
      package_data={"srcf.controllib": ["emails/*/*.txt"]})
