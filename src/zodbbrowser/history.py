import inspect

from ZODB.utils import tid_repr
from ZODB.interfaces import IConnection
from persistent import Persistent
from zope.proxy import removeAllProxies
from zope.interface import implements
from zope.component import adapts

from zodbbrowser.interfaces import IObjectHistory, IDatabaseHistory
from zodbbrowser import cache


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

        See the 'history' method of ZODB.interfaces.IStorage.
        """
        size = 999999999999 # "all of it"; ought to be sufficient
        # NB: ClientStorage violates the interface by calling the last
        # argument 'length' instead of 'size'.  To avoid problems we must
        # use positional argument syntax here.
        # NB: FileStorage in ZODB 3.8 has a mandatory second argument 'version'
        # FileStorage in ZODB 3.9 doesn't accept a 'version' argument at all.
        # This check is ugly, but I see no other options if I want to support
        # both ZODB versions :(
        if 'version' in inspect.getargspec(self._storage.history)[0]:
            version = None
            self._history = self._storage.history(self._oid, version, size)
        else:
            self._history = self._storage.history(self._oid, size=size)
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

    def loadStatePickle(self, tid=None):
        return self._connection._storage.loadSerial(self._obj._p_oid,
                                                    self.lastChange(tid))

    def loadState(self, tid=None):
        return self._connection.oldstate(self._obj, self.lastChange(tid))

    def rollback(self, tid):
        state = self.loadState(tid)
        if state != self.loadState():
            self._obj.__setstate__(state)
            self._obj._p_changed = True


class ZodbHistory(object):

    adapts(IConnection)
    implements(IDatabaseHistory)

    def __init__(self, connection):
        self._connection = connection
        self._storage = connection._storage
        self._tids = cache.getStorageTids(self._storage)

    @property
    def tids(self):
        return tuple(self._tids) # readonlify

    def __len__(self):
        return len(self._tids)

    def __iter__(self):
        return self._storage.iterator()

    def __getslice__(self, start, stop):
        tids = self._tids[start:stop]
        if not tids:
            return []
        return self._storage.iterator(tids[0], tids[-1])

