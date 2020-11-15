srcf
====

A Python library covering database schemas and core functionality for the Student-Run Computing Facility.

Local setup commands
--------------------

.. code-block:: shell

    # Install dependencies and development copy:
    make venv
    make venv2  # directory suffixes also supported

    # Generates HTML documentation (requires pdoc3):
    make docs

    # Build bdist and wheel packages (requires stdeb):
    make dist           # automatic versioning (revision count + timestamp)
    make VERSION= dist  # override version suffix
                        # (blank for release builds with version set in setup.py)

    # Build a Debian package (requires debuild):
    make deb
