Changes
-------

0.16.1 (2019-07-30)
~~~~~~~~~~~~~~~~~~~

- Fix system error when an object refers to another object that was
  added in a newer transaction (GH #29).


0.16.0 (2019-07-24)
~~~~~~~~~~~~~~~~~~~

- You can now view disassembled raw pickle data.


0.15.2 (2019-07-11)
~~~~~~~~~~~~~~~~~~~

- Stop depending on the obsolete ZODB3 metapackage from 2012.  Instead
  depend directly on persistent, BTrees, ZODB, and ZEO.


0.15.1 (2019-04-23)
~~~~~~~~~~~~~~~~~~~

- Dropped Python 3.4 support.


0.15.0 (2019-04-02)
~~~~~~~~~~~~~~~~~~~

- Add support for Python 3.7.

- Add support for PyPy and PyPy3.

- Support zope.security proxies in PURE_PYTHON mode.

- Use our custom __repr__ instead of the new persistent one.

- Transaction IDs in generated URLs are now in hex.

- 100% test coverage.


0.14.0 (2017-11-15)
~~~~~~~~~~~~~~~~~~~

- Add support for Python 3.4, 3.5, 3.6.

- Drop support for ZODB 3.8.


0.13.1 (2017-10-06)
~~~~~~~~~~~~~~~~~~~

- Fixed @@zodbbrowser_history with recent versions of ZODB (AttributeError:
  MVCCAdapterInstance doesn't have attribute ``iterator``).


0.13.0 (2016-11-24)
~~~~~~~~~~~~~~~~~~~

- Dropped Python 2.6 support (because ZODB---more specifically BTrees---dropped
  it).

- Fixed rollback to work with ``transaction`` >= 2.0 (transaction notes must be
  Unicode now).


0.12.0 (2015-02-25)
~~~~~~~~~~~~~~~~~~~

- Show request URLs in history record headers (GH #7).
- Automate ZCML loading for Plone (GH #9).
- Fix standalone zodbbrowser when used with Zope 2 packages (GH #10).


0.11.2 (2015-01-09)
~~~~~~~~~~~~~~~~~~~

- Fix AttributeError: __repr__ when encountering instances of old-style
  classes (GH #6).


0.11.1 (2014-12-12)
~~~~~~~~~~~~~~~~~~~

- Updated bootstrap.py (GH #3).
- Fixed @@zodbbrowser_history not seeing new transactions because the
  cache is forever (GH #4).


0.11.0 (2013-05-29)
~~~~~~~~~~~~~~~~~~~

- Dropped Python 2.4 and 2.5 support.
- Migrated source from Launchpad to Github.
- Custom representation of OOBucket objects.
- Slightly better error pages when you specify an invalid/nonexistent OID.
- Handle OrderedContainers with non-persistent ``_order`` or ``_data``
  attributes (I've seen the first in the wild).
- Partial fix for LP#1185175: cannot browse objects of classes that use
  zope.interface.implementsOnly.


0.10.4 (2012-12-19)
~~~~~~~~~~~~~~~~~~~

- The previous release was completely broken (LP#1091716).  Fix the issue,
  and fix tox.ini to actually run functional tests in addition to unit tests.


0.10.3 (2012-12-06)
~~~~~~~~~~~~~~~~~~~

- Custom representation of persistent objects with no __repr__ to avoid
  showing misleading memory addresses (LP#1087138).


0.10.2 (2012-11-28)
~~~~~~~~~~~~~~~~~~~

- Bugfix for POSKeyErrors when viewing BTrees of non-trivial sizes
  (LP#953480).  This fixes a regression introduced in version 0.10.0.


0.10.1 (2012-11-27)
~~~~~~~~~~~~~~~~~~~

- Standalone app mode uses the Zope exception formatter for easier debugging.

- Bugfix for weird LocationError: '__class__' for some containers
  with custom traversal rules.

- Links to persistent objects in value representations now also use
  hex OIDs.


0.10.0 (2012-02-29)
~~~~~~~~~~~~~~~~~~~

- Browsing of transaction records (@@zodb_history).  Initial implementation so
  far, unbelievably slow when you have large databases (LP#907900).

- ZODB Browser now avoids writing to the database even in read-write mode.
  Previously when your objects had write-on-read semantics, those writes might
  have snuck in.

- More descriptive page titles (LP#931115).

- Show object size in the header (LP#497780).

- Expand truncated values by clicking on them (LP#931184).

- More user-friendly representation of multiline text values.

- Update maintainer email in setup.py.

- Better error message for "address already in use" errors.


0.9.0 (2011-10-21)
~~~~~~~~~~~~~~~~~~

- Make it possible to use zodbbrowser as a plugin for Zope 2.12.  Previously
  you could only use the standalone zodbbrowser app with Zope 2.12 databases.

- Be more robust against exceptions happening in repr(): show the value as
  "<unrepresentable Foo>" instead of erroring out.

- Make 'python -m zodbbrowser' run the standalone app on Python 2.5 and 2.7.
  Note that 'python -m zodbbrowser.standalone' already worked on Python 2.4
  through 2.7.

- Add an option to specify ZEO storage name (--storage NAME). Contributed by
  Thierry Florac.


0.8.1 (2010-12-18)
~~~~~~~~~~~~~~~~~~

- Show tuple differences more clearly in the history.  (Uses a really dumb
  diff algorithm that just looks for a common prefix/suffix.  Works really
  well when you append to the end, or remove just a single item.  I cannot
  use difflib.SequenceMapper because there's no guarantee tuple items are
  hashable.)

- Make it possible to locate an object by OID: press g, then type the oid
  (hex and both decimal supported; even octal, should you wish to use it).
  You can also find subobjects starting from a given OID by entering paths
  like '0x1234/sub/object'.

- Catch and display unpickling errors of the current state, not just
  historical older states.

- Handle missing interfaces that are directly provided by persistent objects.

  This works for the standalone zodbbrowser application; the zope.interface
  monkey-patch for this is too intrusive to install when using zodbbrowser
  as a plugin.

- Made ``pip install zodbbrowser`` work properly by adding explicit
  dependencies that easy_install would've picked up from setuptools extras.

  Note: if you get ``AttributeError: __file__``, make sure
  zope.app.applicationcontrol is at least version 3.5.9.  Older versions will
  not work with pip.


0.8.0 (2010-11-16)
~~~~~~~~~~~~~~~~~~

- Support all kinds of ZODB databases, not just those used by Zope 3/BlueBream
  apps (LP#494987).

- Renders tuples and lists that contain large dicts better.

- Remove dependency on zope.dublincore/zope.app.dublincore (LP#622180).


0.7.2 (2010-08-13)
~~~~~~~~~~~~~~~~~~

- Fixed TypeError: int() can't convert non-string with explicit base
  that could occur if no persistent objects were accessible from the request,
  and no explicit oid was passed.

- Handle proxies better: when type(obj) != obj.__class__, show both.

- Handle ContainedProxy objects with their special persistence scheme.


0.7.1 (2010-03-30)
~~~~~~~~~~~~~~~~~~

- IMPORTANT BUGFIX: don't leave old object states lying around in ZODB object
  cache, which could lead to DATA LOSS (LP#487243 strikes again, this time
  for OrderedContainers).

  I've audited the code and am fairly confident this bug is now dead dead
  dead.

- Try to discard data modifications when the DB is opened read-only.

- Avoid deprecated zope.testing.doctest.

- Avoid zope.app.securitypolicy; use zope.securitypolicy.


0.7 (2009-12-10)
~~~~~~~~~~~~~~~~

- Stopped using setuptools extras; now easy_install zodbbrowser is sufficient
  to run the standalone app.


0.6.1 (2009-12-09)
~~~~~~~~~~~~~~~~~~

- Compatibility with latest Zope packages, including ZODB 3.9.x.


0.6 (2009-12-07)
~~~~~~~~~~~~~~~~

- Ability to revert object state to an older version.  Requires a read-write
  database connection (i.e. run bin/zodbbrowser --rw).  The button is hidden
  and appears when you're hovering over a transaction entry in the list.
- Collapse long item lists by default.


0.5.1 (2009-11-23)
~~~~~~~~~~~~~~~~~~

- IMPORTANT BUGFIX: don't leave old object states lying around in ZODB object
  cache, which could lead to DATA LOSS (LP#487243).  This affected OOBTree
  objects.


0.5 (2009-11-23)
~~~~~~~~~~~~~~~~

- Be a bit more tolerant to unpickling errors (show which revision could not
  be loaded instead of breaking the whole page).
- Show full history of OOBTree objects and subobjects (LP#474334).
- Change background color of links on hover, to make it clear what
  object you'll see when you click, especially when the __repr__ shown
  contains reprs of subobjects.
- Show size of containers next to the "Items" heading (LP#486910).
- Show size of containers next to their representation, e.g.
  "<persistent.dict.PersistentDict object at 0xad0b3ec> (0 items)".
- Pay attention when __name__ is declared as a class attribute (LP#484899).
- Show names of directly provided interfaces on objects (i.e. show a better
  representation of pickled zope.interface.Provides objects).
- Pretty-printing of dictionaries (including nested ones).


0.4 (2009-10-11)
~~~~~~~~~~~~~~~~

- @@zodbbrowser oid and tid parameters now accept values in hex format (0x0123)
  Patch by Adam Groszer.


0.3.1 (2009-07-17)
~~~~~~~~~~~~~~~~~~

- Fixed install error on Windows (path cannot end in /).


0.3 (2009-07-17)
~~~~~~~~~~~~~~~~

- First public release
