import os.path

from setuptools import find_packages, setup


README = os.path.join(os.path.abspath(os.path.dirname(__file__)), "README.rst")


setup(name="srcflib",
      description="Tools and helpers for the Student-Run Computing Facility.",
      long_description=open(README).read(),
      long_description_content_type="text/x-rst",
      author="SRCF Sysadmins",
      author_email="sysadmins@srcf.net",
      url="https://www.srcf.net",
      platforms=["Any"],
      python_requires=">=3.5",
      install_requires=["psycopg2-binary", "pylibacl", "PyMySQL", "requests", "SQLAlchemy"],
      packages=find_packages(),
      package_data={"srcflib.email": ["**/*.j2"]})
