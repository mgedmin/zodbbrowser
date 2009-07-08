ZODB Browser
============

The ZODB browser allows you to inspect persistent objects stored in the ZODB,
view their attributes and historical changes made to them.


Usage
-----

Add zodbbrowser to the list of eggs (e.g. in buildout.cfg) and add this to
your site.zcml::

  <include package="zodbbrowser" />

Restart Zope and append @@zodbbrowser to the end of the URL to start
browsing, e.g. http://localhost:8080/@@zodbbrowser.
