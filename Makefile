#
# Options
#

# Or you may want to select an explicit Python version, e.g.
PYTHON = python2.5

#
# Interesting targets
#

.PHONY: all
all: bin/buildout
	bin/buildout

.PHONY: check test
check test: bin/test
	bin/test -s zodbbrowser --auto-color

# test with pager
.PHONY: testp
testp:
	bin/test -s zodbbrowser -vc 2>&1 |less -RFX

.PHONY: coverage
coverage:
	bin/test -s zodbbrowser -u --coverage=coverage
	bin/coverage parts/test/working-directory/coverage

.PHONY: tags
tags:
	bin/ctags

.PHONY: preview-pypi-description
preview-pypi-description:
	# pip install restview, if missing
	restview -e "$(PYTHON) setup.py --long-description"

.PHONY: dist
dist:
	$(PYTHON) setup.py sdist

.PHONY: checklatestzope
checklatestzope: dist
	version=`$(PYTHON) setup.py --version` && \
	rm -rf tmp && \
	mkdir tmp && \
	cd tmp && \
	tar xvzf ../dist/zodbbrowser-$$version.tar.gz && \
	cd zodbbrowser-$$version && \
	$(PYTHON) bootstrap.py && \
	bin/buildout -c bleeding-edge.cfg && \
	bin/test -s zodbbrowser

.PHONY: checkzope2
checkzope2: dist
	version=`$(PYTHON) setup.py --version` && \
	rm -rf tmp && \
	mkdir tmp && \
	cd tmp && \
	tar xvzf ../dist/zodbbrowser-$$version.tar.gz && \
	cd zodbbrowser-$$version && \
	$(PYTHON) bootstrap.py && \
	bin/buildout -c zope2.cfg && \
	bin/test -s zodbbrowser

.PHONY: distcheck
distcheck: check checklatestzope dist
	version=`$(PYTHON) setup.py --version` && \
	rm -rf tmp && \
	mkdir tmp && \
	cd tmp && \
	tar xvzf ../dist/zodbbrowser-$$version.tar.gz && \
	cd zodbbrowser-$$version && \
	make dist && \
	cd .. && \
	mkdir one two && \
	cd one && \
	tar xvzf ../../dist/zodbbrowser-$$version.tar.gz && \
	cd ../two/ && \
	tar xvzf ../zodbbrowser-$$version/dist/zodbbrowser-$$version.tar.gz && \
	cd .. && \
	diff -ur one two -x SOURCES.txt && \
	cd .. && \
	rm -rf tmp && \
	echo "sdist seems to be ok"
# I'm ignoring SOURCES.txt since it appears that the second sdist gets a new
# source file, namely, setup.cfg.  Setuptools/distutils black magic, may it rot
# in hell forever.

release:
	@$(PYTHON) setup.py --version | grep -qv dev || { \
	    echo "Please remove the 'dev' suffix from the version number in src/zodbbrowser/__init__.py"; exit 1; }
	@$(PYTHON) setup.py --long-description | rst2html --exit-status=2 > /dev/null || { \
	    echo "There's a restructured text error in the package description"; exit 1; }
	@ver_and_date="`$(PYTHON) setup.py --version` (`date +%Y-%m-%d`)" && \
	    grep -q "^$$ver_and_date$$" CHANGES.txt || { \
	        echo "CHANGES.txt has no entry for $$ver_and_date"; exit 1; }
	make distcheck
	test -z "`bzr status 2>&1`" || { echo; echo "Your working tree is not clean" 1>&2; bzr status; exit 1; }
	# I'm chicken so I won't actually do these things yet
	@echo Please run $(PYTHON) setup.py sdist register upload
	@echo Please run bzr tag `$(PYTHON) setup.py --version`
	@echo Please increment the version number in src/zodbbrowser/__init__.py
	@echo Please add a new empty entry in CHANGES.txt

#
# Implementation
#

bin/buildout:
	$(PYTHON) bootstrap.py

bin/test: bin/buildout
	bin/buildout

