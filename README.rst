ZODB Browser
============

|buildstatus|_ |appveyor|_ |coverage|_

The ZODB browser allows you to inspect persistent objects stored in the ZODB,
view their attributes and historical changes made to them.

.. warning::

  ZODB is based on Python pickles, which are not secure -- they allow
  **arbitrary command execution**.  Do not use zodbbrowser on databases from
  untrusted sources.

.. contents::


Usage as a standalone project
-----------------------------

Install zodbbrowser into a virtualenv alongside your application code ::

  pip install zodbbrowser

Run ``zodbbrowser`` specifying either a filename or a ZEO address ::

  zodbbrowser /path/to/Data.fs
  zodbbrowser --zeo localhost:9080
  zodbbrowser --zeo /path/to/zeosock

If you don't have a spare Data.fs to test with, you can create a new empty
one with just the barest Zope 3 scaffolding in it::

  zodbbrowser empty.fs --rw

Open http://localhost:8070 in a web browser.  Note that there are no
access controls; all other users on the local machine will be able to
access the database contents.


Command-line options
--------------------

Run ``zodbbrowser --help`` to see a full and up-to-date list of
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

__ https://pypi.org/project/dm.historical

If you're not interested in history or objects that cannot be reached
through URL traversal, you can use the built-in object inspector that
comes with Zope 3 / Grok.


Authors
-------

ZODB Browser was developed by Tautvilas Mečinskas (tautvilas@pov.lt) and
Marius Gedminas (marius@pov.lt) from `Programmers of Vilnius
<https://pov.lt/>`_.  It is licenced under the `Zope Public Licence
<https://opensource.org/licenses/ZPL-2.0>`_.

Please report bugs at https://github.com/mgedmin/zodbbrowser/issues.

There's an old bugtracker at https://bugs.launchpad.net/zodbbrowser but I'd
really rather prefer new bugs in GitHub.


.. |buildstatus| image:: https://github.com/mgedmin/zodbbrowser/actions/workflows/build.yml/badge.svg?branch=master
.. _buildstatus: https://github.com/mgedmin/zodbbrowser/actions

.. |appveyor| image:: https://ci.appveyor.com/api/projects/status/github/mgedmin/zodbbrowser?branch=master&svg=true
.. _appveyor: https://ci.appveyor.com/project/mgedmin/zodbbrowser

.. |coverage| image:: https://coveralls.io/repos/mgedmin/zodbbrowser/badge.svg?branch=master
.. _coverage: https://coveralls.io/r/mgedmin/zodbbrowser
