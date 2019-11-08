PYTHON = python3
PDOC = pdoc3
VERSION = r$$(git rev-list --count HEAD)$$([ "$$(git diff-index --name-only HEAD)" = "" ] || echo d)-$$(date +"%Y%m%d%H%M%S")
DISTS = sdist bdist_wheel bdist_deb

SETUP = $(PYTHON) setup.py --command-packages=stdeb.command egg_info $(if $(strip $(VERSION)), -b $(VERSION))
DOCS = $(PDOC) --html --force --config show_type_annotations=True

MODULE = srcflib

package-build:
	$(SETUP) $(DISTS)

package-post:
	rm -f $(MODULE)-*-*.tar.gz
	rm -rf deb_dist/$(MODULE)-*-*/

package: package-build package-post

docs:
	$(DOCS) $(MODULE) srcf

venv:
	$(PYTHON) -m venv venv
	venv/bin/pip install --upgrade pip setuptools wheel
	venv/bin/pip install argcomplete jinja2 ldap3 six  # dependencies of `srcf`
	echo /usr/local/lib/python3.5/dist-packages >$$(echo venv/lib/python3.*)/site-packages/srcf.pth
	venv/bin/pip install pdoc3 stdeb  # build dependencies
	venv/bin/pip install -e .

venv%:
	$(PYTHON) -m venv venv$*
	venv$*/bin/pip install --upgrade pip setuptools wheel
	venv$*/bin/pip install argcomplete jinja2 ldap3 six  # dependencies of `srcf`
	echo /usr/local/lib/python3.5/dist-packages >$$(echo venv$*/lib/python3.*)/site-packages/srcf.pth
	venv$*/bin/pip install pdoc3 stdeb  # build dependencies
	venv$*/bin/pip install -e .
