#
# Options
#

# Or you may want to select an explicit Python version, e.g. python3.9
PYTHON = python3

#
# Bit of an implementation detail: all scripts in our virtualenv
#
scripts = bin/test bin/zodbbrowser

# my release rules
FILE_WITH_VERSION = src/zodbbrowser/__init__.py


#
# Interesting targets
#

.PHONY: all
all: $(scripts)                 ##: build a virtualenv

.PHONY: test
test:                           ##: run tests
	tox -p auto

# test with pager
.PHONY: testp
testp: bin/test                 ##: run tests in a pager
	bin/test -s zodbbrowser -vc 2>&1 |less -RFX

.PHONY: coverage
coverage:                       ##: measure test coverage
	tox -e coverage3

include release.mk


#
# Implementation
#

bin:
	mkdir bin

bin/pip: | bin
	virtualenv -p $(PYTHON) .venv
	.venv/bin/pip install -U pip
	ln -sfr .venv/bin/pip bin/

bin/zodbbrowser: setup.py | bin/pip
	bin/pip install -e '.[test]'
	ln -sfr .venv/bin/zodbbrowser bin/
	@touch -c $@

bin/zope-testrunner: | bin/pip
	bin/pip install zope.testrunner
	ln -sfr .venv/bin/zope-testrunner bin/

bin/test: | bin/zope-testrunner
	printf '"$$(dirname "$$0")"/zope-testrunner --test-path=src --tests-pattern='"'"'^f?tests$$'"'"' "$$@"\n' > $@
	chmod +x $@
