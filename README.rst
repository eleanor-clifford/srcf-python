srcf
====

A Python library covering database schemas and core functionality for the Student-Run Computing Facility.

Local setup commands
--------------------

.. code-block:: shell

    # Install dependencies and development copy:
    make venv
    make venv2  # directory suffixes also supported

    # Generate HTML documentation (requires pdoc3):
    make docs

    # Run linting and unit tests:
    make check
    make test
    make MODULE_FILES=srcflib/ check  # lint just SRCFLib (which should pass)
    make UNITTEST_PYTHON="python3-coverage run" test  # unit tests with code coverage
                                                      # (use `coverage3` in a venv)

    # Build bdist and wheel packages:
    make dist           # automatic versioning (revision count + timestamp)
    make VERSION= dist  # override version suffix
                        # (blank for release builds with version set in setup.py)

    # Build a Debian package (requires debuild):
    make deb      # binary package
    make deb-src  # source tarball
