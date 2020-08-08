PYTHON = python3
PIP = pip3
PDOC = pdoc3

VERSION = r$$(git rev-list --count HEAD)$$([ "$$(git diff-index --name-only HEAD)" = "" ] || echo d)-$$(date +"%Y%m%d%H%M%S")
INSTALL = -e
DISTS = sdist bdist_wheel bdist_deb

SETUP = $(PYTHON) setup.py --command-packages=stdeb.command egg_info $(if $(strip $(VERSION)), -b $(VERSION))
DOCS = $(PDOC) --html --force --config show_type_annotations=True

MODULE = srcf

install:
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install pdoc3 stdeb  # build dependencies
	$(PIP) install $(INSTALL) .

package-build:
	$(SETUP) $(DISTS)

package-post:
	rm -f $(MODULE)-*-*.tar.gz
	rm -rf deb_dist/$(MODULE)-*-*/

package: package-build package-post

docs:
	$(DOCS) $(MODULE)

venv:
	$(PYTHON) -m venv venv
	echo /usr/local/lib/python3.5/dist-packages >$$(echo venv/lib/python3.*)/site-packages/srcf.pth
	$(MAKE) PIP=venv/bin/pip install

venv%:
	$(PYTHON) -m venv venv$*
	echo /usr/local/lib/python3.5/dist-packages >$$(echo venv$*/lib/python3.*)/site-packages/srcf.pth
	$(MAKE) PIP=venv$*/bin/pip install
