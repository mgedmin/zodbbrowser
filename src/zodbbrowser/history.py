from ZODB.utils import tid_repr
from ZODB.interfaces import IConnection, IStorageIteration
from persistent import Persistent
from zope.proxy import removeAllProxies
from zope.interface import implementer
from zope.component import adapter

from zodbbrowser.interfaces import IObjectHistory, IDatabaseHistory
from zodbbrowser import cache

try:
    from ZODB.mvccadapter import MVCCAdapterInstance
except ImportError:  # pragma: no-cover
    class MVCCAdapterInstance(object):
        """Placeholder so we can register an adapter that will not be used."""


@adapter(Persistent)
@implementer(IObjectHistory)
class ZodbObjectHistory(object):

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
        self._history = self._storage.history(self._oid, size=size)
        self._index_by_tid()

    def _index_by_tid(self):
        for record in self._history:
            self._by_tid[record['tid']] = record

    def __getitem__(self, item):
        if self._history is None:
            self._load()
        d = dict(self._history[item])
        if isinstance(d['user_name'], bytes):
            d['user_name'] = d['user_name'].decode('UTF-8', 'replace')
        if isinstance(d['description'], bytes):
            d['description'] = d['description'].decode('UTF-8', 'replace')
        return d

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
        raise KeyError('%r did not exist in or before transaction %r' %
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


@adapter(IConnection)
@implementer(IDatabaseHistory)
class ZodbHistory(object):

    def __init__(self, connection):
        self._connection = connection
        self._storage = IStorageIteration(connection._storage)
        self._tids = cache.getStorageTids(self._storage)
        self._iterators = []

    @property
    def tids(self):
        return tuple(self._tids) # readonlify

    def __len__(self):
        return len(self._tids)

    def _addcleanup(self, it):
        self._iterators.append(it)
        return it

    def cleanup(self):
        for it in self._iterators:
            it.close()
        self._iterators = []

    def __iter__(self):
        return self._addcleanup(self._storage.iterator())

    def __getitem__(self, index):
        if isinstance(index, slice):
            assert index.step is None or index.step == 1
            tids = self._tids[index]
            if not tids:
                return []
            return self._addcleanup(self._storage.iterator(tids[0], tids[-1]))
        else:
            tid = self._tids[index]
            return next(self._addcleanup(self._storage.iterator(tid, tid)))


@adapter(MVCCAdapterInstance)
@implementer(IStorageIteration)
def getIterableStorage(storage):
    return storage._storage
