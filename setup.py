from setuptools import find_packages, setup


setup(name="srcflib",
      description="Tools and helpers for the Student-Run Computing Facility.",
      author="SRCF Sysadmins",
      author_email="sysadmins@srcf.net",
      url="https://www.srcf.net",
      platforms=["Any"],
      python_requires=">=3.5",
      install_requires=["psycopg2-binary", "pylibacl", "PyMySQL", "requests", "SQLAlchemy"],
      packages=find_packages())
