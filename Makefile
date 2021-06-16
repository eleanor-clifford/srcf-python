PYTHON = python3
PIP = pip3
FLAKE8 = flake8
PDOC = pdoc3
UNITTEST_PYTHON = fakeroot $(PYTHON)
UNITTEST = $(UNITTEST_PYTHON) -m unittest

UNITTEST_ARGS = discover
INSTALL_ARGS = -e
DPKG_ARGS = -us -uc
LINTIAN_ARGS = --pedantic --suppress-tags binary-without-manpage
DEBUILD_ARGS = $(DPKG_ARGS) --lintian-opts $(LINTIAN_ARGS)
PDOC_ARGS = --html --force --config show_type_annotations=True --config lunr_search={}

VERSION = r$$(git rev-list --count HEAD)$$([ "$$(git diff-index --name-only HEAD)" = "" ] || echo d)-$$(date +"%Y%m%d%H%M%S")
DISTS = sdist bdist_wheel

SETUP = FAKEROOTDONTTRYCHOWN=1 $(PYTHON) setup.py --command-packages=stdeb.command egg_info $(if $(strip $(VERSION)), -b $(VERSION))
DEBPKG = FAKEROOTDONTTRYCHOWN=1 debuild -e FAKEROOTDONTTRYCHOWN
DOCS = $(PDOC) $(PDOC_ARGS)

NAME = srcf
MODULES = srcf srcflib srcfmail srcfmailmanwrapper
MODULE_FILES = srcf/ srcflib/ srcfmail.py srcfmailmanwrapper/

check:
	$(FLAKE8) $(MODULE_FILES)

test:
	$(UNITTEST) $(UNITTEST_ARGS)

install:
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install coverage pdoc3 stdeb  # build dependencies
	$(PIP) install $(INSTALL_ARGS) .

dist-build:
	$(SETUP) $(DISTS)

dist-clean:
	rm -f $(NAME)-*-*.tar.gz
	rm -rf deb_dist/$(NAME)-*-*/

dist: dist-build dist-clean

deb:
	$(DEBPKG) -b $(DEBUILD_ARGS)

deb-src: dist
	cp $$(find dist/ -name $(NAME)-*.tar.gz -printf "%T@ %p\n" | sort -nr | cut -d' ' -f 2- | head -n1) ../python3-$(NAME)_$$(sed -nr 's/^python3-$(NAME) \(([0-9\.r]+?)(-.+?)?\).*$$/\1/p' debian/changelog | head -n1).orig.tar.gz
	$(DEBPKG) -S $(DEBUILD_ARGS)

docs:
	$(DOCS) $(MODULES)

venv:
	$(PYTHON) -m venv venv
	echo /usr/local/lib/python3/dist-packages >$$(echo venv/lib/python3.*)/site-packages/srcf.pth
	$(MAKE) PIP=venv/bin/pip install

venv%:
	$(PYTHON) -m venv venv$*
	echo /usr/local/lib/python3/dist-packages >$$(echo venv$*/lib/python3.*)/site-packages/srcf.pth
	$(MAKE) PIP=venv$*/bin/pip install
