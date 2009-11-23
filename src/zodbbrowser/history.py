import inspect

from ZODB.utils import tid_repr
from persistent import Persistent
from zope.proxy import removeAllProxies
from zope.interface import implements
from zope.component import adapts

from zodbbrowser.interfaces import IObjectHistory


class ZodbObjectHistory(object):

    adapts(Persistent)
    implements(IObjectHistory)

    def __init__(self, obj):
        self._obj = removeAllProxies(obj)
        self._connection = self._obj._p_jar
        self._storage = self._connection._storage
        self._oid = self._obj._p_oid
        self._history = None
        self._by_tid = {}

    def __len__(self):
        if self._history is None:
            self._load()
        return len(self._history)

    def _load(self):
        """Load history of changes made to a Persistent object.

        Returns a list of dictionaries, from latest revision to the oldest.
        The dicts have various interesting pieces of data, such as:

            tid -- transaction ID (a byte string, usually 8 bytes)
            time -- transaction timestamp (number of seconds since the Unix epoch)
            user_name -- name of the user responsible for the change
            description -- short description (often a URL)

        Probably only works with FileStorage and ZEO ClientStorage.
        """
        all_of_it = 999999999999 # ought to be sufficient
        # XXX OMG ouch the APIs are different
        if 'length' in inspect.getargspec(self._storage.history)[0]: # ZEO
            self._history = self._storage.history(self._oid,
                                                  version='', length=all_of_it)
        else: # FileStorage
            self._history = self._storage.history(self._oid, size=all_of_it)
        self._index_by_tid()

    def _index_by_tid(self):
        for record in self._history:
            self._by_tid[record['tid']] = record

    def __getitem__(self, item):
        if self._history is None:
            self._load()
        return self._history[item]

    def lastChange(self, tid=None):
        if self._history is None:
            self._load()
        if tid in self._by_tid:
            # optimization
            return tid
        # sadly ZODB has no API for get revision at or before tid, so
        # we have to find the exact tid
        for record in self._history:
            # we assume records are ordered by tid, newest to oldest
            if tid is None or record['tid'] <= tid:
                return record['tid']
        raise KeyError(
                '%r did not exist in or before transaction %r' %
                (self._obj, tid_repr(tid)))

    def loadState(self, tid=None):
        return self._connection.oldstate(self._obj, self.lastChange(tid))

