#
# Options
#

# Or you may want to select an explicit Python version, e.g.
#   PYTHON = python2.5
PYTHON = python

#
# Interesting targets
#

.PHONY: all
all: bin/buildout
	bin/buildout

.PHONY: check test
check test: bin/test
	bin/test

.PHONY: dist
dist:
	$(PYTHON) setup.py sdist

.PHONY: distcheck
distcheck: check dist
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
	rm -rf tmp && \
	echo "sdist seems to be ok"
# I'm ignoring SOURCES.txt since it appears that the second sdist gets a new
# source file, namely, setup.cfg.  Setuptools/distutils black magic, may it rot
# in hell forever.


#
# Implementation
#

bin/buildout:
	$(PYTHON) bootstrap.py

bin/test: bin/buildout
	bin/buildout

