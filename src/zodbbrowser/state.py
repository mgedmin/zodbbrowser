from BTrees.OOBTree import OOBTree
from persistent import Persistent
from persistent.dict import PersistentDict
from persistent.mapping import PersistentMapping
from zope.component import adapts, getMultiAdapter
from zope.interface import implements, Interface
from zope.proxy import removeAllProxies
from zope.traversing.interfaces import IContainmentRoot
from ZODB.utils import tid_repr, u64

# be compatible with Zope 3.4, but prefer the modern package structure
try:
    from zope.container.folder import Folder
except ImportError:
    from zope.app.folder import Folder # BBB
try:
    from zope.container.sample import SampleContainer
except ImportError:
    from zope.app.container.sample import SampleContainer # BBB
try:
    from zope.container.btree import BTreeContainer
except ImportError:
    from zope.app.container.btree import BTreeContainer # BBB
try:
    from zope.container.ordered import OrderedContainer
except ImportError:
    from zope.app.container.ordered import OrderedContainer # BBB

from zodbbrowser.interfaces import IStateInterpreter
from zodbbrowser.history import ZodbObjectHistory


class LoadedState(object):

    state = None
    tid = None


def _loadState(obj, tid=None):
    """Load (old) state of a Persistent object."""
    # sadly ZODB has no API for get revision at or before tid
    history = ZodbObjectHistory(obj)
    for record in history:
        if tid is None or record['tid'] <= tid:
            result = LoadedState()
            result.state = obj._p_jar.oldstate(obj, record['tid']);
            result.tid = record['tid']
            return result
    raise Exception('%r did not exist in or before transaction %r' %
                    (obj, tid_repr(tid)))


class ZodbObjectState(object):
    implements(IStateInterpreter)

    def __init__(self, obj, tid=None):
        self.obj = removeAllProxies(obj)
        self.tid = None
        self.requestedTid = tid
        self._load()

    def _load(self):
        loadedState = _loadState(self.obj, self.requestedTid)
        self.tid = loadedState.tid
        self.state = getMultiAdapter((self.obj, loadedState.state,
                                      self.requestedTid),
                                     IStateInterpreter)

    def listAttributes(self):
        return self.state.listAttributes()

    def listItems(self):
        return self.state.listItems()

    def getParent(self):
        return self.state.getParent()

    def getName(self):
        return self.state.getName()

    def asDict(self):
        return self.state.asDict()

    # These are not part of IStateInterpreter

    def getObjectId(self):
        return u64(self.obj._p_oid)

    def isRoot(self):
        return IContainmentRoot.providedBy(self.obj)

    def getParentState(self):
        parent = self.getParent()
        if parent is None:
            return None
        else:
            return ZodbObjectState(parent, self.requestedTid)


class GenericState(object):
    """Most persistent objects represent their state as a dict."""
    adapts(Interface, dict, None)
    implements(IStateInterpreter)

    def __init__(self, type, state, tid):
        self.state = state
        self.tid = tid

    def getName(self):
        return self.state.get('__name__', '???')

    def getParent(self):
        parent = self.state.get('__parent__')
        if self.tid and isinstance(parent, Persistent):
            parent.__setstate__(_loadState(parent, self.tid).state)
        return parent

    def listAttributes(self):
        return self.state.items()

    def listItems(self):
        return None

    def asDict(self):
        return self.state


class OOBTreeState(object):
    """Non-empty OOBTrees have a complicated tuple structure."""
    adapts(OOBTree, tuple, None)
    implements(IStateInterpreter)

    def __init__(self, type, state, tid):
        self.btree = OOBTree()
        self.btree.__setstate__(state)
        # Large btrees have more than one bucket; we have to load old states
        # to all of them
        while state and len(state) > 1:
            bucket = state[1]
            state = _loadState(bucket, tid=tid).state
            bucket.__setstate__(state)

    def getName(self):
        return '???'

    def getParent(self):
        return None

    def listAttributes(self):
        return None

    def listItems(self):
        return self.btree.items()

    def asDict(self):
        return self.btree # it's dict-like enough


class EmptyOOBTreeState(OOBTreeState):
    """Empty OOBTrees pickle to None."""
    adapts(OOBTree, type(None), None)
    implements(IStateInterpreter)


class PersistentDictState(GenericState):
    """Convenient access to a persistent dict's items."""
    adapts(PersistentDict, dict, None)

    def listItems(self):
        return sorted(self.state.get('data', {}).items())


class PersistentMappingState(GenericState):
    """Convenient access to a persistent mapping's items."""
    adapts(PersistentMapping, dict, None)

    def listItems(self):
        return sorted(self.state.get('data', {}).items())


class FolderState(GenericState):
    """Convenient access to a Folder's items"""
    adapts(Folder, dict, None)

    def listItems(self):
        data = self.state.get('data')
        if not data:
            return []
        # data will be an OOBTree
        loadedstate = _loadState(data, tid=self.tid).state
        return getMultiAdapter((data, loadedstate, self.tid),
                               IStateInterpreter).listItems()


class SampleContainerState(GenericState):
    """Convenient access to a SampleContainer's items"""
    adapts(SampleContainer, dict, None)

    def listItems(self):
        data = self.state.get('_SampleContainer__data')
        if not data:
            return []
        # data will be a PersistentDict
        loadedstate = _loadState(data, tid=self.tid).state
        return getMultiAdapter((data, loadedstate, self.tid),
                               IStateInterpreter).listItems()


class BTreeContainerState(GenericState):
    """Convenient access to a BTreeContainer's items"""
    adapts(BTreeContainer, dict, None)

    def listItems(self):
        # This is not a typo; BTreeContainer really uses
        # _SampleContainer__data, for BBB
        data = self.state.get('_SampleContainer__data')
        if not data:
            return []
        # data will be an OOBTree
        loadedstate = _loadState(data, tid=self.tid).state
        return getMultiAdapter((data, loadedstate, self.tid),
                               IStateInterpreter).listItems()


class OrderedContainerState(GenericState):
    """Convenient access to an OrderedContainer's items"""
    adapts(OrderedContainer, dict, None)

    def listItems(self):
        container = OrderedContainer()
        container.__setstate__(self.state)
        container._data.__setstate__(_loadState(container._data,
                                               tid=self.tid).state)
        container._order.__setstate__(_loadState(container._order,
                                                tid=self.tid).state)
        return container.items()


class FallbackState(object):
    """Fallback when we've got no idea how to interpret the state"""
    adapts(Interface, Interface, None)
    implements(IStateInterpreter)

    def __init__(self, type, state, tid):
        self.state = state

    def getName(self):
        return '???'

    def getParent(self):
        return None

    def listAttributes(self):
        return [('pickled state', self.state)]

    def listItems(self):
        return None

    def asDict(self):
        return dict(self.listAttributes())
