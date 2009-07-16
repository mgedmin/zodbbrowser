ZODB Browser
============

The ZODB browser allows you to inspect persistent objects stored in the ZODB,
view their attributes and historical changes made to them.


Usage as a plugin
-----------------

Add zodbbrowser to the list of eggs (e.g. in buildout.cfg of your app) and
add this to your site.zcml::

  <include package="zodbbrowser" />

Restart Zope and append @@zodbbrowser to the end of the URL to start
browsing, e.g. http://localhost:8080/@@zodbbrowser.


Usage as a standalone project
-----------------------------

Install all the dependencies into the source tree with zc.buildout::

  python bootstrap.py
  bin/buildout

Run bin/zodbbrowser specifying either a filename or a ZEO address ::

  bin/zodbbrowser /path/to/Data.fs
  bin/zodbbrowser --zeo localhost:9080
  bin/zodbbrowser --zeo /path/to/zeosock

Open http://localhost:8070 in a web browser.  Note that there are no
access controls; all other users on the local machine will be able to
access the database contents.

Or you could use easy_install, if you're not afraid of cluttering your Python
installation with extra packages::

  easy_install zodbbrowser[app]
  zodbbrowser /path/to/Data.fs


Authors
-------

ZODB Browser was developed by Tautvilas Mečinskas (tautvilas@pov.lt) and
Marius Gedminas (marius@pov.lt).  It is licenced under the `Zope Public
Licence <http://www.zope.org/Resources/ZPL>`_.
