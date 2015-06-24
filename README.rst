ZODB Browser
============

|buildstatus|_ |coverage|_

The ZODB browser allows you to inspect persistent objects stored in the ZODB,
view their attributes and historical changes made to them.

.. warning::

  ZODB is based on Python pickles, which are not secure -- they allow
  **arbitrary command execution**.  Do not use zodbbrowser on databases from
  untrusted sources.

.. contents::


Usage as a standalone project
-----------------------------

Install all the dependencies into the source tree with zc.buildout::

  python bootstrap.py
  bin/buildout

Run bin/zodbbrowser specifying either a filename or a ZEO address ::

  bin/zodbbrowser /path/to/Data.fs
  bin/zodbbrowser --zeo localhost:9080
  bin/zodbbrowser --zeo /path/to/zeosock

If you don't have a spare Data.fs to test with, you can create a new empty
one with just the barest Zope 3 scaffolding in it::

  bin/zodbbrowser empty.fs --rw

Open http://localhost:8070 in a web browser.  Note that there are no
access controls; all other users on the local machine will be able to
access the database contents.

Or you could try to use ``easy_install`` or ``pip``.  It may work or it may
not, depending on the current state of all the dependencies (buildout.cfg
hardcodes dependency version to a known-working-together state, called the
"Zope 3.4 Known Good Set", so buildout-based installs are safer) ::

  easy_install zodbbrowser
  zodbbrowser /path/to/Data.fs


Command-line options
--------------------

Run ``bin/zodbbrowser --help`` to see a full and up-to-date list of
command-line options::

  Usage: zodbbrowser [options] [FILENAME | --zeo ADDRESS]

  Open a ZODB database and start a web-based browser app.

  Options:
    -h, --help        show this help message and exit
    --zeo=ADDRESS     connect to ZEO server instead
    --listen=ADDRESS  specify port (or host:port) to listen on
    --rw              open the database read-write (allows creation of the
                      standard Zope local utilities if missing)


Help!  Broken objects everywhere
--------------------------------

If you don't want to see ``<persistent broken ...>`` everywhere, make sure
your application objects are importable from the Python path.  The easiest way
of doing that is adding zodbbrowser to your application's buildout (or
virtualenv, if you use virtualenvs).  This way your application (or Zope's)
nice __repr__ will also be used.


Other scripts
-------------

zodbcheck
~~~~~~~~~

Script to scan and build a database containing the relationships
between object stored in the ZODB. By doing so it will count POSKey
errors: those are links to objects in the ZODB that are no longer
there.

You can use this database with zodbbrowser after: it will contain
additional information to browse objects using this reference
information.

In addition to this, a page will list all missing objects (that
triggers the errors) and the objects that referring to them.


This script only works on history free databases at the moment.

zodbsearch
~~~~~~~~~~

Script to search quickly trough a database to see if a Python class is
still used in it.

To have accurate results you must pack your databases before, as it
could be that the reported class is used in objects that got removed
from the ZODB or are present in older versions of the available
objects.

sqlpack
~~~~~~~

Script to pack Relstorage history free databases. It will use the
result computed by zodbcheck in order to find which object to remove
from the SQL database and generate an SQL file with delete statement
in order to remove them. If you store your blobs outside of the SQL
database, it can generate a shell script to remove those as well.

The advantage of this solution, is, mostly is speed, and the fact that
you do not need to execute it on your production database: you can run
both zodbcheck and sqlpack on a backup of your main database and after
execute the two scripts you obtain on the production one.

Online help
-----------

There's a little 'help' link in the bottom-right corner of every page that
describes the user interface in greater detail.


Usage as a plugin
-----------------

Add zodbbrowser to the list of eggs (e.g. in buildout.cfg of your app) and
add this to your site.zcml::

  <include package="zodbbrowser" />

Rerun bin/buildout, restart Zope and append @@zodbbrowser to the end of the
URL to start browsing, e.g. http://localhost:8080/@@zodbbrowser.  Or, if you
still use ZMI (the Zope Management Interface), look for a new menu item
titled "ZODB Browser".


Alternatives
------------

There's a package called z3c.zodbbrowser in the Zope svn repository that
implements the same idea (but without history browsing) as a GUI desktop
application written using wxPython.  It doesn't have a website and was never
released to the Python Package Index.

There's also `dm.historical`__ which provides access to object history from
an interactive Python shell.

__ http://pypi.python.org/pypi/dm.historical

If you're not interested in history or objects that cannot be reached
through URL traversal, you can use the built-in object inspector that
comes with Zope 3 / Grok.


Authors
-------

ZODB Browser was developed by Tautvilas Mečinskas (tautvilas@pov.lt) and
Marius Gedminas (marius@pov.lt) from `Programmers of Vilnius
<http://pov.lt/>`_.  It is licenced under the `Zope Public Licence
<http://www.zope.org/Resources/ZPL>`_.

Please report bugs at https://github.com/mgedmin/zodbbrowser/issues.

There's an old bugtracker at https://bugs.launchpad.net/zodbbrowser but I'd
really rather prefer new bugs in GitHub.


.. |buildstatus| image:: https://api.travis-ci.org/mgedmin/zodbbrowser.svg?branch=master
.. _buildstatus: https://travis-ci.org/mgedmin/zodbbrowser

.. |coverage| image:: https://coveralls.io/repos/mgedmin/zodbbrowser/badge.svg?branch=master
.. _coverage: https://coveralls.io/r/mgedmin/zodbbrowser
